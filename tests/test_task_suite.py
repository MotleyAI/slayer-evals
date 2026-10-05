"""Suite checks: unit cases for each check, then the checks over the committed task set."""

import pytest

from slayer_evals.core import COVERED_ROWS, Table, Task
from slayer_evals.dataset import BuiltDataset
from slayer_evals.tasks import (
    PROMPT_DENY_LIST,
    check_coverage,
    check_prompts,
    check_snapshots,
    check_truth_sizes,
    compute_truths,
    load_tasks,
)
from tests.helpers import REPO, make_task

TASKS_DIR = REPO / "tasks"
REFUSAL = {"error": "TimeDimensionColumnError", "message_any": ["bucket"]}


def _full_set() -> list[Task]:
    tasks = [make_task(id=f"t-{r}", row=r) for r in COVERED_ROWS]
    tasks.append(make_task(id="t-Q9-warn", row="Q9", expect={"warning": "broadcast", "message_any": ["x"]}))
    tasks.append(make_task(id="t-Q18-err", row="Q18", expect=REFUSAL))
    return tasks


def test_coverage_ok():
    assert check_coverage(_full_set()) == []


def test_coverage_missing_row():
    problems = check_coverage([t for t in _full_set() if t.row != "Q7"])
    assert any("Q7" in p for p in problems)


def test_coverage_needs_refusal_tasks():
    problems = check_coverage([t for t in _full_set() if t.id != "t-Q18-err"])
    assert any("Q18" in p for p in problems)


def test_deny_list_covers_spec_keywords():
    for kw in ("partition_by", "time_shift", "cumsum", "window=", "rank(", "refine", "source_model", "multi-stage"):
        assert kw in PROMPT_DENY_LIST


def test_leaky_prompt_detected():
    leaky = make_task(id="leaky", prompt="Use partition_by to get the region total per city.")
    problems = check_prompts([leaky, make_task(id="clean")])
    assert len(problems) == 1
    assert "leaky" in problems[0] and "partition_by" in problems[0]


def test_truth_size_limit():
    small = Table(columns=["x"], rows=[[i] for i in range(20)])
    big = Table(columns=["x"], rows=[[i] for i in range(21)])
    assert check_truth_sizes({"small": small}) == []
    problems = check_truth_sizes({"small": small, "big": big})
    assert len(problems) == 1 and "big" in problems[0]


# The committed task set.


@pytest.fixture(scope="module")
def committed() -> list[Task]:
    return load_tasks(TASKS_DIR)


def test_committed_coverage(committed: list[Task]):
    assert check_coverage(committed) == []


def test_committed_prompts_neutral(committed: list[Task]):
    assert check_prompts(committed) == []


def test_committed_snapshots_and_sizes(committed: list[Task], built: BuiltDataset):
    truths = compute_truths(committed, built.db_path)
    check_snapshots(truths, TASKS_DIR / "truth")
    assert check_truth_sizes(truths) == []


def test_relative_date_tasks_are_xfail(committed: list[Task]):
    relative = [
        t
        for t in committed
        if any(
            getattr(p, "kind", None) == "time_filter" and getattr(p, "form", None) == "relative" for p in t.capabilities
        )
    ]
    assert relative, "Q20 needs a relative-date task"
    assert all(t.xfail is not None and t.xfail.issue == "DEV-2058" for t in relative)


def test_committed_tasks_have_predicates(committed: list[Task]):
    assert [t.id for t in committed if not t.capabilities] == []
