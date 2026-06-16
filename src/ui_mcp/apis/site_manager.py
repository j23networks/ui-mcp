"""UniFi Site Manager API — read-only tools (Phase 2).

Cloud API at ``https://api.ui.com/v1``, auth via ``X-API-KEY``. Read-only today
(UI notes write endpoints are "coming"). Differs from the local Network API in
two ways handled here:

- **Cursor pagination** (``pageSize`` + ``nextToken``) instead of offset/limit.
- A ``{data, httpStatusCode, traceId, nextToken}`` response envelope; tools
  return the unwrapped ``data`` payload.

Cloud endpoint, so TLS is verified (no self-signed handling).
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..config import Settings
from ..http import UbiquitiClient

API_PATH = "/v1"


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

    async def _data(client: UbiquitiClient, path: str, **params: Any) -> Any:
        """GET a single resource and return its unwrapped ``data`` payload."""
        env = await client.get(path, **params)
        return env.get("data") if isinstance(env, dict) and "data" in env else env

    @mcp.tool()
    async def sitemanager_list_hosts(max_items: int = 200) -> Any:
        """List all UniFi hosts (consoles/gateways) on the UI cloud account.

        A host is a device running UniFi OS. Most other Site Manager tools key off
        a ``host_id`` returned here.

        Args:
            max_items: Cap on hosts returned (follows pagination up to this many).
        """
        c = client()
        try:
            return await c.get_token_collection("/hosts", max_items=max_items)
        finally:
            await c.aclose()

    @mcp.tool()
    async def sitemanager_get_host(host_id: str) -> Any:
        """Get detailed info for a single host by id.

        Args:
            host_id: Host id from ``sitemanager_list_hosts``.
        """
        c = client()
        try:
            return await _data(c, f"/hosts/{host_id}")
        finally:
            await c.aclose()

    @mcp.tool()
    async def sitemanager_list_sites(max_items: int = 200) -> Any:
        """List all UniFi Network sites (across hosts) on the UI cloud account.

        Args:
            max_items: Cap on sites returned.
        """
        c = client()
        try:
            return await c.get_token_collection("/sites", max_items=max_items)
        finally:
            await c.aclose()

    @mcp.tool()
    async def sitemanager_list_devices(
        host_ids: list[str] | None = None,
        time: str | None = None,
        max_items: int = 200,
    ) -> Any:
        """List UniFi devices managed across the account.

        Args:
            host_ids: Optional list of host ids to filter to (from
                ``sitemanager_list_hosts``).
            time: Optional RFC3339 timestamp; only devices processed since then.
            max_items: Cap on devices returned.
        """
        params: dict[str, Any] = {}
        if host_ids:
            # The API expects the ids comma-joined under the ``hostIds[]`` key.
            params["hostIds[]"] = ",".join(host_ids)
        if time:
            params["time"] = time
        c = client()
        try:
            return await c.get_token_collection("/devices", max_items=max_items, **params)
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
