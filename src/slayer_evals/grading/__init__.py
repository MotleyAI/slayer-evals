"""Deterministic scoring of one trial: correctness, capability use and absence of hacks."""

from slayer_evals.grading.errors import error_kind
from slayer_evals.grading.hacks import hack_reasons, is_row_scalar, sql_uses
from slayer_evals.grading.tables import MatchResult, match_tables, normalize
from slayer_evals.grading.verdict import grade

__all__ = [
    "MatchResult",
    "error_kind",
    "grade",
    "hack_reasons",
    "is_row_scalar",
    "match_tables",
    "normalize",
    "sql_uses",
]
