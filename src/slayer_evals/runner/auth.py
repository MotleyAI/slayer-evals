"""Explicit authentication mode and credentials from an optional env file."""

from collections.abc import Mapping
from pathlib import Path

from slayer_evals.core import AuthMode

OAUTH_VAR = "CLAUDE_CODE_OAUTH_TOKEN"
API_KEY_VAR = "ANTHROPIC_API_KEY"
AUTH_TOKEN_VAR = "ANTHROPIC_AUTH_TOKEN"
CREDENTIAL_VARS = (OAUTH_VAR, API_KEY_VAR, AUTH_TOKEN_VAR)


class AuthError(RuntimeError):
    pass


def read_env_file(path: Path) -> dict[str, str]:
    """`KEY=VALUE` lines (optional `export`, quotes and `#` comments)."""
    if not path.is_file():
        raise AuthError(f"env file not found: {path}")
    values: dict[str, str] = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.removeprefix("export ").partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        values[key.strip()] = value
    return values


def resolve_auth(mode: AuthMode | None, env_file: Path | None, environ: Mapping[str, str]) -> dict[str, str]:
    """The agent's credential variables for `mode`; the unused credentials are blanked."""
    if mode is None:
        raise AuthError("choose how to authenticate: --subscription-auth (CLAUDE_CODE_OAUTH_TOKEN) or --api-key-auth")
    values = {**environ, **(read_env_file(env_file) if env_file is not None else {})}
    var = OAUTH_VAR if mode == "subscription" else API_KEY_VAR
    secret = values.get(var, "").strip()
    if not secret:
        source = f" or {env_file}" if env_file is not None else ""
        raise AuthError(f"{mode} auth needs {var}, which is not set in the environment{source}")
    creds: dict[str, str] = dict.fromkeys(CREDENTIAL_VARS, "")
    creds[var] = secret
    return creds
