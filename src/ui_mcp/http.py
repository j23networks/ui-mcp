"""Shared async HTTP client for all Ubiquiti APIs.

Handles the parts every API module would otherwise duplicate:
- API-key auth injection (``X-API-KEY`` header)
- self-signed TLS handling for local consoles
- the UniFi pagination envelope (``{offset, limit, count, totalCount, data}``)
- error normalization into a single ``UbiquitiAPIError``
"""

from __future__ import annotations

from typing import Any

import httpx


class UbiquitiAPIError(Exception):
    """Normalized error raised for any non-success Ubiquiti API response."""

    def __init__(self, status: int, message: str, detail: Any = None) -> None:
        self.status = status
        self.detail = detail
        super().__init__(f"[{status}] {message}")


class UbiquitiClient:
    """Thin async REST client scoped to one API (base URL + key + TLS policy)."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        verify_tls: bool = True,
        api_path: str = "",
        timeout: float = 30.0,
    ) -> None:
        # api_path is the fixed prefix between host and resource (e.g. the Network
        # integration path); resource paths are joined onto it.
        self._base = base_url.rstrip("/") + api_path
        self._client = httpx.AsyncClient(
            headers={"X-API-KEY": api_key, "Accept": "application/json"},
            verify=verify_tls,
            timeout=timeout,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get(self, path: str, **params: Any) -> Any:
        """GET a resource, returning parsed JSON (envelope intact)."""
        clean = {k: v for k, v in params.items() if v is not None}
        resp = await self._client.get(self._base + path, params=clean)
        return self._handle(resp)

    async def post(self, path: str, json: Any = None, **params: Any) -> Any:
        """POST a JSON body, returning parsed JSON (envelope intact)."""
        clean = {k: v for k, v in params.items() if v is not None}
        resp = await self._client.post(self._base + path, params=clean, json=json)
        return self._handle(resp)

    async def get_collection(
        self, path: str, *, limit: int = 200, max_items: int | None = None, **params: Any
    ) -> list[Any]:
        """GET a paginated collection, transparently following the offset/limit
        envelope and returning a flat list of ``data`` items.

        ``max_items`` caps the total fetched (guards against pulling huge fleets into
        an LLM context); ``None`` means fetch everything.
        """
        items: list[Any] = []
        offset = 0
        while True:
            page = await self.get(path, offset=offset, limit=limit, **params)
            if not isinstance(page, dict) or "data" not in page:
                # Endpoint isn't paginated — return whatever we got as a single page.
                return page if isinstance(page, list) else [page]
            batch = page.get("data", [])
            items.extend(batch)
            total = page.get("totalCount", len(items))
            offset += len(batch)
            if not batch or offset >= total or (max_items and len(items) >= max_items):
                break
        return items[:max_items] if max_items else items

    async def get_paged_collection(
        self, path: str, *, page_size: int = 100, max_items: int | None = None, **params: Any
    ) -> list[Any]:
        """GET a limit/offset-paginated collection that pages until a short page is
        returned (no total-count field needed). Unwraps a ``data`` envelope if
        present, otherwise treats the response as a plain list.

        Used by APIs (e.g. Mobility) that page by ``limit``/``offset`` but don't
        return a total count. ``max_items`` caps the total fetched.
        """
        items: list[Any] = []
        offset = 0
        while True:
            page = await self.get(path, limit=page_size, offset=offset, **params)
            batch = page.get("data") if isinstance(page, dict) and "data" in page else page
            if not isinstance(batch, list):
                # Unexpected shape — hand back as-is rather than guess.
                return batch
            items.extend(batch)
            offset += len(batch)
            if len(batch) < page_size or (max_items and len(items) >= max_items):
                break
        return items[:max_items] if max_items else items

    async def get_token_collection(
        self,
        path: str,
        *,
        page_size: int = 200,
        max_items: int | None = None,
        size_param: str = "pageSize",
        token_param: str = "nextToken",
        **params: Any,
    ) -> list[Any]:
        """GET a cursor-paginated collection (Site Manager style), following the
        response ``nextToken`` until it's empty and returning a flat list of the
        ``data`` items.

        Unlike ``get_collection`` (offset/limit), the cloud APIs page with an
        opaque cursor: each response carries a ``nextToken`` that's fed back as a
        query param on the next request. ``max_items`` caps the total fetched.
        """
        items: list[Any] = []
        token: str | None = None
        while True:
            page = await self.get(
                path, **{size_param: page_size, token_param: token}, **params
            )
            if not isinstance(page, dict) or "data" not in page:
                # Not the expected envelope — hand back whatever we got.
                return page if isinstance(page, list) else [page]
            batch = page.get("data") or []
            items.extend(batch)
            token = page.get("nextToken")
            if not token or not batch or (max_items and len(items) >= max_items):
                break
        return items[:max_items] if max_items else items

    def _handle(self, resp: httpx.Response) -> Any:
        if resp.is_success:
            if not resp.content:
                return None
            try:
                return resp.json()
            except ValueError:
                return resp.text
        # Try to surface the API's own error body.
        detail: Any
        try:
            detail = resp.json()
            message = detail.get("message") or detail.get("error") or resp.reason_phrase
        except ValueError:
            detail = resp.text
            message = resp.reason_phrase or "request failed"
        if resp.status_code == 429:
            message = "rate limited (429) — back off and retry"
        elif resp.status_code in (401, 403):
            message = "authentication failed — check the API key and its permissions"
        raise UbiquitiAPIError(resp.status_code, message, detail)
