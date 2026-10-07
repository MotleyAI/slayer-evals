"""ClaudeAgent.run against a scripted client: submission, leak abort, budgets, usage fallback."""

import json
from pathlib import Path
from typing import Any

import pytest

from slayer_evals.agents.claude import ClaudeAgent
from slayer_evals.core import PROFILES, AgentOutcome, Profile, Submission
from tests.fake_sdk import (
    MODEL,
    CallLocal,
    FakeClient,
    Hang,
    Raise,
    make_input,
    result_message,
    text_turn,
    tool_result,
    tool_use,
    turn_usage,
)
from tests.helpers import mcp_fixture

ANSWER = {"columns": ["region", "city", "region_total"], "rows": [["North", "Oslo", 705.0]], "message": "done"}


def agent(script: list[Any], servers: list[str] | None = None) -> tuple[ClaudeAgent, list[FakeClient]]:
    made: list[FakeClient] = []

    def factory(options):
        client = FakeClient(options, script, servers)
        made.append(client)
        return client

    return ClaudeAgent(model=MODEL, client_factory=factory), made


def submitted_script() -> list[Any]:
    fx = mcp_fixture("query_json")
    return [
        tool_use("t1", "mcp__slayer__query", fx["args"], message_id="m1", usage=turn_usage()),
        tool_result("t1", fx["text"]),
        tool_use("t2", "mcp__bench__submit_answer", ANSWER, message_id="m2", usage=turn_usage()),
        CallLocal("t2", "submit_answer", ANSWER),
        result_message(),
    ]


async def test_submitted(tmp_path: Path):
    a, made = agent(submitted_script())
    inp = make_input(tmp_path)
    out = await a.run(inp)
    assert isinstance(out, AgentOutcome)
    assert out.submission == Submission(**ANSWER)
    assert out.trace.end_reason == "submitted"
    assert made[0].prompt == inp.prompt
    assert made[0].interrupted
    query = [c for c in out.trace.calls if c.tool == "query"]
    assert len(query) == 1
    assert query[0].parsed is not None
    assert not query[0].is_error
    assert out.trace.usage.input_tokens == 1000
    assert out.trace.usage.cache_read_tokens == 5000
    assert not out.trace.usage.partial
    assert out.trace.cost_usd == 0.12


@pytest.mark.parametrize("profile", PROFILES)
async def test_trace_carries_the_profile(tmp_path: Path, profile: Profile):
    a, _ = agent(submitted_script())
    out = await a.run(make_input(tmp_path, profile=profile))
    assert out.trace.profile == profile


async def test_slayer_reported_in_raw_sql_profile_aborts(tmp_path: Path):
    a, made = agent(submitted_script(), servers=["bench", "slayer"])
    out = await a.run(make_input(tmp_path, profile="sql+python"))
    assert out.trace.end_reason == "error"
    assert out.trace.error is not None
    assert "slayer" in out.trace.error
    assert out.submission is None
    assert made[0].prompt is None


async def test_raw_sql_profile_runs_with_only_bench(tmp_path: Path):
    a, _ = agent(submitted_script(), servers=["bench"])
    out = await a.run(make_input(tmp_path, profile="sql+python"))
    assert out.trace.end_reason == "submitted"
    assert out.submission == Submission(**ANSWER)


async def test_session_line_names_no_slayer_server_in_raw_sql(tmp_path: Path):
    a, _ = agent(submitted_script(), servers=["bench"])
    inp = make_input(tmp_path, profile="sql+python")
    await a.run(inp)
    session = json.loads(inp.env.transcript_path.read_text().splitlines()[-1])
    assert session["profile"] == "sql+python"
    assert not session["slayer_server"]


async def test_config_dir_is_fresh_and_removed(tmp_path: Path):
    a, made = agent(submitted_script())
    await a.run(make_input(tmp_path))
    seen = made[0].config_dir_seen
    assert seen is not None
    assert not seen.exists()


async def test_leaked_server_aborts(tmp_path: Path):
    a, made = agent(submitted_script(), servers=["slayer", "bench", "claude_ai_Gmail"])
    out = await a.run(make_input(tmp_path))
    assert out.trace.end_reason == "error"
    assert out.trace.error is not None
    assert "claude_ai_Gmail" in out.trace.error
    assert out.submission is None
    assert made[0].prompt is None


async def test_timeout_keeps_transcript(tmp_path: Path):
    script = [text_turn("let me look at the models", message_id="m1", usage=turn_usage()), Hang()]
    a, _ = agent(script)
    inp = make_input(tmp_path, timeout_s=0.5)
    out = await a.run(inp)
    assert out.trace.end_reason == "timeout"
    lines = inp.env.transcript_path.read_text().splitlines()
    assert lines
    assert "let me look at the models" in lines[0]
    json.loads(lines[0])


async def test_max_turns(tmp_path: Path):
    script = [
        text_turn("thinking", message_id="m1"),
        result_message(subtype="error_max_turns", is_error=True, turns=60),
    ]
    a, _ = agent(script)
    out = await a.run(make_input(tmp_path, max_turns=60))
    assert out.trace.end_reason == "max_turns"
    assert out.submission is None


async def test_api_error_surfaces_the_message(tmp_path: Path):
    overloaded = "API Error: 529 Overloaded. This is a server-side issue, usually temporary."
    script = [result_message(is_error=True, turns=1, result=overloaded)]
    a, _ = agent(script)
    out = await a.run(make_input(tmp_path))
    assert out.trace.end_reason == "error"
    assert out.trace.error == f"session ended with an error: {overloaded}"


async def test_error_with_partial_usage(tmp_path: Path):
    shared = turn_usage(inp=100, out=10, read=50, write=5)
    script = [
        tool_use("t1", "mcp__slayer__list_datasources", {}, message_id="m1", usage=shared),
        text_turn("same turn, second block", message_id="m1", usage=shared),
        text_turn("next turn", message_id="m2", usage=turn_usage(inp=200, out=20, read=60, write=6)),
        Raise(RuntimeError("stream broke")),
    ]
    a, _ = agent(script)
    out = await a.run(make_input(tmp_path))
    assert out.trace.end_reason == "error"
    assert out.trace.error is not None
    assert "stream broke" in out.trace.error
    u = out.trace.usage
    assert u.partial
    assert (u.input_tokens, u.output_tokens, u.cache_read_tokens, u.cache_write_tokens) == (300, 30, 110, 11)


async def test_python_audit_reaches_trace(tmp_path: Path):
    code = "print(open('/etc/hostname').read()[:0] + 'hi')"
    script = [
        tool_use("t1", "mcp__bench__python", {"code": code}, message_id="m1"),
        CallLocal("t1", "python", {"code": code}),
        tool_use("t2", "mcp__bench__submit_answer", ANSWER, message_id="m2"),
        CallLocal("t2", "submit_answer", ANSWER),
        result_message(),
    ]
    a, _ = agent(script)
    out = await a.run(make_input(tmp_path, profile="slayer+python"))
    py = [c for c in out.trace.calls if c.tool == "python"]
    assert len(py) == 1
    assert py[0].audit is not None
    assert "/etc/hostname" in [e.path for e in py[0].audit.events]
    assert "hi" in py[0].result_text
