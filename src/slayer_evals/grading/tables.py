"""Table comparison: column resolution, multiset or ordered rows, numeric tolerance, NULL/NaN and date normalization."""

import datetime as dt
import decimal
import math
import re
from typing import Any

from pydantic import BaseModel

from slayer_evals.core import Compare, Table

_NUM_RE = re.compile(r"^\s*-?\d+(\.\d+)?([eE][-+]?\d+)?\s*$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}(:\d{2}(\.\d+)?)?)?(Z|[+-]\d{2}:?\d{2})?$")


class MatchResult(BaseModel):
    ok: bool
    reason: str


def _iso(value: dt.date) -> str:
    if isinstance(value, dt.datetime):
        if value.tzinfo is not None:
            value = value.astimezone(dt.UTC).replace(tzinfo=None)
        if value.time() == dt.time(0):
            return value.date().isoformat()
        return value.isoformat()
    return value.isoformat()


def normalize(value: Any) -> Any:
    """A comparable form: None for NULL/NaN, floats for numbers and numeric strings, ISO text for dates."""
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, (int, float, decimal.Decimal)):
        f = float(value)
        return None if math.isnan(f) else f
    if isinstance(value, dt.date):
        return _iso(value)
    if isinstance(value, str):
        if _NUM_RE.match(value):
            return float(value)
        if _DATE_RE.match(value.strip()):
            try:
                return _iso(dt.datetime.fromisoformat(value.strip()))
            except ValueError:
                return value
        return value
    return value


def _equal(a: Any, b: Any, tolerance: float) -> bool:
    if isinstance(a, float) and isinstance(b, float):
        return abs(a - b) <= tolerance * max(1.0, abs(a), abs(b))
    return a == b and type(a) is type(b)


def _rows_equal(a: list[Any], b: list[Any], tolerance: float) -> bool:
    return all(_equal(x, y, tolerance) for x, y in zip(a, b, strict=True))


def resolve_column(name: str, columns: list[str]) -> tuple[int | None, str]:
    """Index of the result column for truth column `name` (exact, `.name` suffix, then `a__name`), or a reason."""
    rules = (
        lambda c: c == name,
        lambda c: c.endswith("." + name),
        lambda c: c.split(".")[-1].endswith("__" + name),
    )
    for rule in rules:
        hits = [i for i, c in enumerate(columns) if rule(c)]
        if len(hits) == 1:
            return hits[0], ""
        if len(hits) > 1:
            return None, f"column {name!r} is ambiguous: matches {', '.join(columns[i] for i in hits)}"
    return None, f"column {name!r} not found in result columns {columns}"


def match_tables(truth: Table, result: Table, compare: Compare) -> MatchResult:
    names = [*compare.keys, *compare.values] or list(truth.columns)
    truth_idx: list[int] = []
    result_idx: list[int] = []
    for name in names:
        if name not in truth.columns:
            return MatchResult(ok=False, reason=f"truth has no column {name!r}")
        idx, reason = resolve_column(name, result.columns)
        if idx is None:
            return MatchResult(ok=False, reason=reason)
        truth_idx.append(truth.columns.index(name))
        result_idx.append(idx)
    if len(set(result_idx)) < len(result_idx):
        return MatchResult(ok=False, reason="two truth columns resolve to the same result column")
    if compare.columns_exact and len(result.columns) != len(names):
        return MatchResult(ok=False, reason=f"result has {len(result.columns)} columns, expected exactly {len(names)}")
    if len(result.rows) != len(truth.rows):
        return MatchResult(ok=False, reason=f"result has {len(result.rows)} rows, truth has {len(truth.rows)}")
    want = [[normalize(r[i]) for i in truth_idx] for r in truth.rows]
    try:
        got = [[normalize(r[i]) for i in result_idx] for r in result.rows]
    except IndexError:
        return MatchResult(ok=False, reason="a result row is shorter than the result header")
    tol = compare.tolerance
    if compare.ordered:
        for k, (w, g) in enumerate(zip(want, got, strict=True)):
            if not _rows_equal(w, g, tol):
                return MatchResult(ok=False, reason=f"row {k + 1} is {g}, expected {w}")
        return MatchResult(ok=True, reason="rows match in order")
    unused = list(range(len(got)))
    for w in want:
        hit = next((j for j in unused if _rows_equal(w, got[j], tol)), None)
        if hit is None:
            return MatchResult(ok=False, reason=f"truth row {w} has no match in the result")
        unused.remove(hit)
    return MatchResult(ok=True, reason="rows match")
