"""A stand-in Motley MCP server over streamable HTTP that records each request's method and identity header.

Run as `python -m tests.fake_motley <port> <record.jsonl> <mode>`; mode `ok` serves MCP, `421` answers every request
with 421 Misdirected Request, `hang` never answers, and `garbage` answers with a body that is not JSON-RPC.
"""

import asyncio
import contextlib
import json
import socket
import subprocess
import sys
import time
from collections.abc import Generator
from pathlib import Path
from typing import Any

import uvicorn
from mcp.server.fastmcp import FastMCP

USER_ID_HEADER = "X-Storyline-Dev-User-Id"
SERVER_NAME = "motley"
SERVER_VERSION = "9.9.9-motley"
MCP_PATH = "/api/v1/mcp/"
REPO = Path(__file__).resolve().parent.parent


class FakeMotley:
    """A running fake server: its URL and the requests it recorded."""

    def __init__(self, url: str, record: Path):
        self.url, self.record = url, record

    def requests(self) -> list[dict[str, Any]]:
        if not self.record.exists():
            return []
        return [json.loads(x) for x in self.record.read_text().splitlines() if x.strip()]

    def user_ids_by_method(self) -> dict[str, set[str | None]]:
        out: dict[str, set[str | None]] = {}
        for r in self.requests():
            if r["method"]:
                out.setdefault(r["method"], set()).add(r["user_id"])
        return out


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _listening(port: int) -> bool:
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


@contextlib.contextmanager
def fake_motley(tmp: Path, mode: str = "ok") -> Generator[FakeMotley]:
    """Start the fake server in a subprocess on a free local port."""
    port = free_port()
    record = tmp / f"motley-requests-{port}.jsonl"
    proc = subprocess.Popen(
        [sys.executable, "-m", "tests.fake_motley", str(port), str(record), mode], cwd=REPO, stderr=subprocess.DEVNULL
    )
    try:
        deadline = time.monotonic() + 30
        while not _listening(port):
            assert proc.poll() is None, "fake Motley server exited"
            assert time.monotonic() < deadline, "fake Motley server did not start"
            time.sleep(0.1)
        yield FakeMotley(f"http://127.0.0.1:{port}{MCP_PATH}", record)
    finally:
        proc.kill()
        proc.wait()


def _app(record: Path, mode: str) -> Any:
    server = FastMCP(SERVER_NAME, streamable_http_path=MCP_PATH)
    server._mcp_server.version = SERVER_VERSION

    @server.tool()
    def inspect(reference: str) -> str:
        """Describe a model."""
        return reference

    inner = server.streamable_http_app()

    async def app(scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await inner(scope, receive, send)
            return
        messages, more = [], True
        while more:
            msg = await receive()
            messages.append(msg)
            more = msg.get("more_body", False)
        body = b"".join(m.get("body", b"") for m in messages)
        headers = {k.decode().lower(): v.decode() for k, v in scope["headers"]}
        try:
            method = json.loads(body).get("method")
        except (ValueError, AttributeError):
            method = None
        with record.open("a") as f:
            f.write(json.dumps({"method": method, "user_id": headers.get(USER_ID_HEADER.lower())}) + "\n")
        if mode == "hang":
            await asyncio.sleep(3600)
        if mode == "421":
            await send({"type": "http.response.start", "status": 421, "headers": [(b"content-type", b"text/plain")]})
            await send({"type": "http.response.body", "body": b"Misdirected Request"})
            return
        if mode == "garbage":
            await send(
                {"type": "http.response.start", "status": 200, "headers": [(b"content-type", b"application/json")]}
            )
            await send({"type": "http.response.body", "body": b'{"not": "json-rpc"}'})
            return
        replay = iter(messages)

        async def again() -> Any:
            return next(replay, None) or await receive()

        await inner(scope, again, send)

    return app


if __name__ == "__main__":
    port, record, mode = int(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    uvicorn.run(_app(record, mode), host="127.0.0.1", port=port, log_level="warning")
