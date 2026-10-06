"""Suite checks: unit cases for each check, then the checks over the committed task set."""

from collections import Counter
from pathlib import Path

import pytest

from slayer_evals.core import COVERED_ROWS, PITFALLS, Table, Task
from slayer_evals.dataset import BuiltDataset
from slayer_evals.tasks import (
    PROMPT_DENY_LIST,
    ROW_MARKERS,
    check_coverage,
    check_layout,
    check_prompts,
    check_snapshots,
    check_truth_sizes,
    compute_truths,
    load_tasks,
)
from tests.helpers import REPO, make_task, write_task

TASKS_DIR = REPO / "tasks"
REFUSAL = {"error": "TimeDimensionColumnError", "message_any": ["bucket"]}
SUITE_DIRS = {"capability": "capability", "combo": "combo", "trap": "traps"}


def _full_set() -> list[Task]:
    tasks = [make_task(id=f"t-{r}", covers=[r]) for r in COVERED_ROWS]
    tasks.append(make_task(id="t-Q9-warn", covers=["Q9"], expect={"warning": "broadcast", "message_any": ["x"]}))
    tasks.append(make_task(id="t-Q18-err", covers=["Q18"], expect=REFUSAL))
    tasks += [make_task(id=f"trap-{k}", covers=["Q6", PITFALLS[k % len(PITFALLS)]]) for k in range(12)]
    tasks.append(make_task(id="combo-3a", covers=["Q6", "Q12", "Q1"]))
    tasks.append(make_task(id="combo-3b", covers=["Q16", "Q2", "Q4"]))
    return tasks


def test_coverage_ok():
    assert check_coverage(_full_set()) == []


def test_coverage_missing_row():
    problems = check_coverage([t for t in _full_set() if "Q7" not in t.covers])
    assert any("Q7" in p for p in problems)


def test_row_covered_only_by_a_combo_counts():
    tasks = [t for t in _full_set() if t.id != "t-Q12"]
    assert check_coverage(tasks) == []


def test_coverage_needs_refusal_tasks():
    problems = check_coverage([t for t in _full_set() if t.id != "t-Q18-err"])
    assert any("Q18" in p for p in problems)


def test_coverage_needs_twelve_traps():
    problems = check_coverage([t for t in _full_set() if t.id != "trap-0"])
    assert any("trap" in p for p in problems)


def test_coverage_needs_two_three_row_tasks():
    problems = check_coverage([t for t in _full_set() if t.id != "combo-3b"])
    assert any("three" in p or "3" in p for p in problems)


def test_deny_list_covers_spec_keywords():
    spec = (
        "partition_by",
        "time_shift",
        "cumsum",
        "window=",
        "rank(",
        "refine",
        "source_model",
        "multi-stage",
        "join",
        "duplicate",
        "double count",
        "fan-out",
        "chasm",
        "null",
        "not in",
        "counted once",
        "count each",
    )
    for kw in spec:
        assert kw in PROMPT_DENY_LIST, kw


def test_leaky_prompt_detected():
    leaky = make_task(id="leaky", prompt="Use partition_by to get the region total per city.")
    problems = check_prompts([leaky, make_task(id="clean")])
    assert len(problems) == 1
    assert "leaky" in problems[0]
    assert "partition_by" in problems[0]


@pytest.mark.parametrize(
    "prompt, keyword",
    [
        ("Join orders to customers and sum the amounts.", "join"),
        ("Revenue per region, ignoring NULL regions.", "null"),
        ("Count each customer once per region.", "count each"),
        ("Customers whose id is NOT IN the returns list.", "not in"),
        ("Watch out for the chasm between orders and returns.", "chasm"),
        ("Make sure nothing is counted once too often.", "counted once"),
        ("Rank(revenue) per region.", "rank("),
    ],
)
def test_pitfall_hints_detected(prompt: str, keyword: str):
    problems = check_prompts([make_task(id="hinty", prompt=prompt)])
    assert any("hinty" in p and keyword in p for p in problems), problems


@pytest.mark.parametrize(
    "prompt",
    [
        "Revenue of the adjoining regions.",
        "Revenue per region, nullified orders included.",
        "Revenue for orders not included in a campaign.",
        "Customers of Frank's shop, ranked by name.",
        "Revenue of each customer, counting returns.",
    ],
)
def test_embedded_words_pass(prompt: str):
    assert check_prompts([make_task(id="clean", prompt=prompt)]) == []


def test_truth_size_limit():
    small = Table(columns=["x"], rows=[[i] for i in range(20)])
    big = Table(columns=["x"], rows=[[i] for i in range(21)])
    assert check_truth_sizes({"small": small}) == []
    problems = check_truth_sizes({"small": small, "big": big})
    assert len(problems) == 1
    assert "big" in problems[0]


