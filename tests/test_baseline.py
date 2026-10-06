"""The committed baseline: complete and reproducible from its own files."""

from slayer_evals.core import COVERED_ROWS, RunMetadata, TrialResult
from slayer_evals.report import render_report
from slayer_evals.tasks import load_tasks
from tests.helpers import REPO

BASELINE = REPO / "results" / "baseline"


def test_baseline_report_regenerates():
    assert render_report(BASELINE) == (BASELINE / "report.md").read_text()


def test_baseline_covers_all_tasks_both_profiles():
    md = RunMetadata.model_validate_json((BASELINE / "metadata.json").read_text())
    assert md.models == ["claude-opus-5-5"]
    assert md.n == 1
    assert sorted(md.profiles) == ["slayer", "slayer+python"]
    results = [TrialResult.model_validate_json(x) for x in (BASELINE / "results.jsonl").read_text().splitlines()]
    task_ids = {t.id for t in load_tasks(REPO / "tasks")}
    for profile in ("slayer", "slayer+python"):
        assert {r.task_id for r in results if r.profile == profile} == task_ids
    assert {r.row for r in results} == set(COVERED_ROWS)
    assert len(list((BASELINE / "traces").glob("*.json"))) == len(results)


def test_readme_links_baseline():
    readme = (REPO / "README.md").read_text()
    assert "results/baseline" in readme
    assert "single-trial" in readme.lower()
