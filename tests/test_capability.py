"""Capability criterion: predicates on SLayer-parsed queries whose own result matches the truth."""

from typing import Any

import pytest

from slayer_evals.core import Table
from slayer_evals.grading import grade
from tests.helpers import (
    empty_manifest,
    error_call,
    make_task,
    manifest_with_aov,
    plain_call,
    query_call,
    submission_of,
    trace_of,
)

Q1_TRUTH = Table(
    columns=["region", "city", "region_total"],
    rows=[["North", "Oslo", 705.0], ["North", "Bergen", 705.0], ["South", "Rome", 890.0]],
)
Q1_COLS = ["orders_flat.region", "orders_flat.city", "orders_flat.region_total"]
Q1_QUERY = {
    "source_model": "orders_flat",
    "dimensions": ["region", "city"],
    "measures": [{"formula": "sum(amount, partition_by=region)", "name": "region_total"}],
}
SINGLE = Table(columns=["v"], rows=[[42.0]])


def q1_task(**kw: Any):
    return make_task(**kw)


def capability(task, trace, truth=Q1_TRUTH, manifest=None) -> tuple[bool, list[str]]:
    v = grade(task, truth, manifest or empty_manifest(), submission_of(truth), trace)
    return v.capability, v.capability_reasons


def single_task(capabilities: list[dict[str, Any]], **kw: Any):
    return make_task(id="t", compare={"keys": [], "values": ["v"]}, capabilities=capabilities, **kw)


def single_call(query: Any, **extra: Any):
    return query_call(query, ["m.v"], [[42.0]], **extra)


def test_capability_used_result_right():
    trace = trace_of(query_call(Q1_QUERY, Q1_COLS, Q1_TRUTH.rows))
    assert capability(q1_task(), trace)[0]


def test_capability_used_but_result_wrong():
    rows = [list(r) for r in Q1_TRUTH.rows]
    rows[0][2] = 1.0
    ok, reasons = capability(q1_task(), trace_of(query_call(Q1_QUERY, Q1_COLS, rows)))
    assert not ok
    assert reasons


def test_right_answer_without_the_capability():
    per_city = {
        "source_model": "orders_flat",
        "dimensions": ["region", "city"],
        "measures": [{"formula": "sum(amount)", "name": "rev"}],
    }
    per_region = {
        "source_model": "orders_flat",
        "dimensions": ["region"],
        "measures": [{"formula": "sum(amount)", "name": "rev"}],
    }
    trace = trace_of(
        query_call(per_city, ["orders_flat.region", "orders_flat.city", "orders_flat.rev"], [["North", "Oslo", 370.0]]),
        query_call(per_region, ["orders_flat.region", "orders_flat.rev"], [["North", 705.0], ["South", 890.0]]),
    )
    v = grade(q1_task(), Q1_TRUTH, empty_manifest(), submission_of(Q1_TRUTH), trace)
    assert v.correct
    assert not v.capability
    assert any("partition_by" in r for r in v.capability_reasons)


def test_failed_call_does_not_qualify():
    call = query_call(Q1_QUERY, Q1_COLS, Q1_TRUTH.rows)
    bad = call.model_copy(update={"is_error": True})
    assert not capability(q1_task(), trace_of(bad))[0]


def test_measure_as_plain_string():
    query = {**Q1_QUERY, "measures": ["sum(amount, partition_by=region)"]}
    assert capability(q1_task(), trace_of(query_call(query, Q1_COLS, Q1_TRUTH.rows)))[0]


def test_nested_within():
    task = single_task(
        [{"kind": "call", "fn": "avg", "within": {"kind": "call", "fn": "sum", "kwarg": "partition_by"}}]
    )
    good = {
        "source_model": "orders_flat",
        "dimensions": ["region"],
        "measures": [{"formula": "avg(sum(amount, partition_by=[city, region]))", "name": "v"}],
    }
    flat = {
        "source_model": "orders_flat",
        "dimensions": ["region"],
        "measures": [{"formula": "avg(amount)", "name": "v"}],
    }
    assert capability(task, trace_of(single_call(good)), SINGLE)[0]
    assert not capability(task, trace_of(single_call(flat)), SINGLE)[0]


