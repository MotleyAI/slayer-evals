"""Task files: loading, truth computation and snapshots, checks over the task set, and task proofs."""

from slayer_evals.tasks.loading import TRUTH_DIR, TaskFormatError, load_task, load_tasks
from slayer_evals.tasks.proofs import (
    ProofError,
    ReferenceResult,
    missing_markers,
    run_naive,
    run_references,
    saved_definitions,
)
from slayer_evals.tasks.suite import (
    MAX_TRUTH_ROWS,
    PROMPT_DENY_LIST,
    ROW_MARKERS,
    SUITE_DIRS,
    check_coverage,
    check_layout,
    check_prompts,
    check_truth_sizes,
)
from slayer_evals.tasks.truth import (
    SnapshotDriftError,
    TruthError,
    check_snapshots,
    compute_truth,
    compute_truths,
    load_snapshots,
    write_snapshots,
)

__all__ = [
    "MAX_TRUTH_ROWS",
    "PROMPT_DENY_LIST",
    "ROW_MARKERS",
    "SUITE_DIRS",
    "TRUTH_DIR",
    "ProofError",
    "ReferenceResult",
    "SnapshotDriftError",
    "TaskFormatError",
    "TruthError",
    "check_coverage",
    "check_layout",
    "check_prompts",
    "check_snapshots",
    "check_truth_sizes",
    "compute_truth",
    "compute_truths",
    "load_snapshots",
    "load_task",
    "load_tasks",
    "missing_markers",
    "run_naive",
    "run_references",
    "saved_definitions",
    "write_snapshots",
]
