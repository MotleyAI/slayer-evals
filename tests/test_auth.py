"""Explicit auth mode and env-file credentials."""

from pathlib import Path

import pytest

from slayer_evals.runner import AuthError, resolve_auth

OAUTH = "sk-ant-oat01-abc"
KEY = "sk-ant-api03-xyz"


def test_mode_required():
    with pytest.raises(AuthError) as exc:
        resolve_auth(None, env_file=None, environ={"ANTHROPIC_API_KEY": KEY, "CLAUDE_CODE_OAUTH_TOKEN": OAUTH})
    msg = str(exc.value)
    assert "--subscription-auth" in msg and "--api-key-auth" in msg


def test_subscription_mode():
    creds = resolve_auth(
        "subscription", env_file=None, environ={"CLAUDE_CODE_OAUTH_TOKEN": OAUTH, "ANTHROPIC_API_KEY": KEY}
    )
    assert creds["CLAUDE_CODE_OAUTH_TOKEN"] == OAUTH
    assert creds["ANTHROPIC_API_KEY"] == "" and creds["ANTHROPIC_AUTH_TOKEN"] == ""


def test_api_key_mode():
    creds = resolve_auth("api-key", env_file=None, environ={"CLAUDE_CODE_OAUTH_TOKEN": OAUTH, "ANTHROPIC_API_KEY": KEY})
    assert creds["ANTHROPIC_API_KEY"] == KEY
    assert creds["CLAUDE_CODE_OAUTH_TOKEN"] == ""


def test_missing_oauth_token():
    with pytest.raises(AuthError) as exc:
        resolve_auth("subscription", env_file=None, environ={"ANTHROPIC_API_KEY": KEY})
    assert "CLAUDE_CODE_OAUTH_TOKEN" in str(exc.value)


def test_missing_api_key():
    with pytest.raises(AuthError) as exc:
        resolve_auth("api-key", env_file=None, environ={"CLAUDE_CODE_OAUTH_TOKEN": OAUTH})
    assert "ANTHROPIC_API_KEY" in str(exc.value)


def test_env_file(tmp_path: Path):
    f = tmp_path / ".env.agents"
    f.write_text(f"# comment\nexport CLAUDE_CODE_OAUTH_TOKEN={OAUTH}\nOTHER='x'\n\n")
    creds = resolve_auth("subscription", env_file=f, environ={})
    assert creds["CLAUDE_CODE_OAUTH_TOKEN"] == OAUTH


def test_env_file_quoted_value(tmp_path: Path):
    f = tmp_path / ".env"
    f.write_text(f'ANTHROPIC_API_KEY="{KEY}"\n')
    assert resolve_auth("api-key", env_file=f, environ={})["ANTHROPIC_API_KEY"] == KEY


def test_missing_env_file(tmp_path: Path):
    with pytest.raises(AuthError) as exc:
        resolve_auth("api-key", env_file=tmp_path / "nope.env", environ={"ANTHROPIC_API_KEY": KEY})
    assert "nope.env" in str(exc.value)
