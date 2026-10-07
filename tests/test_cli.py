"""CLI: build, truth, run (auth refusal, interruption), report."""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

from slayer_evals.cli import main
from slayer_evals.core import Table, TrialResult
from slayer_evals.dataset import DB_FILE, STORE_DIR, BuiltDataset
from slayer_evals.tasks import write_snapshots
from tests.fake_agents import STATE_ENV
from tests.helpers import REPO, write_task

FAKE = "tests.fake_agents:ScriptedAgent"
SLAYER_QUERY = {"query": {"source_model": "orders", "measures": [{"formula": "sum(amount)", "name": "v"}]}}


def test_build(tmp_path: Path):
    out = tmp_path / "data"
    assert main(["build", "--out", str(out)]) == 0
    for name in (DB_FILE, STORE_DIR):
        assert (out / name).exists()


def _tasks(tmp_path: Path) -> Path:
    d = tmp_path / "tasks"
    d.mkdir()
    write_task(
        d,
        {
            "id": "a",
            "covers": ["Q1"],
            "prompt": "ANSWER 7",
            "truth_sql": "select 7.0 as v",
            "slayer_query": SLAYER_QUERY,
            "compare": {"values": ["v"]},
        },
    )
    return d


def test_truth_write_then_check(tmp_path: Path, built: BuiltDataset):
    td = _tasks(tmp_path)
    args = ["--tasks-dir", str(td), "--dataset-dir", str(built.dir)]
    assert main(["truth", "--write", *args]) == 0
    assert (td / "truth" / "a.json").exists()
    assert main(["truth", *args]) == 0
    write_snapshots({"a": Table(columns=["v"], rows=[[8.0]])}, td / "truth")
    assert main(["truth", *args]) != 0


def test_run_without_auth_mode(tmp_path: Path, built: BuiltDataset, capsys: pytest.CaptureFixture[str]):
    td = _tasks(tmp_path)
    code = main(
        [
            "run",
            "--tasks-dir",
            str(td),
            "--dataset-dir",
            str(built.dir),
            "--out",
            str(tmp_path / "runs"),
            "--agent",
            FAKE,
        ]
    )
    assert code != 0
    err = capsys.readouterr().err
    assert "--subscription-auth" in err
    assert "--api-key-auth" in err
    assert not (tmp_path / "runs").exists() or not any((tmp_path / "runs").iterdir())


def test_run_missing_credential(
    tmp_path: Path, built: BuiltDataset, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    td = _tasks(tmp_path)
    code = main(
        [
            "run",
            "--subscription-auth",
            "--tasks-dir",
            str(td),
            "--dataset-dir",
            str(built.dir),
            "--out",
            str(tmp_path / "runs"),
            "--agent",
            FAKE,
        ]
    )
    assert code != 0
    assert "CLAUDE_CODE_OAUTH_TOKEN" in capsys.readouterr().err


def test_interrupted_run_keeps_results(tmp_path: Path, built: BuiltDataset):
    d = tmp_path / "tasks"
    d.mkdir()
    write_task(
        d,
        {
            "id": "a-fast",
            "covers": ["Q1"],
            "prompt": "ANSWER 7",
            "truth_sql": "select 7.0 as v",
            "slayer_query": SLAYER_QUERY,
            "compare": {"values": ["v"]},
        },
    )
    write_task(
        d,
        {
            "id": "b-slow",
            "covers": ["Q4"],
            "prompt": "SLEEP 120\nANSWER 7",
            "truth_sql": "select 7.0 as v",
            "slayer_query": SLAYER_QUERY,
            "compare": {"values": ["v"]},
        },
    )
    env_file = tmp_path / ".env"
    env_file.write_text("ANTHROPIC_API_KEY=sk-ant-api-test\n")
    out = tmp_path / "runs"
    env = {**os.environ, STATE_ENV: str(tmp_path / "state"), "PYTHONPATH": str(REPO)}
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "slayer_evals.cli",
            "run",
            "--api-key-auth",
            "--env-file",
            str(env_file),
            "--tasks-dir",
            str(d),
            "--dataset-dir",
            str(built.dir),
            "--out",
            str(out),
            "--agent",
            FAKE,
            "--profiles",
            "slayer",
            "--concurrency",
            "1",
        ],
        env=env,
        cwd=REPO,
    )
    try:
        deadline = time.monotonic() + 120
        results: list[Path] = []
        while time.monotonic() < deadline:
            results = list(out.glob("*/results.jsonl"))
            if results and results[0].read_text().strip():
                break
            assert proc.poll() is None, "run exited early"
            time.sleep(0.5)
        assert results, "no results line before the deadline"
    finally:
        proc.kill()
        proc.wait()
    lines = results[0].read_text().splitlines()
    assert [TrialResult.model_validate_json(x).task_id for x in lines] == ["a-fast"]


def test_run_raw_sql_profile(tmp_path: Path, built: BuiltDataset, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(STATE_ENV, str(tmp_path / "state"))
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join([str(REPO), os.environ.get("PYTHONPATH", "")]))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-api-test")
    td = _tasks(tmp_path)
    out = tmp_path / "runs"
    args = ["run", "--api-key-auth", "--tasks-dir", str(td), "--dataset-dir", str(built.dir), "--out", str(out)]
    assert main([*args, "--agent", FAKE, "--profiles", "sql+python"]) == 0
    (results,) = out.glob("*/results.jsonl")
    assert [TrialResult.model_validate_json(x).profile for x in results.read_text().splitlines()] == ["sql+python"]


def test_run_help_mentions_covered_rows(capsys: pytest.CaptureFixture[str]):
    with pytest.raises(SystemExit):
        main(["run", "--help"])
    help_text = " ".join(capsys.readouterr().out.split())
    assert "sql+python" in help_text
    assert "cover" in help_text.lower()


def test_report_command(tmp_path: Path):
    src = REPO / "tests" / "fixtures" / "run_repeat"
    run_dir = tmp_path / "run"
    shutil.copytree(src, run_dir)
    (run_dir / "report.md").unlink(missing_ok=True)
    assert main(["report", str(run_dir)]) == 0
    assert (run_dir / "report.md").read_text().strip()
