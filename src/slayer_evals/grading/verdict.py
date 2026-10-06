"""The verdict: is the answer correct, and is it a single SLayer query's own result; a pure function of its inputs."""

from slayer_evals.core import Expectation, Submission, Table, Task, ToolCall, Trace, Verdict
from slayer_evals.grading.errors import error_kind
from slayer_evals.grading.flags import trace_flags
from slayer_evals.grading.tables import match_tables

NO_SUBMISSION = "no submission"


def produced(call: ToolCall, expect: Expectation) -> bool:
    """Whether the call returned one of the expected error classes or warning kinds."""
    if expect.error is not None:
        return call.is_error and error_kind(call.result_text) in expect.kinds
    return call.parsed is not None and any(w.kind in expect.kinds for w in call.parsed.warnings)


def _single_query(truth: Table, task: Task, calls: list[ToolCall]) -> tuple[bool, list[str], dict[str, str]]:
    """Whether some successful query's own result matches the truth; its reason and column mapping."""
    queries = [(i, c.parsed) for i, c in enumerate(calls, start=1) if c.tool == "query" and not c.is_error and c.parsed]
    if not queries:
        return False, ["no successful query returned a table"], {}
    last_reason = ""
    for i, parsed in queries:
        m = match_tables(truth, parsed, task.compare)
        if m.ok:
            detail = m.reason.removeprefix("rows match in order").removeprefix("rows match")
            return True, [f"query #{i} returns the answer{detail}"], m.columns
        last_reason = f"query #{i}: {m.reason}"
    return False, [f"no single query returns the answer (last, {last_reason})"], {}


def grade(task: Task, truth: Table, submission: Submission | None, trace: Trace) -> Verdict:
    calls = trace.calls
    flags = trace_flags(calls)
    if submission is None:
        return Verdict(
            correct=False,
            single_query=False,
            correct_reasons=[NO_SUBMISSION],
            single_query_reasons=[NO_SUBMISSION],
            flags=flags,
        )
    if task.expect == "match":
        m = match_tables(truth, Table(columns=submission.columns, rows=submission.rows), task.compare)
        single, single_reasons, single_columns = _single_query(truth, task, calls)
        return Verdict(
            correct=m.ok,
            single_query=single,
            correct_reasons=[m.reason],
            single_query_reasons=single_reasons,
            correct_columns=m.columns,
            single_query_columns=single_columns,
            flags=flags,
        )
    expect = task.expect
    kind = " or ".join(expect.kinds)
    phrase = next((p for p in expect.message_any if p.lower() in submission.message.lower()), None)
    hit = next((i for i, c in enumerate(calls, start=1) if produced(c, expect)), None)
    return Verdict(
        correct=phrase is not None and hit is not None,
        single_query=hit is not None,
        correct_reasons=[
            f"message mentions {phrase!r}" if phrase else f"message mentions none of {expect.message_any}",
            f"the trace {'has' if hit else 'lacks'} a {kind} result",
        ],
        single_query_reasons=[f"call #{hit} returned {kind}" if hit else f"no call returned {kind}"],
        flags=flags,
    )
