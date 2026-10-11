"""Unit tests for UpaClient error mapping (no live UPA required)."""

from __future__ import annotations

import httpx
import pytest
import respx

from mcp_upa.client import UpaClient
from mcp_upa.config import Settings
from mcp_upa.errors import UpaApiError, UpaUnavailableError


@pytest.mark.asyncio
@respx.mock
async def test_health_ok() -> None:
    route = respx.get("http://127.0.0.1:8000/health").mock(
        return_value=httpx.Response(200, json={"status": "ok", "app": "UPA"})
    )
    async with UpaClient(Settings(upa_base_url="http://127.0.0.1:8000")) as client:
        data = await client.health()
    assert route.called
    assert data["status"] == "ok"


@pytest.mark.asyncio
@respx.mock
async def test_api_error_payload() -> None:
    respx.get("http://127.0.0.1:8000/api/v1/snapshots/missing").mock(
        return_value=httpx.Response(
            404,
            json={"error": {"code": "not_found", "message": "Snapshot not found"}},
        )
    )
    async with UpaClient(Settings(upa_base_url="http://127.0.0.1:8000")) as client:
        with pytest.raises(UpaApiError) as exc:
            await client.get_snapshot("missing")
    assert exc.value.code == "not_found"
    assert "Snapshot not found" in exc.value.message


@pytest.mark.asyncio
@respx.mock
async def test_unavailable() -> None:
    respx.get("http://127.0.0.1:8000/health").mock(side_effect=httpx.ConnectError("boom"))
    async with UpaClient(Settings(upa_base_url="http://127.0.0.1:8000")) as client:
        with pytest.raises(UpaUnavailableError):
            await client.health()
