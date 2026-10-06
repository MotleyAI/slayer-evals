"""Hermetic Claude session options, sanitized SLayer env, profiles and `submit_answer`."""

import json
from pathlib import Path

import pytest

from slayer_evals.agents.claude import SLAYER_ENV_ALLOW, SYSTEM_PROMPT, AnswerCollector, ClaudeAgent, slayer_server_env
from slayer_evals.core import PROFILES, Profile, Submission
from slayer_evals.tasks import PROMPT_DENY_LIST
from tests.fake_sdk import MODEL, make_input
from tests.helpers import MCP_FIXTURES, call_sdk_tool, list_sdk_tools, servers_of

TELEMETRY = (
    "DISABLE_TELEMETRY",
    "DISABLE_ERROR_REPORTING",
    "DISABLE_AUTOUPDATER",
    "DISABLE_NON_ESSENTIAL_MODEL_CALLS",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC",
)
CREDENTIALS = ("CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")


def options(tmp_path: Path, profile: Profile = "slayer"):
    inp = make_input(tmp_path, profile=profile)
    config_dir = tmp_path / "cfg"
    config_dir.mkdir()
    return inp, ClaudeAgent(model=MODEL).build_options(inp, config_dir=config_dir, collector=AnswerCollector())


def test_hermetic_options(tmp_path: Path):
    inp, opts = options(tmp_path)
    assert opts.tools == []
    assert opts.setting_sources == []
    assert opts.model == MODEL
    assert opts.max_turns == inp.env.max_turns
    assert opts.cwd is not None
    assert Path(opts.cwd) == inp.env.trial_dir
    assert opts.env["CLAUDE_CONFIG_DIR"] == str(tmp_path / "cfg")
    for var in TELEMETRY:
        assert opts.env[var] == "1", var
    caching = [
        v
        for v in ("FORCE_PROMPT_CACHING_5M", "ENABLE_PROMPT_CACHING_1H", "DISABLE_PROMPT_CACHING")
        if opts.env.get(v) == "1"
    ]
    assert len(caching) == 1


def test_credentials_passed_to_agent_env(tmp_path: Path):
    inp, opts = options(tmp_path)
    for k, v in inp.env.credentials.items():
        assert opts.env[k] == v


def test_profile_servers(tmp_path: Path):
    _, opts = options(tmp_path)
    assert set(servers_of(opts)) == {"slayer", "bench"}


def test_slayer_server_runs_on_trial_store(tmp_path: Path):
    inp, opts = options(tmp_path)
    slayer = servers_of(opts)["slayer"]
    args = slayer["args"]
    start = args.index(inp.env.slayer_command[0])
    assert args[start : start + 2] == [inp.env.slayer_command[0], "mcp"]
    assert args[args.index("--storage") + 1] == str(inp.env.store_dir)


