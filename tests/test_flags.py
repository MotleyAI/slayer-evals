"""Trace flags: informational facts read off the trace, independent of passing."""

from typing import Any

import pytest

from slayer_evals.core import AuditEvent, PythonAudit, Table, ToolCall, TraceFlags
from slayer_evals.grading import grade, trace_flags
from tests.helpers import error_call, make_task, plain_call, query_call, submission_of, trace_of

TRUTH = Table(columns=["v"], rows=[[42.0]])
PLAIN = {"source_model": "orders", "measures": [{"formula": "sum(amount)", "name": "v"}]}


def answer() -> ToolCall:
    return query_call(PLAIN, ["orders.v"], [[42.0]])


def python_call() -> ToolCall:
    audit = PythonAudit(sandbox_dir="/s", events=[AuditEvent(event="open", path="/etc/hosts")])
    return ToolCall(tool="python", args={"code": "print(1)"}, result_text="1", audit=audit)


def inline(column: dict[str, Any]) -> ToolCall:
    q = {
        "source_model": {"source_name": "orders", "columns": [column]},
        "measures": [{"formula": "sum(x)", "name": "v"}],
    }
    return query_call(q, ["orders.v"], [[42.0]])


def test_clean_trace_has_no_flags():
    assert trace_flags([answer()]) == TraceFlags()


def test_used_python():
    assert trace_flags([answer(), python_call()]).used_python


@pytest.mark.parametrize(
    "call",
    [
        plain_call("create_model", {"name": "agg", "sql": "select customer_id, sum(amount) from orders group by 1"}),
        plain_call(
            "create_model", {"name": "o2", "sql_table": "orders", "columns": [{"name": "n", "sql": "amount * 2"}]}
        ),
        plain_call("edit_model", {"model_name": "orders", "columns": [{"name": "a", "filter": "status = 'ok'"}]}),
        plain_call("edit_model", {"model_name": "orders", "aggregations": [{"name": "s", "formula": "SUM({value})"}]}),
        plain_call("edit_model", {"model_name": "orders", "add_filters": ["amount > 0"]}),
        plain_call(
            "edit_model",
            {"model_name": "m", "source_queries": [{"source_model": {"source_name": "orders", "sql": "x"}}]},
        ),
        inline({"name": "x", "sql": "amount * 1.1", "type": "number"}),
        plain_call(
            "create_model",
            {
                "name": "qb",
                "query": {"source_model": {"source_name": "orders", "columns": [{"name": "x", "sql": "1"}]}},
            },
        ),
    ],
)
def test_raw_sql(call: ToolCall):
    assert trace_flags([call]).raw_sql


def test_query_backed_model_is_not_raw_sql():
    create = plain_call("create_model", {"name": "per_cust", "query": PLAIN})
    flags = trace_flags([create])
    assert not flags.raw_sql
    assert flags.edited_models


def test_slayer_errors_and_several_queries():
    flags = trace_flags([error_call("query", {"query": PLAIN}, "Error executing tool query: X: y"), answer()])
    assert flags.slayer_errors
    assert flags.several_queries
    assert not trace_flags([answer()]).several_queries


def test_flags_do_not_affect_passing():
    create = plain_call("create_model", {"name": "agg", "sql": "select 1"})
    trace = trace_of(
        create, error_call("query", {"query": PLAIN}, "Error executing tool query: X: y"), answer(), python_call()
    )
    v = grade(make_task(id="t", compare={"values": ["v"]}), TRUTH, submission_of(TRUTH), trace)
    assert v.passed
    assert v.flags == TraceFlags(
        used_python=True, raw_sql=True, edited_models=True, slayer_errors=True, several_queries=True
    )
