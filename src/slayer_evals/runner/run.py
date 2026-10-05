"""Running selected tasks in isolated trial processes, in `repeat` or `until-pass` mode, and recording everything."""

import asyncio
import contextlib
import datetime as dt
import importlib.metadata
import os
import shutil
import sys
import tempfile
import time
from collections.abc import Mapping
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from slayer_evals.agents import slayer_server_env
from slayer_evals.core import (
    AgentInput,
    AgentOutcome,
    Profile,
    RunMetadata,
    Table,
    Task,
    Trace,
    TrialEnv,
    TrialResult,
)
from slayer_evals.dataset import DB_FILE, STORE_DIR, BuiltDataset, build_dataset, load_built
from slayer_evals.grading import grade
from slayer_evals.report import write_report
from slayer_evals.runner.auth import CREDENTIAL_VARS, resolve_auth
from slayer_evals.runner.config import RunConfig, default_slayer_command, select_tasks
from slayer_evals.runner.trial import TrialSpec
from slayer_evals.tasks import compute_truths, load_tasks

# Extra wall-clock a trial process gets beyond the agent's own budget before it is killed.
KILL_GRACE_S = 60.0
VERSION_PROBE_TIMEOUT_S = 60.0
TRANSCRIPT_FILE = "transcript.jsonl"


class Combo:
    """One (task, profile, model) to run N times or until it passes."""

    def __init__(self, task: Task, profile: Profile, model: str):
        self.task: Task = task
        self.profile: Profile = profile
        self.model: str = model


class Runner:
    def __init__(
        self,
        cfg: RunConfig,
        built: BuiltDataset,
        truths: dict[str, Table],
        credentials: dict[str, str],
        slayer_command: list[str],
        run_dir: Path,
    ):
        self.cfg, self.built, self.truths = cfg, built, truths
        self.credentials, self.slayer_command, self.run_dir = credentials, slayer_command, run_dir
        self.semaphore = asyncio.Semaphore(cfg.concurrency)
        self.results_path = run_dir / "results.jsonl"

    def _stem(self, combo: Combo, trial: int) -> str:
        return f"{combo.task.id}__{combo.profile}__{combo.model}__{trial}"

    def _child_env(self) -> dict[str, str]:
        return {k: v for k, v in os.environ.items() if k not in CREDENTIAL_VARS}

    async def _run_agent(self, combo: Combo, trial_dir: Path) -> tuple[AgentOutcome, float]:
        env = TrialEnv(
            trial_dir=trial_dir,
            store_dir=trial_dir / STORE_DIR,
            db_path=trial_dir / DB_FILE,
            slayer_command=self.slayer_command,
            credentials=self.credentials,
            max_turns=self.cfg.max_turns,
            timeout_s=self.cfg.timeout_s,
            transcript_path=trial_dir / TRANSCRIPT_FILE,
        )
        inp = AgentInput(prompt=combo.task.prompt, profile=combo.profile, env=env)
        spec = TrialSpec(agent=self.cfg.agent, model=combo.model, input=inp)
        with tempfile.TemporaryDirectory(prefix="slayer-evals-spec-") as io_dir:
            spec_path, outcome_path = Path(io_dir) / "spec.json", Path(io_dir) / "outcome.json"
            spec_path.write_text(spec.model_dump_json())
            start = time.monotonic()
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                "slayer_evals.runner.trial",
                str(spec_path),
                str(outcome_path),
                env=self._child_env(),
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                _, stderr = await asyncio.wait_for(proc.communicate(), timeout=self.cfg.timeout_s + KILL_GRACE_S)
            except TimeoutError:
                with contextlib.suppress(ProcessLookupError):
                    proc.kill()
                await proc.wait()
                return AgentOutcome(submission=None, trace=Trace(end_reason="timeout")), time.monotonic() - start
            elapsed = time.monotonic() - start
            if not outcome_path.exists():
                tail = stderr.decode(errors="replace")[-2000:]
                error = f"trial process exited with {proc.returncode}: {tail}"
                return AgentOutcome(submission=None, trace=Trace(end_reason="error", error=error)), elapsed
            return AgentOutcome.model_validate_json(outcome_path.read_text()), elapsed

    async def run_trial(self, combo: Combo, trial: int) -> TrialResult:
        stem = self._stem(combo, trial)
        async with self.semaphore:
            trial_dir = Path(tempfile.mkdtemp(prefix="slayer-evals-trial-"))
            try:
                shutil.copy2(self.built.db_path, trial_dir / DB_FILE)
                shutil.copytree(self.built.store_dir, trial_dir / STORE_DIR)
                outcome, elapsed = await self._run_agent(combo, trial_dir)
                transcript = trial_dir / TRANSCRIPT_FILE
                if transcript.exists():
                    shutil.copy2(transcript, self.run_dir / "transcripts" / f"{stem}.jsonl")
            finally:
                shutil.rmtree(trial_dir, ignore_errors=True)
        task = combo.task
        verdict = grade(task, self.truths[task.id], self.built.manifest, outcome.submission, outcome.trace)
        (self.run_dir / "traces" / f"{stem}.json").write_text(outcome.trace.model_dump_json(indent=1) + "\n")
        result = TrialResult(
            task_id=task.id,
            row=task.row,
            profile=combo.profile,
            model=combo.model,
            trial=trial,
            verdict=verdict,
            end_reason=outcome.trace.end_reason,
            usage=outcome.trace.usage,
            cost_usd=outcome.trace.cost_usd,
            duration_s=outcome.trace.duration_s if outcome.trace.duration_s is not None else elapsed,
            xfail=task.xfail.issue if task.xfail else None,
        )
        with self.results_path.open("a") as f:
            f.write(result.model_dump_json() + "\n")
        return result

    async def until_pass(self, combo: Combo) -> None:
        for trial in range(1, self.cfg.n + 1):
            if (await self.run_trial(combo, trial)).passed:
                return

    async def run(self, combos: list[Combo]) -> None:
        if self.cfg.mode == "repeat":
            jobs = [self.run_trial(c, k) for k in range(1, self.cfg.n + 1) for c in combos]
        else:
            jobs = [self.until_pass(c) for c in combos]
        await asyncio.gather(*jobs)


