"""The Motley profiles in the Claude agent: servers, identity header, tools, system prompt, session line and trace."""

import json
from pathlib import Path
from typing import Any

import pytest

from slayer_evals.agents.claude import JSON_RESULTS_SENTENCE, AnswerCollector, ClaudeAgent
from slayer_evals.core import PROFILES, Profile, Submission
from tests.fake_sdk import (
    MODEL,
    MOTLEY_URL,
    MOTLEY_USER_ID,
    CallLocal,
    FakeClient,
    make_input,
    result_message,
    tool_result,
    tool_use,
)
from tests.helpers import list_sdk_tools, motley_json, servers_of

MOTLEY_PROFILES: tuple[Profile, ...] = ("motley", "motley+python")
ANSWER = {"columns": ["region", "rev"], "rows": [["North", 705.0]], "message": "done"}
HEADER = "X-Storyline-Dev-User-Id"


def options(tmp_path: Path, profile: Profile):
    inp = make_input(tmp_path, profile=profile)
    config_dir = tmp_path / "cfg"
    config_dir.mkdir()
    return inp, ClaudeAgent(model=MODEL).build_options(inp, config_dir=config_dir, collector=AnswerCollector())


@pytest.mark.parametrize("profile", MOTLEY_PROFILES)
def test_motley_servers(tmp_path: Path, profile: Profile):
    _, opts = options(tmp_path, profile)
    assert set(servers_of(opts)) == {"motley", "bench"}
    assert set(opts.allowed_tools) == {"mcp__motley", "mcp__bench"}
    assert not any(t.startswith("mcp__slayer") for t in opts.allowed_tools)
    assert not opts.disallowed_tools


@pytest.mark.parametrize("profile", MOTLEY_PROFILES)
def test_motley_server_is_http_with_the_identity_header(tmp_path: Path, profile: Profile):
    _, opts = options(tmp_path, profile)
    assert servers_of(opts)["motley"] == {"type": "http", "url": MOTLEY_URL, "headers": {HEADER: MOTLEY_USER_ID}}


def test_motley_server_uses_the_trials_url_and_user_id(tmp_path: Path):
    inp = make_input(tmp_path, profile="motley", motley_url="http://127.0.0.1:9123/api/v1/mcp/")
    inp.env.motley_user_id = "se-other-run-aaaaaaaaaaaa"
    config_dir = tmp_path / "cfg"
    config_dir.mkdir()
    opts = ClaudeAgent(model=MODEL).build_options(inp, config_dir=config_dir, collector=AnswerCollector())
    motley = servers_of(opts)["motley"]
    assert motley["url"] == "http://127.0.0.1:9123/api/v1/mcp/"
    assert motley["headers"] == {HEADER: "se-other-run-aaaaaaaaaaaa"}


async def test_motley_bench_tools(tmp_path: Path):
    _, plain = options(tmp_path / "a", "motley")
    _, with_py = options(tmp_path / "b", "motley+python")
    assert await list_sdk_tools(servers_of(plain)["bench"]) == ["submit_answer"]
    assert await list_sdk_tools(servers_of(with_py)["bench"]) == ["python", "submit_answer"]


def prompts(tmp_path: Path) -> dict[str, str]:
    return {p: str(options(tmp_path / p.replace("+", "_"), p)[1].system_prompt) for p in PROFILES}


def test_motley_system_prompt_equals_slayers(tmp_path: Path):
    by = prompts(tmp_path)
    assert by["motley"] == by["motley+python"] == by["slayer"]
    assert JSON_RESULTS_SENTENCE in by["motley"]
    assert JSON_RESULTS_SENTENCE not in by["sql+python"]


def test_system_prompt_does_not_name_motley(tmp_path: Path):
    for profile, prompt in prompts(tmp_path).items():
        assert "motley" not in prompt.lower(), profile
        assert "storyline" not in prompt.lower(), profile


def agent(script: list[Any], servers: list[str] | None = None) -> tuple[ClaudeAgent, list[FakeClient]]:
    made: list[FakeClient] = []

    def factory(opts):
        client = FakeClient(opts, script, servers)
        made.append(client)
        return client

    return ClaudeAgent(model=MODEL, client_factory=factory), made


def motley_script() -> list[Any]:
    query = {
        "source_model": "orders",
        "dimensions": ["region"],
        "measures": [{"formula": "sum(amount)", "name": "rev"}],
    }
    return [
        tool_use("t1", "mcp__motley__query", {"query": query}, message_id="m1"),
        tool_result("t1", motley_json(["orders.region", "orders.rev"], [["North", 705.0]])),
        tool_use("t2", "mcp__motley__create_document", {"title": "x"}, message_id="m2"),
        tool_result("t2", "You are not allowed to create documents here.", is_error=True),
        tool_use("t3", "mcp__bench__submit_answer", ANSWER, message_id="m3"),
        CallLocal("t3", "submit_answer", ANSWER),
        result_message(),
    ]


@pytest.mark.parametrize("profile", MOTLEY_PROFILES)
async def test_motley_session_submits(tmp_path: Path, profile: Profile):
    a, made = agent(motley_script())
    inp = make_input(tmp_path, profile=profile)
    out = await a.run(inp)
    assert out.trace.end_reason == "submitted", out.trace.error
    assert out.trace.profile == profile
    assert out.submission == Submission(**ANSWER)
    assert made[0].prompt == inp.prompt


async def test_motley_query_result_is_parsed(tmp_path: Path):
    a, _ = agent(motley_script())
    out = await a.run(make_input(tmp_path, profile="motley"))
    query, doc = out.trace.calls[0], out.trace.calls[1]
    assert query.tool == "query"
    assert query.parsed is not None
    assert (query.parsed.columns, query.parsed.rows) == (["orders.region", "orders.rev"], [["North", 705.0]])
    assert doc.tool == "create_document"
    assert doc.is_error
    assert doc.parsed is None


async def test_motley_session_line(tmp_path: Path):
    a, _ = agent(motley_script())
    inp = make_input(tmp_path, profile="motley")
    await a.run(inp)
    session = json.loads(inp.env.transcript_path.read_text().splitlines()[-1])
    assert session["profile"] == "motley"
    assert session["motley_server"] == {"url": MOTLEY_URL, "user_id": MOTLEY_USER_ID}
    assert not session["slayer_server"]


async def test_slayer_session_line_has_no_motley_server(tmp_path: Path):
    a, _ = agent(motley_script())
    inp = make_input(tmp_path, profile="slayer")
    await a.run(inp)
    session = json.loads(inp.env.transcript_path.read_text().splitlines()[-1])
    assert not session.get("motley_server")


@pytest.mark.parametrize("profile", MOTLEY_PROFILES)
async def test_slayer_reported_in_a_motley_profile_aborts(tmp_path: Path, profile: Profile):
    a, made = agent(motley_script(), servers=["motley", "bench", "slayer"])
    out = await a.run(make_input(tmp_path, profile=profile))
    assert out.trace.end_reason == "error"
    assert out.trace.error is not None
    assert "slayer" in out.trace.error
    assert out.submission is None
    assert made[0].prompt is None
