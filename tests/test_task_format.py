"""Task YAML loading and validation."""

from pathlib import Path
from typing import Any

import pytest

from slayer_evals.tasks import TaskFormatError, load_task, load_tasks
from tests.helpers import write_task


def _doc(**overrides: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "id": "q4-running-total",
        "row": "Q4",
        "prompt": "Monthly revenue in 2025 with a running total.",
        "truth_sql": "select 1 as month, 2 as rev",
        "capabilities": [{"kind": "call", "fn": "cumsum"}],
    }
    doc.update(overrides)
    return doc


def test_valid_task_loads_with_defaults(tmp_path: Path):
    task = load_task(write_task(tmp_path, _doc()))
    assert task.id == "q4-running-total"
    assert task.row == "Q4"
    assert task.prompt == "Monthly revenue in 2025 with a running total."
    assert task.truth_sql == "select 1 as month, 2 as rev"
    assert task.compare.keys == [] and task.compare.values == []
    assert task.compare.tolerance == 1e-6
    assert task.compare.ordered is False and task.compare.columns_exact is False
    assert task.allow == []
    assert task.expect == "match"
    assert task.xfail is None
    assert len(task.capabilities) == 1


def test_all_fields_load(tmp_path: Path):
    doc = _doc(
        compare={"keys": ["month"], "values": ["rev"], "tolerance": 0.01, "ordered": True, "columns_exact": True},
        allow=[{"construct": "inline_column_sql", "scope": "row_scalar"}],
        expect={"error": "TimeDimensionColumnError", "message_any": ["already bucketed", "month"]},
        xfail={"issue": "DEV-2058", "reason": "no pinned clock"},
    )
    task = load_task(write_task(tmp_path, doc))
    assert task.compare.keys == ["month"] and task.compare.tolerance == 0.01 and task.compare.ordered
    assert task.allow[0].construct == "inline_column_sql" and task.allow[0].scope == "row_scalar"
    assert task.expect != "match"
    assert task.expect.error == "TimeDimensionColumnError"
    assert task.expect.message_any == ["already bucketed", "month"]
    assert task.xfail is not None and task.xfail.issue == "DEV-2058"


def test_warning_expectation(tmp_path: Path):
    task = load_task(write_task(tmp_path, _doc(expect={"warning": "broadcast", "message_any": ["repeat"]})))
    assert task.expect != "match" and task.expect.warning == "broadcast"


@pytest.mark.parametrize(
    "doc, problem",
    [
        (_doc(extra_field=1), "extra_field"),
        ({k: v for k, v in _doc().items() if k != "truth_sql"}, "truth_sql"),
        (_doc(row="Q19"), "Q19"),
        (_doc(row="Q22"), "Q22"),
        (_doc(row="Q99"), "Q99"),
        (_doc(capabilities=[{"kind": "no_such_predicate"}]), "no_such_predicate"),
        (_doc(compare={"keys": ["a"], "bogus": 1}), "bogus"),
    ],
)
def test_malformed_task_rejected(tmp_path: Path, doc: dict[str, Any], problem: str):
    path = write_task(tmp_path, doc, name="bad")
    with pytest.raises(TaskFormatError) as exc:
        load_task(path)
    assert "bad.yaml" in str(exc.value)
    assert problem in str(exc.value)


def test_duplicate_id_rejected(tmp_path: Path):
    write_task(tmp_path, _doc(), name="one")
    write_task(tmp_path, _doc(), name="two")
    with pytest.raises(TaskFormatError) as exc:
        load_tasks(tmp_path)
    assert "q4-running-total" in str(exc.value)
    assert "two.yaml" in str(exc.value) or "one.yaml" in str(exc.value)


def test_load_tasks_recurses_and_skips_truth_dir(tmp_path: Path):
    (tmp_path / "q1").mkdir()
    (tmp_path / "q4").mkdir()
    (tmp_path / "truth").mkdir()
    write_task(tmp_path / "q1", _doc(id="q1-a", row="Q1"))
    write_task(tmp_path / "q4", _doc())
    (tmp_path / "truth" / "q1-a.json").write_text('{"columns": [], "rows": []}')
    tasks = load_tasks(tmp_path)
    assert sorted(t.id for t in tasks) == ["q1-a", "q4-running-total"]
