"""Capability predicates evaluated on one tool call of a trace."""

import re
from typing import Any

from slayer.engine.syntax import AggCall, BoolOp, Cmp, DottedRef, Literal, ScalarCall, TransformCall, UnaryOp

from slayer_evals.core import (
    AnyOfPredicate,
    CallPredicate,
    FilterPredicate,
    InlineExtensionPredicate,
    MultiStagePredicate,
    NoSourceModelPredicate,
    OrderUnselectedPredicate,
    Predicate,
    SavedQueryPredicate,
    SourceModelPredicate,
    StoreManifest,
    TimeDimensionPredicate,
    TimeFilterPredicate,
    ToolCall,
    TracePatternPredicate,
    TraceStep,
)
from slayer_evals.grading.queries import (
    Expr,
    QueryView,
    as_stages,
    clause_texts,
    decode,
    extension_measures,
    parse,
    query_view,
    source_name,
    walk,
)

_RELATIVE_RE = re.compile(
    r"^\s*((last|this|next|previous|prior|past|current)\b.*|today|yesterday|tomorrow|.*\bago|.*\bto date)\s*$|"
    r"^\s*(ytd|qtd|mtd|wtd)\s*$",
    re.IGNORECASE,
)
_TYPED_RE = re.compile(r"^\s*\d{4}(-(Q[1-4]|H[12]|W\d{1,2}|\d{2}(-\d{2})?))?\s*$", re.IGNORECASE)
_GRAIN_CALL_RE = re.compile(r"^\s*(\w+)\s*\(")
_POINT_OPS = ("==", "in", "!=", "not in")
SAVING_TOOLS = ("create_model", "edit_model")


class CallContext:
    """One candidate call, the trace before it, and the saved measures visible to it."""

    def __init__(self, calls: list[ToolCall], index: int, manifest: StoreManifest):
        self.calls = calls
        self.index = index
        self.call = calls[index]
        self.view = query_view(self.call.args) if self.call.tool == "query" else QueryView()
        measures = {m.name: m.formula for m in manifest.measures}
        for prior in calls[:index]:
            if prior.tool in SAVING_TOOLS and not prior.is_error:
                for m in prior.args.get("measures") or []:
                    if isinstance(m, dict) and isinstance(m.get("name"), str) and isinstance(m.get("formula"), str):
                        measures[m["name"]] = m["formula"]
        self.stages = list(self.view.stages)
        if self.view.run_name is not None:
            saved = next((q for q in manifest.queries if q.name == self.view.run_name), None)
            self.stages = as_stages(saved.query) if saved else []
        for stage in self.stages:
            measures.update(extension_measures(stage))
        self.fragments = self.stages + ([self.view.refine] if self.view.refine else [])
        self.exprs: list[Expr] = [parse(c, t, measures) for f in self.fragments for c, t in clause_texts(f)]


def _call_name(node: Any) -> str | None:
    if isinstance(node, AggCall):
        return node.agg
    if isinstance(node, TransformCall):
        return node.op
    if isinstance(node, ScalarCall):
        return node.name
    return None


def _arg_nodes(node: Any) -> list[Any]:
    if isinstance(node, AggCall):
        return [node.source, *node.args]
    if isinstance(node, TransformCall):
        return [node.input, *node.args]
    if isinstance(node, ScalarCall):
        return list(node.args)
    return []


def _call_matches(pred: CallPredicate, node: Any) -> bool:
    name = _call_name(node)
    if name is None or name.lower() not in {f.lower() for f in pred.fns}:
        return False
    if pred.kwarg and pred.kwarg not in dict(getattr(node, "kwargs", ())):
        return False
    if pred.dotted_arg and not any(isinstance(n, DottedRef) for a in _arg_nodes(node) for n in walk(a)):
        return False
    if pred.within is not None:
        inner = pred.within
        return any(_call_matches(inner, n) for n in list(walk(node))[1:])
    return True


def _call(pred: CallPredicate, ctx: CallContext) -> bool:
    return any(
        _call_matches(pred, n)
        for e in ctx.exprs
        if e.node is not None and (pred.clause is None or e.clause == pred.clause)
        for n in walk(e.node)
    )


def _multi_stage(ctx: CallContext) -> bool:
    stages = ctx.view.stages
    named = [s.get("name") for s in stages]
    return any(
        source_name(stages[j]) in {n for n in named[:j] if isinstance(n, str) and n} for j in range(1, len(stages))
    )


