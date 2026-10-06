"""What a run selects and how it runs."""

import sys
from pathlib import Path

from pydantic import BaseModel, Field

from slayer_evals.agents import DEFAULT_AGENT
from slayer_evals.core import PROFILES, AuthMode, Profile, RunMode, SafeName, Task

DEFAULT_MODEL = "claude-opus-5-5"


def default_slayer_command() -> list[str]:
    """The pinned SLayer release installed next to this interpreter."""
    return [str(Path(sys.executable).parent / "slayer")]


class RunConfig(BaseModel):
    tasks_dir: Path = Path("tasks")
    dataset_dir: Path | None = None
    out_dir: Path = Path("runs")
    agent: str = DEFAULT_AGENT
    auth_mode: AuthMode | None = None
    env_file: Path | None = None
    task_ids: list[str] = Field(default_factory=list)
    rows: list[str] = Field(default_factory=list)
    profiles: list[Profile] = Field(default_factory=lambda: list(PROFILES))
    models: list[SafeName] = Field(default_factory=lambda: [DEFAULT_MODEL])
    n: int = Field(default=1, ge=1)
    mode: RunMode = "repeat"
    concurrency: int = Field(default=3, ge=1)
    max_turns: int = 60
    timeout_s: float = 900.0
    slayer_command: list[str] | None = None


def select_tasks(tasks: list[Task], cfg: RunConfig) -> list[Task]:
    unknown = sorted(set(cfg.task_ids) - {t.id for t in tasks}) + sorted(set(cfg.rows) - {t.row for t in tasks})
    if unknown:
        raise ValueError(f"no tasks for selection: {', '.join(unknown)}")
    return [t for t in tasks if (not cfg.task_ids or t.id in cfg.task_ids) and (not cfg.rows or t.row in cfg.rows)]
