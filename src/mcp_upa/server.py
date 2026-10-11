"""MCP-UPA stdio server (FastMCP)."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from mcp.server.mcpserver import MCPServer

from mcp_upa import __version__
from mcp_upa.client import UpaClient
from mcp_upa.config import Settings
from mcp_upa.errors import format_tool_error
from mcp_upa.preview import (
    preview_draft_state,
    preview_element_map,
    preview_run,
    preview_run_items,
    preview_scenario_list,
    preview_snapshot,
)

T = TypeVar("T")

mcp = MCPServer(
    "mcp-upa",
    title="MCP-UPA",
    description="MCP server on top of UPA for creating and running parsing scenarios",
    instructions=(
        "MCP-UPA controls a local UPA instance over HTTP. "
        "Typical flow: upa_status → upa_create_snapshot(url) → upa_analyze → "
        "upa_put_draft / upa_save_scenario → upa_run_scenario → upa_get_run_data / upa_export_run. "
        "UPA must already be running (default http://127.0.0.1:8000)."
    ),
    version=__version__,
)

_settings = Settings.from_env()


async def _with_client(fn: Callable[[UpaClient], Awaitable[T]]) -> T | dict[str, Any]:
    try:
        async with UpaClient(_settings) as client:
            return await fn(client)
    except Exception as exc:  # noqa: BLE001 — surface as tool result
        return format_tool_error(exc)


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=str, indent=2)


# ---------------------------------------------------------------------------
# Stage 1 — status
# ---------------------------------------------------------------------------


@mcp.tool()
async def upa_status() -> str:
    """Check whether the local UPA API is healthy and summarize components."""
    result = await _with_client(lambda c: c.health())
    if isinstance(result, dict) and result.get("ok") is False:
        return _json(result)
    return _json({"ok": True, "mcp_upa_version": __version__, "health": result})


@mcp.tool()
async def upa_system_info() -> str:
    """Return UPA build info, stage, data paths, browser and LLM settings."""
    result = await _with_client(lambda c: c.system_info())
    if isinstance(result, dict) and result.get("ok") is False:
        return _json(result)
    return _json({"ok": True, "info": result})


@mcp.tool()
async def upa_ensure_ready() -> str:
    """Verify UPA health + browser readiness and explain how to start UPA if needed."""

    async def _run(client: UpaClient) -> dict[str, Any]:
        health = await client.health()
        try:
            browser = await client.browser_status()
        except Exception as exc:  # noqa: BLE001
            browser = {"error": str(exc)}
        ready = str(health.get("status")) == "ok"
        return {
            "ok": ready,
            "base_url": client.base_url,
            "health": health,
            "browser": browser,
            "hint": (
                None
                if ready
                else (
                    "Start UPA from its repo: .\\run.ps1 "
                    "or `python -m app serve` in backend/. "
                    f"Then confirm {client.base_url}/health returns status ok."
                )
            ),
        }

    return _json(await _with_client(_run))


# ---------------------------------------------------------------------------
# Stage 2 — snapshot + analyze
# ---------------------------------------------------------------------------


@mcp.tool()
async def upa_create_snapshot(
    url: str,
    use_cache: bool = True,
    allow_local: bool = False,
) -> str:
    """Open URL in UPA/Playwright and capture a page snapshot (DOM, network, screenshots)."""

    async def _run(client: UpaClient) -> dict[str, Any]:
        data = await client.create_snapshot(
            url, use_cache=use_cache, allow_local=allow_local
        )
        return preview_snapshot(data)

    return _json(await _with_client(_run))


@mcp.tool()
async def upa_get_snapshot(snapshot_id: str) -> str:
    """Get summary metadata for an existing snapshot."""

    async def _run(client: UpaClient) -> dict[str, Any]:
        return preview_snapshot(await client.get_snapshot(snapshot_id))

    return _json(await _with_client(_run))


@mcp.tool()
async def upa_list_snapshots(
    site_id: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> str:
    """List recent snapshots, optionally filtered by site_id."""

    async def _run(client: UpaClient) -> dict[str, Any]:
        data = await client.list_snapshots(site_id=site_id, limit=limit, offset=offset)
        items = [preview_snapshot(item) for item in list(data.get("items") or [])]
        return {"ok": True, "total": data.get("total"), "items": items}

    return _json(await _with_client(_run))


@mcp.tool()
async def upa_analyze(
    snapshot_id: str,
    use_llm: bool = True,
    force: bool = False,
) -> str:
    """Analyze a snapshot and build an element map (roles, selectors, lists)."""

    async def _run(client: UpaClient) -> dict[str, Any]:
        data = await client.analyze_snapshot(
            snapshot_id, use_llm=use_llm, force=force
        )
        return preview_element_map(data, max_elements=_settings.preview_elements)

    return _json(await _with_client(_run))


@mcp.tool()
async def upa_get_element_map(snapshot_id: str) -> str:
    """Return the stored element map for a snapshot (must analyze first)."""

    async def _run(client: UpaClient) -> dict[str, Any]:
        data = await client.get_element_map(snapshot_id)
        return preview_element_map(data, max_elements=_settings.preview_elements)

    return _json(await _with_client(_run))


@mcp.tool()
async def upa_get_page_report(snapshot_id: str) -> str:
    """Human-readable page report produced during analysis."""

    async def _run(client: UpaClient) -> dict[str, Any]:
        data = await client.get_report(snapshot_id)
        return {"ok": True, **data}

    return _json(await _with_client(_run))


# ---------------------------------------------------------------------------
# Stage 3 — scenarios
# ---------------------------------------------------------------------------


@mcp.tool()
async def upa_list_templates(kind: str | None = None) -> str:
    """List built-in UPA scenario templates (kind: collection | form_fill)."""

    async def _run(client: UpaClient) -> dict[str, Any]:
        data = await client.list_templates(kind=kind)
        return {"ok": True, **data}

    return _json(await _with_client(_run))


@mcp.tool()
async def upa_get_template(template_id: str) -> str:
    """Load a template definition (collection or form_fill) with sample data."""

    async def _run(client: UpaClient) -> dict[str, Any]:
        return {"ok": True, "template": await client.get_template(template_id)}

    return _json(await _with_client(_run))


@mcp.tool()
async def upa_get_draft(snapshot_id: str) -> str:
    """Get the scenario draft + validation state for a snapshot."""

    async def _run(client: UpaClient) -> dict[str, Any]:
        return preview_draft_state(await client.get_draft(snapshot_id))

    return _json(await _with_client(_run))


@mcp.tool()
async def upa_put_draft(snapshot_id: str, definition_json: str) -> str:
    """Replace the scenario draft with a full ScenarioDefinition JSON string."""

    async def _run(client: UpaClient) -> dict[str, Any]:
        definition = json.loads(definition_json)
        return preview_draft_state(await client.put_draft(snapshot_id, definition))

    return _json(await _with_client(_run))


@mcp.tool()
async def upa_update_plan(
    snapshot_id: str,
    plan_mode: str | None = None,
    item_selector: str | None = None,
    container_selector: str | None = None,
    pagination_json: str | None = None,
) -> str:
    """Update extraction plan / pagination on the draft (modes: list, single, api, llm)."""

    async def _run(client: UpaClient) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if plan_mode is not None:
            payload["plan_mode"] = plan_mode
        if item_selector is not None:
            payload["item_selector"] = item_selector
        if container_selector is not None:
            payload["container_selector"] = container_selector
        if pagination_json:
            payload["pagination"] = json.loads(pagination_json)
        return preview_draft_state(await client.update_plan(snapshot_id, payload))

    return _json(await _with_client(_run))


@mcp.tool()
async def upa_add_field(
    snapshot_id: str,
    title: str,
    selector: str,
    key: str | None = None,
    strategy: str = "text",
    attribute: str | None = None,
    required: bool = False,
    role: str | None = None,
) -> str:
    """Add one field to the snapshot draft."""

    async def _run(client: UpaClient) -> dict[str, Any]:
        field: dict[str, Any] = {
            "title": title,
            "selector": selector,
            "strategy": strategy,
            "required": required,
        }
        if key:
            field["key"] = key
        if attribute:
            field["attribute"] = attribute
        if role:
            field["role"] = role
        return preview_draft_state(await client.add_field(snapshot_id, field))

    return _json(await _with_client(_run))


@mcp.tool()
async def upa_update_field(
    snapshot_id: str,
    key: str,
    title: str | None = None,
    selector: str | None = None,
    strategy: str | None = None,
    attribute: str | None = None,
    required: bool | None = None,
) -> str:
    """Patch a draft field by key."""

    async def _run(client: UpaClient) -> dict[str, Any]:
        field: dict[str, Any] = {"key": key}
        if title is not None:
            field["title"] = title
        if selector is not None:
            field["selector"] = selector
        if strategy is not None:
            field["strategy"] = strategy
        if attribute is not None:
            field["attribute"] = attribute
        if required is not None:
            field["required"] = required
        return preview_draft_state(await client.update_field(snapshot_id, field))

    return _json(await _with_client(_run))


@mcp.tool()
async def upa_preview_draft(snapshot_id: str) -> str:
    """Preview extracted field values from the current draft on the snapshot DOM."""

    async def _run(client: UpaClient) -> dict[str, Any]:
        return {"ok": True, **await client.preview_draft(snapshot_id)}

    return _json(await _with_client(_run))


@mcp.tool()
async def upa_save_scenario(
    snapshot_id: str,
    name: str,
    description: str | None = None,
    change_note: str | None = None,
    scenario_id: str | None = None,
) -> str:
    """Save the validated draft as a new scenario (or a new version if scenario_id is set)."""

    async def _run(client: UpaClient) -> dict[str, Any]:
        data = await client.save_as_scenario(
            snapshot_id,
            name=name,
            description=description,
            change_note=change_note,
            scenario_id=scenario_id,
        )
        return {
            "ok": True,
            "scenario_id": data.get("scenario_id"),
            "scenario_name": data.get("scenario_name"),
            "site_id": data.get("site_id"),
            "version": data.get("version"),
            "fields": data.get("fields"),
            "definition_summary": (
                data.get("definition", {}).get("title")
                if isinstance(data.get("definition"), dict)
                else None
            ),
        }

    return _json(await _with_client(_run))


@mcp.tool()
async def upa_create_scenario_from_definition(
    snapshot_id: str,
    name: str,
    definition_json: str,
    description: str | None = None,
) -> str:
    """Put a full ScenarioDefinition JSON as draft, then save it as a named scenario."""

    async def _run(client: UpaClient) -> dict[str, Any]:
        definition = json.loads(definition_json)
        if "snapshot_id" not in definition:
            definition["snapshot_id"] = snapshot_id
        draft = await client.put_draft(snapshot_id, definition)
        validation = draft.get("validation") or {}
        if isinstance(validation, dict) and validation.get("ok") is False:
            return {
                "ok": False,
                "error": {
                    "code": "draft_invalid",
                    "message": "Scenario draft failed validation",
                    "details": {
                        "problems": validation.get("problems"),
                        "warnings": validation.get("warnings"),
                    },
                },
                "draft": preview_draft_state(draft),
            }
        saved = await client.save_as_scenario(
            snapshot_id, name=name, description=description
        )
        return {
            "ok": True,
            "scenario_id": saved.get("scenario_id"),
            "scenario_name": saved.get("scenario_name"),
            "version": saved.get("version"),
            "fields": saved.get("fields"),
        }

    return _json(await _with_client(_run))


@mcp.tool()
async def upa_list_scenarios(
    site_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> str:
    """List saved UPA scenarios."""

    async def _run(client: UpaClient) -> dict[str, Any]:
        return preview_scenario_list(
            await client.list_scenarios(site_id=site_id, limit=limit, offset=offset)
        )

    return _json(await _with_client(_run))


@mcp.tool()
async def upa_get_scenario(scenario_id: str) -> str:
    """Get scenario versions (latest first) including definitions."""

    async def _run(client: UpaClient) -> dict[str, Any]:
        versions = await client.get_scenario_versions(scenario_id)
        return {"ok": True, "scenario_id": scenario_id, "versions": versions}

    return _json(await _with_client(_run))


# ---------------------------------------------------------------------------
# Stage 4 — runs + export
# ---------------------------------------------------------------------------


@mcp.tool()
async def upa_run_scenario(
    scenario_id: str,
    snapshot_id: str | None = None,
    live: bool = False,
    min_coverage: float | None = None,
) -> str:
    """Run a saved collection scenario and return status + coverage report."""

    async def _run(client: UpaClient) -> dict[str, Any]:
        data = await client.create_run(
            scenario_id,
            snapshot_id=snapshot_id,
            live=live,
            min_coverage=min_coverage,
        )
        return preview_run(data)

    return _json(await _with_client(_run))


@mcp.tool()
async def upa_get_run(run_id: str) -> str:
    """Get run status and coverage report."""

    async def _run(client: UpaClient) -> dict[str, Any]:
        return preview_run(await client.get_run(run_id))

    return _json(await _with_client(_run))


@mcp.tool()
async def upa_list_runs(
    scenario_id: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> str:
    """List recent runs, optionally filtered by scenario_id."""

    async def _run(client: UpaClient) -> dict[str, Any]:
        data = await client.list_runs(scenario_id=scenario_id, limit=limit, offset=offset)
        items = [preview_run(item) for item in list(data.get("items") or [])]
        return {"ok": True, "total": data.get("total"), "items": items}

    return _json(await _with_client(_run))


@mcp.tool()
async def upa_get_run_data(
    run_id: str,
    limit: int = 20,
    offset: int = 0,
    only_invalid: bool = False,
) -> str:
    """Return collected rows for a run (preview truncated for chat)."""

    async def _run(client: UpaClient) -> dict[str, Any]:
        data = await client.get_run_items(
            run_id,
            limit=min(limit, _settings.preview_rows),
            offset=offset,
            only_invalid=only_invalid,
        )
        return preview_run_items(data, max_rows=_settings.preview_rows)

    return _json(await _with_client(_run))


@mcp.tool()
async def upa_export_run(
    run_id: str,
    format: str = "csv",
    delimiter: str = ",",
    only_invalid: bool = False,
    include_preview: bool = True,
) -> str:
    """Export a run (csv/xlsx/json/jsonl/md). Returns download meta and optional text preview."""

    async def _run(client: UpaClient) -> dict[str, Any]:
        meta = await client.export_run_meta(
            run_id, fmt=format, delimiter=delimiter, only_invalid=only_invalid
        )
        payload: dict[str, Any] = {"ok": True, "export": meta}
        if include_preview and format in {"csv", "json", "jsonl", "md"}:
            raw = await client.export_run_text(
                run_id, fmt=format, delimiter=delimiter, only_invalid=only_invalid
            )
            content = raw.get("content") or b""
            if isinstance(content, bytes):
                text = content.decode("utf-8", errors="replace")
            else:
                text = str(content)
            payload["preview"] = text[:4000]
            payload["preview_truncated"] = len(text) > 4000
        return payload

    return _json(await _with_client(_run))


# ---------------------------------------------------------------------------
# Stage 5 — advanced
# ---------------------------------------------------------------------------


@mcp.tool()
async def upa_deliver_run(
    run_id: str,
    kind: str,
    target: str,
    options_json: str | None = None,
    only_invalid: bool = False,
    confirm: bool = False,
) -> str:
    """Deliver run results to webhook / Google Sheets / PostgreSQL. Requires confirm=true."""
    if not confirm:
        return _json(
            {
                "ok": False,
                "error": {
                    "code": "confirm_required",
                    "message": "Delivery may send data externally. Call again with confirm=true.",
                    "details": {"kind": kind, "target": target},
                },
            }
        )

    async def _run(client: UpaClient) -> dict[str, Any]:
        options = json.loads(options_json) if options_json else None
        data = await client.deliver_run(
            run_id,
            kind=kind,
            target=target,
            options=options,
            only_invalid=only_invalid,
        )
        return {"ok": True, "delivery": data}

    return _json(await _with_client(_run))


@mcp.tool()
async def upa_heal_propose(run_id: str, refresh: bool = False) -> str:
    """Propose selector healing patches for a failed/low-coverage run (does not apply)."""

    async def _run(client: UpaClient) -> dict[str, Any]:
        return {"ok": True, "proposal": await client.get_heal_proposal(run_id, refresh=refresh)}

    return _json(await _with_client(_run))


@mcp.tool()
async def upa_heal_apply(
    run_id: str,
    keys_json: str | None = None,
    change_note: str | None = None,
    confirm: bool = False,
) -> str:
    """Apply a heal proposal as a new scenario version. Requires confirm=true."""
    if not confirm:
        return _json(
            {
                "ok": False,
                "error": {
                    "code": "confirm_required",
                    "message": "Healing changes scenario selectors. Call again with confirm=true.",
                },
            }
        )

    async def _run(client: UpaClient) -> dict[str, Any]:
        keys = json.loads(keys_json) if keys_json else None
        data = await client.apply_heal(run_id, keys=keys, change_note=change_note)
        return {"ok": True, "result": data}

    return _json(await _with_client(_run))


@mcp.tool()
async def upa_get_run_journal(run_id: str) -> str:
    """Return step journal for a run (useful for debugging selectors)."""

    async def _run(client: UpaClient) -> dict[str, Any]:
        return {"ok": True, "steps": await client.get_run_journal(run_id)}

    return _json(await _with_client(_run))


@mcp.tool()
async def upa_robots_check(url: str) -> str:
    """Check robots.txt guidance for a URL via UPA."""

    async def _run(client: UpaClient) -> dict[str, Any]:
        return {"ok": True, **await client.robots_check(url)}

    return _json(await _with_client(_run))


@mcp.tool()
async def upa_workflow_dry_run(
    scenario_id: str,
    csv_text: str | None = None,
    rows_json: str | None = None,
    snapshot_id: str | None = None,
) -> str:
    """Dry-run a form_fill workflow against a snapshot DOM (no real submits)."""

    async def _run(client: UpaClient) -> dict[str, Any]:
        payload: dict[str, Any] = {"persist": True}
        if csv_text is not None:
            payload["csv_text"] = csv_text
        if rows_json is not None:
            payload["rows"] = json.loads(rows_json)
        if snapshot_id is not None:
            payload["snapshot_id"] = snapshot_id
        return {"ok": True, **await client.workflow_dry_run(scenario_id, payload)}

    return _json(await _with_client(_run))


@mcp.tool()
async def upa_workflow_live_run(
    scenario_id: str,
    csv_text: str | None = None,
    rows_json: str | None = None,
    confirm_dangerous: bool = False,
    confirm: bool = False,
) -> str:
    """Live Playwright workflow run. Requires confirm=true; set confirm_dangerous for submits."""
    if not confirm:
        return _json(
            {
                "ok": False,
                "error": {
                    "code": "confirm_required",
                    "message": (
                        "Live workflow can submit forms / trigger payments. "
                        "Call again with confirm=true (and confirm_dangerous=true if needed)."
                    ),
                },
            }
        )

    async def _run(client: UpaClient) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "persist": True,
            "confirm_dangerous": confirm_dangerous,
        }
        if csv_text is not None:
            payload["csv_text"] = csv_text
        if rows_json is not None:
            payload["rows"] = json.loads(rows_json)
        return {"ok": True, **await client.workflow_live_run(scenario_id, payload)}

    return _json(await _with_client(_run))


@mcp.tool()
async def upa_list_monitors() -> str:
    """List scenarios and their monitoring schedules."""

    async def _run(client: UpaClient) -> dict[str, Any]:
        return {"ok": True, **await client.list_monitors()}

    return _json(await _with_client(_run))


@mcp.tool()
async def upa_set_monitor_schedule(
    scenario_id: str,
    interval: str | None = None,
    confirm: bool = False,
) -> str:
    """Set or clear a monitor interval for a scenario (e.g. 1h, 6h, 1d). Requires confirm=true."""
    if not confirm:
        return _json(
            {
                "ok": False,
                "error": {
                    "code": "confirm_required",
                    "message": "Scheduling changes background runs. Call again with confirm=true.",
                    "details": {"scenario_id": scenario_id, "interval": interval},
                },
            }
        )

    async def _run(client: UpaClient) -> dict[str, Any]:
        return {
            "ok": True,
            "monitor": await client.set_monitor_schedule(scenario_id, interval),
        }

    return _json(await _with_client(_run))


# ---------------------------------------------------------------------------
# Resources + prompts
# ---------------------------------------------------------------------------

SCENARIO_SCHEMA_HINT = """
# UPA ScenarioDefinition (collection) — fields used by MCP-UPA

