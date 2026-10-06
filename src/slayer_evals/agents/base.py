"""The adapter contract any benchmarked agent implements, and loading one by import path."""

import importlib
from typing import Protocol

from slayer_evals.core import AgentInput, AgentOutcome

DEFAULT_AGENT = "slayer_evals.agents.claude:ClaudeAgent"


class Agent(Protocol):
    """Constructed with a model id; runs one trial from the prompt, profile and trial environment only."""

    async def run(self, inp: AgentInput) -> AgentOutcome: ...


def load_agent(spec: str, model: str) -> Agent:
    """Instantiate `module:Class` with `model=`."""
    module, _, name = spec.partition(":")
    if not module or not name:
        raise ValueError(f"agent must be given as module:Class, got {spec!r}")
    return getattr(importlib.import_module(module), name)(model=model)
