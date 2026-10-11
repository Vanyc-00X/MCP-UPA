"""Truncate large UPA payloads for MCP tool responses."""

from __future__ import annotations

from typing import Any


def preview_snapshot(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": True,
        "snapshot_id": data.get("id"),
        "site_id": data.get("site_id"),
        "url": data.get("url"),
        "final_url": data.get("final_url"),
        "status": data.get("status"),
        "http_status": data.get("http_status"),
        "title": data.get("title"),
        "lang": data.get("lang"),
        "html_bytes": data.get("html_bytes"),
        "trimmed_bytes": data.get("trimmed_bytes"),
        "est_tokens": data.get("est_tokens"),
        "duration_ms": data.get("duration_ms"),
        "network_count": data.get("network_count"),
        "data_sources_count": data.get("data_sources_count"),
        "cache_hit": data.get("cache_hit"),
        "error": data.get("error"),
    }


def preview_element_map(
    data: dict[str, Any],
    *,
    max_elements: int = 40,
) -> dict[str, Any]:
    elements = list(data.get("elements") or [])
    slim: list[dict[str, Any]] = []
    for index, element in enumerate(elements[:max_elements]):
        if not isinstance(element, dict):
            continue
        candidates = element.get("selectors") or element.get("selector_candidates") or []
        primary = element.get("selector")
        if not primary and isinstance(candidates, list) and candidates:
            first = candidates[0]
            primary = first.get("selector") if isinstance(first, dict) else first
        slim.append(
            {
                "index": element.get("index", index),
                "role": element.get("role"),
                "label": element.get("label") or element.get("title"),
                "selector": primary,
                "tag": element.get("tag"),
                "text": _clip(element.get("text") or element.get("sample"), 120),
            }
        )

    repeats = []
    for group in list(data.get("repeats") or [])[:10]:
        if isinstance(group, dict):
            repeats.append(
                {
                    "role": group.get("role") or group.get("kind"),
                    "count": group.get("count") or group.get("size"),
                    "item_selector": group.get("item_selector") or group.get("selector"),
                    "sample_fields": group.get("fields") or group.get("sample_fields"),
                }
            )

    return {
        "ok": True,
        "element_map_id": data.get("id"),
        "snapshot_id": data.get("snapshot_id"),
        "version": data.get("version"),
        "confidence": data.get("confidence"),
        "by_role": data.get("by_role") or {},
        "report": _clip(data.get("report") or data.get("summary"), 1500),
        "warnings": list(data.get("warnings") or [])[:20],
        "repeats": repeats,
        "elements_total": len(elements),
        "elements_preview": slim,
        "page": data.get("page") or {},
        "llm": data.get("llm"),
        "reused": data.get("reused"),
    }


def preview_scenario_list(data: dict[str, Any]) -> dict[str, Any]:
    items = []
    for item in list(data.get("items") or [])[:100]:
        if not isinstance(item, dict):
            continue
        definition = item.get("definition") or {}
        items.append(
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "kind": item.get("kind"),
                "site_id": item.get("site_id"),
                "current_version": item.get("current_version"),
                "is_active": item.get("is_active"),
                "url": definition.get("url") if isinstance(definition, dict) else None,
                "fields": (
                    len(definition.get("fields") or [])
                    if isinstance(definition, dict)
                    else None
                ),
            }
        )
    return {"ok": True, "total": data.get("total", len(items)), "items": items}


def preview_run(data: dict[str, Any]) -> dict[str, Any]:
    report = data.get("report")
    report_preview = None
    if isinstance(report, dict):
        report_preview = {
            "records": report.get("records"),
            "valid_records": report.get("valid_records"),
            "invalid_records": report.get("invalid_records"),
            "required_coverage": report.get("required_coverage"),
            "completeness": report.get("completeness"),
            "passed": report.get("passed"),
            "issues_total": report.get("issues_total"),
        }
    return {
        "ok": True,
        "run_id": data.get("id"),
        "scenario_id": data.get("scenario_id"),
        "scenario_name": data.get("scenario_name"),
        "status": data.get("status"),
        "items_count": data.get("items_count"),
        "pages_done": data.get("pages_done"),
        "errors_count": data.get("errors_count"),
        "error": data.get("error"),
        "started_at": data.get("started_at"),
        "finished_at": data.get("finished_at"),
        "report": report_preview,
        "stats": data.get("stats") or {},
    }


def preview_run_items(data: dict[str, Any], *, max_rows: int = 20) -> dict[str, Any]:
    items = []
    for item in list(data.get("items") or [])[:max_rows]:
        if not isinstance(item, dict):
            continue
        items.append(
            {
                "id": item.get("id"),
                "position": item.get("position"),
                "data": item.get("data") or {},
                "source_url": item.get("source_url"),
                "is_valid": item.get("is_valid"),
                "validation_errors": list(item.get("validation_errors") or [])[:5],
            }
        )
    return {
        "ok": True,
        "run_id": data.get("run_id"),
        "total": data.get("total"),
        "returned": len(items),
        "items": items,
    }


def preview_draft_state(data: dict[str, Any]) -> dict[str, Any]:
    draft = data.get("draft") or data.get("definition") or {}
    validation = data.get("validation") or {}
    fields = []
    if isinstance(draft, dict):
        for field in list(draft.get("fields") or [])[:50]:
            if isinstance(field, dict):
                fields.append(
                    {
                        "key": field.get("key"),
                        "title": field.get("title"),
                        "selector": field.get("selector"),
                        "strategy": field.get("strategy"),
                        "required": field.get("required"),
                    }
                )
    return {
        "ok": True,
        "snapshot_id": data.get("snapshot_id"),
        "items_in_dom": data.get("items_in_dom"),
        "draft": {
            "title": draft.get("title") if isinstance(draft, dict) else None,
            "url": draft.get("url") if isinstance(draft, dict) else None,
            "plan": draft.get("plan") if isinstance(draft, dict) else None,
            "pagination": draft.get("pagination") if isinstance(draft, dict) else None,
            "fields": fields,
        },
        "validation": {
            "ok": validation.get("ok") if isinstance(validation, dict) else None,
            "problems": (
                list(validation.get("problems") or [])[:20]
                if isinstance(validation, dict)
                else []
            ),
            "warnings": (
                list(validation.get("warnings") or [])[:20]
                if isinstance(validation, dict)
                else []
            ),
        },
    }


def _clip(value: Any, limit: int) -> str | None:
    if value is None:
        return None
    text = str(value)
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"
