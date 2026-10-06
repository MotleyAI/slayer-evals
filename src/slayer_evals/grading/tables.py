"""Table comparison: column resolution, multiset or ordered rows, numeric tolerance, NULL/NaN/zero and date normalization."""

import datetime as dt
import decimal
import difflib
import itertools
import math
import re
from typing import Any

from pydantic import BaseModel, Field

from slayer_evals.core import Compare, Table

_NUM_RE = re.compile(r"^\s*-?\d+(\.\d+)?([eE][-+]?\d+)?\s*$")
MAX_ASSIGNMENTS = 10_000
_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}(:\d{2}(\.\d+)?)?)?(Z|[+-]\d{2}:?\d{2})?$")


class MatchResult(BaseModel):
    ok: bool
    reason: str
    columns: dict[str, str] = Field(default_factory=dict)


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
        if _MONTH_RE.match(value.strip()):
            return value.strip() + "-01"
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


def resolve_column(name: str, columns: list[str]) -> tuple[int | None, str | None]:
    """The result column for truth column `name` by exact name, `.name` suffix, then `a__name`; or why it is ambiguous."""
    rules = (
        lambda c: c == name,
        lambda c: c.endswith("." + name),
        lambda c: c.split(".")[-1].endswith("__" + name),
    )
    for rule in rules:
        hits = [i for i, c in enumerate(columns) if rule(c)]
        if len(hits) == 1:
            return hits[0], None
        if len(hits) > 1:
            return None, f"column {name!r} is ambiguous: matches {', '.join(columns[i] for i in hits)}"
    return None, None


def _sort_key(v: Any) -> tuple[int, Any]:
    if v is None:
        return 0, 0
    if isinstance(v, bool):
        return 1, v
    if isinstance(v, float):
        return 2, v
    return 3, str(v)


def _same_values(a: list[Any], b: list[Any], tolerance: float) -> bool:
    return _rows_equal(sorted(a, key=_sort_key), sorted(b, key=_sort_key), tolerance)


def _leaf(column: str) -> str:
    return column.rsplit(".", 1)[-1].rsplit("__", 1)[-1].lower()


def _zeroed(values: list[Any]) -> list[Any]:
    return [0.0 if v is None else v for v in values]


def _rows_match(want: list[list[Any]], got: list[list[Any]], compare: Compare) -> str | None:
    """None when the rows match (as a multiset, or in order when `ordered`); else why not."""
    tol = compare.tolerance
    if compare.ordered:
        for k, (w, g) in enumerate(zip(want, got, strict=True)):
            if not _rows_equal(w, g, tol):
                return f"row {k + 1} is {g}, expected {w}"
        return None
    unused = list(range(len(got)))
    for w in want:
        hit = next((j for j in unused if _rows_equal(w, got[j], tol)), None)
        if hit is None:
            return f"truth row {w} has no match in the result"
        unused.remove(hit)
    return None


def _assignments(
    unmatched: list[str],
    free: list[int],
    want_cols: dict[str, list[Any]],
    got_cols: dict[int, list[Any]],
    result: Table,
    compare: Compare,
) -> list[tuple[int, ...]]:
    """Injective assignments of unmatched truth columns to free result columns with equal values, closest names first."""

    def got(n: str, i: int) -> list[Any]:
        return _zeroed(got_cols[i]) if compare.null_as_zero and n in compare.values else got_cols[i]

    candidates = [[i for i in free if _same_values(want_cols[n], got(n, i), compare.tolerance)] for n in unmatched]
    found = [
        combo
        for combo in itertools.islice(itertools.product(*candidates), MAX_ASSIGNMENTS)
        if len(set(combo)) == len(combo)
    ]

    def closeness(combo: tuple[int, ...]) -> float:
        return sum(
            difflib.SequenceMatcher(None, n.lower(), _leaf(result.columns[i])).ratio()
            for n, i in zip(unmatched, combo, strict=True)
        )

    return sorted(found, key=closeness, reverse=True)


def _mapping_text(columns: dict[str, str], by_value: list[str]) -> str:
    if not by_value:
        return ""
    return "; matched by values: " + ", ".join(f"{n} → {columns[n]}" for n in by_value)


def match_tables(truth: Table, result: Table, compare: Compare) -> MatchResult:
    names = [*compare.keys, *compare.values] or list(truth.columns)
    missing = [n for n in names if n not in truth.columns]
    if missing:
        return MatchResult(ok=False, reason=f"truth has no column {missing[0]!r}")
    if compare.columns_exact and len(result.columns) != len(names):
        return MatchResult(ok=False, reason=f"result has {len(result.columns)} columns, expected exactly {len(names)}")
    if len(result.rows) != len(truth.rows):
        return MatchResult(ok=False, reason=f"result has {len(result.rows)} rows, truth has {len(truth.rows)}")
    if any(len(r) != len(result.columns) for r in result.rows):
        return MatchResult(ok=False, reason="a result row does not have one value per column")
    resolved: dict[str, int] = {}
    for name in names:
        idx, ambiguous = resolve_column(name, result.columns)
        if ambiguous is not None:
            return MatchResult(ok=False, reason=ambiguous)
        if idx is not None:
            resolved[name] = idx
    if len(set(resolved.values())) < len(resolved):
        return MatchResult(ok=False, reason="two truth columns resolve to the same result column")
    want_cols = {n: [normalize(r[truth.columns.index(n)]) for r in truth.rows] for n in names}
    zero = {n for n in compare.values if compare.null_as_zero}
    want_cols = {n: _zeroed(v) if n in zero else v for n, v in want_cols.items()}
    got_cols = {i: [normalize(r[i]) for r in result.rows] for i in range(len(result.columns))}
    unmatched = [n for n in names if n not in resolved]
    free = [i for i in range(len(result.columns)) if i not in resolved.values()]
    combos = _assignments(unmatched, free, want_cols, got_cols, result, compare) if unmatched else [()]
    if not combos:
        return MatchResult(ok=False, reason=f"no result column has the values of {', '.join(map(repr, unmatched))}")
    want = [[want_cols[n][k] for n in names] for k in range(len(truth.rows))]
    first_problem = ""
    for combo in combos:
        index = {**resolved, **dict(zip(unmatched, combo, strict=True))}
        cols = {n: _zeroed(got_cols[index[n]]) if n in zero else got_cols[index[n]] for n in names}
        got = [[cols[n][k] for n in names] for k in range(len(result.rows))]
        problem = _rows_match(want, got, compare)
        if problem is None:
            columns = {n: result.columns[index[n]] for n in names}
            ok = "rows match in order" if compare.ordered else "rows match"
            return MatchResult(ok=True, reason=ok + _mapping_text(columns, unmatched), columns=columns)
        first_problem = first_problem or problem
    return MatchResult(ok=False, reason=first_problem)
