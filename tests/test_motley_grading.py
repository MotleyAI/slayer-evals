"""Grading in the Motley profiles: verdicts, the single-query criterion and per-surface trace flags."""

from typing import Any

import pytest

from slayer_evals.core import ParsedResult, Profile, Submission, Table, ToolCall, TraceFlags
from slayer_evals.grading import grade, trace_flags
from tests.helpers import (
    error_call,
    make_task,
    motley_json,
    plain_call,
    query_call,
    sql_call,
    submission_of,
    trace_of,
)

MOTLEY_PROFILES: tuple[Profile, ...] = ("motley", "motley+python")
TRUTH = Table(columns=["region", "city", "region_total"], rows=[["North", "Oslo", 705.0], ["South", "Rome", 890.0]])
COLS = ["orders_flat.region", "orders_flat.city", "orders_flat.region_total"]
QUERY = {
    "source_model": "orders_flat",
    "dimensions": ["region", "city"],
    "measures": [{"formula": "sum(amount, partition_by=region)", "name": "region_total"}],
}
PLAIN = {"source_model": "orders", "measures": [{"formula": "sum(amount)", "name": "v"}]}
BARE_ERROR = "TimeDimensionColumnError: A time dimension must reference a raw date column; 'month' is already bucketed."
SEMANTIC_TOOLS = ("query", "inspect", "search", "create_model", "edit_model", "delete", "save_memory", "switch_branch")


def motley_query(columns: list[str], rows: list[list[Any]], query: Any = QUERY, **kw: Any) -> ToolCall:
    """A successful Motley `query` call, parsed from its real JSON result text."""
    text = motley_json(columns, rows, **kw)
    return ToolCall(tool="query", args={"query": query}, result_text=text, parsed=ParsedResult.from_text(text))


@pytest.mark.parametrize("profile", MOTLEY_PROFILES)
def test_one_motley_query_returns_the_answer(profile: Profile):
    trace = trace_of(motley_query(COLS, TRUTH.rows), profile=profile)
    v = grade(make_task(), TRUTH, submission_of(TRUTH), trace)
    assert v.correct, v.correct_reasons
    assert v.single_query, v.single_query_reasons
    assert v.single_query_columns == dict(zip(TRUTH.columns, COLS, strict=True))


def test_motley_answer_combined_from_two_queries():
    per_city = motley_query(["orders_flat.region", "orders_flat.city"], [["North", "Oslo"], ["South", "Rome"]])
    per_region = motley_query(["orders_flat.region", "orders_flat.total"], [["North", 705.0], ["South", 890.0]])
    v = grade(make_task(), TRUTH, submission_of(TRUTH), trace_of(per_city, per_region, profile="motley"))
    assert v.correct
    assert not v.single_query


def error_task():
    return make_task(
        id="q18-bucketed",
        covers=["Q18"],
        compare={},
        expect={"error": "TimeDimensionColumnError", "message_any": ["already bucketed"]},
    )


EMPTY = Table(columns=[], rows=[])


@pytest.mark.parametrize("profile", MOTLEY_PROFILES)
def test_bare_error_class_in_motley(profile: Profile):
    failed = error_call("query", {"query": PLAIN}, BARE_ERROR)
    sub = submission_of(EMPTY, message="Month is already bucketed, so it cannot be bucketed again.")
    v = grade(error_task(), EMPTY, sub, trace_of(failed, profile=profile))
    assert v.correct, v.correct_reasons
    assert v.single_query, v.single_query_reasons


def test_motley_refusal_still_needs_the_error():
    sub = submission_of(EMPTY, message="Month is already bucketed, so it cannot be bucketed again.")
    v = grade(error_task(), EMPTY, sub, trace_of(profile="motley"))
    assert not v.correct
    assert not v.single_query


def test_labelled_error_text_is_not_the_expected_class():
    failed = error_call("query", {"query": PLAIN}, "Invalid arguments: TimeDimensionColumnError: month")
    sub = submission_of(EMPTY, message="Month is already bucketed.")
    v = grade(error_task(), EMPTY, sub, trace_of(failed, profile="motley"))
    assert not v.correct
    assert not v.single_query


def warning_task():
    return make_task(
        id="q9-credit",
        covers=["Q9"],
        compare={},
        expect={"warning": ["broadcast", "associated"], "message_any": ["broadcast"]},
    )


