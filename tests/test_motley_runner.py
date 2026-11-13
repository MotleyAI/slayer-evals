"""Runs with the Motley profiles: user ids, per-trial org seeding, the warm-up, run metadata and scoped xfail."""

import asyncio
import hashlib
import os
import re
import shlex
import signal
import socket
import subprocess
import sys
import time
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

import slayer_evals.cli as cli_module
import slayer_evals.runner.run as run_module
from slayer_evals.cli import main
from slayer_evals.core import DEFAULT_PROFILES, PROFILES, RunMetadata, Trace, TrialResult, trial_stem
from slayer_evals.dataset import BuiltDataset
from slayer_evals.runner import MotleyWarmUpError, RunConfig, motley_user_id, run_benchmark
from tests.fake_agents import STATE_ENV, recorded_runs
from tests.fake_motley import SERVER_NAME, SERVER_VERSION, FakeMotley, fake_motley
from tests.fake_seed import FAIL_EXIT, NOISE_MARKER, seed_calls
from tests.helpers import REPO, write_task

FAKE = "tests.fake_agents:ScriptedAgent"
ENV = {"ANTHROPIC_API_KEY": "sk-ant-api-test"}
MODEL = "claude-opus-5-5"
SEED_SCRIPT = REPO / "tests" / "fake_seed.py"
USER_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")
CREDENTIALS = ("CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")
SLAYER_QUERY = {"query": {"source_model": "orders", "measures": [{"formula": "sum(amount)", "name": "v"}]}}


def task_doc(tid: str, row: str, prompt: str = "ANSWER 7", **kw: Any) -> dict[str, Any]:
    return {
        "id": tid,
        "covers": [row],
        "prompt": prompt,
        "truth_sql": "select 7.0 as v",
        "slayer_query": SLAYER_QUERY,
        "compare": {"values": ["v"]},
        **kw,
    }


def tasks_dir_with(tmp_path: Path, *docs: dict[str, Any]) -> Path:
    d = tmp_path / "tasks"
    d.mkdir(exist_ok=True)
    for doc in docs:
        write_task(d, doc)
    return d


def results(run_dir: Path) -> list[TrialResult]:
    path = run_dir / "results.jsonl"
    if not path.exists():
        return []
    return [TrialResult.model_validate_json(x) for x in path.read_text().splitlines() if x.strip()]


def all_results(out_dir: Path) -> list[TrialResult]:
    return [r for d in out_dir.glob("*") if d.is_dir() for r in results(d)]


def seed_cmd(state: Path, *flags: str) -> list[str]:
    return [sys.executable, str(SEED_SCRIPT), str(state), *flags]


def _alive(pid: int) -> bool:
    try:
        return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0] != "Z"
    except FileNotFoundError:
        return False


def _gone(*pids: int, within_s: float = 5.0) -> bool:
    deadline = time.monotonic() + within_s
    while any(_alive(p) for p in pids) and time.monotonic() < deadline:
        time.sleep(0.1)
    return not any(_alive(p) for p in pids)


@pytest.fixture
def agent_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    state = tmp_path / "state"
    monkeypatch.setenv(STATE_ENV, str(state))
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join([str(REPO), os.environ.get("PYTHONPATH", "")]))
    return state


@pytest.fixture(scope="module")
def motley(tmp_path_factory: pytest.TempPathFactory) -> Generator[FakeMotley]:
    with fake_motley(tmp_path_factory.mktemp("motley")) as server:
        yield server


def config(tmp_path: Path, built: BuiltDataset, tasks_dir: Path, **kw: Any) -> RunConfig:
    base: dict[str, Any] = {
        "tasks_dir": tasks_dir,
        "dataset_dir": built.dir,
        "out_dir": tmp_path / "runs",
        "agent": FAKE,
        "auth_mode": "api-key",
        "profiles": ["motley"],
        "concurrency": 2,
        **kw,
    }
    return RunConfig(**base)


