"""Deterministic scoring of one trial: correctness, single-query answer, and informational trace flags."""

from slayer_evals.grading.flags import trace_flags
from slayer_evals.grading.tables import MatchResult, match_tables, normalize
from slayer_evals.grading.verdict import grade

__all__ = ["MatchResult", "grade", "match_tables", "normalize", "trace_flags"]
