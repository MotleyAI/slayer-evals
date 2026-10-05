"""No-hack criterion: default-deny raw SQL, construct-specific allowances, Python access checks."""

from typing import Any

import pytest

from slayer_evals.core import AuditEvent, PythonAudit, Table, ToolCall
from slayer_evals.grading import grade
from tests.helpers import empty_manifest, make_task, plain_call, query_call, submission_of, trace_of

TRUTH = Table(columns=["v"], rows=[[42.0]])
SANDBOX = "/tmp/trial-1/sandbox"
PY_PREFIX = "/opt/python3.12"


def no_hack(task, *calls: ToolCall) -> tuple[bool, list[str]]:
    v = grade(task, TRUTH, empty_manifest(), submission_of(TRUTH), trace_of(*calls))
    return v.no_hack, v.no_hack_reasons


def task(allow: list[dict[str, Any]] | None = None):
    return make_task(id="t", compare={"values": ["v"]}, capabilities=[], allow=allow or [])


def inline(sql: str) -> ToolCall:
    q = {
        "source_model": {"source_name": "orders", "columns": [{"name": "x", "sql": sql, "type": "number"}]},
        "measures": [{"formula": "sum(x)", "name": "v"}],
    }
    return query_call(q, ["orders.v"], [[42.0]])


ROW_SCALAR = [{"construct": "inline_column_sql", "scope": "row_scalar"}]


def test_clean_trace():
    q = {"source_model": "orders", "measures": [{"formula": "sum(amount)", "name": "v"}]}
    assert no_hack(task(), query_call(q, ["orders.v"], [[42.0]]))[0]


def test_query_backed_model_is_not_sql():
    create = plain_call(
        "create_model",
        {
            "name": "per_cust",
            "query": {
                "source_model": "orders",
                "dimensions": ["customer_id"],
                "measures": [{"formula": "sum(amount)", "name": "rev"}],
            },
        },
    )
    assert no_hack(task(), create)[0]


def test_raw_aggregate_sql_in_model():
    call = plain_call(
        "create_model",
        {"name": "agg", "data_source": "bench", "sql": "select customer_id, sum(amount) as rev from orders GROUP BY 1"},
    )
    ok, reasons = no_hack(task(), call)
    assert not ok
    assert any("create_model" in r for r in reasons)


def test_model_sql_denied_even_if_trivial():
    call = plain_call("create_model", {"name": "o2", "data_source": "bench", "sql": "select * from orders"})
    assert not no_hack(task(), call)[0]


def test_column_sql_in_create_model():
    call = plain_call(
        "create_model",
        {
            "name": "o2",
            "sql_table": "orders",
            "data_source": "bench",
            "columns": [{"name": "net", "sql": "amount * 0.9", "type": "number"}],
        },
    )
    assert not no_hack(task(), call)[0]


def test_column_sql_in_edit_model():
    call = plain_call(
        "edit_model", {"model_name": "orders", "columns": [{"name": "net", "sql": "amount * 0.9", "type": "number"}]}
    )
    assert not no_hack(task(), call)[0]


def test_edit_model_sql_source():
    call = plain_call("edit_model", {"model_name": "orders", "sql": "select * from orders where amount > 0"})
    assert not no_hack(task(), call)[0]


def test_custom_aggregation_sql():
    call = plain_call(
        "create_model",
        {
            "name": "o2",
            "sql_table": "orders",
            "data_source": "bench",
            "aggregations": [{"name": "sum_sq", "formula": "SUM({value} * {value})"}],
        },
    )
    assert not no_hack(task(), call)[0]


def test_inline_column_sql_denied_by_default():
    assert not no_hack(task(), inline("amount * 1.1"))[0]


def test_allowed_scalar_inline_column():
    assert no_hack(task(ROW_SCALAR), inline("amount * 1.1"))[0]
    assert no_hack(task(ROW_SCALAR), inline("case when status = 'ok' then amount else 0 end"))[0]


@pytest.mark.parametrize(
    "sql",
    [
        "sum(amount) over ()",
        "SUM(amount)",
        '"sum"(amount)',
        "amount / (select max(amount) from orders)",
        "row_number() over (partition by customer_id order by order_date)",
        "amount /* harmless */ + (SELECT 1)",
        "max(amount) -- trailing comment",
        "count(distinct customer_id)",
        "amount * lag(amount) over (order by id)",
    ],
)
def test_scalar_allowance_rejects_aggregates_windows_subqueries(sql: str):
    assert not no_hack(task(ROW_SCALAR), inline(sql))[0], sql


