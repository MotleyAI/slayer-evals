"""Task proofs: run each task's reference SLayer query and each trap's naive SQL on the built dataset."""

import asyncio
import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

import duckdb
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import TextContent
from pydantic import BaseModel, Field
from slayer.mcp.server import create_mcp_server
from slayer.sql.engine_factory import invalidate_engine
from slayer.storage.yaml_storage import YAMLStorage

from slayer_evals.core import ParsedResult, Table, Task
from slayer_evals.tasks.suite import ROW_MARKERS
from slayer_evals.tasks.truth import json_value

DATASOURCE = "bench"
_ERROR_RE = re.compile(r"Error executing tool [\w.-]+: ([A-Za-z_][\w.]*):")


class ProofError(RuntimeError):
    pass


class ReferenceResult(BaseModel):
    """A reference query's table, or the error class it raised; plus its warning kinds."""

    table: Table | None = None
    error: str | None = None
    warnings: list[str] = Field(default_factory=list)


def _error_kind(exc: ToolError) -> str:
    if exc.__cause__ is not None:
        return type(exc.__cause__).__name__
    m = _ERROR_RE.search(str(exc))
    return m.group(1).rsplit(".", 1)[-1] if m else type(exc).__name__


async def _references(tasks: list[Task], store_dir: Path, db_path: Path) -> dict[str, ReferenceResult]:
    with tempfile.TemporaryDirectory(prefix="slayer-evals-proof-") as tmp:
        store = Path(tmp) / "store"
        shutil.copytree(store_dir, store)
        storage = YAMLStorage(base_dir=str(store))
        ds = await storage.get_datasource(DATASOURCE)
        if ds is None:
            raise ProofError(f"{store_dir} has no datasource {DATASOURCE!r}")
        # The template holds the trial-relative database file; point the copy at the built one.
        absolute = ds.model_copy(update={"database": str(db_path.resolve())})
        await storage.save_datasource(absolute)
        server = create_mcp_server(storage=storage, _seed_help=False)
        try:
            return {task.id: await _reference(server, task) for task in tasks}
        finally:
            # SLayer caches database engines per process; a lingering one blocks later read-only opens of the file.
            invalidate_engine(absolute)


async def _reference(server: Any, task: Task) -> ReferenceResult:
    try:
        content, _ = await server.call_tool("query", {**task.slayer_query, "format": "json"})
    except ToolError as exc:
        return ReferenceResult(error=_error_kind(exc))
    text = "\n".join(c.text for c in content if isinstance(c, TextContent))
    parsed = ParsedResult.from_text(text)
    if parsed is None:
        raise ProofError(f"task {task.id}: slayer_query returned no table: {text[:200]}")
    return ReferenceResult(
        table=Table(columns=parsed.columns, rows=parsed.rows), warnings=[w.kind for w in parsed.warnings]
    )


def run_references(tasks: list[Task], store_dir: Path, db_path: Path) -> dict[str, ReferenceResult]:
    """Each task's `slayer_query` through SLayer's `query` tool, in process, on a copy of the store template."""
    return asyncio.run(_references(tasks, store_dir, db_path))


def _statements(task: Task) -> list[str]:
    naive = task.naive_sql
    return [] if naive is None else [naive] if isinstance(naive, str) else list(naive)


def run_naive(tasks: list[Task], db_path: Path) -> dict[str, list[Table]]:
    """One table per `naive_sql` statement of each task; fails naming the task if one does not run."""
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        out: dict[str, list[Table]] = {}
        for task in tasks:
            tables = []
            for k, sql in enumerate(_statements(task), start=1):
                try:
                    if len(con.extract_statements(sql)) != 1:
                        raise ProofError(f"task {task.id}: naive_sql #{k} must be exactly one statement")
                    cur = con.execute(sql)
                    columns = [d[0] for d in cur.description or []]
                    rows = [[json_value(v) for v in r] for r in cur.fetchall()]
                except duckdb.Error as exc:
                    raise ProofError(f"task {task.id}: naive_sql #{k} failed: {exc}") from exc
                tables.append(Table(columns=columns, rows=rows))
            out[task.id] = tables
        return out
    finally:
        con.close()


def missing_markers(task: Task) -> list[str]:
    """The covered rows with DSL markers none of which appears in the task's `slayer_query`."""
    text = re.sub(r"\s+", "", json.dumps(task.slayer_query))
    return [r for r in task.rows if ROW_MARKERS.get(r) and not any(m in text for m in ROW_MARKERS[r])]


async def _saved(store_dir: Path) -> set[str]:
    storage = YAMLStorage(base_dir=str(store_dir))
    names: set[str] = set()
    for name in await storage.list_models(data_source=DATASOURCE):
        model = await storage.get_model(name, data_source=DATASOURCE)
        if model is None:
            continue
        if model.source_queries:
            names.add(model.name)
        names |= {m.name for m in model.measures if m.name}
    return names


def saved_definitions(store_dir: Path) -> set[str]:
    """Names of the store template's saved queries (query-backed models) and saved measures."""
    return asyncio.run(_saved(store_dir))