def _selected(stage: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for key in ("measures", "dimensions", "time_dimensions"):
        items = stage.get(key) or []
        for item in items if isinstance(items, list) else [items]:
            if isinstance(item, str):
                out.add(item)
            elif isinstance(item, dict):
                for field in ("name", "formula", "expression", "label", "dimension"):
                    value = item.get(field)
                    if isinstance(value, dict):
                        value = value.get("name")
                    if isinstance(value, str):
                        out.add(value)
    return out | {s.rsplit(".", 1)[-1] for s in out if "(" not in s}


def _order_unselected(ctx: CallContext) -> bool:
    for fragment in ctx.fragments:
        selected = _selected(fragment)
        for clause, text in clause_texts({"order": fragment.get("order")}):
            short = text.rsplit(".", 1)[-1] if "(" not in text else text
            if clause == "order" and text not in selected and short not in selected:
                return True
    return False


def _inline_extension(ctx: CallContext) -> bool:
    for stage in ctx.view.stages:
        source = decode(stage.get("source_model"))
        if isinstance(source, dict) and any(source.get(k) for k in ("columns", "measures", "joins")):
            return True
    return False


def _time_point_form(text: str) -> str | None:
    if _RELATIVE_RE.match(text):
        return "relative"
    if _TYPED_RE.match(text):
        return "typed"
    return None


def _time_filter(pred: TimeFilterPredicate, ctx: CallContext) -> bool:
    for e in ctx.exprs:
        if e.clause != "filters" or e.node is None:
            continue
        for n in walk(e.node):
            if isinstance(n, Cmp) and n.op in _POINT_OPS:
                for side in (n.left, n.right):
                    if (
                        isinstance(side, Literal)
                        and isinstance(side.value, str)
                        and _time_point_form(side.value) == pred.form
                    ):
                        return True
    for fragment in ctx.fragments:
        for td in fragment.get("time_dimensions") or []:
            if not isinstance(td, dict):
                continue
            bounds = td.get("date_range")
            for bound in bounds if isinstance(bounds, list) else [bounds]:
                if not isinstance(bound, str):
                    continue
                form = _time_point_form(bound)
                if form == pred.form or (pred.form == "typed" and form is None and bound[:4].isdigit()):
                    return True
    return False


def _filter(pred: FilterPredicate, ctx: CallContext) -> bool:
    for e in ctx.exprs:
        if e.clause != "filters" or e.node is None:
            continue
        roots = [e.node] if pred.bool_op is None else [n for n in walk(e.node) if _is_bool_op(n, pred.bool_op)]
        for root in roots:
            if not pred.dotted_ref or any(isinstance(n, DottedRef) for n in walk(root)):
                return True
    return False


def _is_bool_op(node: Any, op: str) -> bool:
    if op == "not":
        return isinstance(node, UnaryOp) and node.op == "not"
    return isinstance(node, BoolOp) and node.op == op


def _source_names(ctx: CallContext) -> set[str]:
    names = {source_name(s) for s in ctx.view.stages}
    if ctx.view.run_name:
        names.add(ctx.view.run_name)
    return {n for n in names if n}


def _time_dimension(pred: TimeDimensionPredicate, ctx: CallContext) -> bool:
    for fragment in ctx.fragments:
        items = fragment.get("time_dimensions") or []
        for td in items if isinstance(items, list) else [items]:
            grain = td.get("granularity") if isinstance(td, dict) else None
            if isinstance(td, str) and (m := _GRAIN_CALL_RE.match(td)):
                grain = m.group(1)
            if isinstance(grain, str) and (pred.granularity is None or grain.lower() == pred.granularity.lower()):
                return True
    return False


def _step_matches(step: TraceStep, call: ToolCall, matched: list[int], calls: list[ToolCall]) -> bool:
    if call.tool != step.tool or call.is_error:
        return False
    if any(call.args.get(a) in (None, "", [], {}) for a in step.has_args):
        return False
    if step.uses_model_from_step is not None:
        if step.uses_model_from_step >= len(matched):
            return False
        model = calls[matched[step.uses_model_from_step]].args.get("name")
        view = query_view(call.args)
        used = {source_name(s) for s in view.stages} | {view.run_name}
        if not isinstance(model, str) or model not in used:
            return False
    return True


def _trace_pattern(pred: TracePatternPredicate, ctx: CallContext) -> bool:
    steps, calls, end = pred.steps, ctx.calls, ctx.index

    def search(k: int, start: int, matched: list[int]) -> bool:
        if k == len(steps) - 1:
            return _step_matches(steps[k], calls[end], matched, calls)
        return any(
            _step_matches(steps[k], calls[i], matched, calls) and search(k + 1, i + 1, [*matched, i])
            for i in range(start, end)
        )

    return search(0, 0, [])


def satisfies(pred: Predicate, ctx: CallContext) -> bool:
    match pred:
        case CallPredicate():
            return _call(pred, ctx)
        case MultiStagePredicate():
            return _multi_stage(ctx)
        case SavedQueryPredicate():
            return ctx.view.run_name == pred.name and (not pred.refine or ctx.view.refine is not None)
        case OrderUnselectedPredicate():
            return _order_unselected(ctx)
        case InlineExtensionPredicate():
            return _inline_extension(ctx)
        case TimeFilterPredicate():
            return _time_filter(pred, ctx)
        case NoSourceModelPredicate():
            return any(not s.get("source_model") for s in ctx.view.stages)
        case FilterPredicate():
            return _filter(pred, ctx)
        case SourceModelPredicate():
            return pred.name in _source_names(ctx)
        case TimeDimensionPredicate():
            return _time_dimension(pred, ctx)
        case TracePatternPredicate():
            return _trace_pattern(pred, ctx)
        case AnyOfPredicate():
            return any(all(satisfies(p, ctx) for p in option) for option in pred.options)
    return False
