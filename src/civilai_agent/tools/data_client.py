"""HTTP client for governed civil-ai-data APIs."""

from __future__ import annotations

import os
from typing import Any

import httpx


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
        self.base_url = (base_url or proxy or os.getenv("CIVILAI_DATA_API_BASE", "http://localhost:8000")).rstrip("/")
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
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.request(method, url, headers=self._headers(), json=json)
            resp.raise_for_status()
            return resp.json()

    def resolve_parcel(self, *, address: str | None = None, prop_id: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if address:
            body["address"] = address
        if prop_id:
            body["prop_id"] = prop_id
        return self._request("POST", "/v1/entities/resolve", json=body)

    def get_section_facts(self, entity_id: str, section_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/sections/{section_id}/facts/{entity_id}")

    def get_site_by_entity(self, entity_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/fe/site?entity_id={entity_id}")

    def get_provenance(self, entity_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/entities/{entity_id}/provenance")

    def run_determinations(self, entity_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/entities/{entity_id}/determinations")
