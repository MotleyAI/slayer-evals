"""Truth tables from each task's `truth_sql`, and the committed truth snapshots."""

import datetime as dt
import decimal
import math
import uuid
from pathlib import Path
from typing import Any

import duckdb

from slayer_evals.core import Table, Task

SNAPSHOT_REL_TOL = 1e-9


class TruthError(RuntimeError):
    pass


class SnapshotDriftError(AssertionError):
    pass


def json_value(v: Any) -> Any:
    if isinstance(v, float) and math.isnan(v):
        return None
    if isinstance(v, decimal.Decimal):
        return float(v)
    if isinstance(v, (dt.date, dt.time)):
        return v.isoformat()
    if isinstance(v, (uuid.UUID, dt.timedelta)):
        return str(v)
    return v


def _sort_key(row: list[Any]) -> list[tuple[int, Any]]:
    return [(0, "") if v is None else (1, v) if isinstance(v, (int, float)) else (2, str(v)) for v in row]


def _run(con: duckdb.DuckDBPyConnection, task: Task) -> Table:
    try:
        cur = con.execute(task.truth_sql)
        columns = [d[0] for d in cur.description or []]
        rows = [[json_value(v) for v in r] for r in cur.fetchall()]
    except duckdb.Error as exc:
        raise TruthError(f"task {task.id}: truth_sql failed: {exc}") from exc
    if not task.compare.ordered:
        rows.sort(key=_sort_key)
    return Table(columns=columns, rows=rows)


def _same_value(a: Any, b: Any) -> bool:
    if isinstance(a, float) and isinstance(b, (int, float)) or isinstance(b, float) and isinstance(a, (int, float)):
        return math.isclose(a, b, rel_tol=SNAPSHOT_REL_TOL, abs_tol=SNAPSHOT_REL_TOL)
    return a == b


def same_table(a: Table, b: Table) -> bool:
    """Equal columns and rows, floats within a relative 1e-9 (parallel sums differ in the last bits)."""
    if a.columns != b.columns or len(a.rows) != len(b.rows):
        return False
    return all(
        len(x) == len(y) and all(_same_value(u, v) for u, v in zip(x, y, strict=True))
        for x, y in zip(a.rows, b.rows, strict=True)
    )


def compute_truth(task: Task, db_path: Path) -> Table:
    return compute_truths([task], db_path)[task.id]


def compute_truths(tasks: list[Task], db_path: Path) -> dict[str, Table]:
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        return {t.id: _run(con, t) for t in tasks}
    finally:
        con.close()


def write_snapshots(truths: dict[str, Table], snapshot_dir: Path) -> None:
    """Write one `<id>.json` per truth and remove snapshots of tasks that no longer exist."""
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    for stale in snapshot_dir.glob("*.json"):
        if stale.stem not in truths:
            stale.unlink()
    for task_id, table in sorted(truths.items()):
        (snapshot_dir / f"{task_id}.json").write_text(table.model_dump_json(indent=1) + "\n")


def load_snapshots(snapshot_dir: Path) -> dict[str, Table]:
    return {p.stem: Table.model_validate_json(p.read_text()) for p in sorted(snapshot_dir.glob("*.json"))}


def check_snapshots(truths: dict[str, Table], snapshot_dir: Path) -> None:
    """Fail naming every task whose regenerated truth differs from, lacks, or outlives its snapshot."""
    committed = load_snapshots(snapshot_dir) if snapshot_dir.is_dir() else {}
    problems = [f"{tid}: no snapshot" for tid in sorted(set(truths) - set(committed))]
    problems += [f"{tid}: stale snapshot (no such task)" for tid in sorted(set(committed) - set(truths))]
    problems += [
        f"{tid}: truth differs from its snapshot"
        for tid in sorted(set(truths) & set(committed))
        if not same_table(Table.model_validate_json(truths[tid].model_dump_json()), committed[tid])
    ]
    if problems:
        raise SnapshotDriftError(
            "truth snapshots out of date (regenerate with `truth --write`): " + "; ".join(problems)
        )
