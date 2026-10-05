"""Pinned shapes of SLayer's parser output that the grader relies on; fails on parser drift."""

import pytest
from slayer.engine.syntax import (
    AggCall,
    BoolOp,
    Cmp,
    DottedRef,
    Literal,
    Ref,
    ScalarCall,
    StarSource,
    TransformCall,
    parse_expr,
    parse_filter_expr,
)


def test_agg_with_partition_by():
    e = parse_expr("sum(amount, partition_by=region)")
    assert isinstance(e, AggCall)
    assert e.agg == "sum"
    assert e.source == Ref(name="amount")
    assert dict(e.kwargs)["partition_by"] == Ref(name="region")


def test_empty_partition_by():
    e = parse_expr("sum(amount, partition_by=[])")
    assert isinstance(e, AggCall)
    assert dict(e.kwargs)["partition_by"] == ()


def test_nested_aggregate():
    e = parse_expr("avg(sum(amount, partition_by=[city, region]))")
    assert isinstance(e, AggCall)
    assert isinstance(e.source, AggCall)


def test_nested_transforms():
    e = parse_expr("cumsum(change(sum(amount)))")
    assert isinstance(e, TransformCall)
    assert e.op == "cumsum"
    assert isinstance(e.input, TransformCall)
    assert e.input.op == "change"


def test_star_and_dotted():
    star, dotted = parse_expr("count(*)"), parse_expr("avg(customers.credit)")
    assert isinstance(star, AggCall)
    assert isinstance(star.source, StarSource)
    assert isinstance(dotted, AggCall)
    assert dotted.source == DottedRef(parts=("customers", "credit"))


def test_window_kwarg():
    e = parse_expr("count_distinct(customer_id, window='90d')")
    assert isinstance(e, AggCall)
    assert dict(e.kwargs)["window"] == Literal(value="90d")


def test_rank_kwargs():
    e = parse_expr("rank(sum(amount), direction='desc', partition_by=region)")
    assert isinstance(e, TransformCall)
    assert e.op == "rank"
    assert set(dict(e.kwargs)) == {"direction", "partition_by"}


def test_scalar_call():
    e = parse_expr("date_part('day_of_week', order_date)")
    assert isinstance(e, ScalarCall)
    assert e.name == "date_part"


def test_weighted_avg_weight_is_aggregate():
    e = parse_expr("weighted_avg(amount, weight=sum(amount, partition_by=region))")
    assert isinstance(e, AggCall)
    assert isinstance(dict(e.kwargs)["weight"], AggCall)


def test_saved_measure_is_bare_ref():
    e = parse_expr("cumsum(aov)")
    assert isinstance(e, TransformCall)
    assert e.input == Ref(name="aov")


def test_sql_style_filter():
    e = parse_filter_expr("tier = 'bronze' or orders.status = 'ok'")
    assert isinstance(e, BoolOp)
    assert e.op == "or"
    assert all(isinstance(o, Cmp) for o in e.operands)


@pytest.mark.parametrize("text", ["order_date = '2025-Q1'", "order_date in '2025-03'", "order_date = 'last 3 months'"])
def test_time_point_literal(text: str):
    e = parse_filter_expr(text)
    assert isinstance(e, Cmp)
    assert isinstance(e.right, Literal)
    assert isinstance(e.right.value, str)


def test_case_when_parses():
    parse_expr("sum(case when status = 'ok' then amount else 0 end)")


def test_unparseable_raises_value_error():
    with pytest.raises(ValueError):
        parse_expr("sum(amount")