def test_transform_within_transform():
    task = single_task([{"kind": "call", "fn": "cumsum", "within": {"kind": "call", "fn": "change"}}])
    query = {
        "source_model": "orders",
        "time_dimensions": ["month(order_date)"],
        "measures": [{"formula": "cumsum(change(sum(amount)))", "name": "v"}],
    }
    assert capability(task, trace_of(single_call(query)), SINGLE)[0]
    swapped = {**query, "measures": [{"formula": "change(cumsum(sum(amount)))", "name": "v"}]}
    assert not capability(task, trace_of(single_call(swapped)), SINGLE)[0]


def test_fn_alternatives():
    task = single_task([{"kind": "call", "fn": ["change_pct", "change"]}])
    q = {
        "source_model": "orders",
        "time_dimensions": ["month(order_date)"],
        "measures": [{"formula": "change_pct(sum(amount))", "name": "v"}],
    }
    assert capability(task, trace_of(single_call(q)), SINGLE)[0]


def test_dotted_arg():
    task = single_task([{"kind": "call", "fn": "avg", "dotted_arg": True}])
    cross = {
        "source_model": "orders",
        "dimensions": ["customers.regions.name"],
        "measures": [{"formula": "avg(customers.credit)", "name": "v"}],
    }
    local = {
        "source_model": "customers",
        "dimensions": ["regions.name"],
        "measures": [{"formula": "avg(credit)", "name": "v"}],
    }
    assert capability(task, trace_of(single_call(cross)), SINGLE)[0]
    assert not capability(task, trace_of(single_call(local)), SINGLE)[0]


def test_scalar_function_call():
    task = single_task([{"kind": "call", "fn": "date_part", "clause": "dimensions"}])
    q = {
        "source_model": "orders",
        "dimensions": [{"expression": "date_part('day_of_week', order_date)", "name": "dow"}],
        "measures": [{"formula": "sum(amount)", "name": "v"}],
    }
    assert capability(task, trace_of(single_call(q)), SINGLE)[0]


def test_clause_filters_rank():
    task = single_task([{"kind": "call", "fn": "rank", "clause": "filters"}])
    in_filter = {
        "source_model": "orders",
        "dimensions": ["customer_id"],
        "measures": [{"formula": "sum(amount)", "name": "v"}],
        "filters": ["rank(sum(amount), direction='desc') <= 2"],
    }
    in_measure = {
        "source_model": "orders",
        "dimensions": ["customer_id"],
        "measures": [{"formula": "rank(sum(amount), direction='desc')", "name": "v"}],
    }
    assert capability(task, trace_of(single_call(in_filter)), SINGLE)[0]
    assert not capability(task, trace_of(single_call(in_measure)), SINGLE)[0]


def test_window_kwarg():
    task = single_task([{"kind": "call", "fn": "count_distinct", "kwarg": "window"}])
    q = {
        "source_model": "orders",
        "time_dimensions": ["month(order_date)"],
        "measures": [{"formula": "count_distinct(customer_id, window='90d')", "name": "v"}],
    }
    assert capability(task, trace_of(single_call(q)), SINGLE)[0]


def test_saved_measure_expanded_from_manifest():
    task = single_task([{"kind": "call", "fn": "cumsum", "within": {"kind": "call", "fn": "sum"}}], row="Q17")
    q = {
        "source_model": "orders",
        "time_dimensions": ["month(order_date)"],
        "measures": [{"formula": "cumsum(aov)", "name": "v"}],
    }
    assert capability(task, trace_of(single_call(q)), SINGLE, manifest_with_aov())[0]
    assert not capability(task, trace_of(single_call(q)), SINGLE, empty_manifest())[0]


def test_saved_measure_from_trace():
    task = single_task([{"kind": "call", "fn": "cumsum", "within": {"kind": "call", "fn": "sum"}}], row="Q17")
    save = plain_call(
        "edit_model",
        {"model_name": "orders", "measures": [{"name": "avg_ticket", "formula": "sum(amount) / count(*)"}]},
        "Model 'orders' updated.",
    )
    q = {
        "source_model": "orders",
        "time_dimensions": ["month(order_date)"],
        "measures": [{"formula": "cumsum(avg_ticket)", "name": "v"}],
    }
    assert capability(task, trace_of(save, single_call(q)), SINGLE)[0]
    assert not capability(task, trace_of(single_call(q), save), SINGLE)[0]


