"""HTTP client for governed civil-ai-data APIs."""

from __future__ import annotations

from typing import Any, cast

import httpx

from civilai_agent.config import DATA_API_TIMEOUT_DEFAULT, settings


class DataApiError(RuntimeError):
    """A governed-data API call failed. Carries the status code when there was a response.

    Tools convert this into a structured ``{"status": "error", ...}`` result so a single
    failed call degrades gracefully instead of crashing the whole agent run.
    """

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


# civil-ai-platform's Prompt Lab drafting workflow has its own 7-step vocabulary
# (LLM_SECTION_STEP_KEYS in civilai_platform.llm_defaults: parcel, zoning,
# environmental, utilities, access, exhibits, draft) that mostly, but not entirely,
# matches civil-ai-data's 11 real section_ids. context.active_section_id (the
# platform's step key) gets injected verbatim into the agent's own prompt text
# ("Active section: {step_key}", see workflows/section_draft.py), so the model
# naturally reuses that exact string as the section_id argument when it calls
# get_section_facts -- it has no way to know the two vocabularies diverge here.
# UAT-reported bug (2026-07-15): drafting the "Parcel" section 404'd every time
# on GET /v1/sections/parcel/facts/{entity_id} -- "parcel" was never a valid
# section_id, the real one is "parcel-overview". "access" has the same latent
# mismatch (the data-layer equivalent is "mobility") though not yet reported.
# "exhibits"/"draft" have no governed-data section equivalent at all and aren't
# aliased -- a tool call for either is a conceptual error, not a naming one.
_SECTION_ID_ALIASES: dict[str, str] = {
    "parcel": "parcel-overview",
    "access": "mobility",
}


def _normalize_section_id(section_id: str) -> str:
    return _SECTION_ID_ALIASES.get(section_id, section_id)


class DataApiClient:
    """Calls civil-ai-data /v1 endpoints (direct or via platform proxy)."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        service_key: str | None = None,
        data_scopes: tuple[str, ...] = (),
        timeout: float | None = None,
    ) -> None:
        cfg = settings()
        proxy = cfg.platform_data_proxy.strip()
        resolved_base = base_url if base_url else (proxy or cfg.data_api_base)
        self.base_url = resolved_base.rstrip("/")
        self.service_key = service_key or cfg.data_service_key.strip()
        self.data_scopes = data_scopes
        # Determinations over Athena can run long; allow an env override for slow backends.
        if timeout is not None:
            self.timeout = timeout
        elif cfg.data_api_timeout is not None:
            self.timeout = cfg.data_api_timeout
        else:
            self.timeout = DATA_API_TIMEOUT_DEFAULT

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
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.request(method, url, headers=self._headers(), json=json)
                resp.raise_for_status()
                return cast(dict[str, Any], resp.json())
        except httpx.HTTPStatusError as exc:
            detail = _error_detail(exc.response)
            raise DataApiError(
                f"{method} {path} -> {exc.response.status_code}: {detail}",
                status_code=exc.response.status_code,
            ) from exc
        except httpx.HTTPError as exc:
            raise DataApiError(f"{method} {path} failed: {exc}") from exc

    def resolve_parcel(
        self, *, address: str | None = None, parcel_id: str | None = None, county: str | None = None
    ) -> dict[str, Any]:
        # Backend EntityResolveRequest is extra="forbid" and accepts address / parcel_id
        # (NOT prop_id — sending prop_id 422s). parcel_id is the authoritative CAD account id.
        body: dict[str, Any] = {}
        if address:
            body["address"] = address
        if parcel_id:
            body["parcel_id"] = parcel_id
        if county:
            body["county"] = county
        return self._request("POST", "/v1/entities/resolve", json=body)

    def get_section_facts(self, entity_id: str, section_id: str) -> dict[str, Any]:
        normalized = _normalize_section_id(section_id)
        return self._request("GET", f"/v1/sections/{normalized}/facts/{entity_id}")

    def get_site_by_entity(self, entity_id: str) -> dict[str, Any]:
        # The by-entity FE route is GET /v1/fe/site/by-entity/{entity_id} (PII-scoped).
        # The old /v1/fe/site?entity_id=... query-param route never existed and 404s.
        return self._request("GET", f"/v1/fe/site/by-entity/{entity_id}")

    def hydrate_regtext(
        self,
        jurisdiction_key: str,
        zoning_code: str | None = None,
        families: list[str] | None = None,
    ) -> dict[str, Any]:
        """POST /v1/regtext/hydrate — parse indexed ordinance fact families."""
        body: dict[str, Any] = {
            "jurisdiction_key": jurisdiction_key,
            "families": families or ["impervious"],
        }
        if zoning_code:
            body["zoning_code"] = zoning_code
        return self._request("POST", "/v1/regtext/hydrate", json=body)

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
