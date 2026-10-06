"""Markdown report from a run directory."""

import json
import shutil
import socket
from pathlib import Path

import pytest

from slayer_evals.report import render_report, write_report
from tests.helpers import REPO

FIXTURES = REPO / "tests" / "fixtures"
MODEL = "claude-opus-5-5"
OTHER_MODEL = "claude-sonnet-5"


def section(report: str, profile: str, model: str = MODEL) -> str:
    """The `## ` section for one profile and model, up to the next `## ` heading."""
    out: list[str] = []
    inside = False
    for line in report.splitlines():
        if line.startswith("## "):
            inside = f"`{profile}`" in line and f"`{model}`" in line
            continue
        if inside:
            out.append(line)
    assert out, f"no section for {profile}"
    return "\n".join(out)


def tables(text: str) -> list[list[list[str]]]:
    """Markdown tables in `text` as lists of cell rows (header first, separator dropped)."""
    found: list[list[list[str]]] = []
    current: list[list[str]] = []
    for line in text.splitlines() + [""]:
        if line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if not all(set(c) <= set("-: ") for c in cells):
                current.append(cells)
        elif current:
            found.append(current)
            current = []
    return found


def table_with(text: str, *headers: str) -> list[dict[str, str]]:
    for t in tables(text):
        if all(h in t[0] for h in headers):
            return [dict(zip(t[0], r)) for r in t[1:]]
    raise AssertionError(f"no table with headers {headers}")


def row_counts(report: str, profile: str, row: str, model: str = MODEL) -> dict[str, str]:
    rows = table_with(
        section(report, profile, model), "Row", "Tasks", "Trials", "Correct", "Single query", "Passed", "Raw SQL"
    )
    (match,) = [r for r in rows if r["Row"] == row]
    return match


@pytest.fixture
def repeat_report() -> str:
    return render_report(FIXTURES / "run_repeat")


def test_metadata(repeat_report: str):
    for text in ("1.0.2", "0.2.163", MODEL, "repeat", "subscription", "2026-10-05", "60", "900"):
        assert text in repeat_report, text


def test_row_counts_per_profile(repeat_report: str):
    q1 = row_counts(repeat_report, "slayer", "Q1")
    assert (q1["Tasks"], q1["Trials"], q1["Correct"], q1["Single query"], q1["Passed"], q1["Raw SQL"]) == (
        "1",
        "3",
        "3",
        "3",
        "3",
        "0",
    )
    q4 = row_counts(repeat_report, "slayer", "Q4")
    assert (q4["Correct"], q4["Single query"], q4["Passed"]) == ("3", "0", "0")
    q1p = row_counts(repeat_report, "slayer+python", "Q1")
    assert (q1p["Single query"], q1p["Passed"], q1p["Raw SQL"], q1p["Several queries"]) == ("2", "2", "1", "1")


def test_uncovered_rows(repeat_report: str):
    for row in ("Q19", "Q22"):
        line = next(x for x in section(repeat_report, "slayer").splitlines() if f"| {row} |" in x)
        assert "not covered" in line


def test_repeat_pass_rate(repeat_report: str):
    tasks = table_with(section(repeat_report, "slayer+python"), "Task", "Pass rate", "pass^3")
    q1 = next(r for r in tasks if "q1-a" in r["Task"])
    assert q1["Pass rate"] == "2/3"
    all_pass = next(r for r in tasks if "q4-a" in r["Task"])
    assert all_pass["Pass rate"] == "3/3"
    assert q1["pass^3"] != all_pass["pass^3"]
    plain = table_with(section(repeat_report, "slayer"), "Task", "Pass rate", "pass^3")
    assert next(r for r in plain if "q1-a" in r["Task"])["pass^3"] == all_pass["pass^3"]


def test_models_reported_separately(repeat_report: str):
    other = row_counts(repeat_report, "slayer", "Q1", model=OTHER_MODEL)
    assert (other["Trials"], other["Single query"], other["Passed"]) == ("3", "0", "0")
    assert row_counts(repeat_report, "slayer", "Q1")["Passed"] == "3"


def test_xfail_section(repeat_report: str):
    assert "DEV-2058" in repeat_report
    heading = next(i for i, x in enumerate(repeat_report.splitlines()) if x.startswith("#") and "xfail" in x.lower())
    rest = "\n".join(repeat_report.splitlines()[heading:])
    assert "x20" in rest
    for profile in ("slayer", "slayer+python"):
        assert all("x20" not in r["Task"] for r in table_with(section(repeat_report, profile), "Task", "Pass rate"))


def test_totals(repeat_report: str):
    assert "21000" in repeat_report or "21,000" in repeat_report
    assert "5.25" in repeat_report
    assert "630" in repeat_report


def test_failures_listed_with_reasons_and_calls(repeat_report: str):
    assert "no single query returns the answer" in repeat_report
    fail_idx = next(
        i
        for i, x in enumerate(repeat_report.splitlines())
        if x.startswith("#") and "fail" in x.lower() and "xfail" not in x.lower()
    )
    failures = "\n".join(repeat_report.splitlines()[fail_idx:])
    assert "q4-a" in failures
    assert "sum(amount)" in failures
    assert failures.count("flags: Raw SQL, Model edits, Several queries") == 1
    assert failures.count("no single query returns the answer") >= 6


def test_not_single_trial(repeat_report: str):
    assert "single-trial snapshot" not in repeat_report.lower()


def test_single_trial_label(tmp_path: Path):
    run = tmp_path / "run"
    shutil.copytree(FIXTURES / "run_repeat", run)
    md = json.loads((run / "metadata.json").read_text())
    md["n"] = 1
    (run / "metadata.json").write_text(json.dumps(md))
    lines = [x for x in (run / "results.jsonl").read_text().splitlines() if json.loads(x)["trial"] == 1]
    (run / "results.jsonl").write_text("\n".join(lines) + "\n")
    assert "single-trial snapshot" in render_report(run).lower()


def test_until_pass_report():
    report = render_report(FIXTURES / "run_until_pass")
    assert "pass^" not in report
    assert "Pass rate" not in report
    tasks = table_with(section(report, "slayer"), "Task", "First try", "Eventual", "Attempts")
    q1 = next(r for r in tasks if "q1-a" in r["Task"])
    q4 = next(r for r in tasks if "q4-a" in r["Task"])
    assert q1["Attempts"] == "2"
    assert q4["Attempts"] == "3"
    assert q1["First try"] != q1["Eventual"]
    assert q4["First try"] == q4["Eventual"]


def test_regenerates_byte_identical_offline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    def refuse(*_a, **_k):
        raise AssertionError("report must not use the network")

    monkeypatch.setattr(socket, "socket", refuse)
    run = tmp_path / "run"
    shutil.copytree(FIXTURES / "run_repeat", run)
    first = write_report(run).read_bytes()
    second = write_report(run).read_bytes()
    assert first == second
    assert (run / "report.md").read_bytes() == first
