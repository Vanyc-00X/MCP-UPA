"""Runtime configuration from environment."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    """MCP-UPA settings."""

    upa_base_url: str = "http://127.0.0.1:8000"
    timeout_seconds: float = 120.0
    preview_rows: int = 20
    preview_elements: int = 40

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            upa_base_url=os.environ.get("UPA_BASE_URL", "http://127.0.0.1:8000").rstrip("/"),
            timeout_seconds=float(os.environ.get("UPA_TIMEOUT_SECONDS", "120")),
            preview_rows=int(os.environ.get("UPA_PREVIEW_ROWS", "20")),
            preview_elements=int(os.environ.get("UPA_PREVIEW_ELEMENTS", "40")),
        )
