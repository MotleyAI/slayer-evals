"""Running tasks against agents in isolated trials and recording verdicts, traces and transcripts."""

from slayer_evals.runner.auth import AuthError, read_env_file, resolve_auth
from slayer_evals.runner.config import DEFAULT_MODEL, RunConfig, select_tasks
from slayer_evals.runner.run import run_benchmark, slayer_version

__all__ = [
    "DEFAULT_MODEL",
    "AuthError",
    "RunConfig",
    "read_env_file",
    "resolve_auth",
    "run_benchmark",
    "select_tasks",
    "slayer_version",
]
