"""Dangerous tools refuse without confirm=true."""

import asyncio
import json

from mcp_upa.server import (
    upa_deliver_run,
    upa_heal_apply,
    upa_set_monitor_schedule,
    upa_workflow_live_run,
)


def _code(payload: str) -> str:
    data = json.loads(payload)
    return data["error"]["code"]


def test_deliver_requires_confirm() -> None:
    out = asyncio.run(upa_deliver_run("r1", kind="webhook", target="https://example.com"))
    assert _code(out) == "confirm_required"


def test_heal_apply_requires_confirm() -> None:
    out = asyncio.run(upa_heal_apply("r1"))
    assert _code(out) == "confirm_required"


def test_live_workflow_requires_confirm() -> None:
    out = asyncio.run(upa_workflow_live_run("sc1", csv_text="a,b\n1,2"))
    assert _code(out) == "confirm_required"


def test_monitor_schedule_requires_confirm() -> None:
    out = asyncio.run(upa_set_monitor_schedule("sc1", interval="1h"))
    assert _code(out) == "confirm_required"
