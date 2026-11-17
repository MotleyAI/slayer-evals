"""Markdown report from a run directory."""

import json
import re
import shutil
import socket
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from slayer_evals.core import Profile, ToolCall, Trace, TrialResult, Verdict
from slayer_evals.report import render_report, write_report
from tests.helpers import REPO

FIXTURES = REPO / "tests" / "fixtures"
MODEL = "claude-opus-5-5"
OTHER_MODEL = "claude-sonnet-5"
RAW = "sql+python"


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


def bare(cell: str) -> str:
    return cell.strip("`* ")


def row_counts(report: str, profile: str, row: str, model: str = MODEL) -> dict[str, str]:
    rows = table_with(
        section(report, profile, model),
        "Row",
        "Tasks",
        "Trials",
        "Correct",
        "Single query",
        "Passed",
        "Raw SQL",
        "Query errors",
    )
    (match,) = [r for r in rows if r["Row"] == row]
    return match


def suite_counts(report: str, suite: str, profile: str, model: str = MODEL) -> tuple[str, str, str, str]:
    rows = table_with(report, "Suite", "Profile", "Model", "Trials", "Correct", "Single query", "Passed")
    (match,) = [
        r for r in rows if bare(r["Suite"]) == suite and bare(r["Profile"]) == profile and bare(r["Model"]) == model
    ]
    return match["Trials"], match["Correct"], match["Single query"], match["Passed"]


def pitfall_counts(report: str, pitfall: str, profile: str, model: str = MODEL) -> tuple[str, str]:
    rows = table_with(report, "Pitfall", "Profile", "Model", "Trials", "Correct")
    (match,) = [
        r for r in rows if bare(r["Pitfall"]) == pitfall and bare(r["Profile"]) == profile and bare(r["Model"]) == model
    ]
    return match["Trials"], match["Correct"]


def failures(report: str) -> str:
    lines = report.splitlines()
    start = next(
        i for i, x in enumerate(lines) if x.startswith("#") and "fail" in x.lower() and "xfail" not in x.lower()
    )
    return "\n".join(lines[start:])


@pytest.fixture
def repeat_report() -> str:
    return render_report(FIXTURES / "run_repeat")


def test_metadata(repeat_report: str):
    for text in ("1.0.2", "0.2.163", MODEL, "repeat", "subscription", "2026-10-05", "60", "900", RAW):
        assert text in repeat_report, text


def test_headline_suite_table(repeat_report: str):
    assert suite_counts(repeat_report, "capability", "slayer") == ("9", "9", "6", "6")
    assert suite_counts(repeat_report, "capability", "slayer+python") == ("6", "6", "5", "5")
    assert suite_counts(repeat_report, "capability", RAW) == ("9", "5", "4", "4")
    assert suite_counts(repeat_report, "capability", "slayer", OTHER_MODEL) == ("3", "3", "0", "0")
    assert suite_counts(repeat_report, "combo", "slayer") == ("3", "3", "3", "3")
    assert suite_counts(repeat_report, "combo", RAW) == ("3", "1", "1", "1")
    assert suite_counts(repeat_report, "trap", "slayer") == ("6", "6", "5", "5")
    assert suite_counts(repeat_report, "trap", "slayer+python") == ("3", "2", "2", "2")
    assert suite_counts(repeat_report, "trap", RAW) == ("6", "1", "1", "1")


def test_headline_comes_first_and_names_correct_as_the_comparison(repeat_report: str):
    suite_at = repeat_report.index("| Suite")
    assert suite_at < repeat_report.index("## `slayer`")
    assert re.search(r"correct.{0,300}(cross-profile|across (the )?profiles)", repeat_report, re.IGNORECASE | re.DOTALL)


