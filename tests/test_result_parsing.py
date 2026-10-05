"""Parsing captured `slayer mcp` query responses (markdown, JSON array, JSON object)."""

import json

import pytest

from slayer_evals.core import Compare, ParsedResult
from slayer_evals.grading import error_kind, match_tables
from tests.helpers import mcp_fixture

PAIRS = [
    ("query_markdown", "query_json"),
    ("query_markdown_warning", "query_json_warning"),
    ("query_markdown_truncated", "query_json_truncated"),
    ("query_markdown_dates", "query_json_dates"),
]


def parse(name: str) -> ParsedResult:
    parsed = ParsedResult.from_text(mcp_fixture(name)["text"])
    assert parsed is not None, name
    return parsed


@pytest.mark.parametrize("md, js", PAIRS)
def test_markdown_and_json_parse_alike(md: str, js: str):
    a, b = parse(md), parse(js)
    assert a.columns == b.columns
    assert len(a.rows) == len(b.rows)
    ok = match_tables(truth=b, result=a, compare=Compare(keys=list(b.columns)))
    assert ok.ok, ok.reason
    assert sorted(w.kind for w in a.warnings) == sorted(w.kind for w in b.warnings)


def test_bare_json_array_parses():
    p = parse("query_json")
    assert p.columns == ["orders_flat.region", "orders_flat.city", "orders_flat.rev", "orders_flat.region_total"]
    assert p.warnings == []
    assert any(r[0] is None for r in p.rows)


def test_markdown_values_are_typed():
    p = parse("query_markdown")
    flat = [v for r in p.rows for v in r]
    assert 705.0 in flat
    assert any(isinstance(v, float) for v in flat)
    assert None in flat


def test_markdown_footer_is_not_rows():
    p = parse("query_markdown_nulls")
    assert p.columns == ["customers.regions.name", "customers.n"]
    assert len(p.rows) == 3
    assert [None, 1] in p.rows


def test_markdown_warning_kind_inferred():
    assert [w.kind for w in parse("query_markdown_warning").warnings] == ["broadcast"]


def test_truncation_reported():
    for name in ("query_markdown_truncated", "query_json_truncated"):
        p = parse(name)
        assert len(p.rows) == 20
        assert "truncated" in [w.kind for w in p.warnings]


def test_json_object_without_warnings():
    p = ParsedResult.from_text(json.dumps({"data": [{"a": 1, "b": "x"}]}))
    assert p is not None
    assert p.columns == ["a", "b"]
    assert p.rows == [[1, "x"]]


def test_empty_json_result():
    p = ParsedResult.from_text(json.dumps({"data": [], "warnings": []}))
    assert p is not None
    assert p.rows == []


@pytest.mark.parametrize("name", ["create_model_from_query", "list_datasources", "models_summary"])
def test_non_query_text_is_not_a_result(name: str):
    assert ParsedResult.from_text(mcp_fixture(name)["text"]) is None


@pytest.mark.parametrize(
    "name, kind",
    [
        ("query_error_granularity", "TimeDimensionColumnError"),
        ("query_error_reaggregation", "ReaggregationError"),
        ("query_error_unknown_column", "UnknownReferenceError"),
    ],
)
def test_error_kind(name: str, kind: str):
    fx = mcp_fixture(name)
    assert fx["is_error"]
    assert error_kind(fx["text"]) == kind


def test_error_kind_none_for_plain_text():
    assert error_kind("Model 'x' created.") is None
