from __future__ import annotations

from typing import Any

import httpx


class GdeltCloudClient:
    """Thin wrapper over httpx for calling the GDELT Cloud public REST API.

    All methods return the parsed JSON `data` array for the corresponding
    endpoint. Bearer auth header is attached automatically.
    """

    def __init__(self, api_key: str, base_url: str = "https://gdeltcloud.com", timeout: float = 60.0):
        if not api_key:
            raise ValueError("GDELT_API_KEY is required. Get one at https://gdeltcloud.com/api-keys")
        self._client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )

    # ---- v2 surface --------------------------------------------------

    def events(self, **params: Any) -> list[dict[str, Any]]:
        return self._get("/api/v2/events", params)

    def stories(self, **params: Any) -> list[dict[str, Any]]:
        return self._get("/api/v2/stories", params)

    def entities(self, **params: Any) -> list[dict[str, Any]]:
        return self._get("/api/v2/entities", params)

    def energy_assets(self, **params: Any) -> list[dict[str, Any]]:
        return self._get("/api/v2/energy/assets", params)

    # ---- internals ---------------------------------------------------

    def _get(self, path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        cleaned = {k: v for k, v in params.items() if v is not None and v != ""}
        resp = self._client.get(path, params=cleaned)
        resp.raise_for_status()
        body = resp.json()
        if not body.get("success", True):
            raise RuntimeError(f"GDELT Cloud error: {body.get('error')}")
        return body.get("data", [])

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "GdeltCloudClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
