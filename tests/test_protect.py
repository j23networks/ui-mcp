"""Tests for the Protect module: registration surface + tool routing (mocked HTTP)."""

from __future__ import annotations

import httpx
import respx

from ui_mcp.config import Settings
from ui_mcp.server import build_server

BASE = "https://nvr.test"
PATH = "/proxy/protect/integration/v1"


def _settings():
    return Settings(
        network_api_key=None,
        site_manager_api_key=None,
        protect_api_key="k",
        protect_base_url=BASE,
        protect_verify_tls=False,
    )


def test_protect_enabled_requires_key_and_base_url():
    assert Settings(protect_api_key="k", protect_base_url=None).protect_enabled is False
    assert Settings(protect_api_key=None, protect_base_url=BASE).protect_enabled is False
    assert Settings(protect_api_key="k", protect_base_url=BASE).protect_enabled is True


async def test_protect_registers_readonly_surface():
    m = build_server(_settings())
    names = {t.name for t in await m.list_tools()}
    assert len(names) == 34
    for n in ("protect_list_cameras", "protect_get_camera", "protect_get_camera_rtsps_stream",
              "protect_list_sensors", "protect_get_meta_info"):
        assert n in names
    # media-bytes / stream / proxy / mutations stay out
    assert not any(
        x in names
        for x in (
            "protect_get_camera_snapshot",
            "protect_subscribe_events",
            "protect_connector_get",
            "protect_patch_camera",
        )
    )


@respx.mock
async def test_protect_list_returns_plain_array():
    route = respx.get(f"{BASE}{PATH}/cameras").mock(
        return_value=httpx.Response(200, json=[{"id": "c1"}, {"id": "c2"}])
    )
    m = build_server(_settings())
    await m.call_tool("protect_list_cameras", {})
    assert route.called


@respx.mock
async def test_protect_get_by_id_path():
    route = respx.get(f"{BASE}{PATH}/cameras/CAM1").mock(
        return_value=httpx.Response(200, json={"id": "CAM1"})
    )
    m = build_server(_settings())
    await m.call_tool("protect_get_camera", {"device_id": "CAM1"})
    assert route.called
    assert route.calls.last.request.headers["X-API-KEY"] == "k"