def test_pitfall_table(repeat_report: str):
    assert pitfall_counts(repeat_report, "fan_out", "slayer") == ("3", "3")
    assert pitfall_counts(repeat_report, "fan_out", "slayer+python") == ("3", "2")
    assert pitfall_counts(repeat_report, "fan_out", RAW) == ("3", "0")
    assert pitfall_counts(repeat_report, "chasm", "slayer") == ("3", "3")
    assert pitfall_counts(repeat_report, "chasm", RAW) == ("3", "1")


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
    q1p = row_counts(repeat_report, "slayer+python", "Q1")
    assert (q1p["Single query"], q1p["Passed"], q1p["Raw SQL"], q1p["Several queries"]) == ("2", "2", "1", "1")
    raw = row_counts(repeat_report, RAW, "Q1")
    assert (raw["Trials"], raw["Correct"], raw["Single query"], raw["Passed"]) == ("3", "2", "1", "1")
    assert (raw["Raw SQL"], raw["Query errors"], raw["Several queries"], raw["Python"]) == ("3", "1", "1", "1")


def test_multi_row_tasks_count_under_every_row(repeat_report: str):
    q2 = row_counts(repeat_report, "slayer", "Q2")
    assert (q2["Tasks"], q2["Trials"], q2["Passed"]) == ("1", "3", "3")
    q4 = row_counts(repeat_report, "slayer", "Q4")
    assert (q4["Tasks"], q4["Trials"], q4["Correct"], q4["Single query"], q4["Passed"]) == ("2", "6", "6", "3", "3")
    q6 = row_counts(repeat_report, RAW, "Q6")
    assert (q6["Tasks"], q6["Trials"], q6["Correct"], q6["Passed"]) == ("2", "6", "1", "1")
    assert "every row it covers" in section(repeat_report, "slayer").lower()


def test_one_multi_row_trial(tmp_path: Path):
    run = tmp_path / "run"
    (run / "traces").mkdir(parents=True)
    md = json.loads((FIXTURES / "run_repeat" / "metadata.json").read_text())
    (run / "metadata.json").write_text(json.dumps({**md, "models": [MODEL], "profiles": ["slayer"], "n": 1}))
    line = next(
        x
        for x in (FIXTURES / "run_repeat" / "results.jsonl").read_text().splitlines()
        if json.loads(x)["task_id"] == "c24-a" and json.loads(x)["profile"] == "slayer"
    )
    assert json.loads(line)["covers"] == ["Q2", "Q4"]
    (run / "results.jsonl").write_text(line + "\n")
    report = render_report(run)
    for row in ("Q2", "Q4"):
        counts = row_counts(report, "slayer", row)
        assert (counts["Tasks"], counts["Trials"], counts["Passed"]) == ("1", "1", "1"), row
    assert row_counts(report, "slayer", "Q1")["Trials"] == "0"
    assert suite_counts(report, "combo", "slayer") == ("1", "1", "1", "1")


def test_uncovered_rows(repeat_report: str):
    for row in ("Q19", "Q22"):
        line = next(x for x in section(repeat_report, "slayer").splitlines() if f"| {row} |" in x)
        assert "not covered" in line


def test_flag_column_renamed(repeat_report: str):
    assert "SLayer errors" not in repeat_report
    assert "Query errors" in repeat_report


def test_repeat_pass_rate(repeat_report: str):
    tasks = table_with(section(repeat_report, "slayer+python"), "Task", "Suite", "Pass rate", "pass^3")
    q1 = next(r for r in tasks if "q1-a" in r["Task"])
    assert q1["Pass rate"] == "2/3"
    all_pass = next(r for r in tasks if "q4-a" in r["Task"])
    assert all_pass["Pass rate"] == "3/3"
    assert q1["pass^3"] != all_pass["pass^3"]
    plain = table_with(section(repeat_report, "slayer"), "Task", "Pass rate", "pass^3")
    assert next(r for r in plain if "q1-a" in r["Task"])["pass^3"] == all_pass["pass^3"]


