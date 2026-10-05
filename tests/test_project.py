"""Project scaffold: CI workflow and ignore rules."""

import re
import tomllib

import yaml

from tests.helpers import REPO


def test_ci_workflow_runs_gates():
    workflows = sorted((REPO / ".github" / "workflows").glob("*.yml"))
    assert workflows
    text = "\n".join(w.read_text() for w in workflows)
    for w in workflows:
        assert isinstance(yaml.safe_load(w.read_text()), dict)
    for cmd in ("ruff", "basedpyright", "pytest"):
        assert cmd in text
    assert "not integration" in text


def test_gitignore():
    lines = (REPO / ".gitignore").read_text().splitlines()
    for pattern in (".env*", "runs/"):
        assert pattern in lines


def test_exact_pins():
    deps = tomllib.loads((REPO / "pyproject.toml").read_text())["tool"]["poetry"]["dependencies"]
    assert deps["motley-slayer"] == "1.0.2"
    assert re.fullmatch(r"\d+\.\d+\.\d+", deps["claude-agent-sdk"])
