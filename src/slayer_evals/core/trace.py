"""The agent seam: what an agent receives (`AgentInput`) and returns (`Submission` plus a normalized `Trace`)."""

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from slayer_evals.core.table import ParsedResult

Profile = Literal["slayer", "slayer+python", "sql+python"]
PROFILES: tuple[Profile, ...] = ("slayer", "slayer+python", "sql+python")
EndReason = Literal["submitted", "max_turns", "timeout", "error", "auto_fail"]


class Submission(BaseModel):
    columns: list[str]
    rows: list[list[Any]]
    message: str = ""


class AuditEvent(BaseModel):
    event: str
    path: str | None = None


class PythonAudit(BaseModel):
    sandbox_dir: str
    allowed_prefixes: list[str] = Field(default_factory=list)
    events: list[AuditEvent] = Field(default_factory=list)


class ToolCall(BaseModel):
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)
    result_text: str = ""
    is_error: bool = False
    parsed: ParsedResult | None = None
    audit: PythonAudit | None = None


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    partial: bool = False


class Trace(BaseModel):
    profile: Profile
    calls: list[ToolCall] = Field(default_factory=list)
    usage: Usage = Field(default_factory=Usage)
    cost_usd: float | None = None
    duration_s: float | None = None
    turns: int = 0
    end_reason: EndReason = "submitted"
    error: str | None = None


class TrialEnv(BaseModel):
    trial_dir: Path
    store_dir: Path
    db_path: Path
    slayer_command: list[str]
    credentials: dict[str, str] = Field(default_factory=dict)
    max_turns: int = 60
    timeout_s: float = 900.0
    transcript_path: Path


class AgentInput(BaseModel):
    """Everything an agent may see: the prompt, its profile and its trial environment."""

    prompt: str
    profile: Profile
    env: TrialEnv


class AgentOutcome(BaseModel):
    submission: Submission | None
    trace: Trace
