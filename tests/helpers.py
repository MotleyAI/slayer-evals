"""Shared builders for tests: traces, tasks, captured MCP responses and in-process SDK servers."""

import json
from pathlib import Path
from typing import Any

import yaml
from mcp.types import CallToolRequest, CallToolRequestParams, ListToolsRequest

from slayer_evals.core import (
    ParsedResult,
    ResultWarning,
    SavedMeasure,
    SavedQuery,
    StoreManifest,
    Submission,
    Table,
    Task,
    ToolCall,
    Trace,
)

REPO = Path(__file__).resolve().parent.parent
MCP_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "mcp"


def mcp_fixture(name: str) -> dict[str, Any]:
    """A response captured from a real `slayer mcp` (tool, args, is_error, text)."""
    return json.loads((MCP_FIXTURES / f"{name}.json").read_text())


def make_task(**overrides: Any) -> Task:
    doc: dict[str, Any] = {
        "id": "q1-region-total",
        "row": "Q1",
        "prompt": "Revenue per region and city, with each region's total revenue alongside.",
        "truth_sql": "select 1",
        "compare": {"keys": ["region", "city"], "values": ["region_total"]},
    }
    doc.update(overrides)
    return Task.model_validate(doc)


def write_task(directory: Path, doc: dict[str, Any], name: str | None = None) -> Path:
    path = directory / f"{name or doc.get('id', 'task')}.yaml"
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    return path


def query_call(
    query: Any,
    columns: list[str],
    rows: list[list[Any]],
    warnings: list[str] | None = None,
    **extra_args: Any,
) -> ToolCall:
    """A successful `query` call whose parsed result is (columns, rows)."""
    data = [dict(zip(columns, r)) for r in rows]
    kinds = warnings or []
    text = json.dumps({"data": data, "warnings": [{"kind": k} for k in kinds]})
    return ToolCall(
        tool="query",
        args={"query": query, **extra_args},
        result_text=text,
        parsed=ParsedResult(columns=columns, rows=rows, warnings=[ResultWarning(kind=k, message=k) for k in kinds]),
    )


def error_call(tool: str, args: dict[str, Any], text: str) -> ToolCall:
    return ToolCall(tool=tool, args=args, result_text=text, is_error=True)


def plain_call(tool: str, args: dict[str, Any], text: str = "ok") -> ToolCall:
    return ToolCall(tool=tool, args=args, result_text=text)


def trace_of(*calls: ToolCall) -> Trace:
    return Trace(calls=list(calls))


def submission_of(table: Table, message: str = "") -> Submission:
    return Submission(columns=list(table.columns), rows=[list(r) for r in table.rows], message=message)


def manifest_with_aov() -> StoreManifest:
    return StoreManifest(
        datasource="bench",
        models=["orders", "customers", "regions", "monthly_rev"],
        measures=[SavedMeasure(model="orders", name="aov", formula="sum(amount) / count(*)")],
        queries=[
            SavedQuery(
                name="monthly_rev",
                query={
                    "source_model": "orders",
                    "time_dimensions": [{"dimension": "order_date", "granularity": "month"}],
                    "measures": [{"formula": "sum(amount)", "name": "rev"}],
                },
            )
        ],
    )


def servers_of(options: Any) -> dict[str, Any]:
    """`ClaudeAgentOptions.mcp_servers` as the dict the agent builds."""
    assert isinstance(options.mcp_servers, dict)
    return dict(options.mcp_servers)


async def list_sdk_tools(server_config: Any) -> list[str]:
    """Tool names an in-process SDK MCP server advertises."""
    server = server_config["instance"]
    res = await server.request_handlers[ListToolsRequest](ListToolsRequest(method="tools/list"))
    return sorted(t.name for t in res.root.tools)


async def call_sdk_tool(server_config: Any, name: str, arguments: dict[str, Any]) -> tuple[bool, str]:
    """Call a tool of an in-process SDK MCP server; returns (is_error, text)."""
    server = server_config["instance"]
    req = CallToolRequest(method="tools/call", params=CallToolRequestParams(name=name, arguments=arguments))
    res = await server.request_handlers[CallToolRequest](req)
    text = "\n".join(c.text for c in res.root.content if c.type == "text")
    return bool(res.root.isError), text