Required-ish shape:
{
  "url": "https://example.com/catalog",
  "snapshot_id": "<id>",
  "title": "Catalog",
  "plan": { "mode": "list", "item_selector": ".product-card" },
  "pagination": { "kind": "next_link", "selector": "a.next", "max_pages": 5 },
  "fields": [
    { "key": "title", "title": "Title", "selector": ".title", "required": true },
    { "key": "price", "title": "Price", "selector": ".price" },
    {
      "key": "url",
      "title": "URL",
      "selector": "a.link",
      "strategy": "attribute",
      "attribute": "href"
    }
  ],
  "created_from": "import"
}

Strategies: text | own_text | attribute | html | image | count
Plan modes: list | single | api | llm
Pagination kinds: none | next_link | url_template | scroll | load_more
""".strip()


@mcp.resource("upa://scenario-schema")
def scenario_schema_resource() -> str:
    """Compact ScenarioDefinition schema hint for agents."""
    from importlib import resources as importlib_resources

    try:
        return (
            importlib_resources.files("mcp_upa.resources")
            .joinpath("scenario_schema.md")
            .read_text(encoding="utf-8")
        )
    except Exception:  # noqa: BLE001
        return SCENARIO_SCHEMA_HINT


@mcp.resource("upa://element-map-guide")
def element_map_guide_resource() -> str:
    """How to read truncated element-map tool responses."""
    from importlib import resources as importlib_resources

    try:
        return (
            importlib_resources.files("mcp_upa.resources")
            .joinpath("element_map.md")
            .read_text(encoding="utf-8")
        )
    except Exception:  # noqa: BLE001
        return (
            "Element map tools return truncated previews: by_role, repeats, "
            "elements_preview (role/label/selector). Use repeats.item_selector for list mode."
        )


@mcp.prompt()
def build_collection_scenario(
    url: str,
    fields_wanted: str = "title, price, url",
    notes: str = "",
) -> str:
    """Guide the agent to build a collection scenario from a live UPA page."""
    return f"""
You are building a UPA collection scenario via MCP-UPA tools.

Target URL: {url}
Desired fields: {fields_wanted}
Extra notes: {notes or "(none)"}

Steps:
1. Call upa_ensure_ready / upa_status.
2. upa_create_snapshot(url="{url}").
3. upa_analyze(snapshot_id=...).
4. From repeats + elements_preview, pick item_selector and field selectors.
5. Build ScenarioDefinition JSON (see resource upa://scenario-schema).
6. upa_create_scenario_from_definition(snapshot_id, name, definition_json).
7. upa_run_scenario(scenario_id) then upa_get_run_data / upa_export_run.

Prefer stable selectors (data-testid, semantic classes). Do not apply healing or live
workflows without explicit user confirmation.
""".strip()


def main() -> None:
    """Entry point for `mcp-upa` / `python -m mcp_upa`."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
