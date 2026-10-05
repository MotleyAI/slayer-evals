"""Tables, and SLayer `query` results parsed from markdown or either JSON shape."""

import json
import re
from typing import Any

from pydantic import BaseModel, Field

_NUM_RE = re.compile(r"^-?\d+(\.\d+)?([eE][-+]?\d+)?$")
_INT_RE = re.compile(r"^-?\d+$")
_SEPARATOR_RE = re.compile(r"^\|(\s*:?-+:?\s*\|)+$")
_WARNING_KINDS = (
    (re.compile(r"^showing first \d+ rows"), "truncated"),
    (re.compile(r"broadcast across"), "broadcast"),
    (re.compile(r"associated over"), "associated"),
    (re.compile(r"degenerate re-aggregation"), "degenerate_reaggregation"),
    (re.compile(r"by semi-join"), "semi_join_pushed"),
    (re.compile(r"statement timeout"), "statement_timeout_skipped"),
    (re.compile(r"^\[[^\]]+\] (rewrote|flagged) "), "normalization"),
    (re.compile(r"whole[_ ]periods"), "whole_periods_non_nesting"),
)


class Table(BaseModel):
    columns: list[str]
    rows: list[list[Any]]


class ResultWarning(BaseModel):
    kind: str
    message: str = ""


class ParsedResult(Table):
    warnings: list[ResultWarning] = Field(default_factory=list)

    @classmethod
    def from_text(cls, text: str) -> "ParsedResult | None":
        """A `query` tool result as a table, or None when the text is not one."""
        stripped = text.strip()
        if stripped.startswith(("{", "[")):
            return _from_json(stripped)
        if stripped.startswith("|"):
            return _from_markdown(stripped)
        return None


def _rows_from_records(records: list[Any]) -> tuple[list[str], list[list[Any]]] | None:
    if not all(isinstance(r, dict) for r in records):
        return None
    columns: list[str] = []
    for r in records:
        columns += [k for k in r if k not in columns]
    return columns, [[r.get(c) for c in columns] for r in records]


def _from_json(text: str) -> ParsedResult | None:
    try:
        payload = json.loads(text)
    except ValueError:
        return None
    warnings: list[ResultWarning] = []
    if isinstance(payload, dict):
        if not isinstance(payload.get("data"), list):
            return None
        for w in payload.get("warnings") or []:
            if isinstance(w, dict) and "kind" in w:
                warnings.append(ResultWarning(kind=str(w["kind"]), message=str(w.get("hint") or "")))
        payload = payload["data"]
    if not isinstance(payload, list):
        return None
    table = _rows_from_records(payload)
    if table is None:
        return None
    return ParsedResult(columns=table[0], rows=table[1], warnings=warnings)


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip()[1:-1].split("|")]


def _cell_value(cell: str) -> Any:
    if cell == "":
        return None
    if _INT_RE.match(cell):
        return int(cell)
    if _NUM_RE.match(cell):
        return float(cell)
    return cell


def _warning_kind(message: str) -> str:
    return next((kind for pattern, kind in _WARNING_KINDS if pattern.search(message)), "other")


def _from_markdown(text: str) -> ParsedResult | None:
    lines = text.splitlines()
    if len(lines) < 2 or not _SEPARATOR_RE.match(lines[1].replace(" ", "")):
        return None
    columns = _cells(lines[0])
    rows: list[list[Any]] = []
    i = 2
    while i < len(lines) and lines[i].strip().startswith("|"):
        rows.append([_cell_value(c) for c in _cells(lines[i])])
        i += 1
    warnings: list[ResultWarning] = []
    rest = lines[i:]
    if "Warnings:" in [x.strip() for x in rest]:
        start = [x.strip() for x in rest].index("Warnings:") + 1
        for line in rest[start:]:
            item = line.strip()
            if not item.startswith("- "):
                break
            message = item[2:]
            warnings.append(ResultWarning(kind=_warning_kind(message), message=message))
    return ParsedResult(columns=columns, rows=rows, warnings=warnings)
