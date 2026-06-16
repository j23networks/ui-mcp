"""Tests for the Mobility module: registration, limit/offset paging, routing."""

from __future__ import annotations

import httpx
import respx

from ui_mcp.config import Settings
from ui_mcp.http import UbiquitiClient
from ui_mcp.server import build_server

BASE = "https://api.ui.com"
PATH = "/v1/mobility"


def _settings():
    return Settings(
        network_api_key=None,
        site_manager_api_key=None,
        protect_api_key=None,
        mobility_api_key="k",
    )


def test_mobility_enabled_requires_key():
    assert Settings(mobility_api_key="k").mobility_enabled is True
    assert Settings(mobility_api_key=None).mobility_enabled is False


async def test_mobility_registers_readonly_surface():
    m = build_server(_settings())
    names = {t.name for t in await m.list_tools()}
    assert names == {
        "mobility_list_workspaces",
        "mobility_list_workspace_admins",
        "mobility_list_devices",
        "mobility_get_device",
        "mobility_list_device_clients",
    }
    # write endpoints stay deferred
    assert not any("update" in n for n in names)


@respx.mock
async def test_paged_collection_follows_limit_offset():
    # Two full pages then a short page -> stops.
    route = respx.get(f"{BASE}{PATH}/workspaces/W1/devices")
    route.side_effect = [
        httpx.Response(200, json=[1, 2]),
        httpx.Response(200, json=[3, 4]),
        httpx.Response(200, json=[5]),
    ]
    c = UbiquitiClient(BASE, "k", verify_tls=True, api_path=PATH)
    try:
        items = await c.get_paged_collection("/workspaces/W1/devices", page_size=2)
    finally:
        await c.aclose()
    assert items == [1, 2, 3, 4, 5]
    assert route.call_count == 3
    assert route.calls[1].request.url.params["offset"] == "2"


@respx.mock
async def test_paged_collection_unwraps_data_envelope_and_caps():
    route = respx.get(f"{BASE}{PATH}/workspaces/W1/devices/D1/clients")
    route.side_effect = [
        httpx.Response(200, json={"data": [1, 2, 3]}),
        httpx.Response(200, json={"data": [4, 5, 6]}),
    ]
    c = UbiquitiClient(BASE, "k", verify_tls=True, api_path=PATH)
    try:
        items = await c.get_paged_collection(
            "/workspaces/W1/devices/D1/clients", page_size=3, max_items=4
        )
    finally:
        await c.aclose()
    assert items == [1, 2, 3, 4]


@respx.mock
async def test_mobility_get_device_routing():
    route = respx.get(f"{BASE}{PATH}/workspaces/W1/devices/D1").mock(
        return_value=httpx.Response(200, json={"id": "D1"})
    )
    m = build_server(_settings())
    await m.call_tool("mobility_get_device", {"workspace_id": "W1", "device_id": "D1"})
    assert route.called
    assert route.calls.last.request.headers["X-API-KEY"] == "k"
