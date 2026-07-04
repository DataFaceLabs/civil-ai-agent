"""HTTP client for governed civil-ai-data APIs."""

from __future__ import annotations

import os
from typing import Any

import httpx


class DataApiError(RuntimeError):
    """A governed-data API call failed. Carries the status code when there was a response.

    Tools convert this into a structured ``{"status": "error", ...}`` result so a single
    failed call degrades gracefully instead of crashing the whole agent run.
    """

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class DataApiClient:
    """Calls civil-ai-data /v1 endpoints (direct or via platform proxy)."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        service_key: str | None = None,
        data_scopes: tuple[str, ...] = (),
        timeout: float = 30.0,
    ) -> None:
        proxy = os.getenv("CIVILAI_PLATFORM_DATA_PROXY", "").strip()
        self.base_url = (
            base_url or proxy or os.getenv("CIVILAI_DATA_API_BASE", "http://localhost:8000")
        ).rstrip("/")
        self.service_key = service_key or os.getenv("CIVILAI_DATA_SERVICE_KEY", "").strip()
        self.data_scopes = data_scopes
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        if self.service_key:
            headers["X-Data-Service-Key"] = self.service_key
        if self.data_scopes:
            headers["X-Data-Scopes"] = " ".join(self.data_scopes)
        return headers

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.request(method, url, headers=self._headers(), json=json)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            detail = _error_detail(exc.response)
            raise DataApiError(
                f"{method} {path} -> {exc.response.status_code}: {detail}",
                status_code=exc.response.status_code,
            ) from exc
        except httpx.HTTPError as exc:
            raise DataApiError(f"{method} {path} failed: {exc}") from exc

    def resolve_parcel(
        self, *, address: str | None = None, parcel_id: str | None = None
    ) -> dict[str, Any]:
        # Backend EntityResolveRequest is extra="forbid" and accepts address / parcel_id
        # (NOT prop_id — sending prop_id 422s). parcel_id is the authoritative CAD account id.
        body: dict[str, Any] = {}
        if address:
            body["address"] = address
        if parcel_id:
            body["parcel_id"] = parcel_id
        return self._request("POST", "/v1/entities/resolve", json=body)

    def get_section_facts(self, entity_id: str, section_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/sections/{section_id}/facts/{entity_id}")

    def get_site_by_entity(self, entity_id: str) -> dict[str, Any]:
        # The by-entity FE route is GET /v1/fe/site/by-entity/{entity_id} (PII-scoped).
        # The old /v1/fe/site?entity_id=... query-param route never existed and 404s.
        return self._request("GET", f"/v1/fe/site/by-entity/{entity_id}")

    def get_provenance(self, entity_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/entities/{entity_id}/provenance")

    def run_determinations(self, entity_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/entities/{entity_id}/determinations")


def _error_detail(response: httpx.Response) -> str:
    """Best-effort human-readable detail from a FastAPI error response."""
    try:
        body = response.json()
    except ValueError:
        return response.text[:300]
    if isinstance(body, dict) and "detail" in body:
        return str(body["detail"])[:300]
    return str(body)[:300]