def test_task_table_shows_suites(repeat_report: str):
    tasks = {bare(r["Task"]): r for r in table_with(section(repeat_report, RAW), "Task", "Suite", "Pass rate")}
    assert bare(tasks["q1-a"]["Suite"]) == "capability"
    assert bare(tasks["c24-a"]["Suite"]) == "combo"
    assert bare(tasks["t1-fan"]["Suite"]) == "trap"
    assert tasks["q1-a"]["Pass rate"] == "1/3"
    assert tasks["s23-a"]["Pass rate"] == "0/3"


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


def test_totals_count_auto_failed_trials(repeat_report: str):
    totals = {r["Total"]: r["Value"] for r in table_with(repeat_report, "Total", "Value")}
    assert totals["Trials"] == "54"
    assert totals["Input tokens"] == "51000"
    assert totals["Cost (USD)"] == "12.75"
    assert totals["Duration (s)"] == "1530"


def test_failures_listed_with_reasons_and_calls(repeat_report: str):
    assert "no single query returns the answer" in repeat_report
    text = failures(repeat_report)
    assert "q4-a" in text
    assert "sum(amount)" in text
    assert text.count("flags: Raw SQL, Model edits, Several queries") == 1
    assert text.count("no single query returns the answer") >= 6


def test_every_failed_trial_listed_with_its_reasons(repeat_report: str):
    entries = {}
    for e in failures(repeat_report).split("\n- **")[1:]:
        head = e.split("\n", 1)[0]
        tid = head.split("**", 1)[0]
        trial = head.rsplit("trial ", 1)[1].split(" ", 1)[0]
        profile, model = head.split(" · ")[1:3]
        entries[(tid, profile, model, trial)] = e
    lines = (FIXTURES / "run_repeat" / "results.jsonl").read_text().splitlines()
    failed = [r for r in map(json.loads, lines) if not (r["verdict"]["correct"] and r["verdict"]["single_query"])]
    assert len(entries) == len(failed)
    for r in failed:
        e = entries[(r["task_id"], r["profile"], r["model"], str(r["trial"]))]
        v = r["verdict"]
        for ok, reasons in ((v["correct"], v["correct_reasons"]), (v["single_query"], v["single_query_reasons"])):
            if not ok:
                assert "; ".join(reasons) in e, (r["task_id"], r["profile"], r["trial"])


def test_failures_digest_sql_calls(repeat_report: str):
    text = failures(repeat_report)
    raw_q1 = text.split("**q1-a**")
    entry = next(e for e in raw_q1 if f"{RAW} · {MODEL} · trial 2" in e.split("\n", 1)[0])
    entry = entry.split("\n- **")[0]
    assert "`sql`" in entry
    assert "select region, count(*) as n from orders_flat group by 1" in entry


def test_auto_failed_trials_listed(repeat_report: str):
    text = failures(repeat_report)
    entries = [e for e in text.split("- **")[1:] if e.startswith("s23-a**") and RAW in e.split("\n", 1)[0]]
    assert len(entries) == 3
    for e in entries:
        assert "auto_fail" in e.split("\n", 1)[0]
        assert "monthly_rev" in e


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


def test_until_pass_auto_fail_is_one_attempt():
    report = render_report(FIXTURES / "run_until_pass")
    tasks = {bare(r["Task"]): r for r in table_with(section(report, RAW), "Task", "First try", "Eventual", "Attempts")}
    assert (tasks["s23-a"]["First try"], tasks["s23-a"]["Eventual"], tasks["s23-a"]["Attempts"]) == ("no", "no", "1")
    assert (tasks["q1-a"]["First try"], tasks["q1-a"]["Eventual"], tasks["q1-a"]["Attempts"]) == ("no", "yes", "2")


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


def run_with(tmp_path: Path, lines: list[dict[str, Any]]) -> Path:
    """A copy of the `run_repeat` fixture holding only `lines` as its results."""
    run = tmp_path / "run"
    shutil.copytree(FIXTURES / "run_repeat", run)
    (run / "results.jsonl").write_text("".join(json.dumps(x) + "\n" for x in lines))
    return run


