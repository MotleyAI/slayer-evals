"""Live check: the real Claude CLI sends the trial's identity header to an HTTP Motley server."""

import json
import os
from pathlib import Path

import pytest
from claude_agent_sdk import ClaudeSDKClient

from slayer_evals.agents.claude import CLAUDE_JSON, AnswerCollector, ClaudeAgent, settled_status
from slayer_evals.runner import resolve_auth
from tests.fake_motley import fake_motley
from tests.fake_sdk import MODEL, MOTLEY_USER_ID, make_input

pytestmark = pytest.mark.integration

ENV_FILE = Path(os.environ.get("SLAYER_EVALS_ENV_FILE", "/home/james/GitHub/SLayer/.env.agents"))


async def test_identity_header_reaches_motley(tmp_path: Path):
    with fake_motley(tmp_path) as server:
        inp = make_input(tmp_path, profile="motley", motley_url=server.url)
        inp.env.credentials = resolve_auth("subscription", ENV_FILE, os.environ)
        config_dir = tmp_path / "cfg"
        config_dir.mkdir()
        (config_dir / ".claude.json").write_text(json.dumps(CLAUDE_JSON))
        opts = ClaudeAgent(model=MODEL).build_options(inp, config_dir=config_dir, collector=AnswerCollector())
        client = ClaudeSDKClient(options=opts)
        await client.connect()
        try:
            status = await settled_status(client, "motley")
        finally:
            await client.disconnect()
        by_method = server.user_ids_by_method()
    statuses = {s["name"]: s["status"] for s in status["mcpServers"]}
    assert statuses.get("motley") == "connected", statuses
    assert by_method["initialize"] == {MOTLEY_USER_ID}
    assert by_method["tools/list"] == {MOTLEY_USER_ID}
