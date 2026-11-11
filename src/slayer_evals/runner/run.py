"""Running selected tasks in isolated trial processes, in `repeat` or `until-pass` mode, and recording everything."""

import asyncio
import contextlib
import datetime as dt
import hashlib
import importlib.metadata
import os
import shutil
import signal
import sys
import tempfile
import time
from collections.abc import Mapping
from pathlib import Path

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client

from slayer_evals.agents import USER_ID_HEADER, slayer_server_env
from slayer_evals.core import (
    PROFILE_SPECS,
    AgentInput,
    AgentOutcome,
    Profile,
    RunMetadata,
    Table,
    Task,
    Trace,
    TrialEnv,
    TrialResult,
    trial_stem,
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
SEED_TIMEOUT_S = 600.0
MOTLEY_INIT_TIMEOUT_S = 60.0
SEED_ERROR_TAIL = 2000
WARM_UP = "warm-up"
MISDIRECTED = 421


def _child_env() -> dict[str, str]:
    """The runner's environment without the Claude credentials."""
    return {k: v for k, v in os.environ.items() if k not in CREDENTIAL_VARS}


class SeedError(RuntimeError):
    pass


class MotleyWarmUpError(RuntimeError):
    """The Motley warm-up seed or `initialize` failed, so the run cannot start."""


def motley_user_id(run_dir: Path, label: str) -> str:
    """`se-<run dir name>-<12 hex>`, unique per absolute run directory and label (a trial stem or `warm-up`)."""
    digest = hashlib.sha256(f"{run_dir.absolute()}|{label}".encode()).hexdigest()[:12]
    return f"se-{run_dir.name}-{digest}"


async def _drain(stream: asyncio.StreamReader, echo: bool) -> bytes:
    chunks: list[bytes] = []
    while chunk := await stream.read(65536):
        chunks.append(chunk)
        if echo:
            sys.stderr.write(chunk.decode(errors="replace"))
            sys.stderr.flush()
    return b"".join(chunks)


async def seed_org(
    command: list[str], user_id: str, store: Path, db: Path, env: Mapping[str, str], echo: bool = False
) -> None:
    """Run the seed command in its own process group; raise `SeedError` with its stderr tail unless it succeeds."""
    argv = [*command, "--user-id", user_id, "--store", str(store), "--db", str(db)]
    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            env=dict(env),
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True,
        )
    except OSError as exc:
        raise SeedError(f"motley seed failed to start: {exc}") from exc
    assert proc.stderr is not None
    drain = asyncio.ensure_future(_drain(proc.stderr, echo))
    problem: str | None = None
    try:
        await asyncio.wait_for(proc.wait(), timeout=SEED_TIMEOUT_S)
        if proc.returncode != 0:
            problem = f"motley seed failed (exit {proc.returncode})"
    except TimeoutError:
        problem = f"motley seed timed out after {SEED_TIMEOUT_S:g} s"
    finally:
        # Also stops whatever the seed started.
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGKILL)
        await proc.wait()
    stderr = (await drain).decode(errors="replace")
    if problem is not None:
        raise SeedError(f"{problem}: {stderr[-SEED_ERROR_TAIL:].strip()}")


def _leaves(exc: BaseException) -> list[BaseException]:
    if isinstance(exc, BaseExceptionGroup):
        return [leaf for e in exc.exceptions for leaf in _leaves(e)]
    return [exc]


def _init_failure(url: str, exc: BaseException) -> str:
    causes = []
    for e in _leaves(exc):
        if isinstance(e, TimeoutError):
            causes.append(f"no answer within {MOTLEY_INIT_TIMEOUT_S:g} s")
        else:
            causes.append(f"{type(e).__name__}: {e}")
        if isinstance(e, httpx.HTTPStatusError) and e.response.status_code == MISDIRECTED:
            causes.append("the --motley-url host must match the backend's public_base_url")
    return f"cannot initialize the Motley MCP server at {url}: {'; '.join(causes)}"


