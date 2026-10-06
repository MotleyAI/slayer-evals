"""The verdict: correct, capability and no-hack, each with reasons; a pure function of its inputs."""

from slayer_evals.core import (
    Expectation,
    Predicate,
    StoreManifest,
    Submission,
    Table,
    Task,
    ToolCall,
    Trace,
    Verdict,
)
from slayer_evals.grading.errors import error_kind
from slayer_evals.grading.hacks import hack_reasons
from slayer_evals.grading.predicates import CallContext, satisfies
from slayer_evals.grading.tables import match_tables

NO_SUBMISSION = "no submission"


def produced(call: ToolCall, expect: Expectation) -> bool:
    """Whether the call returned the expected error class or warning kind."""
    if expect.error is not None:
        return call.is_error and error_kind(call.result_text) == expect.error
    return call.parsed is not None and any(w.kind == expect.warning for w in call.parsed.warnings)


def _unmet(predicates: list[Predicate], contexts: list[CallContext]) -> list[str]:
    unmet = [p for p in predicates if not any(satisfies(p, c) for c in contexts)]
    if unmet:
        return [f"unmet predicate: {p.describe()}" for p in unmet]
    return ["no single query satisfies all predicates"] if predicates else []


def _match_capability(
    task: Task, truth: Table, manifest: StoreManifest, calls: list[ToolCall]
) -> tuple[bool, list[str], dict[str, str]]:
    """Whether some successful query satisfies every predicate and itself returns the truth; reasons; its mapping."""
    candidates = [i for i, c in enumerate(calls) if c.tool == "query" and not c.is_error and c.parsed is not None]
    if not candidates:
        return False, ["no successful query call"], {}
    contexts = [CallContext(calls, i, manifest) for i in candidates]
    mismatches = []
    for ctx in contexts:
        if ctx.call.parsed is not None and all(satisfies(p, ctx) for p in task.capabilities):
            m = match_tables(truth, ctx.call.parsed, task.compare)
            if m.ok:
                detail = m.reason.removeprefix("rows match in order").removeprefix("rows match")
                return True, [f"query #{ctx.index + 1} satisfies all predicates{detail}"], m.columns
            mismatches.append(f"query #{ctx.index + 1} satisfies all predicates but its result differs: {m.reason}")
    return False, mismatches or _unmet(task.capabilities, contexts), {}


def _first_qualifying(task: Task, manifest: StoreManifest, calls: list[ToolCall], expect: Expectation) -> int | None:
    for i, call in enumerate(calls):
        if produced(call, expect) and all(satisfies(p, CallContext(calls, i, manifest)) for p in task.capabilities):
            return i
    return None


def grade(task: Task, truth: Table, manifest: StoreManifest, submission: Submission | None, trace: Trace) -> Verdict:
    if submission is None:
        return Verdict(
            correct=False,
            capability=False,
            no_hack=False,
            correct_reasons=[NO_SUBMISSION],
            capability_reasons=[NO_SUBMISSION],
            no_hack_reasons=[NO_SUBMISSION],
        )
    calls = trace.calls
    hacks = hack_reasons(calls, task.allow)
    no_hack_reasons = hacks or ["no raw SQL"]
    if task.expect == "match":
        m = match_tables(truth, Table(columns=submission.columns, rows=submission.rows), task.compare)
        correct, correct_reasons, correct_columns = m.ok, [m.reason], m.columns
        capability, capability_reasons, capability_columns = _match_capability(task, truth, manifest, calls)
    else:
        correct_columns, capability_columns = {}, {}
        expect = task.expect
        kind = expect.error or expect.warning
        phrase = next((p for p in expect.message_any if p.lower() in submission.message.lower()), None)
        seen = any(produced(c, expect) for c in calls)
        correct = phrase is not None and seen
        correct_reasons = [
            f"message mentions {phrase!r}" if phrase else f"message mentions none of {expect.message_any}",
            f"the trace {'has' if seen else 'lacks'} a {kind} result",
        ]
        hit = _first_qualifying(task, manifest, calls, expect)
        capability = hit is not None
        capability_reasons = (
            [f"call #{hit + 1} satisfies all predicates and returned {kind}"]
            if hit is not None
            else [f"no call satisfying the predicates returned {kind}"]
        )
    return Verdict(
        correct=correct,
        capability=capability,
        no_hack=not hacks,
        correct_reasons=correct_reasons,
        capability_reasons=capability_reasons,
        no_hack_reasons=no_hack_reasons,
        correct_columns=correct_columns,
        capability_columns=capability_columns,
    )