def motley_config(
    tmp_path: Path, built: BuiltDataset, tasks_dir: Path, server: FakeMotley, *flags: str, **kw: Any
) -> RunConfig:
    return config(
        tmp_path,
        built,
        tasks_dir,
        motley_url=server.url,
        motley_seed_command=seed_cmd(tmp_path / "seeds", *flags),
        **kw,
    )


# User ids


def test_user_id_format():
    run_dir = Path("/srv/evals/runs/20261111-143000")
    stem = trial_stem("q1-a", "motley", MODEL, 1)
    digest = hashlib.sha256(f"{run_dir}|{stem}".encode()).hexdigest()[:12]
    assert motley_user_id(run_dir, stem) == f"se-20261111-143000-{digest}"


def test_user_id_uses_the_absolute_run_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    assert motley_user_id(Path("runs/20261111-143000"), "warm-up") == motley_user_id(
        tmp_path / "runs" / "20261111-143000", "warm-up"
    )


def test_user_id_at_maximum_length():
    uid = motley_user_id(Path("/r/runs/20261111-143000-999"), trial_stem("t" * 60, "motley+python", "m" * 60, 999))
    assert len(uid) == 35
    assert USER_ID_RE.fullmatch(uid)


def test_user_id_is_deterministic():
    run_dir = Path("/r/runs/20261111-143000")
    assert motley_user_id(run_dir, "warm-up") == motley_user_id(run_dir, "warm-up")


def test_user_ids_differ_across_trials_and_runs():
    run = Path("/r/runs/20261111-143000")
    ids = [
        motley_user_id(run, "warm-up"),
        motley_user_id(run, trial_stem("q1-a", "motley", MODEL, 1)),
        motley_user_id(run, trial_stem("q1-a", "motley+python", MODEL, 1)),
        motley_user_id(run, trial_stem("q1-a", "motley", "claude-sonnet-5", 1)),
        motley_user_id(run, trial_stem("q1-a", "motley", MODEL, 2)),
        motley_user_id(run, trial_stem("q4-a", "motley", MODEL, 1)),
        motley_user_id(Path("/r/runs/20261111-143000-1"), trial_stem("q1-a", "motley", MODEL, 1)),
        motley_user_id(Path("/other/runs/20261111-143000"), trial_stem("q1-a", "motley", MODEL, 1)),
    ]
    assert len(set(ids)) == len(ids)
    assert all(USER_ID_RE.fullmatch(i) for i in ids)


# Configuration


def test_defaults():
    c = RunConfig()
    assert c.profiles == list(DEFAULT_PROFILES) == ["slayer", "slayer+python", "sql+python"]
    assert c.motley_url == "http://localhost:8100/api/v1/mcp/"
    assert c.motley_seed_command is None


@pytest.mark.parametrize("profiles", [["motley"], ["slayer", "motley+python"]])
def test_motley_profile_without_a_seed_command_refuses(
    tmp_path: Path, built: BuiltDataset, agent_state: Path, profiles: list[str]
):
    td = tasks_dir_with(tmp_path, task_doc("a", "Q1"))
    cfg = config(tmp_path, built, td, profiles=profiles)
    with pytest.raises(ValueError, match="--motley-seed-cmd"):
        run_benchmark(cfg, environ=ENV)
    assert recorded_runs(agent_state) == []
    assert all_results(tmp_path / "runs") == []


# Per-trial seeding


