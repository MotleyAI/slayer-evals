"""Import law between the eight nodes; only `agents` touches the agent SDK."""

import ast
from pathlib import Path

import pytest

from tests.helpers import REPO

SRC = REPO / "src" / "slayer_evals"
NODES = ("core", "dataset", "tasks", "grading", "agents", "runner", "report", "cli")
ALLOWED = {
    "core": set(),
    "dataset": {"core"},
    "tasks": {"core"},
    "grading": {"core"},
    "agents": {"core"},
    "runner": {"core", "dataset", "tasks", "agents", "grading", "report"},
    "report": {"core"},
    "cli": {"runner", "report", "dataset", "tasks"},
}


def node_files(node: str) -> list[Path]:
    pkg = SRC / node
    return sorted(pkg.rglob("*.py")) if pkg.is_dir() else [SRC / f"{node}.py"]


def imported_modules(path: Path) -> set[str]:
    out: set[str] = set()
    for n in ast.walk(ast.parse(path.read_text())):
        if isinstance(n, ast.Import):
            out |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
            out.add(n.module)
        elif isinstance(n, ast.ImportFrom) and n.level:
            raise AssertionError(f"{path}: use absolute imports")
    return out


@pytest.mark.parametrize("node", NODES)
def test_node_exists(node: str):
    files = node_files(node)
    assert files, node
    assert all(f.exists() for f in files), node


@pytest.mark.parametrize("node", NODES)
def test_import_law(node: str):
    for f in node_files(node):
        for mod in imported_modules(f):
            parts = mod.split(".")
            if parts[0] != "slayer_evals" or len(parts) < 2:
                continue
            target = parts[1]
            assert target == node or target in ALLOWED[node], f"{f.relative_to(REPO)} imports {mod}"


@pytest.mark.parametrize("node", [n for n in NODES if n != "agents"])
def test_only_agents_import_the_sdk(node: str):
    for f in node_files(node):
        for mod in imported_modules(f):
            assert mod.split(".")[0] != "claude_agent_sdk", f"{f.relative_to(REPO)} imports {mod}"
