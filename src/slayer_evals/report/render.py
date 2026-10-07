"""The markdown report of a run directory: suite, pitfall, per-row and per-task tables, xfails, totals, failures."""

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from slayer_evals.core import (
    ALL_ROWS,
    COVERED_ROWS,
    PITFALLS,
    UNCOVERED_ROWS,
    RunMetadata,
    Suite,
    Trace,
    TrialResult,
    trial_stem,
)

REPORT_FILE = "report.md"
RESULTS_FILE = "results.jsonl"
METADATA_FILE = "metadata.json"
TRACES_DIR = "traces"
DIGEST_CHARS = 240
ROW_TITLES = {
    "Q1": "Coarser grain in the same query",
    "Q2": "Arithmetic across grains",
    "Q3": "Re-aggregation",
    "Q4": "Transforms / time shift",
    "Q5": "Calculated dimensions, filters, order",
    "Q6": "Fields from many models, fan-out safe",
    "Q7": "Deep composition",
    "Q8": "Population inference",
    "Q9": "No silently wrong numbers",
    "Q10": "Filters across one-to-many joins",
    "Q11": "Rolling time windows",
    "Q12": "Aggregates as arguments",
    "Q13": "Order by what you don't show",
    "Q14": "Ranking and streaks",
    "Q15": "Multi-stage queries",
    "Q16": "Inline model extension",
    "Q17": "Saved measures that compose",
    "Q18": "Time-bucket safety",
    "Q19": "Agent & API surface",
    "Q20": "Relative & typed filters",
    "Q21": "Calendar expressions",
    "Q22": "Nested source data",
    "Q23": "Saved queries & refinement",
    "Q24": "Nested / hierarchical results",
    "Q25": "Explicit aggregate locality",
}
SUITES: tuple[Suite, ...] = ("capability", "combo", "trap")
NON_QUERY_TOOLS = ("submit_answer", "python")
_ERROR_RE = re.compile(r"Error executing tool [\w.-]+: ([A-Za-z_][\w.]*):")


def stem(r: TrialResult) -> str:
    return trial_stem(r.task_id, r.profile, r.model, r.trial)


def suite_of(covers: list[str]) -> Suite:
    """The suite a task's `covers` puts it in (as `Task.suite`)."""
    if any(c in PITFALLS for c in covers):
        return "trap"
    return "combo" if sum(c in COVERED_ROWS for c in covers) >= 2 else "capability"


def load_results(run_dir: Path) -> list[TrialResult]:
    path = run_dir / RESULTS_FILE
    if not path.exists():
        return []
    return [TrialResult.model_validate_json(x) for x in path.read_text().splitlines() if x.strip()]


def _table(header: list[str], rows: list[list[Any]]) -> list[str]:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(" --- " for _ in header) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return out


FLAGS = (
    ("used_python", "Python"),
    ("raw_sql", "Raw SQL"),
    ("edited_models", "Model edits"),
    ("query_errors", "Query errors"),
    ("several_queries", "Several queries"),
)


def _count(results: list[TrialResult], field: str) -> int:
    return sum(1 for r in results if r.verdict is not None and getattr(r.verdict, field))


def _flag_count(results: list[TrialResult], flag: str) -> int:
    return sum(1 for r in results if r.verdict is not None and getattr(r.verdict.flags, flag))


def _row_table(results: list[TrialResult]) -> list[str]:
    rows = []
    for row in ALL_ROWS:
        title = ROW_TITLES[row]
        blank = [""] * (3 + len(FLAGS))
        if row in UNCOVERED_ROWS:
            rows.append([row, title, "not covered", "", *blank])
            continue
        rs = [r for r in results if row in r.covers]
        if not rs:
            rows.append([row, title, 0, 0, *blank])
            continue
        counts = [_count(rs, f) for f in ("correct", "single_query", "passed")]
        flags = [_flag_count(rs, f) for f, _ in FLAGS]
        rows.append([row, title, len({r.task_id for r in rs}), len(rs), *counts, *flags])
    header = ["Row", "Feature", "Tasks", "Trials", "Correct", "Single query", "Passed", *(h for _, h in FLAGS)]
    return _table(header, rows)


def _by_task(results: list[TrialResult]) -> dict[str, list[TrialResult]]:
    out: dict[str, list[TrialResult]] = defaultdict(list)
    for r in sorted(results, key=lambda r: (r.task_id, r.trial)):
        out[r.task_id].append(r)
    return dict(sorted(out.items()))


def _task_table(results: list[TrialResult], md: RunMetadata) -> list[str]:
    tasks = _by_task(results)
    if md.mode == "repeat":
        rows = []
        for tid, rs in tasks.items():
            k, n = sum(r.passed for r in rs), len(rs)
            rows.append([tid, suite_of(rs[0].covers), _covers(rs[0]), f"{k}/{n}", f"{(k / n) ** md.n:.3f}"])
        return _table(["Task", "Suite", "Covers", "Pass rate", f"pass^{md.n}"], rows)
    rows = [
        [
            tid,
            suite_of(rs[0].covers),
            _covers(rs[0]),
            "yes" if rs[0].passed else "no",
            "yes" if any(r.passed for r in rs) else "no",
            len(rs),
        ]
        for tid, rs in tasks.items()
    ]
    return _table(["Task", "Suite", "Covers", "First try", "Eventual", "Attempts"], rows)


