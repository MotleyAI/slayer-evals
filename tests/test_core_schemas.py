"""JSON round-trips of the core schemas."""

import datetime as dt

from slayer_evals.core import (
    ALL_ROWS,
    COVERED_ROWS,
    AuditEvent,
    ParsedResult,
    PythonAudit,
    ResultWarning,
    RunMetadata,
    Submission,
    ToolCall,
    Trace,
    TraceFlags,
    TrialResult,
    Usage,
    Verdict,
)
from tests.helpers import make_task, manifest_with_aov


def _trace() -> Trace:
    return Trace(
        calls=[
            ToolCall(
                tool="query",
                args={"query": {"source_model": "orders", "measures": [{"formula": "sum(amount)", "name": "rev"}]}},
                result_text="| orders.rev |\n| --- |\n| 10.0 |",
                parsed=ParsedResult(
                    columns=["orders.rev"], rows=[[10.0]], warnings=[ResultWarning(kind="broadcast", message="m")]
                ),
            ),
            ToolCall(
                tool="query", args={"query": "nope"}, result_text="Error executing tool query: X: y", is_error=True
            ),
            ToolCall(
                tool="python",
                args={"code": "print(1)"},
                result_text="1",
                audit=PythonAudit(
                    sandbox_dir="/tmp/sb",
                    allowed_prefixes=["/usr/lib/python3.12"],
                    events=[AuditEvent(event="open", path="/tmp/sb/x.csv")],
                ),
            ),
        ],
        usage=Usage(input_tokens=10, output_tokens=5, cache_read_tokens=100, cache_write_tokens=7, partial=True),
        cost_usd=0.25,
        duration_s=12.5,
        turns=4,
        end_reason="timeout",
        error=None,
    )


def test_rows():
    assert ALL_ROWS == tuple(f"Q{i}" for i in range(1, 26))
    assert set(COVERED_ROWS) == set(ALL_ROWS) - {"Q19", "Q22"}


def test_trace_round_trip():
    trace = _trace()
    assert Trace.model_validate_json(trace.model_dump_json()) == trace


def test_task_round_trip():
    task = make_task(
        expect={"warning": ["broadcast", "associated"], "message_any": ["broadcast"]},
        xfail={"issue": "DEV-2058", "reason": "relative dates need a pinned clock"},
    )
    assert type(task).model_validate_json(task.model_dump_json()) == task


def test_manifest_round_trip():
    m = manifest_with_aov()
    assert type(m).model_validate_json(m.model_dump_json()) == m


def test_verdict_passed_is_correct_and_single_query():
    v = Verdict(correct=True, single_query=True, flags=TraceFlags(used_python=True, raw_sql=True))
    assert v.passed
    for field in ("correct", "single_query"):
        assert not v.model_copy(update={field: False}).passed


def test_trial_result_round_trip():
    tr = TrialResult(
        task_id="q1-region-total",
        row="Q1",
        profile="slayer+python",
        model="claude-opus-5-5",
        trial=2,
        verdict=Verdict(
            correct=True,
            single_query=False,
            single_query_reasons=["no single query returns the answer"],
            flags=TraceFlags(several_queries=True),
        ),
        end_reason="submitted",
        usage=Usage(input_tokens=1, output_tokens=2, cache_read_tokens=3, cache_write_tokens=4),
        cost_usd=0.1,
        duration_s=3.0,
        xfail=None,
    )
    assert TrialResult.model_validate_json(tr.model_dump_json()) == tr


def test_run_metadata_round_trip():
    md = RunMetadata(
        slayer_version="1.0.2",
        sdk_version="0.2.163",
        models=["claude-opus-5-5"],
        profiles=["slayer", "slayer+python"],
        mode="until-pass",
        n=3,
        max_turns=60,
        timeout_s=900.0,
        auth_mode="subscription",
        started_at=dt.datetime(2026, 10, 5, 12, 0, tzinfo=dt.UTC),
    )
    assert RunMetadata.model_validate_json(md.model_dump_json()) == md


def test_submission_round_trip():
    s = Submission(columns=["a", "b"], rows=[[1, None], [2.5, "x"]], message="done")
    assert Submission.model_validate_json(s.model_dump_json()) == s