def fixture_lines() -> list[dict[str, Any]]:
    return [json.loads(x) for x in (FIXTURES / "run_repeat" / "results.jsonl").read_text().splitlines()]


def slayer_cell(report: str) -> str:
    rows = table_with(report, "Run")
    (cell,) = [r[""] for r in rows if r["Run"] == "SLayer"]
    return cell


def test_slayer_version_comes_from_the_results_lines(tmp_path: Path):
    lines = [{**x, "slayer_version": "1.7.0"} for x in fixture_lines()]
    assert slayer_cell(render_report(run_with(tmp_path, lines))) == "1.7.0"


def test_mixed_slayer_versions_listed_with_trial_counts(tmp_path: Path):
    lines = fixture_lines()[:5]
    versions = ["1.1.0", "1.1.0", "1.2.0", "1.1.0", "1.2.0"]
    cell = slayer_cell(render_report(run_with(tmp_path, [{**x, "slayer_version": v} for x, v in zip(lines, versions)])))
    assert re.search(r"1\.1\.0\D+3\b", cell), cell
    assert re.search(r"1\.2\.0\D+2\b", cell), cell
    assert cell.index("1.1.0") < cell.index("1.2.0")


def test_results_line_without_slayer_version_rejected(tmp_path: Path):
    lines = [{**x, "slayer_version": "1.7.0"} for x in fixture_lines()]
    del lines[3]["slayer_version"]
    run_dir = run_with(tmp_path, lines)
    with pytest.raises(ValidationError, match="slayer_version"):
        render_report(run_dir)


def test_new_rows_in_the_per_row_table(tmp_path: Path):
    base = next(x for x in fixture_lines() if x["task_id"] == "q1-a" and x["profile"] == "slayer")
    lines = [
        {**base, "task_id": "q26-a", "covers": ["Q26"], "slayer_version": "1.7.0"},
        {**base, "task_id": "q27-a", "covers": ["Q27"], "slayer_version": "1.7.0"},
        {**base, "task_id": "t27-a", "covers": ["Q27", "null_element"], "slayer_version": "1.7.0"},
    ]
    report = render_report(run_with(tmp_path, lines))
    q26 = row_counts(report, "slayer", "Q26")
    q27 = row_counts(report, "slayer", "Q27")
    assert (q26["Feature"], q26["Tasks"], q26["Trials"]) == ("Metrics without a join path", "1", "1")
    assert (q27["Feature"], q27["Tasks"], q27["Trials"]) == ("List columns", "2", "2")
    assert pitfall_counts(report, "null_element", "slayer") == ("1", "1")


MOTLEY_URL = "http://localhost:8000/api/v1/mcp/"
MOTLEY_NOTE = (
    "Motley's `query` cannot run a saved query by name with `refine` yet (DEV-2260); "
    "saved-query tasks are answered with one inline query."
)
BARE_ERROR = "TimeDimensionColumnError: A time dimension must reference a raw date column; 'month' is already bucketed."


def _motley_result(profile: Profile, passed: bool) -> TrialResult:
    verdict = Verdict(
        correct=passed,
        single_query=passed,
        correct_reasons=["rows match" if passed else "message mentions none of ['bucketed']"],
        single_query_reasons=["query #1 returns the answer" if passed else "no call returned TimeDimensionColumnError"],
    )
    return TrialResult(
        task_id="q18-a",
        covers=["Q18"],
        profile=profile,
        model=MODEL,
        trial=1,
        slayer_version="1.8.5",
        verdict=verdict,
        end_reason="submitted",
    )