def test_multi_stage():
    task = single_task([{"kind": "multi_stage"}], row="Q15")
    stages = [
        {
            "name": "per_customer",
            "source_model": "orders",
            "dimensions": ["customer_id"],
            "measures": [{"formula": "sum(amount)", "name": "rev"}],
        },
        {"source_model": "per_customer", "measures": [{"formula": "avg(rev)", "name": "v"}]},
    ]
    assert capability(task, trace_of(single_call(stages)), SINGLE)[0]
    single = {
        "source_model": "orders",
        "measures": [{"formula": "avg(sum(amount, partition_by=customer_id))", "name": "v"}],
    }
    assert not capability(task, trace_of(single_call(single)), SINGLE)[0]


def test_multi_stage_needs_reference_to_earlier_stage():
    task = single_task([{"kind": "multi_stage"}], row="Q15")
    unrelated = [
        {"name": "a", "source_model": "orders", "measures": [{"formula": "sum(amount)", "name": "rev"}]},
        {"source_model": "orders", "measures": [{"formula": "sum(amount)", "name": "v"}]},
    ]
    assert not capability(task, trace_of(single_call(unrelated)), SINGLE)[0]


def test_saved_query_with_refine():
    task = single_task([{"kind": "saved_query", "name": "monthly_rev", "refine": True}], row="Q23")
    refined = single_call("monthly_rev", refine={"dimensions": ["customers.regions.name"]})
    plain = single_call("monthly_rev")
    assert capability(task, trace_of(refined), SINGLE, manifest_with_aov())[0]
    assert not capability(task, trace_of(plain), SINGLE, manifest_with_aov())[0]


def test_order_by_unselected():
    task = single_task([{"kind": "order_unselected"}], row="Q13")
    base = {
        "source_model": "orders",
        "dimensions": ["status"],
        "measures": [{"formula": "count(*)", "name": "v"}],
        "limit": 10,
    }
    hidden = {**base, "order": [{"column": "sum(amount)", "direction": "desc"}]}
    shown = {**base, "order": [{"column": "v", "direction": "desc"}]}
    assert capability(task, trace_of(single_call(hidden)), SINGLE)[0]
    assert not capability(task, trace_of(single_call(shown)), SINGLE)[0]


def test_inline_extension():
    task = single_task([{"kind": "inline_extension"}], row="Q16")
    ext = {
        "source_model": {
            "source_name": "orders",
            "columns": [{"name": "net", "sql": "amount * 0.9", "type": "number"}],
        },
        "measures": [{"formula": "sum(net)", "name": "v"}],
    }
    plain = {"source_model": "orders", "measures": [{"formula": "sum(amount * 0.9)", "name": "v"}]}
    assert capability(task, trace_of(single_call(ext)), SINGLE)[0]
    assert not capability(task, trace_of(single_call(plain)), SINGLE)[0]


@pytest.mark.parametrize(
    "query, form",
    [
        ({"filters": ["order_date = '2025-Q1'"]}, "typed"),
        ({"filters": ["order_date in '2025-03'"]}, "typed"),
        (
            {
                "time_dimensions": [
                    {"dimension": "order_date", "granularity": "month", "date_range": ["2025-01-01", "2025-03-31"]}
                ]
            },
            "typed",
        ),
        ({"filters": ["order_date = 'last 3 months'"]}, "relative"),
        (
            {"time_dimensions": [{"dimension": "order_date", "granularity": "month", "date_range": "this quarter"}]},
            "relative",
        ),
    ],
)
def test_time_filters(query: dict[str, Any], form: str):
    other = "relative" if form == "typed" else "typed"
    q = {"source_model": "orders", "measures": [{"formula": "sum(amount)", "name": "v"}], **query}
    assert capability(single_task([{"kind": "time_filter", "form": form}]), trace_of(single_call(q)), SINGLE)[0]
    assert not capability(single_task([{"kind": "time_filter", "form": other}]), trace_of(single_call(q)), SINGLE)[0]


