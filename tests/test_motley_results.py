"""Motley `query` results (JSON and markdown) and the error classes read from tool errors."""

import itertools
import json
from typing import Any

import pytest

from slayer_evals.core import ParsedResult, error_kind
from tests.helpers import mcp_fixture, motley_json, motley_markdown, motley_payload

COLUMNS = ["orders.region", "orders.city", "orders.rev"]
ROWS: list[list[Any]] = [["North", "Oslo", 705.0], ["South", "Rome", 890.5], [None, "Bern", 12.0]]
SQL = "SELECT region, city, SUM(amount) AS rev\nFROM orders\n\nGROUP BY 1, 2"
REMINDER = "What did the user ask? Use report_feedback: if you could answer, file category 'ok'."


def parse(text: str) -> ParsedResult:
    parsed = ParsedResult.from_text(text)
    assert parsed is not None, text
    return parsed


def test_motley_json_parses():
    p = parse(motley_json(COLUMNS, ROWS))
    assert p.columns == COLUMNS
    assert p.rows == ROWS
    assert p.warnings == []


def test_motley_json_with_optional_keys_parses():
    text = motley_json(COLUMNS, ROWS, sql=SQL, reminder=REMINDER, history_url="https://app.example/usage/1")
    p = parse(text)
    assert (p.columns, p.rows, p.warnings) == (COLUMNS, ROWS, [])


def test_truncated_motley_json_warns():
    p = parse(motley_json(COLUMNS, ROWS, truncated=True))
    assert p.rows == ROWS
    assert [w.kind for w in p.warnings] == ["truncated"]


def test_empty_motley_json_result():
    p = parse(motley_json(COLUMNS, []))
    assert p.columns == COLUMNS
    assert p.rows == []


def test_motley_columns_keep_their_order_not_the_records_key_order():
    payload = motley_payload(COLUMNS, ROWS)
    payload["rows"] = [dict(reversed(list(r.items()))) for r in payload["rows"]]
    p = parse(json.dumps(payload, indent=2))
    assert p.columns == COLUMNS
    assert p.rows == ROWS


def _malformed(mutate) -> str:
    payload = motley_payload(COLUMNS, ROWS)
    mutate(payload)
    return json.dumps(payload, indent=2)


@pytest.mark.parametrize(
    "text",
    [
        _malformed(lambda p: p["columns"][1].pop("name")),
        _malformed(lambda p: p["columns"][1].update(name=7)),
        _malformed(lambda p: p["columns"][1].update(name="orders.region")),
        _malformed(lambda p: p["rows"][2].pop("orders.city")),
        _malformed(lambda p: p["rows"][0].update({"orders.extra": 1})),
        _malformed(lambda p: p.update(rows=[list(r.values()) for r in p["rows"]])),
        _malformed(lambda p: p["columns"].__setitem__(0, "orders.region")),
        _malformed(lambda p: p.update(rows="none")),
        _malformed(lambda p: p.pop("rows")),
    ],
    ids=[
        "column-without-name",
        "non-string-name",
        "duplicate-name",
        "record-missing-a-key",
        "record-with-an-extra-key",
        "list-rows-with-column-objects",
        "mixed-column-entries",
        "rows-not-a-list",
        "no-rows",
    ],
)
def test_malformed_motley_json_is_not_a_table(text: str):
    assert ParsedResult.from_text(text) is None


MARKDOWN_VARIANTS = [
    dict(zip(("sql", "reminder", "history_url", "truncated"), combo, strict=True))
    for combo in itertools.product((None, SQL), (None, REMINDER), (None, "https://app.example/usage/1"), (False, True))
]


@pytest.mark.parametrize(
    "kw",
    MARKDOWN_VARIANTS,
    ids=lambda kw: "-".join(k for k, v in kw.items() if v) or "footer-only",
)
def test_motley_markdown_parses_like_its_json(kw: dict[str, Any]):
    md = parse(motley_markdown(COLUMNS, ROWS, **kw))
    js = parse(motley_json(COLUMNS, ROWS, truncated=kw["truncated"]))
    assert md.columns == js.columns == COLUMNS
    assert md.rows == js.rows == ROWS
    assert [w.kind for w in md.warnings] == (["truncated"] if kw["truncated"] else [])


def test_motley_markdown_footer_is_not_a_row():
    text = motley_markdown(COLUMNS, ROWS)
    assert "_(3 rows)_" in text
    assert len(parse(text).rows) == 3


def test_empty_motley_markdown_result():
    p = parse(motley_markdown(COLUMNS, []))
    assert p.columns == COLUMNS
    assert p.rows == []


def test_every_shape_parses_alike():
    columns, rows = ["region", "revenue"], [["North", 1.5], ["South", 2.0], [None, 3.0]]
    records = [dict(zip(columns, r, strict=True)) for r in rows]
    shapes = [
        "| region | revenue |\n| --- | --- |\n| North | 1.5 |\n| South | 2.0 |\n|  | 3.0 |",
        json.dumps(records),
        json.dumps({"data": records, "warnings": []}),
        json.dumps({"columns": columns, "rows": rows, "truncated": False}),
        motley_json(columns, rows),
        motley_markdown(columns, rows, sql=SQL, reminder=REMINDER),
    ]
    for text in shapes:
        p = parse(text)
        assert (p.columns, p.rows) == (columns, rows), text


@pytest.mark.parametrize(
    ("name", "kind"),
    [
        ("query_error_granularity", "TimeDimensionColumnError"),
        ("query_error_reaggregation", "ReaggregationError"),
        ("query_error_unknown_column", "UnknownReferenceError"),
    ],
)
def test_prefixed_error_kind(name: str, kind: str):
    assert error_kind(mcp_fixture(name)["text"]) == kind


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        (
            "TimeDimensionColumnError: A time dimension must reference a raw date column; 'month' is already bucketed.",
            "TimeDimensionColumnError",
        ),
        ("ReaggregationError: cannot re-aggregate avg(amount)", "ReaggregationError"),
        ("QueryTypeException: the query is not a list of stages", "QueryTypeException"),
    ],
)
def test_bare_error_kind(text: str, kind: str):
    assert error_kind(text) == kind


@pytest.mark.parametrize(
    "text",
    [
        "SQL: SELECT 1",
        "Note: the model has no time dimension",
        "Invalid arguments: 'measures' must be a list",
        "Model 'x' created.",
        "Unknown model 'orders_x'. Use inspect to list models.",
        "TimeDimensionColumnError:no space after the colon",
        "The query failed. TimeDimensionColumnError: not at the start",
        "",
    ],
)
def test_no_error_kind(text: str):
    assert error_kind(text) is None
