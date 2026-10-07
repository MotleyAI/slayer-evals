"""Task YAML loading and validation."""

from pathlib import Path
from typing import Any

import pytest

from slayer_evals.tasks import TaskFormatError, load_task, load_tasks
from tests.helpers import make_task, write_task

SLAYER_QUERY = {
    "query": {
        "source_model": "orders",
        "time_dimensions": [{"dimension": "order_date", "granularity": "month"}],
        "measures": [{"formula": "cumsum(sum(amount))", "name": "running_total"}],
    }
}


def _doc(**overrides: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "id": "q4-running-total",
        "covers": ["Q4"],
        "prompt": "Monthly revenue in 2025 with a running total.",
        "truth_sql": "select 1 as month, 2 as rev",
        "slayer_query": SLAYER_QUERY,
    }
    doc.update(overrides)
    return doc


def _trap(**overrides: Any) -> dict[str, Any]:
    trap: dict[str, Any] = {
        "id": "t-chasm",
        "covers": ["Q6", "chasm"],
        "naive_sql": "select region, sum(amount) as revenue from orders_flat join returns using (customer_id) group by 1",
    }
    return _doc(**{**trap, **overrides})


def test_valid_task_loads_with_defaults(tmp_path: Path):
    task = load_task(write_task(tmp_path, _doc()))
    assert task.id == "q4-running-total"
    assert task.covers == ["Q4"]
    assert task.prompt == "Monthly revenue in 2025 with a running total."
    assert task.truth_sql == "select 1 as month, 2 as rev"
    assert task.slayer_query == SLAYER_QUERY
    assert task.compare.keys == []
    assert task.compare.values == []
    assert task.compare.tolerance == 1e-6
    assert task.compare.ordered is False
    assert task.compare.columns_exact is False
    assert task.compare.null_as_zero is False
    assert task.expect == "match"
    assert task.naive_sql is None
    assert task.uses_saved == []
    assert task.xfail is None


def test_all_fields_load(tmp_path: Path):
    doc = _doc(
        compare={
            "keys": ["month"],
            "values": ["rev"],
            "tolerance": 0.01,
            "ordered": True,
            "columns_exact": True,
            "null_as_zero": True,
        },
        expect={"error": "TimeDimensionColumnError", "message_any": ["already bucketed", "month"]},
        uses_saved=["monthly_rev"],
        xfail={"issue": "DEV-2058", "reason": "no pinned clock"},
    )
    task = load_task(write_task(tmp_path, doc))
    assert task.compare.keys == ["month"]
    assert task.compare.tolerance == 0.01
    assert task.compare.ordered
    assert task.compare.null_as_zero
    assert task.expect != "match"
    assert task.expect.error == "TimeDimensionColumnError"
    assert task.expect.message_any == ["already bucketed", "month"]
    assert task.uses_saved == ["monthly_rev"]
    assert task.xfail is not None
    assert task.xfail.issue == "DEV-2058"


def test_saved_query_reference_loads(tmp_path: Path):
    ref = {"query": "monthly_rev", "refine": {"dimensions": ["customers.regions.name"]}}
    task = load_task(write_task(tmp_path, _doc(covers=["Q23"], slayer_query=ref)))
    assert task.slayer_query == ref


def test_trap_loads_with_one_or_many_naive_statements(tmp_path: Path):
    one = load_task(write_task(tmp_path, _trap(), name="one"))
    assert one.covers == ["Q6", "chasm"]
    assert isinstance(one.naive_sql, str)
    many = load_task(write_task(tmp_path, _trap(naive_sql=["select 1 as revenue", "select 2 as revenue"]), name="two"))
    assert many.naive_sql == ["select 1 as revenue", "select 2 as revenue"]


def test_warning_expectation(tmp_path: Path):
    task = load_task(write_task(tmp_path, _doc(expect={"warning": "broadcast", "message_any": ["repeat"]})))
    assert task.expect != "match"
    assert task.expect.warning == "broadcast"


