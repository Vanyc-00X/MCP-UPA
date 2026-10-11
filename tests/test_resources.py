"""MCP resources resolve to useful agent docs."""

from mcp_upa.server import element_map_guide_resource, scenario_schema_resource


def test_scenario_schema_resource() -> None:
    text = scenario_schema_resource()
    assert "ScenarioDefinition" in text or "plan" in text
    assert "item_selector" in text


def test_element_map_guide_resource() -> None:
    text = element_map_guide_resource()
    assert "elements_preview" in text or "repeats" in text