def test_hand_built_date_bounds_are_not_typed_filter():
    q = {
        "source_model": "orders",
        "measures": [{"formula": "sum(amount)", "name": "v"}],
        "filters": ["order_date >= '2025-01-01 00:00:00' and order_date < '2025-04-01 00:00:00'"],
    }
    assert not capability(single_task([{"kind": "time_filter", "form": "relative"}]), trace_of(single_call(q)), SINGLE)[
        0
    ]


def test_no_source_model():
    task = single_task([{"kind": "no_source_model"}], row="Q8")
    inferred = {"dimensions": ["customers.tier"], "measures": [{"formula": "count(customers.id)", "name": "v"}]}
    rooted = {"source_model": "customers", **inferred}
    assert capability(task, trace_of(single_call(inferred)), SINGLE)[0]
    assert not capability(task, trace_of(single_call(rooted)), SINGLE)[0]


def test_filter_bool_across_join():
    task = single_task([{"kind": "filter", "bool_op": "or", "dotted_ref": True}], row="Q10")
    good = {
        "source_model": "customers",
        "measures": [{"formula": "count(*)", "name": "v"}],
        "filters": ["tier = 'bronze' or orders.status = 'ok'"],
    }
    local = {**good, "filters": ["tier = 'bronze' or tier = 'gold'"]}
    assert capability(task, trace_of(single_call(good)), SINGLE)[0]
    assert not capability(task, trace_of(single_call(local)), SINGLE)[0]


def test_trace_pattern_create_then_query():
    task = single_task(
        [
            {
                "kind": "trace_pattern",
                "steps": [
                    {"tool": "create_model", "has_args": ["query"]},
                    {"tool": "query", "uses_model_from_step": 0},
                ],
            }
        ],
        row="Q15",
    )
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
        "Model 'per_cust' created from query.",
    )
    use = single_call({"source_model": "per_cust", "measures": [{"formula": "avg(rev)", "name": "v"}]})
    other = single_call({"source_model": "orders", "measures": [{"formula": "avg(amount)", "name": "v"}]})
    assert capability(task, trace_of(create, use), SINGLE)[0]
    assert not capability(task, trace_of(use, create), SINGLE)[0]
    assert not capability(task, trace_of(create, other), SINGLE)[0]
    failed_create = create.model_copy(update={"is_error": True})
    assert not capability(task, trace_of(failed_create, use), SINGLE)[0]


def test_any_of():
    task = single_task(
        [
            {
                "kind": "any_of",
                "options": [
                    [{"kind": "multi_stage"}],
                    [{"kind": "call", "fn": "avg", "within": {"kind": "call", "fn": "sum", "kwarg": "partition_by"}}],
                ],
            }
        ],
        row="Q15",
    )
    nested = {
        "source_model": "orders",
        "measures": [{"formula": "avg(sum(amount, partition_by=customer_id))", "name": "v"}],
    }
    flat = {"source_model": "orders", "measures": [{"formula": "avg(amount)", "name": "v"}]}
    assert capability(task, trace_of(single_call(nested)), SINGLE)[0]
    assert not capability(task, trace_of(single_call(flat)), SINGLE)[0]


def test_all_predicates_on_one_call():
    task = single_task([{"kind": "call", "fn": "cumsum"}, {"kind": "call", "fn": "change_pct"}], row="Q4")
    a = single_call(
        {
            "source_model": "orders",
            "time_dimensions": ["month(order_date)"],
            "measures": [{"formula": "cumsum(sum(amount))", "name": "v"}],
        }
    )
    b = single_call(
        {
            "source_model": "orders",
            "time_dimensions": ["month(order_date)"],
            "measures": [{"formula": "change_pct(sum(amount))", "name": "v"}],
        }
    )
    both = single_call(
        {
            "source_model": "orders",
            "time_dimensions": ["month(order_date)"],
            "measures": [
                {"formula": "cumsum(sum(amount))", "name": "c"},
                {"formula": "change_pct(sum(amount))", "name": "v"},
            ],
        }
    )
    assert not capability(task, trace_of(a, b), SINGLE)[0]
    assert capability(task, trace_of(both), SINGLE)[0]