@pytest.mark.parametrize(
    "doc, problem",
    [
        (_doc(extra_field=1), "extra_field"),
        (_doc(row="Q4"), "row"),
        ({k: v for k, v in _doc().items() if k != "id"}, "id"),
        ({k: v for k, v in _doc().items() if k != "prompt"}, "prompt"),
        ({k: v for k, v in _doc().items() if k != "truth_sql"}, "truth_sql"),
        ({k: v for k, v in _doc().items() if k != "slayer_query"}, "slayer_query"),
        ({k: v for k, v in _doc().items() if k != "covers"}, "covers"),
        (_doc(covers=[]), "covers"),
        (_doc(covers=["Q19"]), "Q19"),
        (_doc(covers=["Q22"]), "Q22"),
        (_doc(covers=["Q4", "Q22"]), "Q22"),
        (_doc(covers=["Q99"]), "Q99"),
        (_doc(covers=["Q4", "Q4"]), "Q4"),
        (_trap(covers=["Q6", "chasm", "chasm"]), "chasm"),
        (_trap(covers=["chasm"]), "covers"),
        (_trap(covers=["fan_out", "chasm"]), "covers"),
        (_trap(covers=["Q6", "chasm_trap"]), "chasm_trap"),
        (_doc(capabilities=[{"kind": "call", "fn": "sum"}]), "capabilities"),
        (_doc(compare={"keys": ["a"], "bogus": 1}), "bogus"),
    ],
)
def test_malformed_task_rejected(tmp_path: Path, doc: dict[str, Any], problem: str):
    path = write_task(tmp_path, doc, name="bad")
    with pytest.raises(TaskFormatError) as exc:
        load_task(path)
    assert "bad.yaml" in str(exc.value)
    assert problem in str(exc.value)


@pytest.mark.parametrize(
    "doc",
    [
        {k: v for k, v in _trap().items() if k != "naive_sql"},
        _doc(naive_sql="select 1 as rev"),
        _doc(covers=["Q2", "Q4"], naive_sql=["select 1 as rev"]),
    ],
    ids=["trap-without-naive-sql", "capability-with-naive-sql", "combo-with-naive-sql"],
)
def test_naive_sql_tied_to_traps(tmp_path: Path, doc: dict[str, Any]):
    path = write_task(tmp_path, doc, name="bad")
    with pytest.raises(TaskFormatError) as exc:
        load_task(path)
    assert "bad.yaml" in str(exc.value)
    assert "naive_sql" in str(exc.value)


def test_duplicate_id_rejected(tmp_path: Path):
    write_task(tmp_path, _doc(), name="one")
    write_task(tmp_path, _doc(), name="two")
    with pytest.raises(TaskFormatError) as exc:
        load_tasks(tmp_path)
    assert "q4-running-total" in str(exc.value)
    assert "two.yaml" in str(exc.value) or "one.yaml" in str(exc.value)


def test_load_tasks_recurses_and_skips_truth_dir(tmp_path: Path):
    (tmp_path / "capability" / "q01").mkdir(parents=True)
    (tmp_path / "traps").mkdir()
    (tmp_path / "truth").mkdir()
    write_task(tmp_path / "capability" / "q01", _doc(id="q1-a", covers=["Q1"]))
    write_task(tmp_path / "traps", _trap())
    (tmp_path / "truth" / "q1-a.json").write_text('{"columns": [], "rows": []}')
    tasks = load_tasks(tmp_path)
    assert sorted(t.id for t in tasks) == ["q1-a", "t-chasm"]


def test_expectation_kind_list(tmp_path: Path):
    task = load_task(write_task(tmp_path, _doc(expect={"warning": ["broadcast", "associated"], "message_any": ["x"]})))
    assert task.expect != "match"
    assert task.expect.kinds == ["broadcast", "associated"]


@pytest.mark.parametrize(
    "covers, suite",
    [
        (["Q4"], "capability"),
        (["Q2", "Q4"], "combo"),
        (["Q6", "Q12", "Q1"], "combo"),
        (["Q6", "fan_out"], "trap"),
        (["Q6", "Q2", "chasm"], "trap"),
    ],
)
def test_suite_derivation(covers: list[str], suite: str):
    assert make_task(id="t", covers=covers).suite == suite


def test_suite_is_not_stored(tmp_path: Path):
    path = write_task(tmp_path, _doc(suite="capability"), name="bad")
    with pytest.raises(TaskFormatError) as exc:
        load_task(path)
    assert "suite" in str(exc.value)
    assert "suite" not in make_task().model_dump()