def test_motley_warning_task_graded_as_in_slayer():
    warned = query_call(PLAIN, ["orders.v"], [[1.0]], warnings=["broadcast"])
    sub = submission_of(EMPTY, message="The credit limit is broadcast across orders.")
    for profile in ("slayer", "motley"):
        v = grade(warning_task(), EMPTY, sub, trace_of(warned, profile=profile))
        assert (v.correct, v.single_query) == (True, True), profile
    silent = motley_query(["orders.status", "orders.total_credit"], [["shipped", 10.0]])
    v = grade(warning_task(), EMPTY, sub, trace_of(silent, profile="motley"))
    assert (v.correct, v.single_query) == (False, False)


def test_motley_warning_task_with_rows_and_no_warning_fails():
    silent = motley_query(["orders.status", "orders.total_credit"], [["shipped", 10.0]])
    sub = Submission(columns=["status", "total_credit"], rows=[["shipped", 10.0]], message="Here it is.")
    v = grade(warning_task(), EMPTY, sub, trace_of(silent, profile="motley"))
    assert not v.correct


@pytest.mark.parametrize("profile", MOTLEY_PROFILES)
def test_saved_definition_task_not_auto_failed_in_motley(profile: Profile):
    task = make_task(id="q23", covers=["Q23"], uses_saved=["monthly_rev"])
    v = grade(task, TRUTH, submission_of(TRUTH), trace_of(motley_query(COLS, TRUTH.rows), profile=profile))
    assert v.passed, (v.correct_reasons, v.single_query_reasons)
    assert not any("monthly_rev" in r for r in v.correct_reasons)


def test_motley_product_tool_errors_are_not_query_errors():
    doc = error_call("create_document", {"title": "x"}, "You are not allowed to create documents here.")
    assert not trace_flags([doc, motley_query(COLS, TRUTH.rows)], profile="motley").query_errors
    listing = error_call("list_resources", {"what": "documents"}, "boom")
    assert not trace_flags([listing], profile="motley+python").query_errors


@pytest.mark.parametrize("tool", SEMANTIC_TOOLS)
@pytest.mark.parametrize("profile", MOTLEY_PROFILES)
def test_motley_semantic_layer_errors_are_query_errors(tool: str, profile: Profile):
    failed = error_call(tool, {}, "ValueError: nope")
    assert trace_flags([failed], profile=profile).query_errors


@pytest.mark.parametrize("tool", ["inspect", "query"])
def test_failed_inspect_or_query_instead_of_a_document(tool: str):
    failed = error_call(tool, {}, BARE_ERROR)
    assert trace_flags([failed, motley_query(COLS, TRUTH.rows)], profile="motley").query_errors


def test_grade_reads_query_errors_per_surface():
    doc = error_call("create_document", {"title": "x"}, "You are not allowed to create documents here.")
    v = grade(make_task(), TRUTH, submission_of(TRUTH), trace_of(doc, motley_query(COLS, TRUTH.rows), profile="motley"))
    assert not v.flags.query_errors
    assert v.passed
    v = grade(make_task(), TRUTH, submission_of(TRUTH), trace_of(doc, query_call(QUERY, COLS, TRUTH.rows)))
    assert v.flags.query_errors


def test_slayer_profiles_count_every_slayer_tool():
    failed = error_call("list_datasources", {}, "Error executing tool list_datasources: X: y")
    for profile in ("slayer", "slayer+python"):
        assert trace_flags([failed], profile=profile).query_errors, profile


def test_raw_sql_profile_counts_the_sql_tool():
    failed = error_call("sql", {"sql": "select nope"}, "Binder Error: nope")
    py = error_call("python", {"code": "1/0"}, "ZeroDivisionError")
    assert trace_flags([failed], profile="sql+python").query_errors
    assert not trace_flags([py, sql_call("select 1 as v", ["v"], [[1]])], profile="sql+python").query_errors


def test_flags_from_a_motley_trace():
    calls = [
        error_call("query", {"query": PLAIN}, BARE_ERROR),
        motley_query(["orders.v"], [[42.0]], query=PLAIN),
        plain_call("create_model", {"name": "agg", "sql": "select customer_id, sum(amount) from orders group by 1"}),
        ToolCall(tool="python", args={"code": "print(1)"}, result_text="1"),
    ]
    flags = trace_flags(calls, profile="motley+python")
    assert flags == TraceFlags(
        used_python=True, raw_sql=True, edited_models=True, query_errors=True, several_queries=True
    )
    task = make_task(id="t", compare={"values": ["v"]})
    truth = Table(columns=["v"], rows=[[42.0]])
    v = grade(task, truth, submission_of(truth), trace_of(*calls, profile="motley+python"))
    assert v.passed
    assert v.flags == flags


def test_motley_delete_is_not_a_model_edit():
    flags = trace_flags([plain_call("delete", {"reference": "model:orders_x"})], profile="motley")
    assert not flags.edited_models