def test_seed_before_each_motley_trial(
    tmp_path: Path, built: BuiltDataset, agent_state: Path, motley: FakeMotley, monkeypatch: pytest.MonkeyPatch
):
    for var in CREDENTIALS:
        monkeypatch.setenv(var, f"secret-{var}")
    monkeypatch.setenv("SEED_ENV_MARKER", "inherited")
    monkeypatch.chdir(built.dir.parent)
    td = tasks_dir_with(tmp_path, task_doc("a", "Q1"), task_doc("b", "Q4"))
    cfg = motley_config(
        tmp_path, built, td, motley, "--sleep-from", "2", "--sleep", "3", dataset_dir=Path(built.dir.name)
    )
    run_dir = run_benchmark(cfg, environ=ENV)
    rs = results(run_dir)
    assert len(rs) == 2
    assert all(r.end_reason == "submitted" and r.passed for r in rs)
    seeds = seed_calls(tmp_path / "seeds")
    assert len(seeds) == 3
    by_user = {s["user_id"]: s for s in seeds[1:]}
    agents = {rec["input"]["env"]["motley_user_id"]: rec for rec in recorded_runs(agent_state)}
    assert len(by_user) == len(agents) == 2
    for r in rs:
        uid = motley_user_id(run_dir, trial_stem(r.task_id, r.profile, r.model, r.trial))
        seed, rec = by_user[uid], agents[uid]
        env = rec["input"]["env"]
        assert set(rec["input"]) == {"prompt", "profile", "env"}
        assert env["motley_url"] == motley.url
        assert seed["argv"][-6:] == ["--user-id", uid, "--store", env["store_dir"], "--db", str(built.db_path)]
        assert Path(seed["db"]).is_absolute()
        assert seed["store_is_dir"]
        assert seed["store"] != str(built.store_dir)
        assert seed["end"] <= rec["start"]
        assert r.duration_s < rec["end"] - seed["start"], "the seed's time counts towards the trial"
        for var in CREDENTIALS:
            assert var not in seed["env"], var
        assert seed["env"]["SEED_ENV_MARKER"] == "inherited"


def test_seed_failure_ends_the_trial(tmp_path: Path, built: BuiltDataset, agent_state: Path, motley: FakeMotley):
    td = tasks_dir_with(tmp_path, task_doc("a", "Q1"))
    cfg = motley_config(tmp_path, built, td, motley, "--fail-from", "2", "--noise", "20000")
    run_dir = run_benchmark(cfg, environ=ENV)
    (r,) = results(run_dir)
    assert r.end_reason == "error"
    assert r.verdict is not None
    assert not r.passed
    uid = motley_user_id(run_dir, trial_stem("a", "motley", MODEL, 1))
    stem = trial_stem("a", "motley", MODEL, 1)
    trace = Trace.model_validate_json((run_dir / "traces" / f"{stem}.json").read_text())
    assert trace.error is not None
    assert f"motley seed failed (exit {FAIL_EXIT})" in trace.error
    assert f"seed exploded for {uid}" in trace.error
    assert NOISE_MARKER not in trace.error, "the error keeps only the tail of the seed's stderr"
    assert len(trace.error) < 10000
    assert recorded_runs(agent_state) == []


async def _drained(chunks: list[bytes], keep: int) -> bytes:
    reader = asyncio.StreamReader()
    for chunk in chunks:
        reader.feed_data(chunk)
    reader.feed_eof()
    return await run_module.drain_tail(reader, keep)


@pytest.mark.parametrize("sizes", [[0], [10], [100_000, 5], [3, 70_000, 70_000, 9]])
def test_drain_tail_keeps_only_the_last_bytes(sizes: list[int]):
    chunks = [bytes([65 + i % 26]) * n for i, n in enumerate(sizes)]
    assert asyncio.run(_drained(chunks, 1000)) == b"".join(chunks)[-1000:]


def test_seed_runs_inside_the_concurrency_slot(
    tmp_path: Path, built: BuiltDataset, agent_state: Path, motley: FakeMotley
):
    td = tasks_dir_with(tmp_path, task_doc("a", "Q1", "SLEEP 2\nANSWER 7"), task_doc("b", "Q4", "SLEEP 2\nANSWER 7"))
    run_dir = run_benchmark(motley_config(tmp_path, built, td, motley, concurrency=1), environ=ENV)
    assert len(results(run_dir)) == 2
    first_seed, second_seed = seed_calls(tmp_path / "seeds")[1:]
    agents = {rec["input"]["env"]["motley_user_id"]: rec for rec in recorded_runs(agent_state)}
    assert second_seed["start"] >= agents[first_seed["user_id"]]["end"]