async def warm_up_motley(cfg: RunConfig, built: BuiltDataset, run_dir: Path, env: Mapping[str, str]) -> str:
    """Seed the warm-up org, then `initialize` as its user; returns the server's `<name> <version>`."""
    assert cfg.motley_seed_command is not None
    user_id = motley_user_id(run_dir, WARM_UP)
    try:
        await seed_org(
            cfg.motley_seed_command, user_id, built.store_dir.absolute(), built.db_path.absolute(), env, echo=True
        )
    except SeedError as exc:
        raise MotleyWarmUpError(f"warm-up {exc}") from exc
    try:
        async with asyncio.timeout(MOTLEY_INIT_TIMEOUT_S):
            http = httpx.AsyncClient(headers={USER_ID_HEADER: user_id}, timeout=MOTLEY_INIT_TIMEOUT_S)
            async with (
                http,
                streamable_http_client(cfg.motley_url, http_client=http) as (read, write, _),
                ClientSession(read, write) as session,
            ):
                init = await session.initialize()
    except Exception as exc:
        raise MotleyWarmUpError(_init_failure(cfg.motley_url, exc)) from exc
    return f"{init.serverInfo.name} {init.serverInfo.version}"


class Combo:
    """One (task, profile, model) to run N times or until it passes."""

    def __init__(self, task: Task, profile: Profile, model: str):
        self.task: Task = task
        self.profile: Profile = profile
        self.model: str = model

    @property
    def auto_fails(self) -> bool:
        """A task naming saved SLayer definitions fails in raw SQL without running an agent."""
        return bool(self.task.uses_saved) and PROFILE_SPECS[self.profile].surface == "sql"

    @property
    def motley(self) -> bool:
        return PROFILE_SPECS[self.profile].surface == "motley"


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
        return trial_stem(combo.task.id, combo.profile, combo.model, trial)

    async def _run_agent(self, combo: Combo, trial_dir: Path, user_id: str | None) -> tuple[AgentOutcome, float]:
        env = TrialEnv(
            trial_dir=trial_dir,
            store_dir=trial_dir / STORE_DIR,
            db_path=trial_dir / DB_FILE,
            slayer_command=self.slayer_command,
            credentials=self.credentials,
            max_turns=self.cfg.max_turns,
            timeout_s=self.cfg.timeout_s,
            transcript_path=trial_dir / TRANSCRIPT_FILE,
            motley_url=self.cfg.motley_url if user_id else None,
            motley_user_id=user_id,
        )
        inp = AgentInput(prompt=combo.task.prompt, profile=combo.profile, env=env)
        spec = TrialSpec(agent=self.cfg.agent, model=combo.model, input=inp)
        with tempfile.TemporaryDirectory(prefix="slayer-evals-outcome-") as io_dir:
            outcome_path = Path(io_dir) / "outcome.json"
            start = time.monotonic()
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                "slayer_evals.runner.trial",
                str(outcome_path),
                env=_child_env(),
                stdin=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                start_new_session=True,
            )
            try:
                _, stderr = await asyncio.wait_for(
                    proc.communicate(spec.model_dump_json().encode()), timeout=self.cfg.timeout_s + KILL_GRACE_S
                )
            except TimeoutError:
                trace = Trace(profile=combo.profile, end_reason="timeout")
                return AgentOutcome(submission=None, trace=trace), time.monotonic() - start
            finally:
                # The agent's own subprocesses (CLI, MCP servers, Python tool) share the trial's process group.
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(proc.pid, signal.SIGKILL)
                await proc.wait()
            elapsed = time.monotonic() - start
            if not outcome_path.exists():
                tail = stderr.decode(errors="replace")[-2000:]
                error = f"trial process exited with {proc.returncode}: {tail}"
                trace = Trace(profile=combo.profile, end_reason="error", error=error)
                return AgentOutcome(submission=None, trace=trace), elapsed
            return AgentOutcome.model_validate_json(outcome_path.read_text()), elapsed

    async def _run_isolated(self, combo: Combo, stem: str) -> tuple[AgentOutcome, float]:
        """Run the agent in its own process on fresh copies of the database and store (and its own Motley org)."""
        async with self.semaphore:
            trial_dir = Path(tempfile.mkdtemp(prefix="slayer-evals-trial-"))
            try:
                shutil.copy2(self.built.db_path, trial_dir / DB_FILE)
                shutil.copytree(self.built.store_dir, trial_dir / STORE_DIR)
                user_id = motley_user_id(self.run_dir, stem) if combo.motley else None
                if user_id is not None:
                    assert self.cfg.motley_seed_command is not None
                    try:
                        await seed_org(
                            self.cfg.motley_seed_command,
                            user_id,
                            trial_dir / STORE_DIR,
                            self.built.db_path.absolute(),
                            _child_env(),
                        )
                    except SeedError as exc:
                        trace = Trace(profile=combo.profile, end_reason="error", error=str(exc))
                        return AgentOutcome(submission=None, trace=trace), 0.0
                outcome, elapsed = await self._run_agent(combo, trial_dir, user_id)
                transcript = trial_dir / TRANSCRIPT_FILE
                if transcript.exists():
                    shutil.copy2(transcript, self.run_dir / "transcripts" / f"{stem}.jsonl")
            finally:
                shutil.rmtree(trial_dir, ignore_errors=True)
        return outcome, elapsed

    async def run_trial(self, combo: Combo, trial: int) -> TrialResult:
        stem = self._stem(combo, trial)
        if combo.auto_fails:
            outcome = AgentOutcome(submission=None, trace=Trace(profile=combo.profile, end_reason="auto_fail"))
            elapsed = 0.0
        else:
            outcome, elapsed = await self._run_isolated(combo, stem)
        task = combo.task
        verdict = grade(task, self.truths[task.id], outcome.submission, outcome.trace)
        (self.run_dir / "traces" / f"{stem}.json").write_text(outcome.trace.model_dump_json(indent=1) + "\n")
        result = TrialResult(
            task_id=task.id,
            covers=task.covers,
            profile=combo.profile,
            model=combo.model,
            trial=trial,
            verdict=verdict,
            end_reason=outcome.trace.end_reason,
            usage=outcome.trace.usage,
            cost_usd=outcome.trace.cost_usd,
            duration_s=outcome.trace.duration_s if outcome.trace.duration_s is not None else elapsed,
            xfail=task.xfail.issue if task.xfail and task.xfail.applies_to(combo.profile) else None,
        )
        with self.results_path.open("a") as f:
            f.write(result.model_dump_json() + "\n")
        return result

    async def until_pass(self, combo: Combo) -> None:
        for trial in range(1, self.cfg.n + 1):
            result = await self.run_trial(combo, trial)
            if result.passed or combo.auto_fails:
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
    motley = any(PROFILE_SPECS[p].surface == "motley" for p in cfg.profiles)
    if motley and not cfg.motley_seed_command:
        raise ValueError("the Motley profiles need a seed command (--motley-seed-cmd)")
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
        server_info = None
        if motley:
            try:
                server_info = asyncio.run(warm_up_motley(cfg, built, run_dir, _child_env()))
            except BaseException:
                shutil.rmtree(run_dir, ignore_errors=True)
                raise
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
            motley_url=cfg.motley_url if motley else None,
            motley_server_info=server_info,
        )
        (run_dir / "metadata.json").write_text(metadata.model_dump_json(indent=1) + "\n")
        runner = Runner(cfg, built, truths, credentials, command, run_dir)
        combos = [Combo(t, p, m) for t in tasks for p in cfg.profiles for m in cfg.models]
        asyncio.run(runner.run(combos))
    write_report(run_dir)
    return run_dir