def test_allowance_is_construct_specific():
    call = plain_call(
        "create_model",
        {
            "name": "o2",
            "sql_table": "orders",
            "data_source": "bench",
            "columns": [{"name": "net", "sql": "amount * 0.9", "type": "number"}],
        },
    )
    assert not no_hack(task(ROW_SCALAR), call)[0]
    assert no_hack(task([{"construct": "column_sql", "scope": "row_scalar"}]), call)[0]


def test_model_sql_cte_rejected_under_scalar_allowance():
    call = plain_call(
        "create_model",
        {"name": "o2", "data_source": "bench", "sql": "with t as (select * from orders) select * from t"},
    )
    assert not no_hack(task([{"construct": "model_sql", "scope": "row_scalar"}]), call)[0]


def test_inline_sql_inside_a_stage():
    stages = [
        {
            "name": "s1",
            "source_model": {
                "source_name": "orders",
                "columns": [{"name": "x", "sql": "sum(amount) over ()", "type": "number"}],
            },
            "dimensions": ["customer_id"],
            "measures": [{"formula": "max(x)", "name": "m"}],
        },
        {"source_model": "s1", "measures": [{"formula": "sum(m)", "name": "v"}]},
    ]
    assert not no_hack(task(ROW_SCALAR), query_call(stages, ["s1.v"], [[42.0]]))[0]


def test_query_backed_model_with_inline_sql_in_its_query():
    q = {
        "source_model": {
            "source_name": "orders",
            "columns": [{"name": "x", "sql": "sum(amount) over ()", "type": "number"}],
        },
        "measures": [{"formula": "max(x)", "name": "m"}],
    }
    assert not no_hack(task(ROW_SCALAR), plain_call("create_model", {"name": "qb", "query": q}))[0]


def test_failed_sql_call_still_counts():
    call = plain_call("create_model", {"name": "agg", "data_source": "bench", "sql": "select 1"})
    assert not no_hack(task(), call.model_copy(update={"is_error": True}))[0]


# Python tool.


def py(code: str, *paths: str) -> ToolCall:
    return ToolCall(
        tool="python",
        args={"code": code},
        result_text="",
        audit=PythonAudit(
            sandbox_dir=SANDBOX,
            allowed_prefixes=[PY_PREFIX],
            events=[AuditEvent(event="open", path=p) for p in paths],
        ),
    )


def test_python_in_sandbox_ok():
    code = "import pandas as pd\ndf = pd.DataFrame({'a': [1, 2]})\nprint(df.a.sum())"
    assert no_hack(task(), py(code, f"{SANDBOX}/out.csv", f"{PY_PREFIX}/lib/python3.12/json/__init__.py"))[0]


def test_python_opens_the_database():
    ok, reasons = no_hack(task(), py("import duckdb\ncon = duckdb.connect('/tmp/trial-1/bench.duckdb')"))
    assert not ok
    assert reasons


@pytest.mark.parametrize(
    "code",
    [
        "import sqlite3",
        "from duckdb import connect",
        "__import__('duckdb')",
        "open('../bench.duckdb', 'rb').read()",
    ],
)
def test_python_static_database_checks(code: str):
    assert not no_hack(task(), py(code))[0], code


def test_python_reads_benchmark_files():
    assert not no_hack(task(), py("open(p).read()", "/home/u/slayer-evals/tasks/truth/q1-region-total.json"))[0]
    assert not no_hack(task(), py("open(p).read()", "/home/u/slayer-evals/tasks/q1/q1-region-total.yaml"))[0]


def test_python_sandbox_prefix_is_not_a_string_prefix_match():
    assert not no_hack(task(), py("open(p)", f"{SANDBOX}-evil/x.csv"))[0]


def test_python_relative_path_escaping_sandbox():
    assert not no_hack(task(), py("open(p)", f"{SANDBOX}/../bench.duckdb"))[0]


def test_column_filter_sql():
    call = plain_call(
        "create_model",
        {
            "name": "o2",
            "sql_table": "orders",
            "data_source": "bench",
            "columns": [{"name": "amount", "type": "number", "filter": "status = 'ok'"}],
        },
    )
    assert not no_hack(task(), call)[0]


def test_edit_model_source_queries_with_inline_sql():
    stage = {
        "source_model": {
            "source_name": "orders",
            "columns": [{"name": "x", "sql": "sum(amount) over ()", "type": "number"}],
        },
        "measures": [{"formula": "max(x)", "name": "m"}],
    }
    call = plain_call("edit_model", {"model_name": "monthly_rev", "source_queries": [stage]})
    assert not no_hack(task(ROW_SCALAR), call)[0]
