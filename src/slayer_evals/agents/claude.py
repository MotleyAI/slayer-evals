"""The hermetic Claude Agent SDK agent: SLayer's MCP server verbatim or a raw `sql` tool, plus `submit_answer` and Python."""

import asyncio
import contextlib
import json
import os
import shutil
import tempfile
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, TextIO

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, ResultMessage, create_sdk_mcp_server, tool

from slayer_evals.agents.sandbox import run_python
from slayer_evals.agents.sql import SQL_DESCRIPTION, SQL_TOOL, run_sql
from slayer_evals.agents.trace import PYTHON_TOOL, normalize_messages, transcript_line
from slayer_evals.core import AgentInput, AgentOutcome, EndReason, Profile, PythonAudit, Submission

SLAYER_SERVER = "slayer"
BENCH_SERVER = "bench"
SUBMIT_TOOL = "submit_answer"
SUBMIT_FULL_NAME = f"mcp__{BENCH_SERVER}__{SUBMIT_TOOL}"
TEARDOWN_TIMEOUT_S = 30.0
SLAYER_PROFILES: tuple[Profile, ...] = ("slayer", "slayer+python")
PYTHON_PROFILES: tuple[Profile, ...] = ("slayer+python", "sql+python")
BASE_PROMPT = (
    "You are a data analyst answering a business question about the data available through your tools. "
    f"Work out the answer with the tools, then call {SUBMIT_FULL_NAME} once with the result table and a short message. "
    f"If the question cannot be answered as asked, call {SUBMIT_FULL_NAME} with no rows and explain why in the message."
)
JSON_RESULTS_SENTENCE = (
    'Request query results with format="json" so numbers are exact; the default markdown rounds some values.'
)
TELEMETRY_ENV = {
    "DISABLE_TELEMETRY": "1",
    "DISABLE_ERROR_REPORTING": "1",
    "DISABLE_AUTOUPDATER": "1",
    "DISABLE_BUG_COMMAND": "1",
    "DISABLE_NON_ESSENTIAL_MODEL_CALLS": "1",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
}
# Exactly one caching knob is on; the others are blanked so the parent env cannot override them.
CACHE_ENV = {"FORCE_PROMPT_CACHING_5M": "1", "ENABLE_PROMPT_CACHING_1H": "", "DISABLE_PROMPT_CACHING": ""}
ENV_BIN = shutil.which("env") or "/usr/bin/env"
SLAYER_ENV_ALLOW = ("PATH", "HOME", "USER", "LANG", "LC_ALL", "LC_CTYPE", "TZ", "TMPDIR")
CLAUDE_JSON = {"hasCompletedOnboarding": True, "hasTrustDialogAccepted": True, "mcpServers": {}}
SUBMIT_SCHEMA = {
    "type": "object",
    "properties": {
        "columns": {"type": "array", "items": {"type": "string"}, "description": "Column names of the answer."},
        "rows": {
            "type": "array",
            "items": {"type": "array"},
            "description": "Answer rows; each row has one value per column.",
        },
        "message": {"type": "string", "description": "A short message to go with the answer."},
    },
    "required": ["columns", "rows", "message"],
}
SUBMIT_DESCRIPTION = (
    "Submit the final answer: a table (column names, and rows with one value per column) and a short message. "
    "Only the first submission counts and it ends the session."
)
PYTHON_DESCRIPTION = (
    "Run Python 3 code in a fresh process and return its stdout and stderr; print what you want to see. "
    "pandas and numpy are installed. Files written to the working directory persist between calls."
)


class LeakedServerError(RuntimeError):
    pass


def system_prompt(profile: Profile) -> str:
    """Identical across profiles except for the JSON-results sentence of the SLayer profiles."""
    return f"{BASE_PROMPT} {JSON_RESULTS_SENTENCE}" if profile in SLAYER_PROFILES else BASE_PROMPT


def mcp_servers_of(profile: Profile) -> set[str]:
    """The MCP servers a session in `profile` may load."""
    return {SLAYER_SERVER, BENCH_SERVER} if profile in SLAYER_PROFILES else {BENCH_SERVER}


def slayer_server_env(environ: Mapping[str, str]) -> dict[str, str]:
    """The SLayer server's environment: an allow-list, so no credentials reach it."""
    return {k: environ[k] for k in SLAYER_ENV_ALLOW if k in environ}


