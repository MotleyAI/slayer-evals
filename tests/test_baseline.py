"""The committed baseline: complete and reproducible from its own files."""

from collections import Counter

from slayer_evals.core import COVERED_ROWS, PITFALLS, PROFILES, RunMetadata, TrialResult
from slayer_evals.report import render_report
from slayer_evals.tasks import load_tasks
from tests.helpers import REPO

BASELINE = REPO / "results" / "baseline"


def baseline_results() -> list[TrialResult]:
    return [TrialResult.model_validate_json(x) for x in (BASELINE / "results.jsonl").read_text().splitlines()]


def test_baseline_report_regenerates():
    assert render_report(BASELINE) == (BASELINE / "report.md").read_text()


def test_baseline_covers_all_tasks_in_all_profiles():
    md = RunMetadata.model_validate_json((BASELINE / "metadata.json").read_text())
    assert md.models == ["claude-opus-5-5"]
    assert md.mode == "repeat"
    assert md.n == 1
    assert tuple(md.profiles) == tuple(PROFILES)
    results = baseline_results()
    tasks = load_tasks(REPO / "tasks")
    per_combo = Counter((r.task_id, r.profile) for r in results)
    assert per_combo == {(t.id, p): 1 for t in tasks for p in PROFILES}
    assert {row for r in results for row in r.covers if row in COVERED_ROWS} == set(COVERED_ROWS)
    assert len(list((BASELINE / "traces").glob("*.json"))) == len(results)


def test_baseline_auto_fails_saved_definitions_in_raw_sql():
    saved = {t.id for t in load_tasks(REPO / "tasks") if t.uses_saved}
    assert saved
    for r in baseline_results():
        assert (r.end_reason == "auto_fail") == (r.task_id in saved and r.profile == "sql+python"), r.task_id


def test_readme_summarises_the_baseline():
    readme = (REPO / "README.md").read_text()
    assert "results/baseline" in readme
    for profile in PROFILES:
        assert f"`{profile}`" in readme, profile
    for suite in ("capability", "combo", "trap", "jaffle"):
        assert suite in readme.lower(), suite


def test_failure_breakdown_by_profile_and_pitfall():
    doc = (REPO / "docs" / "baseline-failures.md").read_text()
    for profile in PROFILES:
        assert profile in doc, profile
    kinds = {c for r in baseline_results() if not r.passed for c in r.covers if c in PITFALLS}
    for kind in kinds:
        assert kind in doc, kind


def test_baseline_covers_the_jaffle_suite():
    jaffle = {t.id for t in load_tasks(REPO / "tasks") if t.dataset == "jaffle"}
    assert len(jaffle) == 24
    results = baseline_results()
    for profile in PROFILES:
        got = {r.task_id for r in results if r.profile == profile and r.dataset == "jaffle"}
        assert got == jaffle, profile
    assert all((r.dataset == "jaffle") == (r.task_id in jaffle) for r in results)


def test_baseline_report_has_the_jaffle_suite():
    report = (BASELINE / "report.md").read_text()
    assert any(line.startswith("| jaffle |") for line in report.splitlines())


def test_failure_breakdown_of_the_jaffle_suite_by_business_rule():
    lines = (REPO / "docs" / "baseline-failures.md").read_text().splitlines()
    start = next(i for i, x in enumerate(lines) if x.startswith("#") and "jaffle" in x.lower())
    level = len(lines[start].split(" ", 1)[0])
    end = next(
        (
            i
            for i in range(start + 1, len(lines))
            if lines[i].startswith("#") and len(lines[i].split(" ", 1)[0]) <= level
        ),
        len(lines),
    )
    section = "\n".join(lines[start:end])
    assert "jaffle-" in section
    failed = {r.task_id for r in baseline_results() if r.dataset == "jaffle" and not r.passed}
    assert [t for t in sorted(failed) if t not in section] == []


def test_readme_documents_the_jaffle_suite():
    readme = (REPO / "README.md").read_text()
    for text in ("--suites jaffle", "business rules", "system prompt", "search", "bench/", "jaffle/"):
        assert text in readme, text