@pytest.fixture
def motley_report(tmp_path: Path) -> str:
    run = tmp_path / "run"
    (run / "traces").mkdir(parents=True)
    md = json.loads((FIXTURES / "run_repeat" / "metadata.json").read_text())
    md.update(
        models=[MODEL],
        profiles=["slayer", "motley", "motley+python"],
        n=1,
        motley_url=MOTLEY_URL,
        motley_server_info="motley 1.30.0",
    )
    (run / "metadata.json").write_text(json.dumps(md))
    rs = [_motley_result("slayer", True), _motley_result("motley", True), _motley_result("motley+python", False)]
    (run / "results.jsonl").write_text("".join(r.model_dump_json() + "\n" for r in rs))
    failed = ToolCall(
        tool="query",
        args={"query": {"source_model": "orders", "time_dimensions": [{"dimension": "month", "granularity": "year"}]}},
        result_text=BARE_ERROR,
        is_error=True,
    )
    trace = Trace(profile="motley+python", calls=[failed])
    (run / "traces" / f"q18-a__motley+python__{MODEL}__1.json").write_text(trace.model_dump_json())
    return render_report(run)


def test_motley_metadata_rows(motley_report: str):
    rows = {r["Run"]: r[""] for r in table_with(motley_report, "Run")}
    assert rows["Motley MCP"] == MOTLEY_URL
    assert rows["MCP server info"] == "motley 1.30.0"


def test_motley_sections_open_with_the_saved_query_note(motley_report: str):
    for profile in ("motley", "motley+python"):
        first = next(x for x in section(motley_report, profile).splitlines() if x.strip())
        assert first == MOTLEY_NOTE, profile
    assert MOTLEY_NOTE not in section(motley_report, "slayer")
    assert motley_report.count(MOTLEY_NOTE) == 2


def test_failed_motley_call_digest_names_the_bare_error_class(motley_report: str):
    entry = failures(motley_report).split("**q18-a**", 1)[1]
    assert "motley+python" in entry.split("\n", 1)[0]
    assert "`query`" in entry
    assert "error TimeDimensionColumnError" in entry


def test_run_without_motley_has_no_motley_rows_or_note(repeat_report: str):
    assert "Motley" not in repeat_report
    assert "MCP server info" not in repeat_report


# The Jaffle sub-suite


def _jaffle_result(task_id: str, profile: Profile, trial: int, correct: bool, single: bool, model: str = MODEL):
    return TrialResult(
        task_id=task_id,
        dataset="jaffle",
        covers=[],
        profile=profile,
        model=model,
        trial=trial,
        slayer_version="1.8.5",
        verdict=Verdict(correct=correct, single_query=single),
        end_reason="submitted",
    )


JAFFLE_RESULTS = [
    _jaffle_result("j-q01-stores", "slayer", 1, True, True),
    _jaffle_result("j-q01-stores", "slayer", 2, False, False),
    _jaffle_result("j-q01-stores", RAW, 1, True, True),
    _jaffle_result("j-q01-stores", RAW, 2, True, False),
    _jaffle_result("j-c09-brooklyn-cogs-margin", "slayer+python", 1, True, False),
    _jaffle_result("j-c09-brooklyn-cogs-margin", "slayer", 1, True, True, model=OTHER_MODEL),
]


def jaffle_section(report: str) -> str:
    lines = report.splitlines()
    start = next(i for i, x in enumerate(lines) if x.startswith("#") and "jaffle" in x.lower())
    level = lines[start].split(" ", 1)[0]
    end = next(
        (
            i
            for i in range(start + 1, len(lines))
            if lines[i].startswith("#") and len(lines[i].split(" ", 1)[0]) <= len(level)
        ),
        len(lines),
    )
    return "\n".join(lines[start:end])


@pytest.fixture
def mixed_run(tmp_path: Path) -> Path:
    run = tmp_path / "run"
    shutil.copytree(FIXTURES / "run_repeat", run)
    with (run / "results.jsonl").open("a") as f:
        for r in JAFFLE_RESULTS:
            f.write(r.model_dump_json() + "\n")
    return run


