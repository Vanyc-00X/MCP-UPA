"""Error types and agent-friendly formatting."""

from __future__ import annotations

from typing import Any


class McpUpaError(Exception):
    """Base error for MCP-UPA."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "mcp_upa_error",
        details: dict[str, Any] | None = None,
        hint: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
        self.hint = hint

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "ok": False,
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            },
        }
        if self.hint:
            payload["error"]["hint"] = self.hint
        return payload


class UpaUnavailableError(McpUpaError):
    """UPA HTTP API is not reachable."""

    def __init__(self, base_url: str, reason: str) -> None:
        super().__init__(
            f"UPA is not reachable at {base_url}: {reason}",
            code="upa_unavailable",
            details={"base_url": base_url, "reason": reason},
            hint=(
                "Start UPA first (from UPA repo: .\\run.ps1 or python -m app serve), "
                "then retry. Check UPA_BASE_URL if the API is not on 127.0.0.1:8000."
            ),
        )


class UpaApiError(McpUpaError):
    """UPA returned an application error."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        code: str = "upa_api_error",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code=code,
            details={"status_code": status_code, **(details or {})},
        )


def format_tool_error(exc: Exception) -> dict[str, Any]:
    """Convert any exception into a structured tool response."""
    if isinstance(exc, McpUpaError):
        return exc.as_dict()
    return McpUpaError(str(exc), code="unexpected_error").as_dict()
