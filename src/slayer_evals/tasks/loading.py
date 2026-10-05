"""Loading and validating task YAML files."""

from pathlib import Path

import yaml
from pydantic import ValidationError

from slayer_evals.core import Task

TRUTH_DIR = "truth"


class TaskFormatError(ValueError):
    pass


def load_task(path: Path) -> Task:
    try:
        doc = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        raise TaskFormatError(f"{path}: invalid YAML: {exc}") from exc
    if not isinstance(doc, dict):
        raise TaskFormatError(f"{path}: a task file must be a mapping")
    try:
        return Task.model_validate(doc)
    except ValidationError as exc:
        raise TaskFormatError(f"{path}: {exc}") from exc


def task_files(tasks_dir: Path) -> list[Path]:
    """Every task file under `tasks_dir`, skipping the truth snapshot directory."""
    files = [*tasks_dir.rglob("*.yaml"), *tasks_dir.rglob("*.yml")]
    return sorted(f for f in files if TRUTH_DIR not in f.relative_to(tasks_dir).parts[:-1])


def load_tasks(tasks_dir: Path) -> list[Task]:
    """All tasks under `tasks_dir`, sorted by id; fails on a malformed file or a duplicate id."""
    seen: dict[str, Path] = {}
    tasks: list[Task] = []
    for path in task_files(tasks_dir):
        task = load_task(path)
        if task.id in seen:
            raise TaskFormatError(f"{path}: duplicate task id {task.id!r} (also in {seen[task.id]})")
        seen[task.id] = path
        tasks.append(task)
    return sorted(tasks, key=lambda t: t.id)
