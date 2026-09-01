"""
The envelope, in one place both the host and every handler import BY NAME.

This module exists because of a bug worth keeping the fix for. The host runs as
`__main__`, so when a handler did `from server import ToolError` Python built a
SECOND server module — and `except ToolError` in the host no longer matched the
ToolError raised in the handler. Every typed failure came back as INTERNAL.

One module, imported the same way by everyone, and the identity holds.
"""


def ok(data, warnings=None):
    env = {"ok": True, "data": data}
    if warnings:
        env["warnings"] = warnings
    return env


def err(code, message, retryable=False, **detail):
    env = {"ok": False, "code": code, "message": message, "retryable": retryable}
    if detail:
        env["detail"] = detail
    return env


class ToolError(Exception):
    """Raised by a handler to return a typed failure rather than a stack trace."""

    def __init__(self, code, message, retryable=False, **detail):
        super().__init__(message)
        self.envelope = err(code, message, retryable, **detail)
