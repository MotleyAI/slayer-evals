"""Verdict: correctness criterion, missing submission, determinism and purity."""

import ast
import builtins
import socket
from pathlib import Path

import pytest

from slayer_evals.core import Submission, Table, Trace
from slayer_evals.grading import grade
from tests.helpers import REPO, empty_manifest, make_task, query_call, submission_of, trace_of

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
    v = grade(make_task(), TRUTH, empty_manifest(), submission_of(TRUTH), good_trace())
    assert v.correct and v.capability and v.no_hack and v.passed


def test_wrong_answer():
    sub = Submission(columns=TRUTH.columns, rows=[["North", "Oslo", 1.0], ["South", "Rome", 890.0]])
    v = grade(make_task(), TRUTH, empty_manifest(), sub, good_trace())
    assert not v.correct and v.correct_reasons and not v.passed


def test_missing_submission():
    v = grade(make_task(), TRUTH, empty_manifest(), None, good_trace())
    assert (v.correct, v.capability, v.no_hack) == (False, False, False)
    for reasons in (v.correct_reasons, v.capability_reasons, v.no_hack_reasons):
        assert any("no submission" in r for r in reasons)


def test_same_inputs_same_verdict():
    args = (make_task(), TRUTH, empty_manifest(), submission_of(TRUTH), good_trace())
    assert grade(*args) == grade(*args)


def test_grading_does_no_io(monkeypatch: pytest.MonkeyPatch):
    def refuse(*_a, **_k):
        raise AssertionError("grading must not do I/O")

    args = (make_task(), TRUTH, empty_manifest(), submission_of(TRUTH), good_trace())
    expected = grade(*args)
    monkeypatch.setattr(builtins, "open", refuse)
    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(Path, "read_text", refuse)
    assert grade(*args) == expected


ALLOWED_SLAYER = {"slayer.engine.syntax", "slayer.core.formula"}
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


def test_grading_imports_only_core_and_slayer_parser():
    files = sorted((REPO / "src" / "slayer_evals" / "grading").rglob("*.py"))
    assert files
    for f in files:
        for mod in _imports(f):
            top = mod.split(".")[0]
            assert top not in FORBIDDEN_TOP, f"{f.name} imports {mod}"
            if top == "slayer":
                assert mod in ALLOWED_SLAYER, f"{f.name} imports {mod}"
            if top == "slayer_evals":
                assert mod == "slayer_evals.core" or mod.startswith(("slayer_evals.core.", "slayer_evals.grading")), (
                    f"{f.name} imports {mod}"
                )
