"""Runner: selection, run modes, isolation, blind agents, SLayer override, run output."""

import json
import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import claude_agent_sdk
import duckdb
import pytest
from pydantic import ValidationError

import slayer_evals.runner.run as run_module
from slayer_evals.core import RunMetadata, TrialResult
from slayer_evals.dataset import BuiltDataset
from slayer_evals.runner import AuthError, RunConfig, run_benchmark, select_tasks
from tests.fake_agents import SLEEPER_PID, STATE_ENV, TRANSCRIPT_TAG, recorded_runs
from tests.helpers import REPO, make_task, write_task

FAKE = "tests.fake_agents:ScriptedAgent"
ENV = {"ANTHROPIC_API_KEY": "sk-ant-api-test"}
SECRET_SQL = "select 7.0 as v -- secret truth marker"


def task_doc(tid: str, row: str, prompt: str, truth: str = "select 7.0 as v", **kw: Any) -> dict[str, Any]:
    return {
        "id": tid,
        "row": row,
        "prompt": prompt,
        "truth_sql": truth,
        "compare": {"values": ["v"]},
        **kw,
    }


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    state = tmp_path / "state"
    monkeypatch.setenv(STATE_ENV, str(state))
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join([str(REPO), os.environ.get("PYTHONPATH", "")]))
    return state


def config(tmp_path: Path, built: BuiltDataset, tasks_dir: Path, **kw: Any) -> RunConfig:
    base: dict[str, Any] = {
        "tasks_dir": tasks_dir,
        "dataset_dir": built.dir,
        "out_dir": tmp_path / "runs",
        "agent": FAKE,
        "auth_mode": "api-key",
        "profiles": ["slayer"],
        "concurrency": 2,
    }
    base.update(kw)
    return RunConfig(**base)


def results(run_dir: Path) -> list[TrialResult]:
    return [TrialResult.model_validate_json(line) for line in (run_dir / "results.jsonl").read_text().splitlines()]


def tasks_dir_with(tmp_path: Path, *docs: dict[str, Any]) -> Path:
    d = tmp_path / "tasks"
    d.mkdir(exist_ok=True)
    for doc in docs:
        write_task(d, doc)
    return d


def test_defaults():
    c = RunConfig()
    assert c.profiles == ["slayer", "slayer+python"]
    assert c.models == ["claude-opus-5-5"]
    assert c.n == 1
    assert c.mode == "repeat"
    assert c.concurrency == 3
    assert c.max_turns == 60
    assert c.timeout_s == 900
    assert c.auth_mode is None
    assert c.task_ids == []
    assert c.rows == []


def test_select_by_rows_and_ids():
    tasks = [make_task(id="a", row="Q1"), make_task(id="b", row="Q4"), make_task(id="c", row="Q7")]
    assert [t.id for t in select_tasks(tasks, RunConfig(rows=["Q1", "Q4"]))] == ["a", "b"]
    assert [t.id for t in select_tasks(tasks, RunConfig(task_ids=["c"]))] == ["c"]
    assert [t.id for t in select_tasks(tasks, RunConfig())] == ["a", "b", "c"]


@pytest.mark.parametrize("model", ["a/b", "..", ".hidden", "a__b", ""])
def test_model_names_must_be_path_safe(model: str):
    with pytest.raises(ValidationError):
        RunConfig(models=[model])


@pytest.mark.parametrize(
    ("cfg", "unknown"),
    [(RunConfig(task_ids=["a", "typo"]), "typo"), (RunConfig(rows=["Q1", "Q99"]), "Q99")],
)
def test_select_rejects_unknown_ids_and_rows(cfg: RunConfig, unknown: str):
    tasks = [make_task(id="a", row="Q1"), make_task(id="b", row="Q4")]
    with pytest.raises(ValueError, match=unknown):
        select_tasks(tasks, cfg)


def test_row_filter_run(tmp_path: Path, built: BuiltDataset, env: Path):
    td = tasks_dir_with(
        tmp_path, task_doc("a", "Q1", "ANSWER 7"), task_doc("b", "Q4", "ANSWER 7"), task_doc("c", "Q7", "ANSWER 7")
    )
    run_dir = run_benchmark(config(tmp_path, built, td, rows=["Q1", "Q4"]), environ=ENV)
    assert sorted(r.task_id for r in results(run_dir)) == ["a", "b"]


def test_repeat_runs_n_times(tmp_path: Path, built: BuiltDataset, env: Path):
    td = tasks_dir_with(tmp_path, task_doc("a", "Q1", "ANSWER 7"))
    run_dir = run_benchmark(config(tmp_path, built, td, n=3, profiles=["slayer", "slayer+python"]), environ=ENV)
    rs = results(run_dir)
    assert Counter((r.task_id, r.profile, r.model) for r in rs) == {
        ("a", "slayer", "claude-opus-5-5"): 3,
        ("a", "slayer+python", "claude-opus-5-5"): 3,
    }
    assert sorted(r.trial for r in rs if r.profile == "slayer") == [1, 2, 3]
    assert all(r.verdict is not None and r.verdict.passed for r in rs)


