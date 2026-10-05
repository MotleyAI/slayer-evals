"""Checks over a whole task set: row coverage, capability-neutral prompts, truth sizes."""

from collections.abc import Collection

from slayer_evals.core import COVERED_ROWS, UNCOVERED_ROWS, Table, Task

MAX_TRUTH_ROWS = 20
REFUSAL_ROWS = ("Q9", "Q18")
# DSL names and syntax a prompt must not leak; matched case-insensitively as substrings.
PROMPT_DENY_LIST = (
    "partition_by",
    "time_shift",
    "cumsum",
    "change_pct",
    "window=",
    "rank(",
    "consecutive_periods",
    "weighted_avg",
    "count_distinct",
    "date_part",
    "date_diff",
    "date_add",
    "refine",
    "source_model",
    "source_queries",
    "multi-stage",
    "to_many_handling",
    "time_dimensions",
    "query-backed",
)


def check_coverage(tasks: list[Task]) -> list[str]:
    rows = {t.row for t in tasks}
    problems = [f"row {r} has no task" for r in COVERED_ROWS if r not in rows]
    problems += [f"row {r} is not covered but has tasks" for r in UNCOVERED_ROWS if r in rows]
    for r in REFUSAL_ROWS:
        if not any(t.row == r and t.expect != "match" for t in tasks):
            problems.append(f"row {r} needs a refusal or warning task")
    return problems


def check_prompts(tasks: list[Task]) -> list[str]:
    return [
        f"task {t.id}: prompt names DSL keyword {kw!r}"
        for t in tasks
        for kw in PROMPT_DENY_LIST
        if kw.lower() in t.prompt.lower()
    ]


def check_truth_sizes(truths: dict[str, Table], exempt: Collection[str] = ()) -> list[str]:
    return [
        f"task {tid}: truth has {len(t.rows)} rows (max {MAX_TRUTH_ROWS})"
        for tid, t in sorted(truths.items())
        if len(t.rows) > MAX_TRUTH_ROWS and tid not in exempt
    ]