def _section(results: list[TrialResult], md: RunMetadata, profile: str, model: str) -> list[str]:
    scored = [r for r in results if r.profile == profile and r.model == model and r.xfail is None]
    out = [f"## `{profile}` · `{model}`", ""]
    if not any(r.profile == profile and r.model == model for r in results):
        return [*out, "No trials.", ""]
    out += ["A task counts under every row it covers, so a multi-row task adds to several rows.", ""]
    out += _row_table(scored) + [""]
    if scored:
        out += _task_table(scored, md) + [""]
    return out


def _covers(r: TrialResult) -> str:
    return ", ".join(r.covers)


def _scored(results: list[TrialResult]) -> list[TrialResult]:
    return [r for r in results if r.xfail is None]


def _suite_table(results: list[TrialResult], md: RunMetadata) -> list[str]:
    rows = []
    for suite in SUITES:
        for profile in md.profiles:
            for model in md.models:
                rs = [r for r in results if suite_of(r.covers) == suite and r.profile == profile and r.model == model]
                counts = [_count(rs, f) for f in ("correct", "single_query", "passed")]
                rows.append([suite, f"`{profile}`", f"`{model}`", len(rs), *counts])
    return _table(["Suite", "Profile", "Model", "Trials", "Correct", "Single query", "Passed"], rows)


def _pitfall_table(results: list[TrialResult], md: RunMetadata) -> list[str]:
    rows = []
    for pitfall in PITFALLS:
        if not any(pitfall in r.covers for r in results):
            continue
        for profile in md.profiles:
            for model in md.models:
                rs = [r for r in results if pitfall in r.covers and r.profile == profile and r.model == model]
                rows.append([pitfall, f"`{profile}`", f"`{model}`", len(rs), _count(rs, "correct")])
    if not rows:
        return []
    return [
        "### Traps by pitfall",
        "",
        *_table(["Pitfall", "Profile", "Model", "Trials", "Correct"], rows),
        "",
    ]


def _headline(results: list[TrialResult], md: RunMetadata) -> list[str]:
    return [
        "## Results by suite",
        "",
        (
            "**Correct** is the cross-profile comparison: every profile can reach a correct answer. "
            "**Single query** is not equally hard across profiles, since one raw SQL statement can express almost "
            "any answer, while SLayer needs its DSL to do the same in one query. Expected failures (xfail) are "
            "left out."
        ),
        "",
        *_suite_table(results, md),
        "",
        *_pitfall_table(results, md),
    ]


def _xfail_section(results: list[TrialResult]) -> list[str]:
    xf = [r for r in results if r.xfail is not None]
    out = ["## Expected failures (xfail)", ""]
    if not xf:
        return [*out, "None.", ""]
    out.append("These tasks run but are left out of the pass counts until the linked issue is fixed.")
    out.append("")
    groups: dict[tuple[str, str, str, str], list[TrialResult]] = defaultdict(list)
    for r in xf:
        groups[(r.task_id, r.xfail or "", r.profile, r.model)].append(r)
    rows = [[t, issue, p, m, len(rs), sum(r.passed for r in rs)] for (t, issue, p, m), rs in sorted(groups.items())]
    return [*out, *_table(["Task", "Issue", "Profile", "Model", "Trials", "Passed"], rows), ""]


def _totals(results: list[TrialResult]) -> list[str]:
    u = [r.usage for r in results]
    cost = sum(r.cost_usd or 0.0 for r in results)
    partial = sum(1 for x in u if x.partial)
    rows = [
        ["Trials", len(results)],
        ["Input tokens", sum(x.input_tokens for x in u)],
        ["Output tokens", sum(x.output_tokens for x in u)],
        ["Cache read tokens", sum(x.cache_read_tokens for x in u)],
        ["Cache write tokens", sum(x.cache_write_tokens for x in u)],
        ["Cost (USD)", f"{cost:.2f}"],
        ["Duration (s)", f"{sum(r.duration_s for r in results):.0f}"],
    ]
    if partial:
        rows.append(["Trials with partial usage", partial])
    return ["## Totals", "", *_table(["Total", "Value"], rows), ""]


def _clip(text: str) -> str:
    return text if len(text) <= DIGEST_CHARS else text[: DIGEST_CHARS - 1] + "…"


