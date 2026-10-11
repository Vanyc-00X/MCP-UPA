"""Run/export preview helpers."""

from mcp_upa.preview import preview_run_items


def test_preview_run_items_limits() -> None:
    data = {
        "run_id": "r1",
        "total": 100,
        "items": [
            {
                "id": f"i{i}",
                "position": i,
                "data": {"title": f"t{i}"},
                "is_valid": True,
                "validation_errors": [],
            }
            for i in range(50)
        ],
    }
    out = preview_run_items(data, max_rows=5)
    assert out["total"] == 100
    assert out["returned"] == 5
    assert out["items"][0]["data"]["title"] == "t0"
