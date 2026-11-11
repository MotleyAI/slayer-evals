"""Exception class names in MCP tool errors."""

import re

_PREFIXED_RE = re.compile(r"Error executing tool [\w.-]+: ([A-Za-z_][\w.]*):")
_BARE_RE = re.compile(r"([A-Za-z_][\w.]*(?:Error|Exception)): ")


def error_kind(text: str) -> str | None:
    """The exception class a tool error reports: `Error executing tool X: <Class>: …` or a bare `<Class>: …`."""
    m = _PREFIXED_RE.search(text) or _BARE_RE.match(text)
    return m.group(1).rsplit(".", 1)[-1] if m else None
