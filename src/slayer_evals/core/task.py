"""Task schema: prompt, truth SQL, comparison rules, capability predicates, allowances, expectations."""

import warnings
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ALL_ROWS = tuple(f"Q{i}" for i in range(1, 26))
UNCOVERED_ROWS = ("Q19", "Q22")
COVERED_ROWS = tuple(r for r in ALL_ROWS if r not in UNCOVERED_ROWS)

Clause = Literal["measures", "dimensions", "time_dimensions", "filters", "order"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Compare(Strict):
    keys: list[str] = Field(default_factory=list)
    values: list[str] = Field(default_factory=list)
    tolerance: float = 1e-6
    ordered: bool = False
    columns_exact: bool = False


class CallPredicate(Strict):
    """A function call in the query, optionally with a keyword argument or containing another call."""

    kind: Literal["call"] = "call"
    fn: str | list[str]
    kwarg: str | None = None
    within: "CallPredicate | None" = None
    dotted_arg: bool = False
    clause: Clause | None = None

    @property
    def fns(self) -> list[str]:
        return [self.fn] if isinstance(self.fn, str) else list(self.fn)

    def describe(self) -> str:
        out = f"call {' or '.join(self.fns)}"
        if self.kwarg:
            out += f" with {self.kwarg}"
        if self.dotted_arg:
            out += " over a joined model's column"
        if self.clause:
            out += f" in {self.clause}"
        if self.within:
            out += f" containing {self.within.describe()}"
        return out


class MultiStagePredicate(Strict):
    kind: Literal["multi_stage"] = "multi_stage"

    def describe(self) -> str:
        return "multi-stage query whose later stage reads an earlier named stage"


class SavedQueryPredicate(Strict):
    kind: Literal["saved_query"] = "saved_query"
    name: str
    refine: bool = False

    def describe(self) -> str:
        return f"run of saved query {self.name}" + (" with refine" if self.refine else "")


class OrderUnselectedPredicate(Strict):
    kind: Literal["order_unselected"] = "order_unselected"

    def describe(self) -> str:
        return "order by a column that is not selected"


class InlineExtensionPredicate(Strict):
    kind: Literal["inline_extension"] = "inline_extension"

    def describe(self) -> str:
        return "inline source_model extension"


class TimeFilterPredicate(Strict):
    kind: Literal["time_filter"] = "time_filter"
    form: Literal["typed", "relative"]

    def describe(self) -> str:
        return f"{self.form} time filter"


class NoSourceModelPredicate(Strict):
    kind: Literal["no_source_model"] = "no_source_model"

    def describe(self) -> str:
        return "query without a source_model"


class FilterPredicate(Strict):
    kind: Literal["filter"] = "filter"
    bool_op: Literal["and", "or", "not"] | None = None
    dotted_ref: bool = False

    def describe(self) -> str:
        out = "filter"
        if self.bool_op:
            out += f" with {self.bool_op.upper()}"
        if self.dotted_ref:
            out += " over a joined model's column"
        return out


class SourceModelPredicate(Strict):
    kind: Literal["source_model"] = "source_model"
    name: str

    def describe(self) -> str:
        return f"query on {self.name}"


class TimeDimensionPredicate(Strict):
    kind: Literal["time_dimension"] = "time_dimension"
    granularity: str | None = None

    def describe(self) -> str:
        return "time dimension" + (f" at {self.granularity}" if self.granularity else "")


class TraceStep(Strict):
    tool: str
    has_args: list[str] = Field(default_factory=list)
    uses_model_from_step: int | None = None


class TracePatternPredicate(Strict):
    """Successful calls in this order; the last step is the qualifying call."""

    kind: Literal["trace_pattern"] = "trace_pattern"
    steps: list[TraceStep] = Field(min_length=1)

    def describe(self) -> str:
        return "trace pattern " + " -> ".join(s.tool for s in self.steps)


class AnyOfPredicate(Strict):
    kind: Literal["any_of"] = "any_of"
    options: list[list["Predicate"]] = Field(min_length=1)

    def describe(self) -> str:
        return "any of: " + " | ".join(" & ".join(p.describe() for p in opt) for opt in self.options)


Predicate = Annotated[
    CallPredicate
    | MultiStagePredicate
    | SavedQueryPredicate
    | OrderUnselectedPredicate
    | InlineExtensionPredicate
    | TimeFilterPredicate
    | NoSourceModelPredicate
    | FilterPredicate
    | SourceModelPredicate
    | TimeDimensionPredicate
    | TracePatternPredicate
    | AnyOfPredicate,
    Field(discriminator="kind"),
]
AnyOfPredicate.model_rebuild()

SqlConstruct = Literal["model_sql", "column_sql", "inline_column_sql", "aggregation_sql", "model_filter_sql"]


# `construct` is the task-file key; it shadows the deprecated `BaseModel.construct` on purpose.
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", message='Field name "construct"')

    class Allowance(Strict):
        """Exempts one raw-SQL construct from the no-hack rule, for row-level scalar SQL only or for any SQL."""

        construct: SqlConstruct  # pyright: ignore[reportIncompatibleMethodOverride]
        scope: Literal["row_scalar", "any"] = "row_scalar"


class Expectation(Strict):
    """The agent must surface an error (exception class) or a warning (kind) instead of an answer."""

    error: str | None = None
    warning: str | None = None
    message_any: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def _one_kind(self) -> "Expectation":
        if (self.error is None) == (self.warning is None):
            raise ValueError("expect needs exactly one of error / warning")
        return self


class XFail(Strict):
    issue: str
    reason: str


class Task(Strict):
    id: str
    row: str
    prompt: str
    truth_sql: str
    compare: Compare = Field(default_factory=Compare)
    capabilities: list[Predicate]
    allow: list[Allowance] = Field(default_factory=list)
    expect: Literal["match"] | Expectation = "match"
    xfail: XFail | None = None

    @field_validator("row")
    @classmethod
    def _covered_row(cls, v: str) -> str:
        if v not in COVERED_ROWS:
            raise ValueError(f"row {v!r} is not a covered row ({', '.join(COVERED_ROWS)})")
        return v
