"""Single-query criterion: some successful query's own result is the answer; refusals: some call returned the kind."""

from typing import Any

from slayer_evals.core import Table
from slayer_evals.grading import grade
from tests.helpers import error_call, make_task, query_call, sql_call, submission_of, trace_of

Q1_TRUTH = Table(
    columns=["region", "city", "region_total"],
    rows=[["North", "Oslo", 705.0], ["North", "Bergen", 705.0], ["South", "Rome", 890.0]],
)
Q1_COLS = ["orders_flat.region", "orders_flat.city", "orders_flat.region_total"]
Q1_QUERY: dict[str, Any] = {
    "source_model": "orders_flat",
    "dimensions": ["region", "city"],
    "measures": [{"formula": "sum(amount, partition_by=region)", "name": "region_total"}],
}
EMPTY = Table(columns=[], rows=[])


def verdict(trace, truth=Q1_TRUTH, task=None, submission=None):
    return grade(task or make_task(), truth, submission or submission_of(truth), trace)


def test_one_query_returns_the_answer():
    v = verdict(trace_of(query_call(Q1_QUERY, Q1_COLS, Q1_TRUTH.rows)))
    assert v.single_query
    assert v.passed


def test_any_query_shape_counts():
    other = {"source_model": "orders", "dimensions": ["customers.regions.name", "customers.city"], "measures": ["x"]}
    v = verdict(trace_of(query_call(other, ["a", "b", "c"], Q1_TRUTH.rows)))
    assert v.single_query


def test_answer_combined_from_two_queries():
    per_city = query_call(
        Q1_QUERY, ["orders_flat.region", "orders_flat.city", "orders_flat.rev"], [["North", "Oslo", 370.0]]
    )
    per_region = query_call(Q1_QUERY, ["orders_flat.region", "orders_flat.rev"], [["North", 705.0], ["South", 890.0]])
    v = verdict(trace_of(per_city, per_region))
    assert v.correct
    assert not v.single_query
    assert not v.passed
    assert any("no single query" in r for r in v.single_query_reasons)


Q1_SQL = (
    "select region, city, sum(sum(amount)) over (partition by region) as region_total from orders_flat group by 1, 2"
)


def test_one_sql_statement_returns_the_answer():
    v = verdict(trace_of(sql_call(Q1_SQL, ["region", "city", "region_total"], Q1_TRUTH.rows), profile="sql+python"))
    assert v.correct
    assert v.single_query
    assert v.passed


def test_sql_and_query_calls_both_count():
    wrong = query_call(Q1_QUERY, Q1_COLS, Q1_TRUTH.rows[:1])
    right = sql_call(Q1_SQL, ["region", "city", "region_total"], Q1_TRUTH.rows)
    assert verdict(trace_of(wrong, right)).single_query


def test_failed_sql_does_not_count():
    bad = sql_call(Q1_SQL, ["region", "city", "region_total"], Q1_TRUTH.rows).model_copy(update={"is_error": True})
    v = verdict(trace_of(bad, profile="sql+python"))
    assert v.correct
    assert not v.single_query


def test_sql_answer_combined_from_two_statements():
    per_city = sql_call("select ...", ["region", "city", "rev"], [["North", "Oslo", 370.0]])
    per_region = sql_call("select ...", ["region", "rev"], [["North", 705.0], ["South", 890.0]])
    v = verdict(trace_of(per_city, per_region, profile="sql+python"))
    assert v.correct
    assert not v.single_query


def test_python_output_is_not_a_query():
    table = sql_call("", ["region", "city", "region_total"], Q1_TRUTH.rows)
    py = table.model_copy(update={"tool": "python", "args": {"code": "print(df.to_json())"}})
    assert not verdict(trace_of(py, profile="sql+python")).single_query


def test_wrong_query_result():
    rows = [list(r) for r in Q1_TRUTH.rows]
    rows[0][2] = 1.0
    assert not verdict(trace_of(query_call(Q1_QUERY, Q1_COLS, rows))).single_query


def test_failed_query_does_not_count():
    bad = query_call(Q1_QUERY, Q1_COLS, Q1_TRUTH.rows).model_copy(update={"is_error": True})
    v = verdict(trace_of(bad))
    assert not v.single_query
    assert v.single_query_reasons == ["no successful query returned a table"]


def test_later_query_can_qualify():
    wrong = query_call(Q1_QUERY, Q1_COLS, Q1_TRUTH.rows[:1])
    right = query_call(Q1_QUERY, Q1_COLS, Q1_TRUTH.rows)
    v = verdict(trace_of(wrong, right))
    assert v.single_query
    assert v.single_query_reasons[0].startswith("query #2 returns the answer")


