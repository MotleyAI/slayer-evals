"""Task schema: prompt, truth SQL, comparison rules, expectations."""

from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator, model_validator

ALL_ROWS = tuple(f"Q{i}" for i in range(1, 26))
UNCOVERED_ROWS = ("Q19", "Q22")
COVERED_ROWS = tuple(r for r in ALL_ROWS if r not in UNCOVERED_ROWS)
STEM_SEP = "__"


def _safe_name(v: str) -> str:
    if not v or v.startswith(".") or "/" in v or "\\" in v or STEM_SEP in v:
        raise ValueError(f"{v!r} must be a single path component without a leading dot or {STEM_SEP!r}")
    return v


# A name that becomes part of a trial's output file stem.
SafeName = Annotated[str, AfterValidator(_safe_name)]


def trial_stem(task_id: str, profile: str, model: str, trial: int) -> str:
    """The file stem of one trial's trace and transcript."""
    return STEM_SEP.join([task_id, profile, model, str(trial)])


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Compare(Strict):
    keys: list[str] = Field(default_factory=list)
    values: list[str] = Field(default_factory=list)
    tolerance: float = 1e-6
    ordered: bool = False
    columns_exact: bool = False


class Expectation(Strict):
    """The agent must surface an error (exception class) or a warning (kind) instead of an answer."""

    error: str | list[str] | None = None
    warning: str | list[str] | None = None
    message_any: list[str] = Field(min_length=1)

    @property
    def kinds(self) -> list[str]:
        """The accepted error classes or warning kinds."""
        value = self.error if self.error is not None else self.warning
        return [value] if isinstance(value, str) else list(value or [])

    @model_validator(mode="after")
    def _one_kind(self) -> "Expectation":
        if (self.error is None) == (self.warning is None):
            raise ValueError("expect needs exactly one of error / warning")
        return self


class XFail(Strict):
    issue: str
    reason: str


class Task(Strict):
    id: SafeName
    row: str
    prompt: str
    truth_sql: str
    compare: Compare = Field(default_factory=Compare)
    expect: Literal["match"] | Expectation = "match"
    xfail: XFail | None = None

    @field_validator("row")
    @classmethod
    def _covered_row(cls, v: str) -> str:
        if v not in COVERED_ROWS:
            raise ValueError(f"row {v!r} is not a covered row ({', '.join(COVERED_ROWS)})")
        return v
