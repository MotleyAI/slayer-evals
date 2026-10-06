"""Exception class names in SLayer MCP tool errors."""

import re

_ERROR_RE = re.compile(r"Error executing tool [\w.-]+: ([A-Za-z_][\w.]*):")


def error_kind(text: str) -> str | None:
    """The exception class a `slayer mcp` tool error reports, e.g. `TimeDimensionColumnError`."""
    m = _ERROR_RE.search(text)
    return m.group(1).rsplit(".", 1)[-1] if m else None
