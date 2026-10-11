"""Preview helpers keep MCP responses small."""

from mcp_upa.preview import preview_element_map, preview_run, preview_snapshot


def test_preview_snapshot() -> None:
    out = preview_snapshot(
        {
            "id": "s1",
            "url": "https://example.com",
            "title": "Demo",
            "status": "ready",
            "html_bytes": 1234,
        }
    )
    assert out["ok"] is True
    assert out["snapshot_id"] == "s1"
    assert out["title"] == "Demo"


def test_preview_element_map_truncates() -> None:
    elements = [
        {"index": i, "role": "price", "label": f"p{i}", "selector": f".p{i}", "text": "x" * 200}
        for i in range(100)
    ]
    out = preview_element_map({"id": "m1", "snapshot_id": "s1", "elements": elements}, max_elements=5)
    assert out["elements_total"] == 100
    assert len(out["elements_preview"]) == 5
    assert out["elements_preview"][0]["text"] is not None
    assert len(out["elements_preview"][0]["text"]) <= 121


def test_preview_run() -> None:
    out = preview_run(
        {
            "id": "r1",
            "scenario_id": "sc1",
            "status": "completed",
            "items_count": 3,
            "report": {"records": 3, "passed": True},
        }
    )
    assert out["run_id"] == "r1"
    assert out["report"]["records"] == 3
