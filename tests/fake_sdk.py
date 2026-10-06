"""A scripted stand-in for `ClaudeSDKClient` and builders for SDK messages."""

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, Self

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

from slayer_evals.core import AgentInput, Profile, TrialEnv
from tests.helpers import call_sdk_tool, servers_of

MODEL = "claude-opus-5-5"


def turn_usage(inp: int = 100, out: int = 10, read: int = 50, write: int = 5) -> dict[str, int]:
    return {
        "input_tokens": inp,
        "output_tokens": out,
        "cache_read_input_tokens": read,
        "cache_creation_input_tokens": write,
    }


def tool_use(tid: str, name: str, args: dict[str, Any], message_id: str | None = None, usage=None) -> AssistantMessage:
    return AssistantMessage(
        content=[ToolUseBlock(id=tid, name=name, input=args)], model=MODEL, message_id=message_id, usage=usage
    )


def text_turn(text: str, message_id: str | None = None, usage=None) -> AssistantMessage:
    return AssistantMessage(content=[TextBlock(text=text)], model=MODEL, message_id=message_id, usage=usage)


def tool_result(tid: str, text: str, is_error: bool = False, as_list: bool = True) -> UserMessage:
    content: Any = [{"type": "text", "text": text}] if as_list else text
    return UserMessage(content=[ToolResultBlock(tool_use_id=tid, content=content, is_error=is_error)])


def result_message(
    subtype: str = "success", is_error: bool = False, turns: int = 3, cost: float = 0.12, result: str | None = None
) -> ResultMessage:
    return ResultMessage(
        result=result,
        subtype=subtype,
        duration_ms=4000,
        duration_api_ms=3500,
        is_error=is_error,
        num_turns=turns,
        session_id="s1",
        total_cost_usd=cost,
        usage={
            "input_tokens": 1000,
            "output_tokens": 200,
            "cache_read_input_tokens": 5000,
            "cache_creation_input_tokens": 300,
        },
    )


class CallLocal:
    """Script step: call a tool of the in-process `bench` server and yield its result message."""

    def __init__(self, tid: str, name: str, args: dict[str, Any]):
        self.tid, self.name, self.args = tid, name, args


class Hang:
    """Script step: never yield again."""


class Raise:
    def __init__(self, exc: BaseException):
        self.exc = exc


class FakeClient:
    def __init__(self, options: ClaudeAgentOptions, script: list[Any], servers: list[str] | None = None):
        self.options = options
        self.script = script
        self.servers = servers
        self.prompt: str | None = None
        self.interrupted = False
        self.connected = False
        self.config_dir_seen: Path | None = None

    async def __aenter__(self) -> Self:
        await self.connect()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.disconnect()

    async def connect(self, prompt: Any = None) -> None:
        self.connected = True
        self.config_dir_seen = Path(self.options.env["CLAUDE_CONFIG_DIR"])
        assert self.config_dir_seen.is_dir()

    async def disconnect(self) -> None:
        self.connected = False

    async def get_mcp_status(self) -> dict[str, Any]:
        names = self.servers if self.servers is not None else list(servers_of(self.options))
        return {"mcpServers": [{"name": n, "status": "connected"} for n in names]}

    async def query(self, prompt: str, session_id: str = "default") -> None:
        self.prompt = prompt

    async def interrupt(self) -> None:
        self.interrupted = True

    async def receive_response(self) -> AsyncIterator[Any]:
        for step in self.script:
            if isinstance(step, CallLocal):
                servers = servers_of(self.options)
                is_error, text = await call_sdk_tool(servers["bench"], step.name, step.args)
                yield tool_result(step.tid, text, is_error=is_error)
            elif isinstance(step, Hang):
                await asyncio.sleep(3600)
            elif isinstance(step, Raise):
                raise step.exc
            else:
                yield step


def make_input(tmp: Path, profile: Profile = "slayer", timeout_s: float = 60.0, max_turns: int = 60) -> AgentInput:
    trial = tmp / "trial"
    (trial / "store").mkdir(parents=True, exist_ok=True)
    return AgentInput(
        prompt="Revenue per region and city, with each region's total alongside.",
        profile=profile,
        env=TrialEnv(
            trial_dir=trial,
            store_dir=trial / "store",
            db_path=trial / "bench.duckdb",
            slayer_command=["/opt/slayer/bin/slayer"],
            credentials={
                "CLAUDE_CODE_OAUTH_TOKEN": "sk-ant-oat01-test",
                "ANTHROPIC_API_KEY": "",
                "ANTHROPIC_AUTH_TOKEN": "",
            },
            max_turns=max_turns,
            timeout_s=timeout_s,
            transcript_path=trial / "transcript.jsonl",
        ),
    )