async def slayer_version(command: list[str], built: BuiltDataset) -> str:
    """The version a SLayer MCP server reports, from a throwaway copy of the store."""
    with tempfile.TemporaryDirectory(prefix="slayer-evals-version-") as tmp:
        shutil.copy2(built.db_path, Path(tmp) / DB_FILE)
        shutil.copytree(built.store_dir, Path(tmp) / STORE_DIR)
        params = StdioServerParameters(
            command=command[0],
            args=[*command[1:], "mcp", "--storage", str(Path(tmp) / STORE_DIR)],
            env=slayer_server_env(os.environ),
            cwd=tmp,
        )
        async with asyncio.timeout(VERSION_PROBE_TIMEOUT_S):
            async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
                init = await session.initialize()
                return init.serverInfo.version


def _run_dir(out_dir: Path, started: dt.datetime) -> Path:
    base = started.strftime("%Y%m%d-%H%M%S")
    for k in range(1000):
        path = out_dir / (base if k == 0 else f"{base}-{k}")
        try:
            path.mkdir(parents=True)
            return path
        except FileExistsError:
            continue
    raise RuntimeError(f"cannot create a run directory under {out_dir}")


def run_benchmark(cfg: RunConfig, environ: Mapping[str, str] | None = None) -> Path:
    """Run the selected tasks; returns the run directory holding results, traces, transcripts and the report."""
    credentials = resolve_auth(cfg.auth_mode, cfg.env_file, os.environ if environ is None else environ)
    assert cfg.auth_mode is not None
    tasks = select_tasks(load_tasks(cfg.tasks_dir), cfg)
    if not tasks:
        raise ValueError("no tasks match the selection")
    command = cfg.slayer_command or default_slayer_command()
    with contextlib.ExitStack() as stack:
        if cfg.dataset_dir is not None:
            built = load_built(cfg.dataset_dir)
        else:
            built = build_dataset(Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="slayer-evals-data-"))))
        truths = compute_truths(tasks, built.db_path)
        started = dt.datetime.now(dt.UTC).replace(microsecond=0)
        version = asyncio.run(slayer_version(command, built))
        run_dir = _run_dir(cfg.out_dir, started)
        for sub in ("traces", "transcripts"):
            (run_dir / sub).mkdir()
        metadata = RunMetadata(
            slayer_version=version,
            sdk_version=importlib.metadata.version("claude-agent-sdk"),
            models=cfg.models,
            profiles=cfg.profiles,
            mode=cfg.mode,
            n=cfg.n,
            max_turns=cfg.max_turns,
            timeout_s=cfg.timeout_s,
            auth_mode=cfg.auth_mode,
            started_at=started,
        )
        (run_dir / "metadata.json").write_text(metadata.model_dump_json(indent=1) + "\n")
        runner = Runner(cfg, built, truths, credentials, command, run_dir)
        combos = [Combo(t, p, m) for t in tasks for p in cfg.profiles for m in cfg.models]
        asyncio.run(runner.run(combos))
    write_report(run_dir)
    return run_dir
