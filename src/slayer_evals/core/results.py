"""Store manifest, verdicts, per-trial results and run metadata."""

import datetime as dt
from typing import Any, Literal

from pydantic import BaseModel, Field

from slayer_evals.core.trace import EndReason, Profile, Usage

RunMode = Literal["repeat", "until-pass"]
AuthMode = Literal["subscription", "api-key"]


class SavedMeasure(BaseModel):
    model: str
    name: str
    formula: str


class SavedQuery(BaseModel):
    name: str
    query: dict[str, Any] | list[dict[str, Any]]


class StoreManifest(BaseModel):
    """What the agent's store starts with, for expanding saved measures and queries during grading."""

    datasource: str
    models: list[str] = Field(default_factory=list)
    measures: list[SavedMeasure] = Field(default_factory=list)
    queries: list[SavedQuery] = Field(default_factory=list)


class Verdict(BaseModel):
    correct: bool
    capability: bool
    no_hack: bool
    correct_reasons: list[str] = Field(default_factory=list)
    capability_reasons: list[str] = Field(default_factory=list)
    no_hack_reasons: list[str] = Field(default_factory=list)
    # Truth column → result column of the submission match and of the qualifying query's match.
    correct_columns: dict[str, str] = Field(default_factory=dict)
    capability_columns: dict[str, str] = Field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.correct and self.capability and self.no_hack


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
