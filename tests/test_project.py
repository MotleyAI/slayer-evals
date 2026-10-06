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


def _exact(pin: str | dict[str, str]) -> bool:
    """A release version, or a git dependency on one full commit."""
    if isinstance(pin, dict):
        return set(pin) == {"git", "rev"} and re.fullmatch(r"[0-9a-f]{40}", pin["rev"]) is not None
    return re.fullmatch(r"\d+\.\d+\.\d+", pin) is not None


def test_exact_pins():
    deps = tomllib.loads((REPO / "pyproject.toml").read_text())["tool"]["poetry"]["dependencies"]
    assert _exact(deps["motley-slayer"])
    assert _exact(deps["claude-agent-sdk"])
    assert not _exact({"git": "https://example.com/x.git", "rev": "main"})
    assert not _exact(">=1.0")
