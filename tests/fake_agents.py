"""Agents the runner can load by import path in its trial subprocesses; behaviour is read from the prompt.

Prompt directives (one per line): `ANSWER <x>`, `PASS_FROM_ATTEMPT <k>`, `END <reason>`, `SLEEP <s>`,
`WRITE_MARKER`, `CHECK_MARKER`, `WRITE_DB`. Every run is recorded under `$FAKE_AGENT_STATE` and writes a
one-line transcript.
"""

import asyncio
import fcntl
import hashlib
import json
import os
import time
from pathlib import Path
from typing import cast

import duckdb

from slayer_evals.core import AgentInput, AgentOutcome, EndReason, ParsedResult, Submission, ToolCall, Trace

STATE_ENV = "FAKE_AGENT_STATE"
MARKER = "leak_marker.yaml"
TRANSCRIPT_TAG = "fake-agent-transcript"


def _directives(prompt: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in prompt.splitlines():
        key, _, value = line.strip().partition(" ")
        if key.isupper():
            out[key] = value
    return out


def _state_dir() -> Path:
    path = Path(os.environ[STATE_ENV])
    path.mkdir(parents=True, exist_ok=True)
    return path


def _attempt(inp: AgentInput, model: str) -> int:
    key = hashlib.sha256(f"{inp.prompt}|{inp.profile}|{model}".encode()).hexdigest()[:16]
    counter = _state_dir() / f"attempts-{key}"
    with counter.open("a+") as f:  # concurrent trials of one task must not read the same count
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0)
        n = int(f.read() or "0") + 1
        f.seek(0)
        f.truncate()
        f.write(str(n))
    return n


def _answer(value: float) -> AgentOutcome:
    query = {"source_model": "orders", "measures": [{"formula": "sum(amount)", "name": "v"}]}
    call = ToolCall(
        tool="query",
        args={"query": query},
        result_text=json.dumps({"data": [{"orders.v": value}], "warnings": []}),
        parsed=ParsedResult(columns=["orders.v"], rows=[[value]]),
    )
    return AgentOutcome(
        submission=Submission(columns=["v"], rows=[[value]], message=""),
        trace=Trace(calls=[call], turns=2, end_reason="submitted"),
    )


class ScriptedAgent:
    def __init__(self, model: str):
        self.model = model

    async def run(self, inp: AgentInput) -> AgentOutcome:
        d = _directives(inp.prompt)
        record = {
            "pid": os.getpid(),
            "input": json.loads(inp.model_dump_json()),
            "model": self.model,
            "start": time.time(),
        }
        inp.env.transcript_path.write_text(json.dumps({"tag": TRANSCRIPT_TAG, "prompt": inp.prompt}) + "\n")
        attempt = _attempt(inp, self.model)
        if "SLEEP" in d:
            await asyncio.sleep(float(d["SLEEP"]))
        if "WRITE_MARKER" in d:
            (inp.env.store_dir / MARKER).write_text("name: leak\n")
        con = duckdb.connect(str(inp.env.db_path))
        try:
            row = con.execute("select count(*) from orders").fetchone()
            assert row is not None
            record["orders"] = row[0]
            if "WRITE_DB" in d:
                con.execute("delete from returns")
                con.execute("delete from orders where customer_id is not null")
        finally:
            con.close()
        saw_marker = (inp.env.store_dir / MARKER).exists()
        record["saw_marker"] = saw_marker
        record["end"] = time.time()
        tag = hashlib.sha256(f"{inp.prompt}|{inp.profile}|{self.model}|{attempt}".encode()).hexdigest()[:16]
        (_state_dir() / f"run-{tag}.json").write_text(json.dumps(record))
        if "END" in d:
            return AgentOutcome(submission=None, trace=Trace(calls=[], end_reason=cast(EndReason, d["END"])))
        value = float(d.get("ANSWER", "0"))
        if "CHECK_MARKER" in d:
            value = 1.0 if saw_marker else 0.0
        if attempt < int(d.get("PASS_FROM_ATTEMPT", "1")):
            value += 1.0
        return _answer(value)


def recorded_runs(state: Path) -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(state.glob("run-*.json"))]
