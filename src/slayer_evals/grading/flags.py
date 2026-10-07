"""Informational trace flags: Python used, raw SQL, model edits, query errors, several queries."""

import json
from typing import Any

from slayer_evals.core import ToolCall, TraceFlags

PYTHON_TOOL = "python"
SQL_TOOL = "sql"
# Calls that neither query the data nor go to SLayer.
NON_QUERY_TOOLS = (PYTHON_TOOL, "submit_answer")
QUERY_TOOLS = ("query", SQL_TOOL)
MODEL_TOOLS = ("create_model", "edit_model")
_SQL_LIST_KEYS = ("add_filters", "filters")


def _decode(value: Any) -> Any:
    """JSON text an agent passed instead of an object, decoded; anything else unchanged."""
    if isinstance(value, str) and value.strip().startswith(("{", "[")):
        try:
            return json.loads(value)
        except ValueError:
            return value
    return value


def _items(value: Any) -> list[Any]:
    value = _decode(value)
    return value if isinstance(value, list) else [] if value is None else [value]


def _model_has_sql(model: dict[str, Any]) -> bool:
    """A model-shaped dict (tool args or an inline `source_model`) with any SQL-bearing field."""
    if isinstance(model.get("sql"), str) and model["sql"].strip():
        return True
    for col in _items(model.get("columns")):
        if isinstance(col, dict) and any(isinstance(col.get(k), str) and col[k].strip() for k in ("sql", "filter")):
            return True
    for agg in _items(model.get("aggregations")):
        if isinstance(agg, dict) and isinstance(agg.get("formula"), str) and agg["formula"].strip():
            return True
    return any(isinstance(f, str) and f.strip() for key in _SQL_LIST_KEYS for f in _items(model.get(key)))


def _query_has_sql(query: Any) -> bool:
    return any(
        isinstance(source := _decode(stage.get("source_model")), dict) and _model_has_sql(source)
        for stage in _items(query)
        if isinstance(stage, dict)
    )


def _has_sql(call: ToolCall) -> bool:
    if call.tool == SQL_TOOL:
        return True
    if call.tool in MODEL_TOOLS:
        return (
            _model_has_sql(call.args)
            or _query_has_sql(call.args.get("query"))
            or _query_has_sql(call.args.get("source_queries"))
        )
    return call.tool == "query" and _query_has_sql(call.args.get("query"))


def trace_flags(calls: list[ToolCall]) -> TraceFlags:
    data = [c for c in calls if c.tool not in NON_QUERY_TOOLS]
    return TraceFlags(
        used_python=any(c.tool == PYTHON_TOOL for c in calls),
        raw_sql=any(_has_sql(c) for c in data),
        edited_models=any(c.tool in MODEL_TOOLS for c in data),
        query_errors=any(c.is_error for c in data),
        several_queries=sum(c.tool in QUERY_TOOLS for c in data) > 1,
    )
