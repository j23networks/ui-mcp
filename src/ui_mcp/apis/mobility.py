"""UniFi Mobility API — read-only tools (Phase 4).

Cloud API at ``https://api.ui.com/v1/mobility``, auth via ``X-API-KEY`` (scope
``read:mobility``). Resources are workspace-scoped: most calls take a
``workspace_id`` from ``mobility_list_workspaces``.

Lists page by ``limit``/``offset`` (no total-count field), handled by the shared
client's ``get_paged_collection``. The device write endpoints (PUT name / network /
wireless, scope ``write:mobility``) are deferred; the full inventory is in
``docs/mobility_api_catalog.json``.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..config import Settings
from ..http import UbiquitiClient

API_PATH = "/v1/mobility"


def register(mcp: FastMCP, settings: Settings) -> None:
    if not settings.mobility_enabled:
        return

    def client() -> UbiquitiClient:
        return UbiquitiClient(
            settings.mobility_base_url,
            settings.mobility_api_key,  # type: ignore[arg-type]
            verify_tls=True,
            api_path=API_PATH,
        )

    @mcp.tool()
    async def mobility_list_workspaces() -> Any:
        """List the Mobility workspaces visible to the authenticated account.

        Most other Mobility tools require a ``workspace_id`` from this list.
        """
        c = client()
        try:
            return await c.get("/workspaces")
        finally:
            await c.aclose()

    @mcp.tool()
    async def mobility_list_workspace_admins(workspace_id: str) -> Any:
        """List the admins of a workspace.

        Args:
            workspace_id: Workspace id from ``mobility_list_workspaces``.
        """
        c = client()
        try:
            return await c.get(f"/workspaces/{workspace_id}/admins")
        finally:
            await c.aclose()

    @mcp.tool()
    async def mobility_list_devices(workspace_id: str, max_items: int = 200) -> Any:
        """List Mobility devices in a workspace.

        Args:
            workspace_id: Workspace id from ``mobility_list_workspaces``.
            max_items: Cap on devices returned (follows limit/offset paging).
        """
        c = client()
        try:
            return await c.get_paged_collection(
                f"/workspaces/{workspace_id}/devices", max_items=max_items
            )
        finally:
            await c.aclose()

    @mcp.tool()
    async def mobility_get_device(workspace_id: str, device_id: str) -> Any:
        """Get details for a single Mobility device.

        Args:
            workspace_id: Workspace id from ``mobility_list_workspaces``.
            device_id: Device id from ``mobility_list_devices``.
        """
        c = client()
        try:
            return await c.get(f"/workspaces/{workspace_id}/devices/{device_id}")
        finally:
            await c.aclose()

    @mcp.tool()
    async def mobility_list_device_clients(
        workspace_id: str, device_id: str, max_items: int = 200
    ) -> Any:
        """List the clients connected to a Mobility device.

        Args:
            workspace_id: Workspace id from ``mobility_list_workspaces``.
            device_id: Device id from ``mobility_list_devices``.
            max_items: Cap on clients returned (follows limit/offset paging).
        """
        c = client()
        try:
            return await c.get_paged_collection(
                f"/workspaces/{workspace_id}/devices/{device_id}/clients",
                max_items=max_items,
            )
        finally:
            await c.aclose()
