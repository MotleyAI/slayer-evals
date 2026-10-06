"""Task schema: prompt, covered rows and pitfalls, truth and reference queries, comparison rules, expectations."""

from typing import Annotated, Any, Literal, get_args

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator, model_validator

ALL_ROWS = tuple(f"Q{i}" for i in range(1, 26))
UNCOVERED_ROWS = ("Q19", "Q22")
COVERED_ROWS = tuple(r for r in ALL_ROWS if r not in UNCOVERED_ROWS)
Pitfall = Literal[
    "fan_out",
    "count_after_join",
    "chasm",
    "bridge",
    "non_unique_key",
    "outer_join_filter",
    "not_in_null",
    "count_outer_join",
    "filtered_total",
    "distinct_reagg",
    "missing_periods",
    "filter_before_window",
    "rows_window_gap",
    "timestamp_bounds",
    "avg_of_avgs",
    "bucket_reaggregation",
]
PITFALLS: tuple[str, ...] = get_args(Pitfall)
Suite = Literal["capability", "combo", "trap"]
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
    # NULL equals 0 in value columns (an empty period or a zero count).
    null_as_zero: bool = False


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
    covers: list[str] = Field(min_length=1)
    prompt: str
    truth_sql: str
    # The intended single SLayer query, in the argument shape of the SLayer MCP `query` tool.
    slayer_query: dict[str, Any]
    compare: Compare = Field(default_factory=Compare)
    expect: Literal["match"] | Expectation = "match"
    naive_sql: str | list[str] | None = None
    uses_saved: list[str] = Field(default_factory=list)
    xfail: XFail | None = None

    @field_validator("covers")
    @classmethod
    def _covers(cls, v: list[str]) -> list[str]:
        for c in v:
            if c in UNCOVERED_ROWS:
                raise ValueError(f"row {c} is not covered by the benchmark")
            if c not in COVERED_ROWS and c not in PITFALLS:
                raise ValueError(f"covers entry {c!r} is neither a covered row nor a pitfall kind")
        repeated = sorted({c for c in v if v.count(c) > 1})
        if repeated:
            raise ValueError(f"covers repeats {', '.join(repeated)}")
        if not any(c in COVERED_ROWS for c in v):
            raise ValueError("covers needs at least one row")
        return v

    @model_validator(mode="after")
    def _naive_sql_iff_trap(self) -> "Task":
        if (self.suite == "trap") != bool(self.naive_sql):
            raise ValueError("naive_sql is required on a trap task and forbidden on any other")
        return self

    @property
    def rows(self) -> list[str]:
        return [c for c in self.covers if c in COVERED_ROWS]

    @property
    def suite(self) -> Suite:
        if any(c in PITFALLS for c in self.covers):
            return "trap"
        return "combo" if len(self.rows) >= 2 else "capability"
