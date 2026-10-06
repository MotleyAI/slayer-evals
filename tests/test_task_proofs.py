"""Task proofs: every reference SLayer query answers its task, every trap's naive SQL misses it."""

import asyncio
import os
from pathlib import Path

import pytest
from slayer.storage.yaml_storage import YAMLStorage

from slayer_evals.core import Table, Task
from slayer_evals.dataset import BuiltDataset
from slayer_evals.grading import match_tables
from slayer_evals.grading.tables import resolve_column
from slayer_evals.tasks import (
    ProofError,
    ReferenceResult,
    compute_truths,
    load_tasks,
    missing_markers,
    run_naive,
    run_references,
    saved_definitions,
)
from tests.helpers import REPO, make_task

TASKS_DIR = REPO / "tasks"
COUNT_QUERY = {"query": {"source_model": "orders", "measures": [{"formula": "count(*)", "name": "n"}]}}


def reference_problems(task: Task, truth: Table, ref: ReferenceResult) -> list[str]:
    """Why `task`'s reference query does not answer it (empty when it does)."""
    if task.expect == "match":
        if ref.table is None:
            return [f"{task.id}: slayer_query raised {ref.error}"]
        m = match_tables(truth, ref.table, task.compare)
        return [] if m.ok else [f"{task.id}: slayer_query does not match the truth: {m.reason}"]
    got = [ref.error] if task.expect.error is not None else ref.warnings
    if any(k in task.expect.kinds for k in got):
        return []
    return [f"{task.id}: slayer_query produced {got}, expected one of {task.expect.kinds}"]


def naive_problems(task: Task, truth: Table, tables: list[Table]) -> list[str]:
    """Why `task`'s naive SQL is not a live trap (empty when every statement misses the truth)."""
    names = [*task.compare.keys, *task.compare.values] or list(truth.columns)
    problems = []
    for k, table in enumerate(tables, start=1):
        unresolved = [n for n in names if resolve_column(n, table.columns)[0] is None]
        if unresolved:
            problems.append(f"{task.id}: naive_sql #{k} has no column for {', '.join(unresolved)}")
        elif match_tables(truth, table, task.compare).ok:
            problems.append(f"{task.id}: naive_sql #{k} returns the truth (dead trap)")
    return problems


def marker_problems(task: Task) -> list[str]:
    return [f"{task.id}: covers {row} but slayer_query has none of its markers" for row in missing_markers(task)]


# The proof machinery on synthetic tasks.


def no_chdir(*_a, **_k):
    raise AssertionError("proofs must not chdir")


