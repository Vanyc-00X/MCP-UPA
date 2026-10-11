# Safety notes for advanced MCP-UPA tools

Dangerous or externally visible actions require an explicit `confirm=true` argument.
Without it, the tool returns `error.code = confirm_required` and does **not** call UPA.

| Tool | Risk | Extra flags |
|---|---|---|
| `upa_deliver_run` | Sends data to webhook / Sheets / PostgreSQL | `kind`, `target` |
| `upa_heal_apply` | Writes a new scenario version with patched selectors | optional `keys_json` |
| `upa_workflow_live_run` | Real browser actions; may submit forms | also `confirm_dangerous` for UPA |
| `upa_set_monitor_schedule` | Enables background scheduled runs | `interval` or `null` to clear |

Safe by default:

- `upa_heal_propose` — proposal only
- `upa_workflow_dry_run` — DOM dry-run, no live submit
- `upa_robots_check` — advisory robots.txt check
- `upa_list_monitors` / `upa_get_run_journal` — read-only

Respect site Terms of Service. MCP-UPA does not bypass CAPTCHA or antibot measures.