def _query_digest(args: dict[str, Any]) -> str:
    query = args.get("query")
    if isinstance(query, str):
        refine = args.get("refine")
        return f"saved query {query}" + (f" refined by {json.dumps(refine)}" if refine else "")
    stages = query if isinstance(query, list) else [query]
    parts = []
    for s in stages:
        if not isinstance(s, dict):
            continue
        fields = [str(s.get("source_model") or "(no source_model)")]
        for key in ("dimensions", "time_dimensions", "measures", "filters", "order"):
            if s.get(key):
                fields.append(f"{key}={json.dumps(s[key], separators=(',', ':'))}")
        parts.append(" ".join(fields))
    return " ; ".join(parts) or json.dumps(args)


def _what(tool: str, args: dict[str, Any]) -> str:
    if tool == "query":
        return _query_digest(args)
    if tool == "sql" and isinstance(args.get("sql"), str):
        return " ".join(args["sql"].split())
    return json.dumps(args, separators=(",", ":"))


def call_digest(trace: Trace) -> list[str]:
    """One line per SLayer or `sql` call: what was asked and what came back."""
    lines = []
    for i, c in enumerate(trace.calls, start=1):
        if c.tool in NON_QUERY_TOOLS:
            continue
        what = _what(c.tool, c.args)
        if c.is_error:
            m = _ERROR_RE.search(c.result_text)
            got = f"error {m.group(1)}" if m else "error"
        elif c.parsed is not None:
            got = f"{len(c.parsed.rows)} rows" + "".join(f", {w.kind} warning" for w in c.parsed.warnings)
        else:
            got = "ok"
        lines.append(f"#{i} `{c.tool}` {_clip(what)} → {got}")
    return lines


def _load_trace(run_dir: Path, r: TrialResult) -> Trace | None:
    path = run_dir / TRACES_DIR / f"{stem(r)}.json"
    return Trace.model_validate_json(path.read_text()) if path.exists() else None


def _failures(run_dir: Path, results: list[TrialResult]) -> list[str]:
    failed = [r for r in results if not r.passed]
    out = ["## Failed trials", ""]
    if not failed:
        return [*out, "None.", ""]
    for r in sorted(failed, key=lambda r: (r.task_id, r.profile, r.model, r.trial)):
        tag = f" · xfail {r.xfail}" if r.xfail else ""
        head = f"- **{r.task_id}** ({_covers(r)}) · {r.profile} · {r.model} · trial {r.trial} · {r.end_reason}{tag}"
        out.append(head)
        v = r.verdict
        if v is None:
            out.append("  - no verdict")
        else:
            for name, ok, reasons in (
                ("correct", v.correct, v.correct_reasons),
                ("single query", v.single_query, v.single_query_reasons),
            ):
                if not ok:
                    out.append(f"  - {name}: {'; '.join(reasons) or 'failed'}")
            raised = [h for f, h in FLAGS if getattr(v.flags, f)]
            if raised:
                out.append(f"  - flags: {', '.join(raised)}")
        trace = _load_trace(run_dir, r)
        if trace is not None:
            if trace.error:
                out.append(f"  - error: {trace.error}")
            digest = call_digest(trace)
            out += [f"  - {line}" for line in digest] or ["  - no query calls"]
    return [*out, ""]


def _metadata(md: RunMetadata, results: list[TrialResult]) -> list[str]:
    mode = f"{md.mode}, N = {md.n}"
    rows = [
        ["SLayer", md.slayer_version],
        ["Agent SDK", md.sdk_version],
        ["Models", ", ".join(md.models)],
        ["Profiles", ", ".join(md.profiles)],
        ["Mode", mode],
        ["Budgets", f"{md.max_turns} turns, {md.timeout_s:g} s per trial"],
        ["Auth", md.auth_mode],
        ["Started", md.started_at.strftime("%Y-%m-%d %H:%M UTC")],
        ["Trials", len(results)],
    ]
    return _table(["Run", ""], rows)


def render_report(run_dir: Path) -> str:
    md = RunMetadata.model_validate_json((run_dir / METADATA_FILE).read_text())
    results = load_results(run_dir)
    out = ["# SLayer capability benchmark report", ""]
    if md.n == 1:
        out += [
            "> **Single-trial snapshot:** every task ran once per profile and model, so individual rates are noisy.",
            "",
        ]
    out += [*_metadata(md, results), ""]
    out += [
        (
            "A trial passes when its answer is **correct** (the submitted table matches the truth) and is a "
            "**single query**'s result (the own result of one SLayer query or one SQL statement matches the truth, "
            "with no combining or post-processing). The flag columns count trials that used Python, used raw SQL, "
            "edited models, hit query errors or ran several queries; they do not affect passing."
        ),
        "",
    ]
    out += _headline(_scored(results), md)
    for profile in md.profiles:
        for model in md.models:
            out += _section(results, md, profile, model)
    out += _xfail_section(results)
    out += _totals(results)
    out += _failures(run_dir, results)
    return "\n".join(out).rstrip() + "\n"


def write_report(run_dir: Path) -> Path:
    path = run_dir / REPORT_FILE
    path.write_text(render_report(run_dir))
    return path
