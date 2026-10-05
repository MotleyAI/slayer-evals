"""Python tool sandbox: cwd, env allow-list, limits, timeout, audit log."""

import json
from pathlib import Path

import pytest

from slayer_evals.agents.sandbox import run_python


async def test_runs_in_sandbox_cwd(tmp_path: Path):
    sb = tmp_path / "sb"
    r = await run_python("import os; print(os.getcwd())", sandbox_dir=sb)
    assert r.ok
    assert not r.timed_out
    assert Path(r.stdout.strip()).resolve() == sb.resolve()


async def test_libraries_available(tmp_path: Path):
    r = await run_python("import pandas, numpy, duckdb; print('ok')", sandbox_dir=tmp_path / "sb")
    assert r.ok, r.stderr
    assert r.stdout.strip() == "ok", r.stderr


async def test_env_is_sanitized(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    for var in ("CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "SOME_SECRET"):
        monkeypatch.setenv(var, "secret")
    r = await run_python("import os, json; print(json.dumps(dict(os.environ)))", sandbox_dir=tmp_path / "sb")
    env = json.loads(r.stdout)
    for var in ("CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "SOME_SECRET"):
        assert var not in env
    assert "secret" not in env.values()


async def test_audit_records_outside_open(tmp_path: Path):
    outside = tmp_path / "outside.txt"
    outside.write_text("x")
    sb = tmp_path / "sb"
    r = await run_python(f"open({str(outside)!r}).read(); open('mine.txt', 'w').write('y')", sandbox_dir=sb)
    assert r.ok, r.stderr
    paths = [e.path for e in r.audit.events if e.event == "open" and e.path is not None]
    assert str(outside) in paths
    assert any(Path(p).name == "mine.txt" for p in paths)
    assert Path(r.audit.sandbox_dir).resolve() == sb.resolve()
    assert r.audit.allowed_prefixes


async def test_audit_records_subprocess(tmp_path: Path):
    r = await run_python("import subprocess; subprocess.run(['true'])", sandbox_dir=tmp_path / "sb")
    assert any(e.event == "subprocess.Popen" for e in r.audit.events)


async def test_timeout_returns_error_and_next_call_works(tmp_path: Path):
    sb = tmp_path / "sb"
    r = await run_python("while True: pass", sandbox_dir=sb, timeout_s=1.0)
    assert r.timed_out
    assert not r.ok
    again = await run_python("print(2)", sandbox_dir=sb)
    assert again.ok
    assert again.stdout.strip() == "2"


async def test_memory_limit(tmp_path: Path):
    r = await run_python("x = bytearray(64 * 1024 ** 3)", sandbox_dir=tmp_path / "sb", memory_bytes=1024**3)
    assert not r.ok


async def test_exception_is_reported(tmp_path: Path):
    r = await run_python("raise ValueError('nope')", sandbox_dir=tmp_path / "sb")
    assert not r.ok
    assert "nope" in r.stderr
