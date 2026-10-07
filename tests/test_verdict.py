"""Verdict: correctness criterion, missing submission, determinism and purity."""

import ast
import builtins
import socket
from pathlib import Path

import pytest

from slayer_evals.core import Submission, Table, Trace
from slayer_evals.grading import grade
from tests.helpers import REPO, make_task, query_call, sql_call, submission_of, trace_of

TRUTH = Table(columns=["region", "city", "region_total"], rows=[["North", "Oslo", 705.0], ["South", "Rome", 890.0]])
COLS = ["orders_flat.region", "orders_flat.city", "orders_flat.region_total"]
QUERY = {
    "source_model": "orders_flat",
    "dimensions": ["region", "city"],
    "measures": [{"formula": "sum(amount, partition_by=region)", "name": "region_total"}],
}


def good_trace() -> Trace:
    return trace_of(query_call(QUERY, COLS, TRUTH.rows))


def test_right_answer_passes():
    v = grade(make_task(), TRUTH, submission_of(TRUTH), good_trace())
    assert v.correct
    assert v.single_query
    assert v.passed


def test_wrong_answer():
    sub = Submission(columns=TRUTH.columns, rows=[["North", "Oslo", 1.0], ["South", "Rome", 890.0]])
    v = grade(make_task(), TRUTH, sub, good_trace())
    assert not v.correct
    assert v.correct_reasons
    assert not v.passed


def test_missing_submission():
    v = grade(make_task(), TRUTH, None, good_trace())
    assert (v.correct, v.single_query) == (False, False)
    for reasons in (v.correct_reasons, v.single_query_reasons):
        assert any("no submission" in r for r in reasons)


def test_same_inputs_same_verdict():
    args = (make_task(), TRUTH, submission_of(TRUTH), good_trace())
    assert grade(*args) == grade(*args)


def test_grading_does_no_io(monkeypatch: pytest.MonkeyPatch):
    def refuse(*_a, **_k):
        raise AssertionError("grading must not do I/O")

    args = (make_task(), TRUTH, submission_of(TRUTH), good_trace())
    expected = grade(*args)
    monkeypatch.setattr(builtins, "open", refuse)
    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(Path, "read_text", refuse)
    assert grade(*args) == expected


FORBIDDEN_TOP = {
    "duckdb",
    "sqlite3",
    "socket",
    "subprocess",
    "urllib",
    "http",
    "httpx",
    "requests",
    "shutil",
    "tempfile",
    "claude_agent_sdk",
    "mcp",
    "pathlib",
    "os",
    "io",
}


def _imports(path: Path) -> set[str]:
    out: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            out |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            out.add(node.module)
    return out


def test_grading_imports_only_core():
    files = sorted((REPO / "src" / "slayer_evals" / "grading").rglob("*.py"))
    assert files
    for f in files:
        for mod in _imports(f):
            top = mod.split(".")[0]
            assert top not in FORBIDDEN_TOP, f"{f.name} imports {mod}"
            assert top != "slayer", f"{f.name} imports {mod}"
            if top == "slayer_evals":
                assert mod == "slayer_evals.core" or mod.startswith(("slayer_evals.core.", "slayer_evals.grading")), (
                    f"{f.name} imports {mod}"
                )


def test_verdict_records_column_mappings():
    sub = Submission(columns=["Region", "City", "Total"], rows=[[r[0], r[1], r[2]] for r in TRUTH.rows])
    v = grade(make_task(), TRUTH, sub, good_trace())
    assert v.passed
    assert v.correct_columns == {"region": "Region", "city": "City", "region_total": "Total"}
    assert v.single_query_columns == dict(zip(TRUTH.columns, COLS, strict=True))


def test_single_query_matched_by_values():
    renamed = query_call(QUERY, ["orders.customers.regions.name", "orders.customers.city", "orders.rt"], TRUTH.rows)
    v = grade(make_task(), TRUTH, submission_of(TRUTH), trace_of(renamed))
    assert v.single_query, v.single_query_reasons
    assert v.single_query_columns["region_total"] == "orders.rt"
    assert any("matched by values" in r for r in v.single_query_reasons)


SAVED_TASK = {"id": "q23", "covers": ["Q23"], "uses_saved": ["monthly_rev"]}


def _saved_reasons(v) -> bool:
    return any("monthly_rev" in r for r in v.correct_reasons) and any(
        "monthly_rev" in r for r in v.single_query_reasons
    )


def test_saved_definition_auto_fails_raw_sql():
    task = make_task(**SAVED_TASK)
    perfect = trace_of(sql_call("select ...", TRUTH.columns, TRUTH.rows), profile="sql+python")
    v = grade(task, TRUTH, submission_of(TRUTH), perfect)
    assert (v.correct, v.single_query) == (False, False)
    assert _saved_reasons(v)


def test_saved_definition_auto_fail_trace():
    task = make_task(**SAVED_TASK)
    v = grade(task, TRUTH, None, Trace(profile="sql+python", end_reason="auto_fail"))
    assert (v.correct, v.single_query) == (False, False)
    assert _saved_reasons(v)


def test_saved_definition_refusal_auto_fails_raw_sql():
    task = make_task(
        id="q18",
        covers=["Q18"],
        compare={},
        uses_saved=["monthly_rev"],
        expect={"error": "TimeDimensionColumnError", "message_any": ["bucketed"]},
    )
    empty = Table(columns=[], rows=[])
    v = grade(task, empty, submission_of(empty, message="It is already bucketed."), trace_of(profile="sql+python"))
    assert (v.correct, v.single_query) == (False, False)
    assert _saved_reasons(v)


def test_saved_definition_fine_in_slayer_profiles():
    task = make_task(**SAVED_TASK)
    for profile in ("slayer", "slayer+python"):
        trace = trace_of(query_call(QUERY, COLS, TRUTH.rows), profile=profile)
        assert grade(task, TRUTH, submission_of(TRUTH), trace).passed, profile
