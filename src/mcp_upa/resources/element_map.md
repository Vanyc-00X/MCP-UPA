# Element map preview (MCP-UPA)

`upa_analyze` / `upa_get_element_map` return a **truncated** view:

- `by_role` — counts by role (price, title, pagination, …)
- `repeats` — detected list groups with `item_selector` candidates
- `elements_preview` — up to N elements: `role`, `label`, `selector`, short `text`
- `report` — short human summary

Use `repeats[].item_selector` as `plan.item_selector` when building a collection scenario.
Prefer selectors with `data-testid` / stable classes over long structural paths.
