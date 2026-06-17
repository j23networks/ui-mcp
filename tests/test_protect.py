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


async def test_protect_registers_consolidated_surface():
    m = build_server(_settings())
    tools = {t.name: t for t in await m.list_tools()}
    assert set(tools) == {"protect_get_meta_info", "protect_list", "protect_get"}
    list_enum = tools["protect_list"].inputSchema["properties"]["resource"]["enum"]
    get_enum = tools["protect_get"].inputSchema["properties"]["resource"]["enum"]
    for r in ("cameras", "sensors", "lights", "nvrs"):
        assert r in list_enum
    for r in ("camera", "sensor", "camera_rtsps_stream"):
        assert r in get_enum
    # media-bytes / stream / proxy resources stay out
    assert "snapshot" not in get_enum and "files" not in list_enum


@respx.mock
async def test_protect_list_returns_plain_array():
    route = respx.get(f"{BASE}{PATH}/cameras").mock(
        return_value=httpx.Response(200, json=[{"id": "c1"}, {"id": "c2"}])
    )
    m = build_server(_settings())
    await m.call_tool("protect_list", {"resource": "cameras"})
    assert route.called


@respx.mock
async def test_protect_get_by_id_path():
    route = respx.get(f"{BASE}{PATH}/cameras/CAM1").mock(
        return_value=httpx.Response(200, json={"id": "CAM1"})
    )
    m = build_server(_settings())
    await m.call_tool("protect_get", {"resource": "camera", "device_id": "CAM1"})
    assert route.called
    assert route.calls.last.request.headers["X-API-KEY"] == "k"


@respx.mock
async def test_protect_get_camera_rtsps_stream_subpath():
    route = respx.get(f"{BASE}{PATH}/cameras/CAM1/rtsps-stream").mock(
        return_value=httpx.Response(200, json={"rtspsUrl": "rtsps://x"})
    )
    m = build_server(_settings())
    await m.call_tool("protect_get", {"resource": "camera_rtsps_stream", "device_id": "CAM1"})
    assert route.called