def test_slayer_launched_with_only_the_allow_list(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    for var in CREDENTIALS:
        monkeypatch.setenv(var, "secret-" + var)
    monkeypatch.setenv("SOME_UNRELATED_SECRET", "x")
    inp, opts = options(tmp_path)
    slayer = servers_of(opts)["slayer"]
    args = slayer["args"]
    assert Path(slayer["command"]).name == "env"
    assert args[0] == "-i"
    assignments = args[1 : args.index(inp.env.slayer_command[0])]
    assert {a.split("=", 1)[0] for a in assignments} <= set(SLAYER_ENV_ALLOW)
    assert not any("secret" in a for a in args)


def test_slayer_subprocess_has_no_credentials(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    for var in CREDENTIALS:
        monkeypatch.setenv(var, "secret-" + var)
    monkeypatch.setenv("SOME_UNRELATED_SECRET", "x")
    _, opts = options(tmp_path)
    env = servers_of(opts)["slayer"]["env"]
    for var in CREDENTIALS:
        assert var not in env
    assert "SOME_UNRELATED_SECRET" not in env
    assert "PATH" in env


def test_slayer_server_env_is_allow_list():
    env = slayer_server_env(
        {
            "PATH": "/bin",
            "HOME": "/home/u",
            "ANTHROPIC_API_KEY": "k",
            "CLAUDE_CODE_OAUTH_TOKEN": "t",
            "AWS_SECRET_ACCESS_KEY": "a",
            "OPENAI_API_KEY": "o",
        }
    )
    assert env["PATH"] == "/bin"
    for var in ("ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN", "AWS_SECRET_ACCESS_KEY", "OPENAI_API_KEY"):
        assert var not in env


async def test_profile_tool_sets(tmp_path: Path):
    _, plain = options(tmp_path / "a")
    _, with_py = options(tmp_path / "b", profile="slayer+python")
    assert await list_sdk_tools(servers_of(plain)["bench"]) == ["submit_answer"]
    assert await list_sdk_tools(servers_of(with_py)["bench"]) == ["python", "submit_answer"]
    assert set(servers_of(with_py)) == {"slayer", "bench"}


def test_system_prompt_generic_and_shared(tmp_path: Path):
    _, a = options(tmp_path / "a")
    _, b = options(tmp_path / "b", profile="slayer+python")
    assert a.system_prompt == b.system_prompt == SYSTEM_PROMPT
    low = SYSTEM_PROMPT.lower()
    for kw in PROMPT_DENY_LIST:
        assert kw.lower() not in low, kw
    for word in ("partition", "rolling", "rank", "re-aggregat", "time shift", "Q1"):
        assert word.lower() not in low, word


def test_prompt_is_not_in_system_prompt(tmp_path: Path):
    inp, opts = options(tmp_path)
    assert inp.prompt not in str(opts.system_prompt)


async def test_submit_answer_accepts_valid(tmp_path: Path):
    collector = AnswerCollector()
    inp = make_input(tmp_path)
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    opts = ClaudeAgent(model=MODEL).build_options(inp, config_dir=cfg, collector=collector)
    bench = servers_of(opts)["bench"]
    args = {"columns": ["region", "total"], "rows": [["North", 1.5], ["South", None]], "message": "done"}
    is_error, _ = await call_sdk_tool(bench, "submit_answer", args)
    assert not is_error
    assert collector.submission == Submission(**args)


async def test_ragged_submission_rejected(tmp_path: Path):
    collector = AnswerCollector()
    inp = make_input(tmp_path)
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    opts = ClaudeAgent(model=MODEL).build_options(inp, config_dir=cfg, collector=collector)
    bench = servers_of(opts)["bench"]
    is_error, text = await call_sdk_tool(
        bench, "submit_answer", {"columns": ["a", "b"], "rows": [[1, 2], [3]], "message": ""}
    )
    assert is_error
    assert text
    assert collector.submission is None
    is_error, _ = await call_sdk_tool(bench, "submit_answer", {"columns": ["a", "b"], "rows": [[1, 2]], "message": ""})
    assert not is_error
    assert collector.submission is not None


async def test_first_submission_wins(tmp_path: Path):
    collector = AnswerCollector()
    inp = make_input(tmp_path)
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    bench = servers_of(ClaudeAgent(model=MODEL).build_options(inp, config_dir=cfg, collector=collector))["bench"]
    await call_sdk_tool(bench, "submit_answer", {"columns": ["a"], "rows": [[1]], "message": "first"})
    await call_sdk_tool(bench, "submit_answer", {"columns": ["a"], "rows": [[2]], "message": "second"})
    assert collector.submission is not None
    assert collector.submission.message == "first"


def test_every_slayer_tool_offered(tmp_path: Path):
    names = json.loads((MCP_FIXTURES / "tool_names.json").read_text())
    for profile in PROFILES:
        _, opts = options(tmp_path / profile.replace("+", "_"), profile=profile)
        offered = {f"mcp__slayer__{n}" for n in names}
        assert not offered & set(opts.disallowed_tools)
        assert not any(t.startswith("mcp__slayer") for t in opts.disallowed_tools)
        if opts.allowed_tools:
            assert offered <= set(opts.allowed_tools) or "mcp__slayer" in opts.allowed_tools


def test_system_prompt_asks_for_json_results():
    assert 'format="json"' in SYSTEM_PROMPT


def test_system_prompt_names_the_submit_tool_exactly():
    assert "mcp__bench__submit_answer" in SYSTEM_PROMPT
