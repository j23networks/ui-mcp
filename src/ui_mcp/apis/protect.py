"""UniFi Protect API — read-only tools (Phase 3).

Local NVR API, base ``https://<nvr>/proxy/protect/integration/v1``, auth via
``X-API-KEY``. Lists return plain JSON arrays and single resources plain objects
(no pagination envelope), so tools just return the parsed JSON.

Scope: **metadata + URLs only**, per the project plan. The following endpoints are
intentionally *not* exposed as read tools:

- ``/cameras/{id}/snapshot`` and ``/files/{fileType}`` — return media bytes.
- ``/subscribe/events`` and ``/subscribe/devices`` — long-lived SSE streams that
  don't fit a request/response tool.
- ``/connector/consoles/{id}/*path`` — a generic cloud-connector passthrough.

``/cameras/{id}/rtsps-stream`` *is* exposed: it returns stream URLs/metadata, not
bytes. All mutating endpoints (PATCH/POST/DELETE: device config, PTZ, siren/speaker
actions, arm-profiles) are deferred; the full inventory is in
``docs/protect_api_catalog.json``.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..config import Settings
from ..http import UbiquitiClient

API_PATH = "/proxy/protect/integration/v1"


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

    def _list(path: str):
        async def tool() -> Any:
            c = client()
            try:
                return await c.get(path)
            finally:
                await c.aclose()

        return tool

    def _by_id(path: str):
        async def tool(device_id: str) -> Any:
            c = client()
            try:
                return await c.get(path.format(id=device_id))
            finally:
                await c.aclose()

        return tool

    # name, path (relative to /v1), description
    lists = [
        ("protect_list_cameras", "/cameras", "List all Protect cameras with full metadata."),
        ("protect_list_sensors", "/sensors", "List all Protect sensors (motion/door/etc.)."),
        ("protect_list_lights", "/lights", "List all Protect lights."),
        ("protect_list_chimes", "/chimes", "List all Protect chimes."),
        ("protect_list_sirens", "/sirens", "List all Protect sirens."),
        ("protect_list_speakers", "/speakers", "List all Protect speakers."),
        ("protect_list_viewers", "/viewers", "List all Protect viewers (display devices)."),
        ("protect_list_liveviews", "/liveviews", "List all configured live views."),
        ("protect_list_bridges", "/bridges", "List all Protect bridges."),
        ("protect_list_alarm_hubs", "/alarm-hubs", "List all alarm hubs."),
        ("protect_list_fobs", "/fobs", "List all key fobs."),
        ("protect_list_relays", "/relays", "List all relays."),
        ("protect_list_link_stations", "/link-stations", "List all link stations."),
        ("protect_list_arm_profiles", "/arm-profiles", "List all arm profiles."),
        ("protect_list_users", "/users", "List Protect users."),
        ("protect_list_ulp_users", "/ulp-users", "List UniFi LocalPortal (ULP) users."),
        ("protect_list_nvrs", "/nvrs", "List the NVR(s) and their system info."),
        ("protect_get_meta_info", "/meta/info", "Get Protect application meta/system info."),
    ]
    by_id = [
        ("protect_get_camera", "/cameras/{id}", "Get one camera. device_id from protect_list_cameras."),
        ("protect_get_sensor", "/sensors/{id}", "Get one sensor. device_id from protect_list_sensors."),
        ("protect_get_light", "/lights/{id}", "Get one light. device_id from protect_list_lights."),
        ("protect_get_chime", "/chimes/{id}", "Get one chime. device_id from protect_list_chimes."),
        ("protect_get_siren", "/sirens/{id}", "Get one siren. device_id from protect_list_sirens."),
        ("protect_get_speaker", "/speakers/{id}", "Get one speaker. device_id from protect_list_speakers."),
        ("protect_get_viewer", "/viewers/{id}", "Get one viewer. device_id from protect_list_viewers."),
        ("protect_get_liveview", "/liveviews/{id}", "Get one live view. device_id from protect_list_liveviews."),
        ("protect_get_bridge", "/bridges/{id}", "Get one bridge. device_id from protect_list_bridges."),
        ("protect_get_alarm_hub", "/alarm-hubs/{id}", "Get one alarm hub. device_id from protect_list_alarm_hubs."),
        ("protect_get_fob", "/fobs/{id}", "Get one key fob. device_id from protect_list_fobs."),
        ("protect_get_relay", "/relays/{id}", "Get one relay. device_id from protect_list_relays."),
        ("protect_get_link_station", "/link-stations/{id}", "Get one link station. device_id from protect_list_link_stations."),
        ("protect_get_user", "/users/{id}", "Get one Protect user. device_id is the user id from protect_list_users."),
        ("protect_get_ulp_user", "/ulp-users/{id}", "Get one ULP user. device_id is the user id from protect_list_ulp_users."),
        ("protect_get_camera_rtsps_stream", "/cameras/{id}/rtsps-stream",
         "Get RTSPS stream URLs/metadata for a camera (stream addresses, not video bytes). device_id from protect_list_cameras."),
    ]

    for _name, _path, _doc in lists:
        _fn = _list(_path)
        _fn.__name__ = _name
        mcp.tool(name=_name, description=_doc)(_fn)
    for _name, _path, _doc in by_id:
        _fn = _by_id(_path)
        _fn.__name__ = _name
        mcp.tool(name=_name, description=_doc)(_fn)
