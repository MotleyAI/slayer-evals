"""Trial subprocess entry point: load the agent, run it on one input, write its outcome as JSON."""

import asyncio
import sys
from pathlib import Path

from pydantic import BaseModel

from slayer_evals.agents import load_agent
from slayer_evals.core import AgentInput, AgentOutcome, Trace


class TrialSpec(BaseModel):
    agent: str
    model: str
    input: AgentInput


def run_trial(spec: TrialSpec) -> AgentOutcome:
    try:
        return asyncio.run(load_agent(spec.agent, spec.model).run(spec.input))
    except Exception as exc:  # noqa: BLE001 - report the failure as a trial outcome rather than a crashed process
        return AgentOutcome(submission=None, trace=Trace(end_reason="error", error=f"{type(exc).__name__}: {exc}"))


def main(argv: list[str]) -> int:
    spec_path, outcome_path = Path(argv[1]), Path(argv[2])
    outcome = run_trial(TrialSpec.model_validate_json(spec_path.read_text()))
    outcome_path.write_text(outcome.model_dump_json())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