Q18_EXPECT = {"error": "TimeDimensionColumnError", "message_any": ["already bucketed", "monthly"]}
Q18_ARGS = {
    "query": {"source_model": "monthly_rev", "time_dimensions": [{"dimension": "order_date", "granularity": "day"}]}
}
GRAN_ERR = (
    "Error executing tool query: TimeDimensionColumnError: Cannot re-bucket to 'day': already bucketed at 'month'"
)


def refusal(**expect: Any):
    return make_task(id="q18", covers=["Q18"], compare={}, expect={**Q18_EXPECT, **expect})


def test_refusal_surfaced():
    sub = submission_of(EMPTY, message="That column is already bucketed by month.")
    v = grade(refusal(), EMPTY, sub, trace_of(error_call("query", Q18_ARGS, GRAN_ERR)))
    assert v.correct
    assert v.single_query


def test_refusal_not_mentioned():
    sub = submission_of(Table(columns=["d", "v"], rows=[["2025-01-01", 1.0]]), message="Here is the daily breakdown.")
    v = grade(refusal(), EMPTY, sub, trace_of(error_call("query", Q18_ARGS, GRAN_ERR)))
    assert not v.correct
    assert v.single_query


def test_wrong_error_kind():
    other = "Error executing tool query: UnknownReferenceError: Cannot resolve reference 'day'."
    sub = submission_of(EMPTY, message="Already bucketed monthly.")
    v = grade(refusal(), EMPTY, sub, trace_of(error_call("query", Q18_ARGS, other)))
    assert not v.correct
    assert not v.single_query


def test_error_kind_list():
    sub = submission_of(EMPTY, message="Already bucketed monthly.")
    task = refusal(error=["UnknownReferenceError", "TimeDimensionColumnError"])
    assert grade(task, EMPTY, sub, trace_of(error_call("query", Q18_ARGS, GRAN_ERR))).single_query


def test_warning_kind_list():
    task = make_task(
        id="q9", covers=["Q9"], compare={}, expect={"warning": ["broadcast", "associated"], "message_any": ["overlap"]}
    )
    q = {
        "source_model": "orders",
        "dimensions": ["status"],
        "measures": [{"formula": "sum(customers.credit)", "name": "v"}],
    }
    sub = submission_of(EMPTY, message="The status totals overlap.")
    warned = query_call(q, ["orders.status", "orders.v"], [["ok", 1.0]], warnings=["associated"])
    v = grade(task, EMPTY, sub, trace_of(warned))
    assert v.correct
    assert v.single_query
    silent = query_call(q, ["orders.status", "orders.v"], [["ok", 1.0]], warnings=["truncated"])
    v2 = grade(task, EMPTY, sub, trace_of(silent))
    assert not v2.correct
    assert not v2.single_query


WARN_TASK = {
    "id": "q9",
    "covers": ["Q9"],
    "compare": {},
    "expect": {"warning": ["broadcast", "associated"], "message_any": ["overlap", "double count"]},
}


def test_raw_sql_refusal():
    task = make_task(**WARN_TASK)
    explored = sql_call("select status, sum(credit) from orders_flat group by 1", ["status", "v"], [["ok", 1.0]])
    trace = trace_of(explored, profile="sql+python")
    v = grade(task, EMPTY, submission_of(EMPTY, message="Credit limits overlap across statuses."), trace)
    assert v.correct
    assert v.single_query
    assert v.passed


def test_raw_sql_refusal_without_any_call():
    task = make_task(**WARN_TASK)
    v = grade(task, EMPTY, submission_of(EMPTY, message="The totals would overlap."), trace_of(profile="sql+python"))
    assert v.correct
    assert v.single_query


def test_raw_sql_refusal_with_rows_fails():
    task = make_task(**WARN_TASK)
    answered = Table(columns=["status", "credit"], rows=[["ok", 1.0]])
    v = grade(task, EMPTY, submission_of(answered, message="These overlap."), trace_of(profile="sql+python"))
    assert not v.correct
    assert not v.single_query


def test_raw_sql_refusal_without_phrase_fails():
    task = make_task(**WARN_TASK)
    v = grade(task, EMPTY, submission_of(EMPTY, message="No data."), trace_of(profile="sql+python"))
    assert not v.correct
    assert not v.single_query


def test_slayer_refusal_still_needs_the_warning():
    task = make_task(**WARN_TASK)
    v = grade(task, EMPTY, submission_of(EMPTY, message="These overlap."), trace_of(profile="slayer"))
    assert not v.correct
    assert not v.single_query
