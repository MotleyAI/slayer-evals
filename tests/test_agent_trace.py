"""Trace normalization from SDK messages."""

from claude_agent_sdk import AssistantMessage, ToolResultBlock, ToolUseBlock, UserMessage

from slayer_evals.agents.claude import normalize_messages
from slayer_evals.core import AuditEvent, PythonAudit, Trace
from tests.fake_sdk import result_message, text_turn, tool_result, tool_use, turn_usage
from tests.helpers import mcp_fixture


def test_tool_calls_normalized():
    ok = mcp_fixture("query_markdown")
    err = mcp_fixture("query_error_granularity")
    created = mcp_fixture("create_model_from_query")
    msgs = [
        tool_use("a", "mcp__slayer__query", ok["args"], message_id="m1"),
        tool_result("a", ok["text"]),
        tool_use("b", "mcp__slayer__query", err["args"], message_id="m2"),
        tool_result("b", err["text"], is_error=True),
        tool_use("c", "mcp__slayer__create_model", created["args"], message_id="m3"),
        tool_result("c", created["text"], as_list=False),
        result_message(),
    ]
    trace = normalize_messages(msgs, end_reason="submitted")
    assert [c.tool for c in trace.calls] == ["query", "query", "create_model"]
    q, e, c = trace.calls
    assert q.args == ok["args"]
    assert q.result_text == ok["text"]
    assert not q.is_error
    assert q.parsed is not None
    assert "orders_flat.region_total" in q.parsed.columns
    assert e.is_error
    assert e.result_text == err["text"]
    assert c.parsed is None
    assert c.result_text == created["text"]


def test_parallel_tool_calls_matched_by_id():
    a, b = mcp_fixture("query_json"), mcp_fixture("query_json_dates")
    msgs = [
        AssistantMessage(
            content=[
                ToolUseBlock(id="x", name="mcp__slayer__query", input=a["args"]),
                ToolUseBlock(id="y", name="mcp__slayer__query", input=b["args"]),
            ],
            model="m",
        ),
        UserMessage(
            content=[
                ToolResultBlock(tool_use_id="y", content=[{"type": "text", "text": b["text"]}]),
                ToolResultBlock(tool_use_id="x", content=[{"type": "text", "text": a["text"]}]),
            ]
        ),
    ]
    trace = normalize_messages(msgs, end_reason="error")
    assert [c.args for c in trace.calls] == [a["args"], b["args"]]
    assert [c.result_text for c in trace.calls] == [a["text"], b["text"]]


def test_call_without_result_kept():
    trace = normalize_messages([tool_use("a", "mcp__slayer__query", {"query": "monthly_rev"})], end_reason="timeout")
    assert len(trace.calls) == 1
    assert trace.calls[0].result_text == ""
    assert trace.end_reason == "timeout"


def test_usage_from_result_message():
    msgs = [text_turn("x", message_id="m1", usage=turn_usage()), result_message(turns=7, cost=0.5)]
    trace = normalize_messages(msgs, end_reason="submitted")
    assert trace.usage.input_tokens == 1000
    assert trace.usage.output_tokens == 200
    assert trace.usage.cache_read_tokens == 5000
    assert trace.usage.cache_write_tokens == 300
    assert not trace.usage.partial
    assert trace.turns == 7
    assert trace.cost_usd == 0.5


def test_usage_fallback_deduplicated():
    u1, u2 = turn_usage(inp=10, out=1, read=2, write=3), turn_usage(inp=20, out=2, read=4, write=6)
    msgs = [
        text_turn("a", message_id="m1", usage=u1),
        text_turn("b", message_id="m1", usage=u1),
        text_turn("c", message_id="m2", usage=u2),
    ]
    trace = normalize_messages(msgs, end_reason="error", error="boom")
    u = trace.usage
    assert u.partial
    assert (u.input_tokens, u.output_tokens, u.cache_read_tokens, u.cache_write_tokens) == (30, 3, 6, 9)
    assert trace.error == "boom"
    assert trace.cost_usd is None


def test_python_audits_attached_in_order():
    audits = [
        PythonAudit(sandbox_dir="/s", allowed_prefixes=[], events=[AuditEvent(event="open", path="/s/a")]),
        PythonAudit(sandbox_dir="/s", allowed_prefixes=[], events=[AuditEvent(event="open", path="/etc/b")]),
    ]
    msgs = [
        tool_use("a", "mcp__bench__python", {"code": "1"}),
        tool_result("a", "1"),
        tool_use("q", "mcp__slayer__list_datasources", {}),
        tool_result("q", "- bench (duckdb)"),
        tool_use("b", "mcp__bench__python", {"code": "2"}),
        tool_result("b", "2"),
    ]
    trace = normalize_messages(msgs, end_reason="submitted", python_audits=audits)
    py = [c for c in trace.calls if c.tool == "python"]
    assert [c.audit for c in py] == audits
    assert next(c for c in trace.calls if c.tool == "list_datasources").audit is None


def test_trace_serializes():
    msgs = [
        tool_use("a", "mcp__slayer__query", {"query": "x"}),
        tool_result("a", "Error executing tool query: X: y", True),
    ]
    trace = normalize_messages(msgs, end_reason="error")
    assert Trace.model_validate_json(trace.model_dump_json()) == trace