def test_unparseable_formula_does_not_crash():
    q = {"source_model": "orders", "measures": [{"formula": "sum(amount", "name": "v"}]}
    ok, reasons = capability(single_task([{"kind": "call", "fn": "sum"}]), trace_of(single_call(q)), SINGLE)
    assert not ok
    assert reasons


# Refusal and warning tasks.

Q18_EXPECT = {"error": "TimeDimensionColumnError", "message_any": ["already bucketed", "monthly"]}
Q18_PREDICATES = [{"kind": "source_model", "name": "monthly_rev"}, {"kind": "time_dimension", "granularity": "day"}]
Q18_ARGS = {
    "query": {
        "source_model": "monthly_rev",
        "time_dimensions": [{"dimension": "order_date", "granularity": "day"}],
        "measures": [{"formula": "sum(rev)", "name": "v"}],
    }
}
GRAN_ERR = "Error executing tool query: TimeDimensionColumnError: Cannot re-bucket to 'day': the column is already bucketed at 'month'"


def refusal_task():
    return make_task(id="q18", row="Q18", compare={}, capabilities=Q18_PREDICATES, expect=Q18_EXPECT)


def test_refusal_surfaced():
    trace = trace_of(error_call("query", Q18_ARGS, GRAN_ERR))
    sub = submission_of(Table(columns=[], rows=[]), message="That column is already bucketed by month; no daily data.")
    v = grade(refusal_task(), Table(columns=[], rows=[]), empty_manifest(), sub, trace)
    assert v.correct
    assert v.capability


def test_refusal_not_mentioned():
    trace = trace_of(error_call("query", Q18_ARGS, GRAN_ERR))
    sub = submission_of(Table(columns=["d", "v"], rows=[["2025-01-01", 1.0]]), message="Here is the daily breakdown.")
    v = grade(refusal_task(), Table(columns=[], rows=[]), empty_manifest(), sub, trace)
    assert not v.correct


def test_wrong_call_refusal_does_not_count():
    unrelated = {
        "query": {
            "source_model": "events",
            "time_dimensions": [{"dimension": "event_ts", "granularity": "day"}],
            "measures": [{"formula": "sum(amount)", "name": "v"}],
        }
    }
    trace = trace_of(error_call("query", unrelated, GRAN_ERR))
    sub = submission_of(Table(columns=[], rows=[]), message="Already bucketed monthly.")
    v = grade(refusal_task(), Table(columns=[], rows=[]), empty_manifest(), sub, trace)
    assert v.correct
    assert not v.capability


def test_wrong_error_kind_does_not_count():
    other = "Error executing tool query: UnknownReferenceError: Cannot resolve reference 'day'."
    trace = trace_of(error_call("query", Q18_ARGS, other))
    sub = submission_of(Table(columns=[], rows=[]), message="Already bucketed monthly.")
    v = grade(refusal_task(), Table(columns=[], rows=[]), empty_manifest(), sub, trace)
    assert not v.correct
    assert not v.capability


def test_warning_surfaced():
    task = make_task(
        id="q9",
        row="Q9",
        compare={},
        capabilities=[{"kind": "source_model", "name": "customers"}],
        expect={"warning": "broadcast", "message_any": ["repeat", "broadcast", "same value"]},
    )
    q = {
        "source_model": "customers",
        "dimensions": ["orders.status"],
        "measures": [{"formula": "sum(credit)", "name": "v"}],
    }
    call = query_call(
        q, ["customers.orders.status", "customers.v"], [["ok", 2800.0], ["bad", 2800.0]], warnings=["broadcast"]
    )
    sub = submission_of(Table(columns=[], rows=[]), message="Credit is broadcast: every status shows the same value.")
    v = grade(task, Table(columns=[], rows=[]), empty_manifest(), sub, trace_of(call))
    assert v.correct
    assert v.capability
    assert call.parsed is not None
    silent = call.model_copy(update={"parsed": call.parsed.model_copy(update={"warnings": []})})
    v2 = grade(task, Table(columns=[], rows=[]), empty_manifest(), sub, trace_of(silent))
    assert not v2.correct
    assert not v2.capability
