"""UniFi Network Integration API — read-only tools (Phase 1).

Local controller API, base ``https://<console>/proxy/network/integration/v1``,
auth via ``X-API-KEY``. Mutating endpoints (device/client actions, voucher
create/delete) are intentionally deferred to a later phase.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..config import Settings
from ..http import UbiquitiClient

API_PATH = "/proxy/network/integration/v1"


def register(mcp: FastMCP, settings: Settings) -> None:
    if not settings.network_enabled:
        return

    def client() -> UbiquitiClient:
        return UbiquitiClient(
            settings.network_base_url,
            settings.network_api_key,  # type: ignore[arg-type]
            verify_tls=settings.network_verify_tls,
            api_path=API_PATH,
        )

    @mcp.tool()
    async def network_get_info() -> Any:
        """Get the UniFi Network controller's application info (version, capabilities).

        Use this first to confirm connectivity and the API version the console exposes.
        """
        c = client()
        try:
            return await c.get("/info")
        finally:
            await c.aclose()

    @mcp.tool()
    async def network_list_sites() -> Any:
        """List the local sites managed by this UniFi Network console.

        Returns site id and metadata. Most other Network tools require a ``site_id``
        from this list.
        """
        c = client()
        try:
            return await c.get_collection("/sites")
        finally:
            await c.aclose()

    @mcp.tool()
    async def network_list_devices(site_id: str, max_items: int = 200) -> Any:
        """List UniFi devices (gateways, switches, access points) adopted in a site.

        Args:
            site_id: Site id from ``network_list_sites``.
            max_items: Cap on devices returned (avoids flooding context on large fleets).
        """
        c = client()
        try:
            return await c.get_collection(f"/sites/{site_id}/devices", max_items=max_items)
        finally:
            await c.aclose()

    @mcp.tool()
    async def network_get_device(site_id: str, device_id: str) -> Any:
        """Get full metadata for a single device in a site.

        Args:
            site_id: Site id from ``network_list_sites``.
            device_id: Device id from ``network_list_devices``.
        """
        c = client()
        try:
            return await c.get(f"/sites/{site_id}/devices/{device_id}")
        finally:
            await c.aclose()

    @mcp.tool()
    async def network_get_device_stats(site_id: str, device_id: str) -> Any:
        """Get the latest statistics/metrics for a device (uptime, load, throughput).

        Args:
            site_id: Site id from ``network_list_sites``.
            device_id: Device id from ``network_list_devices``.
        """
        c = client()
        try:
            return await c.get(f"/sites/{site_id}/devices/{device_id}/statistics/latest")
        finally:
            await c.aclose()

    @mcp.tool()
    async def network_list_clients(site_id: str, max_items: int = 200) -> Any:
        """List clients currently connected to a site's network.

        Args:
            site_id: Site id from ``network_list_sites``.
            max_items: Cap on clients returned (avoids flooding context).
        """
        c = client()
        try:
            return await c.get_collection(f"/sites/{site_id}/clients", max_items=max_items)
        finally:
            await c.aclose()

    @mcp.tool()
    async def network_get_client(site_id: str, client_id: str) -> Any:
        """Get details for a specific connected client.

        Args:
            site_id: Site id from ``network_list_sites``.
            client_id: Client id from ``network_list_clients``.
        """
        c = client()
        try:
            return await c.get(f"/sites/{site_id}/clients/{client_id}")
        finally:
            await c.aclose()

    @mcp.tool()
    async def network_list_vouchers(site_id: str, max_items: int = 200) -> Any:
        """List hotspot vouchers for a site.

        Args:
            site_id: Site id from ``network_list_sites``.
            max_items: Cap on vouchers returned.
        """
        c = client()
        try:
            return await c.get_collection(
                f"/sites/{site_id}/hotspot/vouchers", max_items=max_items
            )
        finally:
            await c.aclose()
