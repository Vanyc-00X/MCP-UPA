# MCP-UPA

MCP server on top of [UPA](https://github.com/Vanyc-00X/UPA-Universal-Parser-Automatization-) so Cursor / Claude can create and run parsing scenarios from chat.

```text
Cursor / Claude ──stdio MCP──► MCP-UPA ──HTTP──► UPA API (127.0.0.1:8000)
```

MCP-UPA does **not** embed Playwright or SQLite. It talks to a running UPA instance.

## Requirements

1. **UPA** installed and running ([quick start](https://github.com/Vanyc-00X/UPA-Universal-Parser-Automatization-#quick-start)):

   ```powershell
   git clone https://github.com/Vanyc-00X/UPA-Universal-Parser-Automatization-.git
   cd UPA-Universal-Parser-Automatization-
   .\run.ps1
   ```

   API: `http://127.0.0.1:8000` · docs: `http://127.0.0.1:8000/docs`

2. **Python 3.11+**

## Install MCP-UPA

```powershell
git clone https://github.com/Vanyc-00X/MCP-UPA.git
cd MCP-UPA
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
```

## Cursor config

Add to Cursor MCP settings (see also [`examples/cursor-mcp.json`](examples/cursor-mcp.json)):

```json
{
  "mcpServers": {
    "mcp-upa": {
      "command": "D:\\Dowland\\MCP-UPA\\.venv\\Scripts\\python.exe",
      "args": ["-m", "mcp_upa"],
      "env": {
        "UPA_BASE_URL": "http://127.0.0.1:8000"
      }
    }
  }
}
```

Use an absolute path to the venv Python so Cursor finds the package.

## Environment

| Variable | Default | Meaning |
|---|---|---|
| `UPA_BASE_URL` | `http://127.0.0.1:8000` | UPA HTTP API base |
| `UPA_TIMEOUT_SECONDS` | `120` | HTTP timeout for long snapshot/run calls |

## Tools (snapshot + analyze)

| Tool | Purpose |
|---|---|
| `upa_create_snapshot` | Capture URL via UPA/Playwright |
| `upa_get_snapshot` / `upa_list_snapshots` | Inspect existing snapshots |
| `upa_analyze` | Build element map (roles, lists, selectors) |
| `upa_get_element_map` | Read stored map |
| `upa_get_page_report` | Human-readable page report |

Resources: `upa://element-map-guide`, `upa://scenario-schema`.

## Tools (scenarios)

| Tool | Purpose |
|---|---|
| `upa_list_templates` / `upa_get_template` | Built-in collection / form_fill templates |
| `upa_get_draft` / `upa_put_draft` | Read/replace snapshot draft |
| `upa_add_field` / `upa_update_field` / `upa_update_plan` | Edit draft incrementally |
| `upa_preview_draft` | Preview values on current DOM |
| `upa_save_scenario` | Persist validated draft |
| `upa_create_scenario_from_definition` | Put definition JSON + save |
| `upa_list_scenarios` / `upa_get_scenario` | Inspect saved scenarios |

Prompt: `build_collection_scenario` — guided collection pipeline from a URL.

## Tools (runs + export)

| Tool | Purpose |
|---|---|
| `upa_run_scenario` | Execute a saved collection scenario |
| `upa_get_run` / `upa_list_runs` | Status + coverage report |
| `upa_get_run_data` | Preview collected rows (truncated) |
| `upa_export_run` | Export csv/xlsx/json/jsonl/md + text preview |

Chat responses are capped (`UPA_PREVIEW_ROWS`, default 20). Use export meta `download_url` (relative to UPA) for full files.

## Tools (advanced) + safety

| Tool | Purpose |
|---|---|
| `upa_deliver_run` | webhook / Sheets / PG (**confirm**) |
| `upa_heal_propose` / `upa_heal_apply` | Selector healing (**apply needs confirm**) |
| `upa_workflow_dry_run` / `upa_workflow_live_run` | Form workflows (live needs **confirm**) |
| `upa_list_monitors` / `upa_set_monitor_schedule` | Change monitoring (**set needs confirm**) |
| `upa_get_run_journal` / `upa_robots_check` | Diagnostics |

Details: [docs/SAFETY.md](docs/SAFETY.md).

## Development stages

See [PLAN.md](PLAN.md). Stages 0–6 grow tools from status → snapshot/analyze → scenarios → runs/export → advanced → polish.

## Status tools

| Tool | Purpose |
|---|---|
| `upa_status` | UPA `/health` |
| `upa_system_info` | Build / paths / LLM settings |
| `upa_ensure_ready` | Health + browser readiness + start hint |

## Smoke test

With UPA running:

```powershell
.\.venv\Scripts\python scripts\smoke_mcp.py
```

Exit code `0` means MCP-UPA can reach UPA. Exit `1` prints a structured error (`upa_unavailable`, etc.).

## Troubleshooting

| Symptom | Fix |
|---|---|
| `upa_unavailable` / connection refused | Start UPA (`.\run.ps1` or `python -m app serve`). Check `UPA_BASE_URL`. |
| Cursor cannot start MCP | Use absolute path to `.venv\Scripts\python.exe` and `args: ["-m", "mcp_upa"]`. Reinstall: `pip install -e .` |
| Snapshot/analyze hangs | Increase `UPA_TIMEOUT_SECONDS` (default 120). Ensure Playwright browser is installed in UPA. |
| `draft_invalid` on save | Fix `validation.problems` from `upa_get_draft` / preview before `upa_save_scenario`. |
| `confirm_required` | Re-call the tool with `confirm=true` only after the user agrees ([docs/SAFETY.md](docs/SAFETY.md)). |
| Tool returns huge JSON | Previews are truncated; use `upa_export_run` for full files. |

Error shape:

```json
{
  "ok": false,
  "error": {
    "code": "upa_unavailable",
    "message": "...",
    "details": {},
    "hint": "Start UPA first..."
  }
}
```

## Contributors

Commits in this repository are authored by the project owner. Automated assistants may help write code locally; they are not listed as GitHub contributors.

## License

MIT (same spirit as local-first UPA tooling).
