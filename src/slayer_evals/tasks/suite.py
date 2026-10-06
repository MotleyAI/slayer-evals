"""Checks over a whole task set: coverage, suite folders, capability-neutral prompts, truth sizes, row markers."""

import re
from collections.abc import Collection
from pathlib import Path

from slayer_evals.core import COVERED_ROWS, UNCOVERED_ROWS, Suite, Table, Task
from slayer_evals.tasks.loading import load_task, task_files

MAX_TRUTH_ROWS = 20
REFUSAL_ROWS = ("Q9", "Q18")
MIN_TRAPS = 12
MIN_THREE_ROW_TASKS = 2
SUITE_DIRS: dict[Suite, str] = {"capability": "capability", "combo": "combo", "trap": "traps"}
# DSL names and syntax, and hints at a pitfall's mechanism, that a prompt must not contain (whole words, any case).
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
    "join",
    "joins",
    "joined",
    "joining",
    "duplicate",
    "duplicates",
    "duplicated",
    "double count",
    "double-count",
    "double counting",
    "double-counting",
    "fan-out",
    "fan out",
    "fans out",
    "chasm",
    "null",
    "nulls",
    "not in",
    "counted once",
    "count once",
    "counts once",
    "counting once",
    "count each",
    "counting each",
)
# DSL substrings, one of which a task's `slayer_query` must contain for each row it covers (rows without a clean tell
# have none).
ROW_MARKERS: dict[str, tuple[str, ...]] = {
    "Q1": ("partition_by",),
    "Q2": ("partition_by",),
    "Q3": ("partition_by",),
    "Q4": ("time_shift", "cumsum", "change"),
    "Q11": ("window=",),
    "Q14": ("rank(",),
    "Q16": ("source_name",),
    "Q17": ("aov",),
    "Q23": ("refine",),
    "Q24": ("rank(",),
}


def _pattern(entry: str) -> re.Pattern[str]:
    """`entry` as a whole word or phrase: word boundaries on its alphabetic edges only."""
    lead = r"\b" if entry[0].isalnum() else ""
    trail = r"\b" if entry[-1].isalnum() else ""
    return re.compile(lead + re.escape(entry) + trail, re.IGNORECASE)


DENY_PATTERNS = tuple((kw, _pattern(kw)) for kw in PROMPT_DENY_LIST)


def check_coverage(tasks: list[Task]) -> list[str]:
    rows = {r for t in tasks for r in t.rows}
    problems = [f"row {r} has no task" for r in COVERED_ROWS if r not in rows]
    problems += [f"row {r} is not covered but has tasks" for r in UNCOVERED_ROWS if r in rows]
    for r in REFUSAL_ROWS:
        if not any(r in t.rows and t.expect != "match" for t in tasks):
            problems.append(f"row {r} needs a refusal or warning task")
    traps = sum(t.suite == "trap" for t in tasks)
    if traps < MIN_TRAPS:
        problems.append(f"{traps} trap tasks, need at least {MIN_TRAPS}")
    wide = sum(len(t.rows) >= 3 for t in tasks)
    if wide < MIN_THREE_ROW_TASKS:
        problems.append(f"{wide} tasks cover three or more rows, need at least {MIN_THREE_ROW_TASKS}")
    return problems


def check_layout(tasks_dir: Path) -> list[str]:
    """Every task file sits under the folder of its suite."""
    problems = []
    for path in task_files(tasks_dir):
        task = load_task(path)
        folder = path.relative_to(tasks_dir).parts[0]
        want = SUITE_DIRS[task.suite]
        if folder != want:
            problems.append(f"{path}: a {task.suite} task belongs under {want}/")
    return problems


def check_prompts(tasks: list[Task]) -> list[str]:
    return [
        f"task {t.id}: prompt names DSL keyword or pitfall hint {kw!r}"
        for t in tasks
        for kw, pattern in DENY_PATTERNS
        if pattern.search(t.prompt)
    ]


def check_truth_sizes(truths: dict[str, Table], exempt: Collection[str] = ()) -> list[str]:
    return [
        f"task {tid}: truth has {len(t.rows)} rows (max {MAX_TRUTH_ROWS})"
        for tid, t in sorted(truths.items())
        if len(t.rows) > MAX_TRUTH_ROWS and tid not in exempt
    ]
