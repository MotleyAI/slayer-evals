"""Verdicts, per-trial results and run metadata."""

import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field

from slayer_evals.core.trace import EndReason, Profile, Usage

RunMode = Literal["repeat", "until-pass"]
AuthMode = Literal["subscription", "api-key"]


class TraceFlags(BaseModel):
    """Informational facts read off the trace; they do not affect `passed`."""

    used_python: bool = False
    raw_sql: bool = False
    edited_models: bool = False
    slayer_errors: bool = False
    several_queries: bool = False


class Verdict(BaseModel):
    correct: bool
    single_query: bool
    correct_reasons: list[str] = Field(default_factory=list)
    single_query_reasons: list[str] = Field(default_factory=list)
    # Truth column → result column of the submission match and of the single query's match.
    correct_columns: dict[str, str] = Field(default_factory=dict)
    single_query_columns: dict[str, str] = Field(default_factory=dict)
    flags: TraceFlags = Field(default_factory=TraceFlags)

    @property
    def passed(self) -> bool:
        return self.correct and self.single_query


class TrialResult(BaseModel):
    task_id: str
    row: str
    profile: Profile
    model: str
    trial: int
    verdict: Verdict | None
    end_reason: EndReason
    usage: Usage = Field(default_factory=Usage)
    cost_usd: float | None = None
    duration_s: float = 0.0
    xfail: str | None = None

    @property
    def passed(self) -> bool:
        return self.verdict is not None and self.verdict.passed


class RunMetadata(BaseModel):
    slayer_version: str
    sdk_version: str
    models: list[str]
    profiles: list[Profile]
    mode: RunMode
    n: int
    max_turns: int
    timeout_s: float
    auth_mode: AuthMode
    started_at: dt.datetime
