"""UniFi Protect API — read-only tools (consolidated).

Local NVR API, base ``https://<nvr>/proxy/protect/integration/v1``, auth via
``X-API-KEY``. Lists return plain JSON arrays and single resources plain objects
(no pagination envelope).

Exposed through three tools driven by a resource registry:

- ``protect_get_meta_info`` — Protect application meta/system info (singleton).
- ``protect_list(resource)`` — any device/resource collection, by enum.
- ``protect_get(resource, device_id)`` — any single resource by id.

Scope is **metadata + URLs only**: media-byte endpoints (``/snapshot``,
``/files/{type}``), WebSocket ``/subscribe/*`` streams, the connector passthrough,
and all mutations are excluded. ``camera_rtsps_stream`` is included (it returns
stream URLs, not bytes). Full inventory in ``docs/protect_api_catalog.json``.

(No ``from __future__ import annotations`` so the dynamic ``Literal`` enums are
real annotation objects FastMCP can introspect.)
"""

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from ..config import Settings
from ..http import UbiquitiClient

API_PATH = "/proxy/protect/integration/v1"

# resource key -> path relative to API_PATH (collections; plain arrays)
_LIST: dict[str, str] = {
    "cameras": "/cameras",
    "sensors": "/sensors",
    "lights": "/lights",
    "chimes": "/chimes",
    "sirens": "/sirens",
    "speakers": "/speakers",
    "viewers": "/viewers",
    "liveviews": "/liveviews",
    "bridges": "/bridges",
    "alarm_hubs": "/alarm-hubs",
    "fobs": "/fobs",
    "relays": "/relays",
    "link_stations": "/link-stations",
    "arm_profiles": "/arm-profiles",
    "users": "/users",
    "ulp_users": "/ulp-users",
    "nvrs": "/nvrs",
}

# resource key -> path relative to API_PATH (single resource by {id})
_GET: dict[str, str] = {
    "camera": "/cameras/{id}",
    "camera_rtsps_stream": "/cameras/{id}/rtsps-stream",
    "sensor": "/sensors/{id}",
    "light": "/lights/{id}",
    "chime": "/chimes/{id}",
    "siren": "/sirens/{id}",
    "speaker": "/speakers/{id}",
    "viewer": "/viewers/{id}",
    "liveview": "/liveviews/{id}",
    "bridge": "/bridges/{id}",
    "alarm_hub": "/alarm-hubs/{id}",
    "fob": "/fobs/{id}",
    "relay": "/relays/{id}",
    "link_station": "/link-stations/{id}",
    "user": "/users/{id}",
    "ulp_user": "/ulp-users/{id}",
}

ListResource = Literal[tuple(_LIST)]  # type: ignore[valid-type]
GetResource = Literal[tuple(_GET)]  # type: ignore[valid-type]


def register(mcp: FastMCP, settings: Settings) -> None:
    if not settings.protect_enabled:
        return

    def client() -> UbiquitiClient:
        return UbiquitiClient(
            settings.protect_base_url,  # type: ignore[arg-type]
            settings.protect_api_key,  # type: ignore[arg-type]
            verify_tls=settings.protect_verify_tls,
            api_path=API_PATH,
        )

    @mcp.tool()
    async def protect_get_meta_info() -> Any:
        """Get UniFi Protect application meta/system info (NVR/app version, etc.)."""
        c = client()
        try:
            return await c.get("/meta/info")
        finally:
            await c.aclose()

    @mcp.tool()
    async def protect_list(resource: ListResource) -> Any:
        """List a Protect resource collection (full metadata for each item).

        Args:
            resource: Which collection to list (see the enum of allowed values) —
                e.g. ``cameras``, ``sensors``, ``lights``, ``nvrs``.
        """
        c = client()
        try:
            return await c.get(_LIST[resource])
        finally:
            await c.aclose()

    @mcp.tool()
    async def protect_get(resource: GetResource, device_id: str) -> Any:
        """Get a single Protect resource by id.

        Args:
            resource: Which resource type to fetch (see the enum). Use
                ``camera_rtsps_stream`` to get a camera's RTSPS stream URLs
                (addresses/metadata, not video bytes).
            device_id: The resource's id (from the matching ``protect_list``).
        """
        c = client()
        try:
            return await c.get(_GET[resource].format(id=device_id))
        finally:
            await c.aclose()
