"""SLayer query arguments as stages and parsed expressions, with saved measures expanded."""

import json
from collections.abc import Iterator
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from slayer.engine.syntax import DottedRef, Ref, parse_expr, parse_filter_expr

MAX_EXPANSION_DEPTH = 5


class Expr(BaseModel):
    """One expression of a query, tagged with the clause it came from."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    clause: str
    text: str
    node: Any = None
    error: str | None = None


class QueryView(BaseModel):
    """A `query` call's query: inline stages, or a run of a saved query by name with an optional refinement."""

    stages: list[dict[str, Any]] = Field(default_factory=list)
    run_name: str | None = None
    refine: dict[str, Any] | None = None


def decode(value: Any) -> Any:
    """JSON text an agent passed instead of an object, decoded; anything else unchanged."""
    if isinstance(value, str) and value.strip().startswith(("{", "[")):
        try:
            return json.loads(value)
        except ValueError:
            return value
    return value


def as_stages(value: Any) -> list[dict[str, Any]]:
    value = decode(value)
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        return [s for s in value if isinstance(s, dict)]
    return []


def query_view(args: dict[str, Any]) -> QueryView:
    query = decode(args.get("query"))
    refine = decode(args.get("refine"))
    refine = refine if isinstance(refine, dict) and refine else None
    if isinstance(query, str):
        return QueryView(run_name=query.strip(), refine=refine)
    return QueryView(stages=as_stages(query), refine=refine)


def source_name(stage: dict[str, Any]) -> str | None:
    source = decode(stage.get("source_model"))
    if isinstance(source, str):
        return source
    if isinstance(source, dict):
        name = source.get("source_name") or source.get("name")
        return name if isinstance(name, str) else None
    return None


def _items(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _name_of(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        name = value.get("name") or value.get("dimension") or value.get("column")
        return _name_of(name)
    return None


def clause_texts(stage: dict[str, Any]) -> list[tuple[str, str]]:
    """(clause, text) for every measure, dimension, time dimension, filter and order expression of a stage."""
    out: list[tuple[str, str]] = []
    for m in _items(stage.get("measures")):
        text = m.get("formula") if isinstance(m, dict) else m
        if isinstance(text, str):
            out.append(("measures", text))
    for d in _items(stage.get("dimensions")):
        text = (d.get("expression") or _name_of(d)) if isinstance(d, dict) else d
        if isinstance(text, str):
            out.append(("dimensions", text))
    for t in _items(stage.get("time_dimensions")):
        text = _name_of(t.get("dimension") or t.get("column")) if isinstance(t, dict) else t
        if isinstance(text, str):
            out.append(("time_dimensions", text))
    for f in _items(stage.get("filters")):
        if isinstance(f, str):
            out.append(("filters", f))
    for o in _items(stage.get("order")):
        text = _name_of(o.get("column")) if isinstance(o, dict) else o
        if isinstance(text, str):
            out.append(("order", text))
    return out


def walk(node: Any) -> Iterator[Any]:
    """`node` and every parsed node below it, kwargs included."""
    if isinstance(node, BaseModel):
        yield node
        for field in type(node).model_fields:
            yield from walk(getattr(node, field))
    elif isinstance(node, tuple):
        for item in node:
            yield from walk(item)


def expand(node: Any, measures: dict[str, str], depth: int = 0) -> Any:
    """Replace references to saved measures by their parsed formulas."""
    if isinstance(node, (Ref, DottedRef)):
        name = node.name if isinstance(node, Ref) else node.parts[-1]
        formula = measures.get(name)
        if formula is None or depth >= MAX_EXPANSION_DEPTH:
            return node
        try:
            return expand(parse_expr(formula), measures, depth + 1)
        except Exception:  # noqa: BLE001 - an unparseable saved formula stays a plain reference
            return node
    if isinstance(node, BaseModel):
        update = {}
        for field in type(node).model_fields:
            old = getattr(node, field)
            new = expand(old, measures, depth)
            if new is not old:
                update[field] = new
        return node.model_copy(update=update) if update else node
    if isinstance(node, tuple):
        mapped = tuple(expand(x, measures, depth) for x in node)
        return node if all(a is b for a, b in zip(mapped, node, strict=True)) else mapped
    return node


def parse(clause: str, text: str, measures: dict[str, str]) -> Expr:
    try:
        node = parse_filter_expr(text) if clause == "filters" else parse_expr(text)
    except Exception as exc:  # noqa: BLE001 - agent text is arbitrary; grading must not crash on it
        return Expr(clause=clause, text=text, error=str(exc))
    return Expr(clause=clause, text=text, node=expand(node, measures))


def extension_measures(stage: dict[str, Any]) -> dict[str, str]:
    source = decode(stage.get("source_model"))
    if not isinstance(source, dict):
        return {}
    return {
        m["name"]: m["formula"]
        for m in _items(source.get("measures"))
        if isinstance(m, dict) and isinstance(m.get("name"), str) and isinstance(m.get("formula"), str)
    }
