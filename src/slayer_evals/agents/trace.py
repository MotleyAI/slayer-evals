"""Normalizing Claude Agent SDK messages into the agent-agnostic `Trace`."""

import json
from typing import Any

from claude_agent_sdk import AssistantMessage, ResultMessage, ToolResultBlock, ToolUseBlock, UserMessage

from slayer_evals.core import EndReason, ParsedResult, PythonAudit, ToolCall, Trace, Usage

PYTHON_TOOL = "python"


def tool_name(name: str) -> str:
    """`mcp__<server>__<tool>` → `<tool>`."""
    return name.split("__", 2)[2] if name.startswith("mcp__") and name.count("__") >= 2 else name


def _unwrap(text: str) -> str:
    """The CLI hands a tool's structured content back as `{"result": "<text>"}`; return the tool's own text."""
    if not text.startswith('{"result"'):
        return text
    try:
        payload = json.loads(text)
    except ValueError:
        return text
    if isinstance(payload, dict) and set(payload) == {"result"} and isinstance(payload["result"], str):
        return payload["result"]
    return text


def result_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return _unwrap(content)
    texts = [str(c.get("text", "")) for c in content if isinstance(c, dict) and c.get("type", "text") == "text"]
    return "\n".join(_unwrap(t) for t in texts)


def _usage(raw: dict[str, Any] | None) -> tuple[int, int, int, int]:
    raw = raw or {}
    return (
        int(raw.get("input_tokens") or 0),
        int(raw.get("output_tokens") or 0),
        int(raw.get("cache_read_input_tokens") or 0),
        int(raw.get("cache_creation_input_tokens") or 0),
    )


def _fallback_usage(messages: list[Any]) -> tuple[Usage, int]:
    """Per-turn usage summed once per assistant message id (one API turn may span several messages)."""
    seen: dict[str, dict[str, Any] | None] = {}
    for k, msg in enumerate(messages):
        if isinstance(msg, AssistantMessage):
            seen.setdefault(msg.message_id or f"anon-{k}", msg.usage)
    totals = [sum(col) for col in zip(*(_usage(u) for u in seen.values()), strict=True)] or [0, 0, 0, 0]
    usage = Usage(
        input_tokens=totals[0],
        output_tokens=totals[1],
        cache_read_tokens=totals[2],
        cache_write_tokens=totals[3],
        partial=True,
    )
    return usage, len(seen)


def normalize_messages(
    messages: list[Any],
    end_reason: EndReason,
    error: str | None = None,
    python_audits: list[PythonAudit] | None = None,
) -> Trace:
    order: list[str] = []
    calls: dict[str, ToolCall] = {}
    result: ResultMessage | None = None
    for msg in messages:
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, ToolUseBlock):
                    order.append(block.id)
                    calls[block.id] = ToolCall(tool=tool_name(block.name), args=dict(block.input))
        elif isinstance(msg, UserMessage) and isinstance(msg.content, list):
            for block in msg.content:
                if isinstance(block, ToolResultBlock) and block.tool_use_id in calls:
                    call = calls[block.tool_use_id]
                    call.result_text = result_text(block.content)
                    call.is_error = bool(block.is_error)
                    if call.tool == "query" and not call.is_error:
                        call.parsed = ParsedResult.from_text(call.result_text)
        elif isinstance(msg, ResultMessage):
            result = msg
    ordered = [calls[i] for i in order]
    audits = iter(python_audits or [])
    for call in ordered:
        if call.tool == PYTHON_TOOL:
            call.audit = next(audits, None)
    if result is not None:
        inp, out, read, write = _usage(result.usage)
        usage = Usage(input_tokens=inp, output_tokens=out, cache_read_tokens=read, cache_write_tokens=write)
        turns, cost = result.num_turns, result.total_cost_usd
    else:
        usage, turns = _fallback_usage(messages)
        cost = None
    return Trace(calls=ordered, usage=usage, cost_usd=cost, turns=turns, end_reason=end_reason, error=error)


def _jsonable(obj: Any) -> Any:
    if hasattr(obj, "__dict__"):
        return {"type": type(obj).__name__, **vars(obj)}
    return str(obj)


def transcript_line(msg: Any) -> str:
    return json.dumps(_jsonable(msg), default=_jsonable)