def _text(text: str, is_error: bool = False) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": text}], "is_error": is_error}


def _ragged(columns: Any, rows: Any) -> str | None:
    if not isinstance(columns, list) or not all(isinstance(c, str) for c in columns):
        return "columns must be a list of column names"
    if not isinstance(rows, list) or not all(isinstance(r, list) for r in rows):
        return "rows must be a list of rows, each a list of values"
    bad = next((i for i, r in enumerate(rows) if len(r) != len(columns)), None)
    if bad is not None:
        return f"row {bad} has {len(rows[bad])} values but there are {len(columns)} columns"
    return None


class AnswerCollector:
    """State the in-process `bench` tools share with the session: the first submission and Python audits."""

    def __init__(self) -> None:
        self.submission: Submission | None = None
        self.python_audits: list[PythonAudit] = []

    def bench_server(self, profile: Profile, sandbox_dir: Path, db_path: Path) -> Any:
        @tool(SUBMIT_TOOL, SUBMIT_DESCRIPTION, SUBMIT_SCHEMA)
        async def submit_answer(args: dict[str, Any]) -> dict[str, Any]:
            problem = _ragged(args.get("columns"), args.get("rows"))
            if problem is not None:
                return _text(f"Answer rejected: {problem}. Fix it and submit again.", is_error=True)
            if self.submission is None:
                message = args.get("message")
                self.submission = Submission(
                    columns=args["columns"], rows=args["rows"], message=message if isinstance(message, str) else ""
                )
            return _text("Answer submitted.")

        @tool(PYTHON_TOOL, PYTHON_DESCRIPTION, {"code": str})
        async def python(args: dict[str, Any]) -> dict[str, Any]:
            run = await run_python(str(args.get("code", "")), sandbox_dir=sandbox_dir)
            self.python_audits.append(run.audit)
            out = run.stdout + (f"\n[stderr]\n{run.stderr}" if run.stderr.strip() else "")
            return _text(out or "(no output)", is_error=not run.ok)

        @tool(SQL_TOOL, SQL_DESCRIPTION, {"sql": str})
        async def sql(args: dict[str, Any]) -> dict[str, Any]:
            run = await run_sql(str(args.get("sql", "")), db_path=db_path)
            return _text(run.text, is_error=not run.ok)

        tools = [submit_answer]
        if profile in PYTHON_PROFILES:
            tools.append(python)
        if profile not in SLAYER_PROFILES:
            tools.append(sql)
        return create_sdk_mcp_server(BENCH_SERVER, tools=tools)


def _end_reason(result: ResultMessage | None, submitted: bool) -> tuple[EndReason, str | None]:
    if submitted:
        return "submitted", None
    if result is None:
        return "error", "session ended without a result"
    if result.subtype == "error_max_turns":
        return "max_turns", None
    if result.is_error:
        # API failures arrive as subtype "success" with is_error set; the cause is in `result`.
        return "error", f"session ended with an error: {result.result or result.subtype}"
    return "error", "session ended without submitting an answer"


