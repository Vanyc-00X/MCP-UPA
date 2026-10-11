"""HTTP client for the UPA FastAPI backend."""

from __future__ import annotations

from typing import Any

import httpx

from mcp_upa.config import Settings
from mcp_upa.errors import UpaApiError, UpaUnavailableError


class UpaClient:
    """Thin async wrapper around UPA REST API (`/api/v1/...` and `/health`)."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        self._client: httpx.AsyncClient | None = None

    @property
    def base_url(self) -> str:
        return self.settings.upa_base_url

    async def __aenter__(self) -> UpaClient:
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.settings.timeout_seconds),
            headers={"Accept": "application/json"},
        )
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _require(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("UpaClient must be used as an async context manager")
        return self._client

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        expect_json: bool = True,
    ) -> Any:
        client = self._require()
        try:
            response = await client.request(method, path, params=params, json=json)
        except httpx.TimeoutException as exc:
            raise UpaUnavailableError(self.base_url, f"timeout: {exc}") from exc
        except httpx.HTTPError as exc:
            raise UpaUnavailableError(self.base_url, str(exc)) from exc

        if response.status_code >= 400:
            raise self._api_error(response)

        if not expect_json or response.status_code == 204:
            return {
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type", ""),
                "content": response.content,
                "headers": dict(response.headers),
            }

        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()
        return {
            "status_code": response.status_code,
            "content_type": content_type,
            "text": response.text[:8000],
        }

    def _api_error(self, response: httpx.Response) -> UpaApiError:
        code = "upa_api_error"
        message = f"UPA HTTP {response.status_code}"
        details: dict[str, Any] = {"body": response.text[:2000]}
        try:
            payload = response.json()
        except Exception:  # noqa: BLE001
            payload = None
        if isinstance(payload, dict):
            err = payload.get("error")
            if isinstance(err, dict):
                code = str(err.get("code") or code)
                message = str(err.get("message") or message)
                if isinstance(err.get("details"), dict):
                    details.update(err["details"])
            elif "detail" in payload:
                message = str(payload["detail"])
        return UpaApiError(message, status_code=response.status_code, code=code, details=details)

    # --- system ---

    async def health(self) -> dict[str, Any]:
        return await self.request("GET", "/health")

    async def system_info(self) -> dict[str, Any]:
        return await self.request("GET", "/api/v1/system/info")

    async def system_features(self) -> dict[str, Any]:
        return await self.request("GET", "/api/v1/system/features")

    async def browser_status(self) -> dict[str, Any]:
        return await self.request("GET", "/api/v1/system/browser")

    # --- snapshots / analyze ---

    async def create_snapshot(
        self,
        url: str,
        *,
        use_cache: bool = True,
        allow_local: bool = False,
    ) -> dict[str, Any]:
        return await self.request(
            "POST",
            "/api/v1/snapshots",
            json={"url": url, "use_cache": use_cache, "allow_local": allow_local},
        )

    async def get_snapshot(self, snapshot_id: str) -> dict[str, Any]:
        return await self.request("GET", f"/api/v1/snapshots/{snapshot_id}")

    async def list_snapshots(
        self,
        *,
        site_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if site_id:
            params["site_id"] = site_id
        return await self.request("GET", "/api/v1/snapshots", params=params)

    async def analyze_snapshot(
        self,
        snapshot_id: str,
        *,
        use_llm: bool = True,
        force: bool = False,
    ) -> dict[str, Any]:
        return await self.request(
            "POST",
            f"/api/v1/snapshots/{snapshot_id}/analyze",
            json={"use_llm": use_llm, "force": force},
        )

    async def get_element_map(self, snapshot_id: str) -> dict[str, Any]:
        return await self.request("GET", f"/api/v1/snapshots/{snapshot_id}/element-map")

    async def get_report(self, snapshot_id: str) -> dict[str, Any]:
        return await self.request("GET", f"/api/v1/snapshots/{snapshot_id}/report")

    # --- editor / scenarios ---

    async def get_draft(self, snapshot_id: str) -> dict[str, Any]:
        return await self.request("GET", f"/api/v1/snapshots/{snapshot_id}/draft")

    async def put_draft(self, snapshot_id: str, definition: dict[str, Any]) -> dict[str, Any]:
        return await self.request(
            "PUT",
            f"/api/v1/snapshots/{snapshot_id}/draft",
            json={"definition": definition},
        )

    async def save_as_scenario(
        self,
        snapshot_id: str,
        *,
        name: str,
        description: str | None = None,
        change_note: str | None = None,
        scenario_id: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"name": name}
        if description is not None:
            payload["description"] = description
        if change_note is not None:
            payload["change_note"] = change_note
        if scenario_id is not None:
            payload["scenario_id"] = scenario_id
        return await self.request(
            "POST",
            f"/api/v1/snapshots/{snapshot_id}/draft/save-as-scenario",
            json=payload,
        )

    async def list_scenarios(
        self,
        *,
        site_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if site_id:
            params["site_id"] = site_id
        return await self.request("GET", "/api/v1/scenarios", params=params)

    async def get_scenario_versions(self, scenario_id: str, *, limit: int = 50) -> Any:
        return await self.request(
            "GET",
            f"/api/v1/scenarios/{scenario_id}/versions",
            params={"limit": limit},
        )

    async def delete_scenario(self, scenario_id: str) -> dict[str, Any]:
        return await self.request("DELETE", f"/api/v1/scenarios/{scenario_id}")

    async def list_templates(self, kind: str | None = None) -> dict[str, Any]:
        params = {"kind": kind} if kind else None
        return await self.request("GET", "/api/v1/templates", params=params)

    async def get_template(self, template_id: str) -> dict[str, Any]:
        return await self.request("GET", f"/api/v1/templates/{template_id}")

    async def add_field(self, snapshot_id: str, field: dict[str, Any]) -> dict[str, Any]:
        return await self.request(
            "POST",
            f"/api/v1/snapshots/{snapshot_id}/draft/fields",
            json=field,
        )

    async def update_field(self, snapshot_id: str, field: dict[str, Any]) -> dict[str, Any]:
        return await self.request(
            "PATCH",
            f"/api/v1/snapshots/{snapshot_id}/draft/fields",
            json=field,
        )

    async def update_plan(self, snapshot_id: str, plan: dict[str, Any]) -> dict[str, Any]:
        return await self.request(
            "PATCH",
            f"/api/v1/snapshots/{snapshot_id}/draft/plan",
            json=plan,
        )

    async def preview_draft(self, snapshot_id: str) -> dict[str, Any]:
        return await self.request("GET", f"/api/v1/snapshots/{snapshot_id}/draft/preview")

    # --- runs / export ---

    async def create_run(
        self,
        scenario_id: str,
        *,
        snapshot_id: str | None = None,
        live: bool = False,
        min_coverage: float | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"scenario_id": scenario_id, "live": live}
        if snapshot_id is not None:
            payload["snapshot_id"] = snapshot_id
        if min_coverage is not None:
            payload["min_coverage"] = min_coverage
        return await self.request("POST", "/api/v1/runs", json=payload)

    async def get_run(self, run_id: str) -> dict[str, Any]:
        return await self.request("GET", f"/api/v1/runs/{run_id}")

    async def list_runs(
        self,
        *,
        scenario_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if scenario_id:
            params["scenario_id"] = scenario_id
        return await self.request("GET", "/api/v1/runs", params=params)

    async def get_run_items(
        self,
        run_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
        only_invalid: bool = False,
    ) -> dict[str, Any]:
        return await self.request(
            "GET",
            f"/api/v1/runs/{run_id}/items",
            params={"limit": limit, "offset": offset, "only_invalid": only_invalid},
        )

    async def export_run_meta(
        self,
        run_id: str,
        *,
        fmt: str = "csv",
        delimiter: str = ",",
        only_invalid: bool = False,
    ) -> dict[str, Any]:
        return await self.request(
            "GET",
            f"/api/v1/runs/{run_id}/export/meta",
            params={"format": fmt, "delimiter": delimiter, "only_invalid": only_invalid},
        )

    async def export_run_text(
        self,
        run_id: str,
        *,
        fmt: str = "json",
        delimiter: str = ",",
        only_invalid: bool = False,
    ) -> dict[str, Any]:
        return await self.request(
            "GET",
            f"/api/v1/runs/{run_id}/export",
            params={"format": fmt, "delimiter": delimiter, "only_invalid": only_invalid},
            expect_json=False,
        )

    async def deliver_run(
        self,
        run_id: str,
        *,
        kind: str,
        target: str,
        options: dict[str, Any] | None = None,
        only_invalid: bool = False,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "kind": kind,
            "target": target,
            "only_invalid": only_invalid,
        }
        if options is not None:
            payload["options"] = options
        return await self.request("POST", f"/api/v1/runs/{run_id}/deliver", json=payload)

    # --- healing / workflows / monitor ---

    async def get_heal_proposal(self, run_id: str, *, refresh: bool = False) -> dict[str, Any]:
        return await self.request(
            "GET",
            f"/api/v1/runs/{run_id}/heal",
            params={"refresh": refresh},
        )

    async def apply_heal(
        self,
        run_id: str,
        *,
        keys: list[str] | None = None,
        change_note: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if keys is not None:
            payload["keys"] = keys
        if change_note is not None:
            payload["change_note"] = change_note
        return await self.request("POST", f"/api/v1/runs/{run_id}/heal/apply", json=payload)

    async def get_run_journal(self, run_id: str) -> Any:
        return await self.request("GET", f"/api/v1/runs/{run_id}/journal")

    async def robots_check(self, url: str) -> dict[str, Any]:
        return await self.request("GET", "/api/v1/robots/check", params={"url": url})

    async def save_workflow(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.request("POST", "/api/v1/workflows", json=payload)

    async def get_workflow(self, scenario_id: str) -> dict[str, Any]:
        return await self.request("GET", f"/api/v1/workflows/{scenario_id}")

    async def workflow_dry_run(self, scenario_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.request(
            "POST",
            f"/api/v1/workflows/{scenario_id}/dry-run",
            json=payload,
        )

    async def workflow_live_run(self, scenario_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.request(
            "POST",
            f"/api/v1/workflows/{scenario_id}/run",
            json=payload,
        )

    async def list_monitors(self) -> dict[str, Any]:
        return await self.request("GET", "/api/v1/monitor")

    async def set_monitor_schedule(self, scenario_id: str, interval: str | None) -> dict[str, Any]:
        return await self.request(
            "PUT",
            f"/api/v1/monitor/scenarios/{scenario_id}/schedule",
            json={"interval": interval},
        )

    async def monitor_check(self, scenario_id: str, *, live: bool = False) -> dict[str, Any]:
        return await self.request(
            "POST",
            f"/api/v1/monitor/scenarios/{scenario_id}/check",
            json={"live": live},
        )
