# MCP-UPA — план разработки

MCP-сервер поверх [UPA](https://github.com/Vanyc-00X/UPA-Universal-Parser-Automatization-):
Cursor / Claude создают и запускают сценарии парсинга из чата.

## Архитектура

Тонкий MCP-клиент (stdio) → HTTP REST UPA (`UPA_BASE_URL`).
Движок Playwright / SQLite остаётся в UPA.

## Этапы

| Этап | Цель | DoD |
|---|---|---|
| 0 | Каркас репозитория | README, PLAN, pyproject, пример mcp.json на GitHub | **done** |
| 1 | MCP skeleton + UpaClient | `upa_status`, `upa_system_info`, MCPServer stdio | **done** |
| 2 | Snapshot + analyze | snapshot_id + element map preview | **done** |
| 3 | CRUD сценариев | create/list/get/update + templates + prompt | **done** |
| 4 | Run + export | run → rows preview → CSV/JSON | **done** |
| 5 | Advanced | deliver, healing, workflows (confirm) | **done** |
| 6 | Полировка | smoke, troubleshooting, UX ошибок | **done** |

После каждого этапа — commit и push в `https://github.com/Vanyc-00X/MCP-UPA-.git`
от identity владельца (без Cursor в Contributors).

## Вне скоупа

- Копия frontend / Playwright-движка UPA
- Hosted SaaS scraper
- Обход CAPTCHA / antibot