def test_until_pass_stops_at_first_pass(tmp_path: Path, built: BuiltDataset, env: Path):
    td = tasks_dir_with(tmp_path, task_doc("a", "Q1", "ANSWER 7\nPASS_FROM_ATTEMPT 2"))
    run_dir = run_benchmark(config(tmp_path, built, td, n=3, mode="until-pass", concurrency=1), environ=ENV)
    rs = sorted(results(run_dir), key=lambda r: r.trial)
    assert [r.trial for r in rs] == [1, 2]
    assert [r.verdict.passed for r in rs if r.verdict] == [False, True]


def test_until_pass_exhausts(tmp_path: Path, built: BuiltDataset, env: Path):
    td = tasks_dir_with(tmp_path, task_doc("a", "Q1", "ANSWER 8"))
    run_dir = run_benchmark(config(tmp_path, built, td, n=3, mode="until-pass"), environ=ENV)
    rs = results(run_dir)
    assert len(rs) == 3
    assert not any(r.verdict and r.verdict.passed for r in rs)


def test_until_pass_retries_abnormal_endings(tmp_path: Path, built: BuiltDataset, env: Path):
    td = tasks_dir_with(tmp_path, task_doc("a", "Q1", "END timeout"))
    run_dir = run_benchmark(config(tmp_path, built, td, n=2, mode="until-pass"), environ=ENV)
    rs = results(run_dir)
    assert len(rs) == 2
    assert {r.end_reason for r in rs} == {"timeout"}


def test_agent_changes_do_not_leak(tmp_path: Path, built: BuiltDataset, env: Path):
    td = tasks_dir_with(
        tmp_path,
        task_doc("a-writer", "Q1", "WRITE_MARKER\nWRITE_DB\nANSWER 7"),
        task_doc("b-reader", "Q4", "CHECK_MARKER", truth="select 0.0 as v"),
    )
    run_dir = run_benchmark(config(tmp_path, built, td, concurrency=1), environ=ENV)
    by_id = {r.task_id: r for r in results(run_dir)}
    assert by_id["b-reader"].verdict is not None
    assert by_id["b-reader"].verdict.correct
    con = duckdb.connect(str(built.db_path), read_only=True)
    try:
        template_orders = con.execute("select count(*) from orders").fetchone()
    finally:
        con.close()
    assert template_orders is not None
    reader = next(r for r in recorded_runs(env) if r["input"]["prompt"] == "CHECK_MARKER")
    assert reader["orders"] == template_orders[0] > 0
    assert not (built.store_dir / "leak_marker.yaml").exists()


def _max_overlap(runs: list[dict]) -> int:
    return max(sum(1 for o in runs if o["start"] <= r["start"] < o["end"]) for r in runs)


@pytest.mark.parametrize("limit", [None, 2])
def test_concurrency_limit(tmp_path: Path, built: BuiltDataset, env: Path, limit: int | None):
    td = tasks_dir_with(tmp_path, *[task_doc(f"t{i}", "Q1", f"SLEEP 3\nANSWER 7\nID {i}") for i in range(6)])
    cfg = config(tmp_path, built, td)
    cfg = cfg.model_copy(update={"concurrency": limit if limit is not None else RunConfig().concurrency})
    run_benchmark(cfg, environ=ENV)
    runs = recorded_runs(env)
    assert len(runs) == 6
    assert _max_overlap(runs) == (limit or 3)


def test_one_process_per_trial(tmp_path: Path, built: BuiltDataset, env: Path):
    td = tasks_dir_with(tmp_path, task_doc("a", "Q1", "ANSWER 7"), task_doc("b", "Q4", "ANSWER 7"))
    run_benchmark(config(tmp_path, built, td, n=2), environ=ENV)
    pids = [r["pid"] for r in recorded_runs(env)]
    assert len(pids) == 4
    assert len(set(pids)) == 4
    assert os.getpid() not in pids


def test_agent_sees_only_the_prompt(tmp_path: Path, built: BuiltDataset, env: Path):
    td = tasks_dir_with(
        tmp_path,
        task_doc("a", "Q1", "ANSWER 7", truth=SECRET_SQL, xfail={"issue": "DEV-1", "reason": "secret_fn_marker"}),
    )
    run_benchmark(config(tmp_path, built, td), environ=ENV)
    (rec,) = recorded_runs(env)
    assert set(rec["input"]) == {"prompt", "profile", "env"}
    assert rec["input"]["prompt"] == "ANSWER 7"
    blob = json.dumps(rec)
    for leak in ("secret truth marker", "secret_fn_marker", "Q1", '"row"'):
        assert leak not in blob


def test_trials_get_fresh_copies(tmp_path: Path, built: BuiltDataset, env: Path):
    td = tasks_dir_with(tmp_path, task_doc("a", "Q1", "ANSWER 7"))
    run_benchmark(config(tmp_path, built, td, n=2), environ=ENV)
    envs = [r["input"]["env"] for r in recorded_runs(env)]
    stores = {e["store_dir"] for e in envs}
    dbs = {e["db_path"] for e in envs}
    assert len(stores) == 2
    assert len(dbs) == 2
    assert str(built.store_dir) not in stores
    assert str(built.db_path) not in dbs


