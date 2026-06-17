"""UniFi Site Manager API — read-only tools (consolidated).

Cloud API at ``https://api.ui.com/v1``, auth via ``X-API-KEY``. Read-only today
(UI notes write endpoints are "coming"). Differs from the local Network API in
two ways handled here:

- **Cursor pagination** (``pageSize`` + ``nextToken``) instead of offset/limit.
- A ``{data, httpStatusCode, traceId, nextToken}`` response envelope; tools
  return the unwrapped ``data`` payload.

The three collection endpoints are exposed through one ``sitemanager_list(resource)``
tool; the by-id host fetch and the two ISP-metrics calls (a time-windowed GET and a
POST query) stay as dedicated tools since their shapes differ.

Cloud endpoint, so TLS is verified (no self-signed handling). (No
``from __future__ import annotations`` so the dynamic ``Literal`` enum is a real
annotation object FastMCP can introspect.)
"""

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from ..config import Settings
from ..http import UbiquitiClient

API_PATH = "/v1"

# resource key -> path relative to API_PATH (cursor-paginated collections)
_LIST: dict[str, str] = {
    "hosts": "/hosts",
    "sites": "/sites",
    "devices": "/devices",
}

ListResource = Literal[tuple(_LIST)]  # type: ignore[valid-type]


def register(mcp: FastMCP, settings: Settings) -> None:
    if not settings.site_manager_enabled:
        return

    def client() -> UbiquitiClient:
        return UbiquitiClient(
            settings.site_manager_base_url,
            settings.site_manager_api_key,  # type: ignore[arg-type]
            verify_tls=True,
            api_path=API_PATH,
        )

    async def _data(c: UbiquitiClient, path: str, **params: Any) -> Any:
        """GET a single resource and return its unwrapped ``data`` payload."""
        env = await c.get(path, **params)
        return env.get("data") if isinstance(env, dict) and "data" in env else env

    @mcp.tool()
    async def sitemanager_list(
        resource: ListResource,
        host_ids: list[str] | None = None,
        time: str | None = None,
        max_items: int = 200,
    ) -> Any:
        """List a Site Manager collection (cursor-paginated, returns flat data).

        Args:
            resource: ``hosts`` (consoles/gateways — source of host ids),
                ``sites`` (Network sites across hosts), or ``devices``.
            host_ids: Only for ``resource="devices"`` — filter to these host ids.
            time: Only for ``resource="devices"`` — RFC3339 timestamp; devices
                processed since then.
            max_items: Cap on items returned (follows nextToken paging).
        """
        params: dict[str, Any] = {}
        if resource == "devices":
            if host_ids:
                # The API expects the ids comma-joined under the ``hostIds[]`` key.
                params["hostIds[]"] = ",".join(host_ids)
            if time:
                params["time"] = time
        c = client()
        try:
            return await c.get_token_collection(_LIST[resource], max_items=max_items, **params)
        finally:
            await c.aclose()

    @mcp.tool()
    async def sitemanager_get_host(host_id: str) -> Any:
        """Get detailed info for a single host by id.

        Args:
            host_id: Host id from ``sitemanager_list`` with ``resource="hosts"``.
        """
        c = client()
        try:
            return await _data(c, f"/hosts/{host_id}")
        finally:
            await c.aclose()

    @mcp.tool()
    async def sitemanager_get_isp_metrics(
        interval: str = "1h",
        begin_timestamp: str | None = None,
        end_timestamp: str | None = None,
        duration: str | None = None,
    ) -> Any:
        """Get ISP performance metrics for all sites on the account.

        Args:
            interval: ``5m`` (retained >=24h) or ``1h`` (retained >=30d).
            begin_timestamp: Earliest RFC3339 timestamp to return. Pair with
                ``end_timestamp``; mutually exclusive with ``duration``.
            end_timestamp: Latest RFC3339 timestamp to return.
            duration: Relative window ending now — ``24h`` (5m interval) or
                ``7d``/``30d`` (1h interval). Cannot combine with the timestamps.
        """
        c = client()
        try:
            return await _data(
                c,
                f"/isp-metrics/{interval}",
                beginTimestamp=begin_timestamp,
                endTimestamp=end_timestamp,
                duration=duration,
            )
        finally:
            await c.aclose()

    @mcp.tool()
    async def sitemanager_query_isp_metrics(interval: str, sites: list[dict]) -> Any:
        """Query ISP metrics for specific sites and time ranges.

        Args:
            interval: ``5m`` or ``1h``.
            sites: List of site query objects, each like
                ``{"hostId": "...", "siteId": "...", "beginTimestamp": "...",
                "endTimestamp": "..."}`` (RFC3339 timestamps).
        """
        c = client()
        try:
            env = await c.post(f"/isp-metrics/{interval}/query", json={"sites": sites})
            return env.get("data") if isinstance(env, dict) and "data" in env else env
        finally:
            await c.aclose()
