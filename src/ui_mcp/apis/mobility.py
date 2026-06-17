"""UniFi Mobility API — read-only tools (consolidated).

Cloud API at ``https://api.ui.com/v1/mobility``, auth via ``X-API-KEY`` (scope
``read:mobility``). Resources are workspace-scoped; lists page by ``limit``/
``offset`` (shared client's ``get_paged_collection``).

Exposed through two tools:

- ``mobility_list(resource, workspace_id?, device_id?, max_items)`` — any
  collection, by enum. ``workspaces`` needs no ids; ``workspace_admins`` and
  ``devices`` need ``workspace_id``; ``device_clients`` needs both.
- ``mobility_get_device(workspace_id, device_id)`` — a single device.

The device write endpoints (PUT name / network / wireless, scope
``write:mobility``) are deferred; full inventory in
``docs/mobility_api_catalog.json``.

(No ``from __future__ import annotations`` so the dynamic ``Literal`` enum is a
real annotation object FastMCP can introspect.)
"""

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from ..config import Settings
from ..http import UbiquitiClient

API_PATH = "/v1/mobility"

# resource key -> (path relative to API_PATH, required-id params, paginated)
_LIST: dict[str, tuple[str, tuple[str, ...], bool]] = {
    "workspaces": ("/workspaces", (), False),
    "workspace_admins": ("/workspaces/{workspace_id}/admins", ("workspace_id",), False),
    "devices": ("/workspaces/{workspace_id}/devices", ("workspace_id",), True),
    "device_clients": (
        "/workspaces/{workspace_id}/devices/{device_id}/clients",
        ("workspace_id", "device_id"),
        True,
    ),
}

ListResource = Literal[tuple(_LIST)]  # type: ignore[valid-type]


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
    async def mobility_list(
        resource: ListResource,
        workspace_id: str | None = None,
        device_id: str | None = None,
        max_items: int = 200,
    ) -> Any:
        """List a Mobility resource collection.

        Args:
            resource: ``workspaces`` (no ids), ``workspace_admins`` / ``devices``
                (need ``workspace_id``), or ``device_clients`` (needs both ids).
            workspace_id: Workspace id from ``resource="workspaces"``.
            device_id: Device id (only for ``device_clients``).
            max_items: Cap on items for paginated resources (devices, clients).
        """
        path, required, paged = _LIST[resource]
        ids = {"workspace_id": workspace_id, "device_id": device_id}
        missing = [k for k in required if not ids[k]]
        if missing:
            raise ValueError(f"resource '{resource}' requires: {', '.join(missing)}")
        target = path.format(**ids)
        c = client()
        try:
            if paged:
                return await c.get_paged_collection(target, max_items=max_items)
            return await c.get(target)
        finally:
            await c.aclose()

    @mcp.tool()
    async def mobility_get_device(workspace_id: str, device_id: str) -> Any:
        """Get details for a single Mobility device.

        Args:
            workspace_id: Workspace id from ``mobility_list`` (resource="workspaces").
            device_id: Device id from ``mobility_list`` (resource="devices").
        """
        c = client()
        try:
            return await c.get(f"/workspaces/{workspace_id}/devices/{device_id}")
        finally:
            await c.aclose()