def test_credentials_reach_agent(tmp_path: Path, built: BuiltDataset, env: Path):
    td = tasks_dir_with(tmp_path, task_doc("a", "Q1", "ANSWER 7"))
    run_benchmark(config(tmp_path, built, td), environ=ENV)
    (rec,) = recorded_runs(env)
    creds = rec["input"]["env"]["credentials"]
    assert creds["ANTHROPIC_API_KEY"] == "sk-ant-api-test"
    assert creds.get("CLAUDE_CODE_OAUTH_TOKEN", "") == ""


def _alive(pid: int) -> bool:
    try:
        return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0] != "Z"
    except FileNotFoundError:
        return False


def test_trial_timeout_kills_the_agents_subprocesses(
    tmp_path: Path, built: BuiltDataset, env: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(run_module, "KILL_GRACE_S", 0.0)
    td = tasks_dir_with(tmp_path, task_doc("a", "Q1", "SPAWN_SLEEPER\nSLEEP 60\nANSWER 7"))
    start = time.monotonic()
    run_dir = run_benchmark(config(tmp_path, built, td, timeout_s=5.0), environ=ENV)
    assert time.monotonic() - start < 30  # a surviving sleeper holds the trial's stderr open until it exits
    (r,) = results(run_dir)
    assert r.end_reason == "timeout"
    pid = int((env / SLEEPER_PID).read_text())
    deadline = time.monotonic() + 5
    while _alive(pid) and time.monotonic() < deadline:
        time.sleep(0.1)
    assert not _alive(pid)


def test_credentials_not_in_a_file_named_on_the_trial_command_line(tmp_path: Path, built: BuiltDataset, env: Path):
    td = tasks_dir_with(tmp_path, task_doc("a", "Q1", "ANSWER 7"))
    run_benchmark(config(tmp_path, built, td), environ=ENV)
    (rec,) = recorded_runs(env)
    assert rec["argv_files_with_secrets"] == []


FAKE_SLAYER = """
import sys
from mcp.server.fastmcp import FastMCP
server = FastMCP("SLayer")
server._mcp_server.version = "9.9.9-local"
server.run()
"""


def test_local_slayer_override(tmp_path: Path, built: BuiltDataset, env: Path):
    script = tmp_path / "fake_slayer.py"
    script.write_text(FAKE_SLAYER)
    command = [sys.executable, str(script)]
    td = tasks_dir_with(tmp_path, task_doc("a", "Q1", "ANSWER 7"), task_doc("b", "Q4", "ANSWER 7"))
    run_dir = run_benchmark(config(tmp_path, built, td, slayer_command=command), environ=ENV)
    assert all(r["input"]["env"]["slayer_command"] == command for r in recorded_runs(env))
    md = RunMetadata.model_validate_json((run_dir / "metadata.json").read_text())
    assert md.slayer_version == "9.9.9-local"


def test_run_output(tmp_path: Path, built: BuiltDataset, env: Path):
    td = tasks_dir_with(
        tmp_path,
        task_doc("a", "Q1", "ANSWER 7"),
        task_doc("x", "Q20", "ANSWER 7", xfail={"issue": "DEV-2058", "reason": "clock"}),
    )
    run_dir = run_benchmark(config(tmp_path, built, td, n=1), environ=ENV)
    assert run_dir.parent == tmp_path / "runs"
    md = RunMetadata.model_validate_json((run_dir / "metadata.json").read_text())
    assert md.slayer_version == "1.0.2"
    assert md.sdk_version == claude_agent_sdk.__version__
    assert md.models == ["claude-opus-5-5"]
    assert md.mode == "repeat"
    assert md.n == 1
    assert md.auth_mode == "api-key"
    assert md.max_turns == 60
    assert md.timeout_s == 900
    rs = {r.task_id: r for r in results(run_dir)}
    assert rs["x"].xfail == "DEV-2058"
    assert rs["a"].xfail is None
    for r in rs.values():
        assert r.row in ("Q1", "Q20")
        assert r.end_reason == "submitted"
        assert r.verdict is not None
    for r in rs.values():
        stem = f"{r.task_id}__{r.profile}__{r.model}__{r.trial}"
        trace = run_dir / "traces" / f"{stem}.json"
        assert trace.read_text().strip()
        transcript = run_dir / "transcripts" / f"{stem}.jsonl"
        assert TRANSCRIPT_TAG in transcript.read_text()
    assert (run_dir / "report.md").read_text().strip()


def test_missing_auth_mode_refuses_before_running(tmp_path: Path, built: BuiltDataset, env: Path):
    td = tasks_dir_with(tmp_path, task_doc("a", "Q1", "ANSWER 7"))
    cfg = config(tmp_path, built, td, auth_mode=None)
    with pytest.raises(AuthError):
        run_benchmark(cfg, environ=ENV)
    assert recorded_runs(env) == []