def test_reference_query_returns_its_table(built: BuiltDataset, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # From an unrelated cwd without chdir, the store's trial-relative `bench.duckdb` only resolves if rewritten.
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(os, "chdir", no_chdir)
    task = make_task(
        id="count",
        covers=["Q1"],
        truth_sql="select count(*) as n from orders",
        slayer_query=COUNT_QUERY,
        compare={"values": ["n"]},
    )
    truth = compute_truths([task], built.db_path)["count"]
    ref = run_references([task], built.store_dir, built.db_path)["count"]
    assert ref.error is None
    assert ref.table is not None
    assert ref.table.columns == ["orders.n"]
    assert reference_problems(task, truth, ref) == []


def test_reference_error_kind(built: BuiltDataset):
    query = {
        "query": {
            "source_model": "monthly_rev",
            "time_dimensions": [{"dimension": "order_date", "granularity": "day"}],
            "measures": [{"formula": "sum(rev)", "name": "v"}],
        }
    }
    task = make_task(
        id="q18",
        covers=["Q18"],
        slayer_query=query,
        compare={},
        expect={"error": "TimeDimensionColumnError", "message_any": ["bucketed"]},
    )
    ref = run_references([task], built.store_dir, built.db_path)["q18"]
    assert ref.table is None
    assert ref.error == "TimeDimensionColumnError"
    assert reference_problems(task, Table(columns=[], rows=[]), ref) == []


def test_reference_warning_kinds(built: BuiltDataset):
    query = {
        "query": {
            "source_model": "orders",
            "dimensions": ["status"],
            "measures": [{"formula": "sum(customers.credit)", "name": "v"}],
        }
    }
    task = make_task(
        id="q9",
        covers=["Q9"],
        slayer_query=query,
        compare={},
        expect={"warning": ["broadcast", "associated"], "message_any": ["overlap"]},
    )
    ref = run_references([task], built.store_dir, built.db_path)["q9"]
    assert set(ref.warnings) & {"broadcast", "associated"}
    assert reference_problems(task, Table(columns=[], rows=[]), ref) == []


def test_saved_query_with_refinement(built: BuiltDataset):
    query = {"query": "monthly_rev", "refine": {"dimensions": ["customers.regions.name"]}}
    task = make_task(id="q23", covers=["Q23"], slayer_query=query)
    ref = run_references([task], built.store_dir, built.db_path)["q23"]
    assert ref.error is None
    assert ref.table is not None
    assert ref.table.rows


def test_wrong_reference_query_reported(built: BuiltDataset):
    task = make_task(
        id="off-by-one",
        covers=["Q1"],
        truth_sql="select count(*) + 1 as n from orders",
        slayer_query=COUNT_QUERY,
        compare={"values": ["n"]},
    )
    truth = compute_truths([task], built.db_path)["off-by-one"]
    ref = run_references([task], built.store_dir, built.db_path)["off-by-one"]
    problems = reference_problems(task, truth, ref)
    assert problems
    assert "off-by-one" in problems[0]


async def _datasource_path(store_dir: Path) -> str | None:
    ds = await YAMLStorage(base_dir=str(store_dir)).get_datasource("bench")
    return None if ds is None else ds.database


def test_references_leave_the_store_template_alone(built: BuiltDataset):
    before = asyncio.run(_datasource_path(built.store_dir))
    files_before = sorted(p.relative_to(built.store_dir) for p in built.store_dir.rglob("*"))
    run_references([make_task(id="count", slayer_query=COUNT_QUERY, compare={})], built.store_dir, built.db_path)
    assert asyncio.run(_datasource_path(built.store_dir)) == before
    assert before is not None
    assert not Path(before).is_absolute()
    assert sorted(p.relative_to(built.store_dir) for p in built.store_dir.rglob("*")) == files_before


def test_naive_statements_one_table_each(built: BuiltDataset):
    trap = make_task(
        id="trap",
        covers=["Q6", "fan_out"],
        truth_sql="select count(*) as n from orders",
        naive_sql=["select count(*) as n from orders_flat", "select count(*) - 1 as n from orders"],
        compare={"values": ["n"]},
    )
    tables = run_naive([trap], built.db_path)["trap"]
    assert len(tables) == 2
    assert all(t.columns == ["n"] for t in tables)


def test_naive_string_must_be_one_statement(built: BuiltDataset):
    trap = make_task(
        id="two-in-one", covers=["Q6", "fan_out"], naive_sql="select 1 as n; select 2 as n", compare={"values": ["n"]}
    )
    with pytest.raises(ProofError) as exc:
        run_naive([trap], built.db_path)
    assert "two-in-one" in str(exc.value)


def test_dead_trap_detected(built: BuiltDataset):
    sql = "select count(*) as n from orders"
    trap = make_task(id="dead-trap", covers=["Q6", "fan_out"], truth_sql=sql, naive_sql=sql, compare={"values": ["n"]})
    truth = compute_truths([trap], built.db_path)["dead-trap"]
    problems = naive_problems(trap, truth, run_naive([trap], built.db_path)["dead-trap"])
    assert len(problems) == 1
    assert "dead-trap" in problems[0]


def test_naive_columns_must_resolve(built: BuiltDataset):
    trap = make_task(
        id="renamed",
        covers=["Q6", "fan_out"],
        truth_sql="select count(*) as n from orders",
        naive_sql="select count(*) + 1 as total from orders",
        compare={"values": ["n"]},
    )
    truth = compute_truths([trap], built.db_path)["renamed"]
    problems = naive_problems(trap, truth, run_naive([trap], built.db_path)["renamed"])
    assert problems
    assert problems == ["renamed: naive_sql #1 has no column for n"]


def test_failing_naive_sql_names_the_task(built: BuiltDataset):
    trap = make_task(id="broken-trap", covers=["Q6", "fan_out"], naive_sql="select nope from orders")
    with pytest.raises(ProofError) as exc:
        run_naive([trap], built.db_path)
    assert "broken-trap" in str(exc.value)


def test_mislabelled_cover_detected():
    task = make_task(
        id="mislabelled",
        covers=["Q14"],
        slayer_query={"query": {"source_model": "orders", "measures": [{"formula": "sum(amount)", "name": "v"}]}},
    )
    assert missing_markers(task) == ["Q14"]
    problems = marker_problems(task)
    assert len(problems) == 1
    assert "mislabelled" in problems[0]
    assert "Q14" in problems[0]


def test_markers_found_anywhere_in_the_query():
    query = [
        {
            "name": "ranked",
            "source_model": "orders",
            "dimensions": ["customer_id"],
            "measures": [{"formula": "rank(sum(amount))", "name": "rk"}],
        },
        {"source_model": "ranked", "dimensions": ["customer_id"], "filters": ["rk <= 2"]},
    ]
    assert missing_markers(make_task(id="t", covers=["Q14", "Q8"], slayer_query={"query": query})) == []


def test_saved_definitions(built: BuiltDataset):
    names = saved_definitions(built.store_dir)
    assert "monthly_rev" in names
    assert "aov" in names
    assert "orders" not in names


# The committed task set.


@pytest.fixture(scope="module")
def committed() -> list[Task]:
    return load_tasks(TASKS_DIR)


@pytest.fixture(scope="module")
def truths(committed: list[Task], built: BuiltDataset) -> dict[str, Table]:
    return compute_truths(committed, built.db_path)


def test_reference_query_answers_every_task(committed: list[Task], truths: dict[str, Table], built: BuiltDataset):
    refs = run_references(committed, built.store_dir, built.db_path)
    assert set(refs) == {t.id for t in committed}
    problems = [p for t in committed for p in reference_problems(t, truths[t.id], refs[t.id])]
    assert problems == []


def test_every_trap_is_live(committed: list[Task], truths: dict[str, Table], built: BuiltDataset):
    traps = [t for t in committed if t.suite == "trap"]
    assert traps
    naive = run_naive(traps, built.db_path)
    problems = [p for t in traps for p in naive_problems(t, truths[t.id], naive[t.id])]
    assert problems == []


def test_covered_rows_have_their_markers(committed: list[Task]):
    assert [p for t in committed for p in marker_problems(t)] == []


def test_saved_definitions_exist(committed: list[Task], built: BuiltDataset):
    names = saved_definitions(built.store_dir)
    unknown = [f"{t.id}: {n}" for t in committed for n in t.uses_saved if n not in names]
    assert unknown == []
