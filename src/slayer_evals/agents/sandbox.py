"""The `slayer+python` profile's Python tool: a fresh subprocess with limits, a clean env and an audit log."""

import asyncio
import contextlib
import json
import os
import resource
import signal
import site
import sys
import sysconfig
import tempfile
from pathlib import Path

from pydantic import BaseModel

from slayer_evals.core import AuditEvent, PythonAudit

DEFAULT_TIMEOUT_S = 60.0
DEFAULT_MEMORY_BYTES = 4 * 1024**3
MAX_OUTPUT_CHARS = 50_000
ENV_ALLOW = ("PATH", "LANG", "LC_ALL", "LC_CTYPE", "TZ")
THREAD_ENV = {"OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}

# Runs in the child: logs opens outside the interpreter's own files and subprocess launches, then runs stdin.
BOOTSTRAP = r"""
import json, os, sys
def _main():
    log = open(sys.argv[1], "w", buffering=1)
    allowed = tuple(json.loads(sys.argv[2]))
    def hook(event, args):
        if event == "open" and isinstance(args[0], (str, bytes)):
            path = os.path.normpath(os.path.join(os.getcwd(), os.fsdecode(args[0])))
            if not any(path == p or path.startswith(p.rstrip(os.sep) + os.sep) for p in allowed):
                log.write(json.dumps({"event": "open", "path": path}) + "\n")
        elif event == "subprocess.Popen":
            log.write(json.dumps({"event": event, "path": os.fsdecode(args[0])}) + "\n")
    code = sys.stdin.read()
    sys.stdin = open(os.devnull)
    sys.addaudithook(hook)
    exec(compile(code, "<python>", "exec"), {"__name__": "__main__"})
_main()
"""


class PythonRun(BaseModel):
    ok: bool
    timed_out: bool = False
    stdout: str = ""
    stderr: str = ""
    audit: PythonAudit


def allowed_prefixes() -> list[str]:
    """The interpreter's own installation: stdlib, site-packages and prefixes."""
    paths = {sys.prefix, sys.base_prefix, sys.exec_prefix, sys.base_exec_prefix, *sysconfig.get_paths().values()}
    paths |= set(site.getsitepackages())
    paths |= {os.path.realpath(p) for p in paths}
    return sorted(p for p in paths if p)


def _limits(memory_bytes: int, cpu_s: int) -> None:
    resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_s, cpu_s))


def _clip(data: bytes) -> str:
    text = data.decode(errors="replace")
    return text if len(text) <= MAX_OUTPUT_CHARS else text[:MAX_OUTPUT_CHARS] + "\n[output truncated]"


def _read_audit(path: Path) -> list[AuditEvent]:
    events = []
    for line in path.read_text().splitlines():
        with contextlib.suppress(ValueError):
            events.append(AuditEvent.model_validate(json.loads(line)))
    return events


async def run_python(
    code: str,
    sandbox_dir: Path,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    memory_bytes: int = DEFAULT_MEMORY_BYTES,
) -> PythonRun:
    sandbox_dir.mkdir(parents=True, exist_ok=True)
    prefixes = allowed_prefixes()
    fd, audit_name = tempfile.mkstemp(prefix="slayer-evals-audit-", suffix=".jsonl")
    os.close(fd)
    audit_path = Path(audit_name)
    env = {k: os.environ[k] for k in ENV_ALLOW if k in os.environ}
    env |= {**THREAD_ENV, "HOME": str(sandbox_dir), "TMPDIR": str(sandbox_dir)}
    cpu_s = int(timeout_s) + 5
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-I",
        "-c",
        BOOTSTRAP,
        str(audit_path),
        json.dumps(prefixes),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=sandbox_dir,
        env=env,
        start_new_session=True,
        preexec_fn=lambda: _limits(memory_bytes, cpu_s),
    )
    timed_out = False
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(code.encode()), timeout=timeout_s)
    except TimeoutError:
        timed_out = True
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGKILL)
        stdout, stderr = await proc.communicate()
    try:
        events = _read_audit(audit_path)
    finally:
        audit_path.unlink(missing_ok=True)
    err = _clip(stderr)
    if timed_out:
        err += f"\nTimed out after {timeout_s:g}s."
    return PythonRun(
        ok=proc.returncode == 0 and not timed_out,
        timed_out=timed_out,
        stdout=_clip(stdout),
        stderr=err,
        audit=PythonAudit(sandbox_dir=str(sandbox_dir.resolve()), allowed_prefixes=prefixes, events=events),
    )
