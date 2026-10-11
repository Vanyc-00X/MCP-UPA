# UPA ScenarioDefinition (collection)

Used by `upa_put_draft` / `upa_create_scenario_from_definition`.

```json
{
  "url": "https://example.com/catalog",
  "snapshot_id": "<id>",
  "title": "Catalog",
  "description": "optional",
  "plan": {
    "mode": "list",
    "item_selector": ".product-card",
    "container_selector": null
  },
  "pagination": {
    "kind": "next_link",
    "selector": "a.pagination__next",
    "max_pages": 5
  },
  "detail": {
    "enabled": false,
    "link_field": "url",
    "fields": []
  },
  "fields": [
    {
      "key": "title",
      "title": "Title",
      "selector": ".product-card__title",
      "strategy": "text",
      "required": true
    },
    {
      "key": "price",
      "title": "Price",
      "selector": ".product-card__price",
      "strategy": "text"
    },
    {
      "key": "url",
      "title": "URL",
      "selector": "a.product-card__link",
      "strategy": "attribute",
      "attribute": "href"
    }
  ],
  "created_from": "import"
}
```

- Strategies: `text` | `own_text` | `attribute` | `html` | `image` | `count`
- Plan modes: `list` | `single` | `api` | `llm`
- Pagination: `none` | `next_link` | `url_template` | `scroll` | `load_more`

Prompt helper: `build_collection_scenario`.