def _layout(tmp_path: Path, placements: dict[str, tuple[str, list[str]]]) -> Path:
    for tid, (folder, covers) in placements.items():
        d = tmp_path / folder / tid
        d.mkdir(parents=True)
        doc = make_task(id=tid, covers=covers).model_dump(exclude_none=True, exclude_defaults=True)
        write_task(d, {"id": tid, **doc})
    return tmp_path


def test_layout_ok(tmp_path: Path):
    root = _layout(
        tmp_path,
        {"a": ("capability", ["Q4"]), "b": ("combo", ["Q2", "Q4"]), "c": ("traps", ["Q6", "fan_out"])},
    )
    assert check_layout(root) == []


def test_misplaced_file(tmp_path: Path):
    root = _layout(tmp_path, {"a": ("capability", ["Q4"]), "c": ("combo", ["Q6", "fan_out"])})
    problems = check_layout(root)
    assert len(problems) == 1
    assert "c.yaml" in problems[0]


def test_task_outside_a_suite_folder(tmp_path: Path):
    root = _layout(tmp_path, {"a": ("q04", ["Q4"])})
    assert any("a.yaml" in p for p in check_layout(root))


def test_row_markers():
    assert "partition_by" in ROW_MARKERS["Q2"]
    assert "partition_by" in ROW_MARKERS["Q3"]
    assert {"time_shift", "cumsum", "change"} <= set(ROW_MARKERS["Q4"])
    assert "window=" in ROW_MARKERS["Q11"]
    assert "rank(" in ROW_MARKERS["Q14"]
    assert set(ROW_MARKERS) <= set(COVERED_ROWS)
    for row in ("Q8", "Q9", "Q10", "Q18", "Q25"):
        assert not ROW_MARKERS.get(row), row


# The committed task set.

COMBOS = [
    {"Q2", "Q4"},
    {"Q14", "Q2"},
    {"Q5", "Q2"},
    {"Q17", "Q4"},
    {"Q6", "Q14"},
    {"Q21", "Q2"},
    {"Q23", "Q4"},
    {"Q13", "Q4"},
    {"Q6", "Q12", "Q1"},
    {"Q24", "Q2", "Q20"},
    {"Q16", "Q2", "Q4"},
]
TRAPS = Counter(
    {
        "fan_out": 2,
        "count_after_join": 1,
        "chasm": 1,
        "bridge": 1,
        "non_unique_key": 1,
        "outer_join_filter": 1,
        "not_in_null": 1,
        "count_outer_join": 1,
        "filtered_total": 1,
        "distinct_reagg": 1,
        "missing_periods": 1,
        "filter_before_window": 2,
        "rows_window_gap": 1,
        "timestamp_bounds": 1,
        "avg_of_avgs": 1,
    }
)


@pytest.fixture(scope="module")
def committed() -> list[Task]:
    return load_tasks(TASKS_DIR)


def test_committed_coverage(committed: list[Task]):
    assert check_coverage(committed) == []


def test_committed_layout():
    assert check_layout(TASKS_DIR) == []


def test_committed_prompts_neutral(committed: list[Task]):
    assert check_prompts(committed) == []


def test_committed_snapshots_and_sizes(committed: list[Task], built: BuiltDataset):
    truths = compute_truths(committed, built.db_path)
    check_snapshots(truths, TASKS_DIR / "truth")
    assert check_truth_sizes(truths) == []


def test_relative_date_task_is_xfail(committed: list[Task]):
    relative = [t for t in committed if "Q20" in t.covers and t.suite == "capability" and t.xfail is not None]
    assert relative, "Q20 needs a relative-date task"
    assert all(t.xfail is not None and t.xfail.issue == "DEV-2058" for t in relative)


def test_committed_capability_tasks_kept(committed: list[Task]):
    capability = {t.id for t in committed if t.suite == "capability"}
    assert len(capability) >= 25
    for tid in ("q1-region-total", "q4-running-total", "q18-day-of-monthly", "q23-monthly-by-region"):
        assert tid in capability


def test_committed_saved_definition_tasks(committed: list[Task]):
    by_id = {t.id: t for t in committed}
    assert by_id["q18-day-of-monthly"].uses_saved == ["monthly_rev"]
    assert by_id["q23-monthly-by-region"].uses_saved == ["monthly_rev"]


def test_committed_combo_catalogue(committed: list[Task]):
    combos = [t for t in committed if t.suite == "combo"]
    found = [set(t.covers) for t in combos]
    for want in COMBOS:
        assert want in found, sorted(want)
    assert sum(len(t.covers) >= 3 for t in combos) >= 3
    q23 = next(t for t in combos if set(t.covers) == {"Q23", "Q4"})
    assert q23.uses_saved


def test_committed_trap_catalogue(committed: list[Task]):
    traps = [t for t in committed if t.suite == "trap"]
    assert len(traps) >= 17
    kinds = Counter(c for t in traps for c in t.covers if c in PITFALLS)
    for kind, n in TRAPS.items():
        assert kinds[kind] >= n, kind
    assert all(t.naive_sql for t in traps)
