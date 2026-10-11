#!/usr/bin/env python3
"""Smoke-check MCP-UPA against a running UPA instance.

Usage:
  python scripts/smoke_mcp.py
  python scripts/smoke_mcp.py --base-url http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mcp_upa.client import UpaClient  # noqa: E402
from mcp_upa.config import Settings  # noqa: E402
from mcp_upa.errors import McpUpaError  # noqa: E402


async def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test MCP-UPA ↔ UPA HTTP API")
    parser.add_argument("--base-url", default=None, help="Override UPA_BASE_URL")
    args = parser.parse_args()

    settings = Settings.from_env()
    if args.base_url:
        settings = Settings(
            upa_base_url=args.base_url.rstrip("/"),
            timeout_seconds=settings.timeout_seconds,
            preview_rows=settings.preview_rows,
            preview_elements=settings.preview_elements,
        )

    print(f"Checking UPA at {settings.upa_base_url} …")
    try:
        async with UpaClient(settings) as client:
            health = await client.health()
            info = await client.system_info()
            try:
                browser = await client.browser_status()
            except McpUpaError as exc:
                browser = exc.as_dict()
            templates = await client.list_templates()
    except McpUpaError as exc:
        print(json.dumps(exc.as_dict(), ensure_ascii=False, indent=2))
        return 1

    summary = {
        "ok": str(health.get("status")) == "ok",
        "health_status": health.get("status"),
        "app": info.get("app"),
        "version": info.get("version"),
        "stage": info.get("stage"),
        "templates": len((templates or {}).get("items") or []),
        "browser": browser,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    if not summary["ok"]:
        print(
            "\nHint: start UPA with .\\run.ps1 (or python -m app serve) "
            "and retry this smoke script.",
            file=sys.stderr,
        )
        return 1
    print("\nSmoke OK — MCP-UPA can talk to UPA.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