def test_seed_timeout_leaves_no_processes(
    tmp_path: Path, built: BuiltDataset, agent_state: Path, motley: FakeMotley, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(run_module, "SEED_TIMEOUT_S", 3.0)
    td = tasks_dir_with(tmp_path, task_doc("a", "Q1"))
    start = time.monotonic()
    run_dir = run_benchmark(motley_config(tmp_path, built, td, motley, "--hang-from", "2"), environ=ENV)
    assert time.monotonic() - start < 60
    (r,) = results(run_dir)
    assert r.end_reason == "error"
    seeds = tmp_path / "seeds"
    seed_pid = seed_calls(seeds)[1]["pid"]
    sleeper_pid = int((seeds / "sleeper-2.pid").read_text())
    assert _gone(seed_pid, sleeper_pid)
    assert recorded_runs(agent_state) == []


def test_interrupted_run_stops_the_seed(tmp_path: Path, built: BuiltDataset, motley: FakeMotley):
    td = tasks_dir_with(tmp_path, task_doc("a", "Q1"))
    seeds = tmp_path / "seeds"
    env_file = tmp_path / ".env"
    env_file.write_text("ANTHROPIC_API_KEY=sk-ant-api-test\n")
    argv = ["run", "--api-key-auth", "--env-file", str(env_file), "--tasks-dir", str(td)]
    argv += ["--dataset-dir", str(built.dir), "--out", str(tmp_path / "runs"), "--agent", FAKE, "--profiles", "motley"]
    argv += ["--motley-url", motley.url, "--motley-seed-cmd", shlex.join(seed_cmd(seeds, "--hang-from", "2"))]
    env = {**os.environ, STATE_ENV: str(tmp_path / "state"), "PYTHONPATH": str(REPO)}
    proc = subprocess.Popen([sys.executable, "-m", "slayer_evals.cli", *argv], env=env, cwd=REPO)
    try:
        deadline = time.monotonic() + 120
        while not (seeds / "sleeper-2.pid").exists():
            assert proc.poll() is None, "run exited before the trial's seed started"
            assert time.monotonic() < deadline, "the trial's seed never started"
            time.sleep(0.2)
        time.sleep(0.5)
        proc.send_signal(signal.SIGINT)
        proc.wait(timeout=30)
    finally:
        proc.kill()
        proc.wait()
    seed_pid = seed_calls(seeds)[1]["pid"]
    sleeper_pid = int((seeds / "sleeper-2.pid").read_text())
    assert _gone(seed_pid, sleeper_pid)


def test_saved_definition_task_runs_in_motley(
    tmp_path: Path, built: BuiltDataset, agent_state: Path, motley: FakeMotley
):
    td = tasks_dir_with(tmp_path, task_doc("q23-saved", "Q23", uses_saved=["monthly_rev"]))
    run_dir = run_benchmark(motley_config(tmp_path, built, td, motley), environ=ENV)
    (r,) = results(run_dir)
    assert r.end_reason == "submitted"
    assert r.passed
    assert len(recorded_runs(agent_state)) == 1


# Warm-up and run metadata


def test_motley_metadata(tmp_path: Path, built: BuiltDataset, agent_state: Path, motley: FakeMotley):
    td = tasks_dir_with(tmp_path, task_doc("a", "Q1"))
    run_dir = run_benchmark(motley_config(tmp_path, built, td, motley), environ=ENV)
    md = RunMetadata.model_validate_json((run_dir / "metadata.json").read_text())
    assert md.motley_url == motley.url
    assert md.motley_server_info == f"{SERVER_NAME} {SERVER_VERSION}"
    warm_up = motley_user_id(run_dir, "warm-up")
    assert seed_calls(tmp_path / "seeds")[0]["user_id"] == warm_up
    assert warm_up in motley.user_ids_by_method()["initialize"]


def test_warm_up_stderr_reaches_the_user(
    tmp_path: Path, built: BuiltDataset, agent_state: Path, motley: FakeMotley, capfd: pytest.CaptureFixture[str]
):
    td = tasks_dir_with(tmp_path, task_doc("a", "Q1"))
    run_dir = run_benchmark(motley_config(tmp_path, built, td, motley), environ=ENV)
    err = capfd.readouterr().err
    assert f"seed-stderr {motley_user_id(run_dir, 'warm-up')}" in err
    assert f"seed-stderr {motley_user_id(run_dir, trial_stem('a', 'motley', MODEL, 1))}" not in err


def test_no_motley_without_a_motley_profile(tmp_path: Path, built: BuiltDataset, agent_state: Path, motley: FakeMotley):
    td = tasks_dir_with(tmp_path, task_doc("a", "Q1"))
    run_dir = run_benchmark(motley_config(tmp_path, built, td, motley, profiles=["slayer"]), environ=ENV)
    md = RunMetadata.model_validate_json((run_dir / "metadata.json").read_text())
    assert (md.motley_url, md.motley_server_info) == (None, None)
    assert seed_calls(tmp_path / "seeds") == []
    assert all(rec["input"]["env"].get("motley_user_id") is None for rec in recorded_runs(agent_state))


def _refused(tmp_path: Path, built: BuiltDataset, url: str, seed: list[str]) -> MotleyWarmUpError:
    td = tasks_dir_with(tmp_path, task_doc("a", "Q1"))
    cfg = config(tmp_path, built, td, motley_url=url, motley_seed_command=seed)
    start = time.monotonic()
    with pytest.raises(MotleyWarmUpError) as exc:
        run_benchmark(cfg, environ=ENV)
    assert time.monotonic() - start < 60
    assert all_results(tmp_path / "runs") == []
    return exc.value


def test_warm_up_missing_seed_executable(tmp_path: Path, built: BuiltDataset, agent_state: Path, motley: FakeMotley):
    err = _refused(tmp_path, built, motley.url, ["/nonexistent/seed-eval-org"])
    assert "/nonexistent/seed-eval-org" in str(err)
    assert recorded_runs(agent_state) == []


def test_warm_up_seed_fails(tmp_path: Path, built: BuiltDataset, agent_state: Path, motley: FakeMotley):
    err = _refused(tmp_path, built, motley.url, seed_cmd(tmp_path / "seeds", "--fail-from", "1"))
    assert "seed exploded" in str(err)
    assert recorded_runs(agent_state) == []
    assert len(seed_calls(tmp_path / "seeds")) == 1


def test_warm_up_connection_refused(tmp_path: Path, built: BuiltDataset, agent_state: Path):
    with socket.socket() as held:  # bound but not listening: connections are refused and the port stays ours
        held.bind(("127.0.0.1", 0))
        url = f"http://127.0.0.1:{held.getsockname()[1]}/api/v1/mcp/"
        err = _refused(tmp_path, built, url, seed_cmd(tmp_path / "seeds"))
    assert url in str(err)
    assert recorded_runs(agent_state) == []


def test_warm_up_initialize_timeout(
    tmp_path: Path, built: BuiltDataset, agent_state: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(run_module, "MOTLEY_INIT_TIMEOUT_S", 2.0)
    with fake_motley(tmp_path, mode="hang") as server:
        err = _refused(tmp_path, built, server.url, seed_cmd(tmp_path / "seeds"))
    assert server.url in str(err)
    assert recorded_runs(agent_state) == []


def test_warm_up_seed_timeout_leaves_no_processes(
    tmp_path: Path, built: BuiltDataset, agent_state: Path, motley: FakeMotley, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(run_module, "SEED_TIMEOUT_S", 3.0)
    seeds = tmp_path / "seeds"
    _refused(tmp_path, built, motley.url, seed_cmd(seeds, "--hang-from", "1"))
    assert _gone(seed_calls(seeds)[0]["pid"], int((seeds / "sleeper-1.pid").read_text()))
    assert recorded_runs(agent_state) == []


def test_warm_up_protocol_error(
    tmp_path: Path, built: BuiltDataset, agent_state: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(run_module, "MOTLEY_INIT_TIMEOUT_S", 5.0)
    with fake_motley(tmp_path, mode="garbage") as server:
        err = _refused(tmp_path, built, server.url, seed_cmd(tmp_path / "seeds"))
    assert server.url in str(err)
    assert recorded_runs(agent_state) == []


def test_warm_up_misdirected_request(tmp_path: Path, built: BuiltDataset, agent_state: Path):
    with fake_motley(tmp_path, mode="421") as server:
        err = _refused(tmp_path, built, server.url, seed_cmd(tmp_path / "seeds"))
    assert "421" in str(err)
    assert "public_base_url" in str(err)
    assert recorded_runs(agent_state) == []


# Profile-scoped xfail


def test_profile_scoped_xfail(tmp_path: Path, built: BuiltDataset, agent_state: Path, motley: FakeMotley):
    xfail = {"issue": "DEV-1951", "reason": "no warnings", "profiles": ["motley", "motley+python"]}
    td = tasks_dir_with(tmp_path, task_doc("q9-x", "Q9", xfail=xfail))
    run_dir = run_benchmark(motley_config(tmp_path, built, td, motley, profiles=["slayer", "motley"]), environ=ENV)
    by_profile = {r.profile: r for r in results(run_dir)}
    assert by_profile["motley"].xfail == "DEV-1951"
    assert by_profile["slayer"].xfail is None


# CLI


def captured_runs(monkeypatch: pytest.MonkeyPatch, run_dir: Path) -> list[RunConfig]:
    seen: list[RunConfig] = []

    def fake_run(cfg: RunConfig, environ: Any = None) -> Path:
        seen.append(cfg)
        return run_dir

    monkeypatch.setattr(cli_module, "run_benchmark", fake_run)
    return seen


def test_cli_motley_flags(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    seen = captured_runs(monkeypatch, tmp_path)
    seed = "uv run python 'scripts/seed eval org.py' --verbose"
    url = "http://127.0.0.1:9000/api/v1/mcp/"
    argv = ["run", "--api-key-auth", "--profiles", "motley,slayer", "--motley-url", url, "--motley-seed-cmd", seed]
    assert main(argv) == 0
    (cfg,) = seen
    assert cfg.profiles == ["motley", "slayer"]
    assert cfg.motley_url == url
    assert cfg.motley_seed_command == ["uv", "run", "python", "scripts/seed eval org.py", "--verbose"]


def test_cli_motley_defaults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    seen = captured_runs(monkeypatch, tmp_path)
    assert main(["run", "--api-key-auth"]) == 0
    (cfg,) = seen
    assert cfg.profiles == ["slayer", "slayer+python", "sql+python"]
    assert cfg.motley_url == "http://localhost:8100/api/v1/mcp/"
    assert cfg.motley_seed_command is None


def test_cli_help_lists_every_profile(capsys: pytest.CaptureFixture[str]):
    with pytest.raises(SystemExit):
        main(["run", "--help"])
    help_text = " ".join(capsys.readouterr().out.split())
    for profile in PROFILES:
        assert profile in help_text, profile
    assert "--motley-url" in help_text
    assert "--motley-seed-cmd" in help_text


def test_cli_warm_up_failure_exits_2(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]):
    def failing_run(cfg: RunConfig, environ: Any = None) -> Path:
        raise MotleyWarmUpError("cannot reach the Motley server")

    monkeypatch.setattr(cli_module, "run_benchmark", failing_run)
    assert main(["run", "--api-key-auth", "--profiles", "motley", "--motley-seed-cmd", "seed"]) == 2
    assert "cannot reach the Motley server" in capsys.readouterr().err


def test_cli_motley_without_a_seed_command(
    tmp_path: Path,
    built: BuiltDataset,
    agent_state: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-api-test")
    td = tasks_dir_with(tmp_path, task_doc("a", "Q1"))
    argv = ["run", "--api-key-auth", "--tasks-dir", str(td), "--dataset-dir", str(built.dir)]
    argv += ["--out", str(tmp_path / "runs"), "--agent", FAKE, "--profiles", "motley"]
    assert main(argv) == 2
    assert "--motley-seed-cmd" in capsys.readouterr().err
    assert recorded_runs(agent_state) == []


# Docs


def test_readme_documents_the_motley_profiles():
    readme = (REPO / "README.md").read_text()
    for text in (
        "`motley`",
        "`motley+python`",
        "--motley-url",
        "--motley-seed-cmd",
        "public_base_url",
        "eval_org_seed.md",
    ):
        assert text in readme, text
