"""Live smoke test: one Q1 task in each of the three profiles through the real SDK and SLayer."""

import os
from pathlib import Path

import pytest

from slayer_evals.core import RunMetadata, TrialResult
from slayer_evals.runner import RunConfig, run_benchmark
from slayer_evals.tasks import load_tasks
from tests.helpers import REPO

pytestmark = pytest.mark.integration

ENV_FILE = Path(os.environ.get("SLAYER_EVALS_ENV_FILE", "/home/james/GitHub/SLayer/.env.agents"))


def test_q1_every_profile(tmp_path: Path):
    q1 = min(t.id for t in load_tasks(REPO / "tasks") if t.covers == ["Q1"])
    cfg = RunConfig(
        task_ids=[q1], auth_mode="subscription", env_file=ENV_FILE, out_dir=tmp_path / "runs", tasks_dir=REPO / "tasks"
    )
    run_dir = run_benchmark(cfg)
    RunMetadata.model_validate_json((run_dir / "metadata.json").read_text())
    results = [TrialResult.model_validate_json(x) for x in (run_dir / "results.jsonl").read_text().splitlines()]
    assert sorted(r.profile for r in results) == ["slayer", "slayer+python", "sql+python"]
    for r in results:
        assert r.verdict is not None
        trace = run_dir / "traces" / f"{r.task_id}__{r.profile}__{r.model}__{r.trial}.json"
        assert trace.exists()
    assert (run_dir / "report.md").exists()