class ClaudeAgent:
    """Runs one trial in a fresh, empty Claude config dir with only the profile's MCP servers."""

    def __init__(self, model: str, client_factory: Callable[[ClaudeAgentOptions], Any] | None = None):
        self.model = model
        self.client_factory = client_factory or (lambda options: ClaudeSDKClient(options=options))

    def build_options(self, inp: AgentInput, config_dir: Path, collector: AnswerCollector) -> ClaudeAgentOptions:
        cmd = inp.env.slayer_command
        env = slayer_server_env(os.environ)
        # The CLI hands its whole environment to stdio servers, so `env -i` is what enforces the allow-list.
        slayer = {
            "type": "stdio",
            "command": ENV_BIN,
            "args": ["-i", *(f"{k}={v}" for k, v in env.items()), *cmd, "mcp", "--storage", str(inp.env.store_dir)],
            "env": env,
        }
        bench = collector.bench_server(inp.profile, inp.env.trial_dir / "sandbox", inp.env.db_path)
        servers = {SLAYER_SERVER: slayer, BENCH_SERVER: bench}
        names = sorted(mcp_servers_of(inp.profile))
        return ClaudeAgentOptions(
            tools=[],
            setting_sources=[],
            allowed_tools=[f"mcp__{n}" for n in names],
            mcp_servers={n: servers[n] for n in names},  # pyright: ignore[reportArgumentType]
            system_prompt=system_prompt(inp.profile),
            model=self.model,
            max_turns=inp.env.max_turns,
            cwd=inp.env.trial_dir,
            env={**TELEMETRY_ENV, **CACHE_ENV, "CLAUDE_CONFIG_DIR": str(config_dir), **inp.env.credentials},
        )

    async def _converse(
        self,
        client: Any,
        inp: AgentInput,
        collector: AnswerCollector,
        sink: TextIO,
        messages: list[Any],
        session: dict[str, Any],
    ) -> None:
        """Connect, check for leaked servers, ask, and stream into `messages` and the transcript until the result."""
        await client.connect()
        status = await client.get_mcp_status()
        session["mcp_status"] = status
        servers = (status or {}).get("mcpServers", [])
        extra = sorted({s["name"] for s in servers} - mcp_servers_of(inp.profile))
        if extra:
            raise LeakedServerError(f"unexpected MCP server(s) loaded: {', '.join(extra)}")
        await client.query(inp.prompt)
        interrupted = False
        async for msg in client.receive_response():
            messages.append(msg)
            sink.write(transcript_line(msg) + "\n")
            sink.flush()
            if collector.submission is not None and not interrupted:
                interrupted = True
                await client.interrupt()

    def _session_line(
        self,
        inp: AgentInput,
        options: ClaudeAgentOptions,
        session: dict[str, Any],
        end_reason: EndReason,
        error: str | None,
        collector: AnswerCollector,
    ) -> dict[str, Any]:
        """The transcript's closing line: everything needed to read the session without the run's other files."""
        servers = dict(options.mcp_servers) if isinstance(options.mcp_servers, dict) else {}
        return {
            "type": "Session",
            "model": self.model,
            "profile": inp.profile,
            "system_prompt": options.system_prompt,
            "prompt": inp.prompt,
            "max_turns": inp.env.max_turns,
            "timeout_s": inp.env.timeout_s,
            "slayer_server": {k: v for k, v in servers.get(SLAYER_SERVER, {}).items() if k != "env"},
            "mcp_status": session.get("mcp_status"),
            "end_reason": end_reason,
            "error": error,
            "submission": collector.submission.model_dump() if collector.submission else None,
        }

    async def run(self, inp: AgentInput) -> AgentOutcome:
        config_dir = Path(tempfile.mkdtemp(prefix="slayer-evals-claude-"))
        (config_dir / ".claude.json").write_text(json.dumps(CLAUDE_JSON))
        collector = AnswerCollector()
        options = self.build_options(inp, config_dir, collector)
        client = self.client_factory(options)
        messages: list[Any] = []
        session: dict[str, Any] = {}
        end_reason: EndReason = "error"
        error: str | None = None
        start = time.monotonic()
        inp.env.transcript_path.parent.mkdir(parents=True, exist_ok=True)
        with inp.env.transcript_path.open("w") as sink:
            try:
                async with asyncio.timeout(inp.env.timeout_s):
                    await self._converse(client, inp, collector, sink, messages, session)
                result = next((m for m in reversed(messages) if isinstance(m, ResultMessage)), None)
                end_reason, error = _end_reason(result, collector.submission is not None)
            except TimeoutError:
                end_reason = "submitted" if collector.submission is not None else "timeout"
            except LeakedServerError as exc:
                error = str(exc)
            except Exception as exc:  # noqa: BLE001 - any SDK or transport failure ends the trial, keeping what streamed so far
                end_reason = "submitted" if collector.submission is not None else "error"
                error = f"{type(exc).__name__}: {exc}"
            finally:
                with contextlib.suppress(Exception):
                    await asyncio.wait_for(client.disconnect(), timeout=TEARDOWN_TIMEOUT_S)
                shutil.rmtree(config_dir, ignore_errors=True)
            sink.write(json.dumps(self._session_line(inp, options, session, end_reason, error, collector), default=str))
            sink.write("\n")
        trace = normalize_messages(
            messages, end_reason=end_reason, error=error, python_audits=collector.python_audits, profile=inp.profile
        )
        trace.duration_s = time.monotonic() - start
        return AgentOutcome(submission=collector.submission, trace=trace)