def test_jaffle_headline_row(mixed_run: Path):
    report = render_report(mixed_run)
    assert suite_counts(report, "jaffle", "slayer") == ("2", "1", "1", "1")
    assert suite_counts(report, "jaffle", RAW) == ("2", "2", "1", "1")
    assert suite_counts(report, "jaffle", "slayer+python") == ("1", "1", "0", "0")
    assert suite_counts(report, "jaffle", "slayer", OTHER_MODEL) == ("1", "1", "1", "1")


def test_bench_suites_unchanged_by_jaffle_trials(mixed_run: Path, repeat_report: str):
    report = render_report(mixed_run)
    for suite in ("capability", "combo", "trap"):
        for profile in ("slayer", "slayer+python", RAW):
            assert suite_counts(report, suite, profile) == suite_counts(repeat_report, suite, profile), (suite, profile)


def test_row_and_pitfall_tables_count_bench_trials_only(mixed_run: Path, repeat_report: str):
    report = render_report(mixed_run)
    for profile in ("slayer", "slayer+python", RAW):
        assert table_with(section(report, profile), "Row", "Tasks", "Trials") == table_with(
            section(repeat_report, profile), "Row", "Tasks", "Trials"
        ), profile
    assert table_with(report, "Pitfall", "Trials", "Correct") == table_with(
        repeat_report, "Pitfall", "Trials", "Correct"
    )


def test_jaffle_section_lists_each_task(mixed_run: Path):
    text = jaffle_section(render_report(mixed_run))
    rows = table_with(text, "Task", "Profile", "Model", "Trials", "Correct", "Single query", "Passed")
    got = {
        (bare(r["Task"]), bare(r["Profile"]), bare(r["Model"])): (
            r["Trials"],
            r["Correct"],
            r["Single query"],
            r["Passed"],
        )
        for r in rows
    }
    assert got[("j-q01-stores", "slayer", MODEL)] == ("2", "1", "1", "1")
    assert got[("j-q01-stores", RAW, MODEL)] == ("2", "2", "1", "1")
    assert got[("j-c09-brooklyn-cogs-margin", "slayer+python", MODEL)] == ("1", "1", "0", "0")
    assert got[("j-c09-brooklyn-cogs-margin", "slayer", OTHER_MODEL)] == ("1", "1", "1", "1")
    assert not any(t.startswith(("q", "c", "t", "s", "x")) for t, _, _ in got)


def test_jaffle_section_states_how_rules_reach_each_profile(mixed_run: Path):
    text = " ".join(jaffle_section(render_report(mixed_run)).lower().split())
    assert "business rules" in text
    assert "system prompt" in text
    assert "search" in text


def test_jaffle_report_regenerates_byte_identical(mixed_run: Path):
    first = write_report(mixed_run).read_bytes()
    assert write_report(mixed_run).read_bytes() == first


def test_run_without_jaffle(repeat_report: str):
    suites = {bare(r["Suite"]) for r in table_with(repeat_report, "Suite", "Profile", "Model", "Trials")}
    assert suites == {"capability", "combo", "trap"}
    assert not any(x.startswith("#") and "jaffle" in x.lower() for x in repeat_report.splitlines())


def test_headline_lists_only_suites_with_trials(tmp_path: Path):
    run = tmp_path / "run"
    (run / "traces").mkdir(parents=True)
    md = json.loads((FIXTURES / "run_repeat" / "metadata.json").read_text())
    (run / "metadata.json").write_text(json.dumps({**md, "models": [MODEL], "profiles": ["slayer", RAW], "n": 2}))
    (run / "results.jsonl").write_text("".join(r.model_dump_json() + "\n" for r in JAFFLE_RESULTS[:4]))
    report = render_report(run)
    suites = {bare(r["Suite"]) for r in table_with(report, "Suite", "Profile", "Model", "Trials")}
    assert suites == {"jaffle"}
