"""Tests for the shared HTTP core and the Network module, with mocked HTTP."""

from __future__ import annotations

import httpx
import pytest
import respx

from ui_mcp.config import Settings
from ui_mcp.http import UbiquitiAPIError, UbiquitiClient
from ui_mcp.server import build_server

BASE = "https://console.test"
PATH = "/proxy/network/integration/v1"


def make_client() -> UbiquitiClient:
    return UbiquitiClient(BASE, "key-123", verify_tls=False, api_path=PATH)


@respx.mock
async def test_get_collection_follows_pagination():
    route = respx.get(f"{BASE}{PATH}/sites")
    route.side_effect = [
        httpx.Response(200, json={"offset": 0, "limit": 2, "totalCount": 3, "data": [1, 2]}),
        httpx.Response(200, json={"offset": 2, "limit": 2, "totalCount": 3, "data": [3]}),
    ]
    c = make_client()
    try:
        items = await c.get_collection("/sites", limit=2)
    finally:
        await c.aclose()
    assert items == [1, 2, 3]
    assert route.call_count == 2


@respx.mock
async def test_get_collection_respects_max_items():
    respx.get(f"{BASE}{PATH}/clients").mock(
        return_value=httpx.Response(
            200, json={"offset": 0, "limit": 200, "totalCount": 5, "data": [1, 2, 3, 4, 5]}
        )
    )
    c = make_client()
    try:
        items = await c.get_collection("/clients", max_items=2)
    finally:
        await c.aclose()
    assert items == [1, 2]


@respx.mock
async def test_auth_header_sent():
    route = respx.get(f"{BASE}{PATH}/info").mock(return_value=httpx.Response(200, json={"v": 1}))
    c = make_client()
    try:
        await c.get("/info")
    finally:
        await c.aclose()
    assert route.calls.last.request.headers["X-API-KEY"] == "key-123"


@respx.mock
async def test_error_normalization():
    respx.get(f"{BASE}{PATH}/sites").mock(
        return_value=httpx.Response(401, json={"message": "nope"})
    )
    c = make_client()
    try:
        with pytest.raises(UbiquitiAPIError) as exc:
            await c.get("/sites")
    finally:
        await c.aclose()
    assert exc.value.status == 401
    assert "authentication failed" in str(exc.value)


def test_disabled_api_registers_no_tools():
    # No API key -> Network module should be inert.
    s = Settings(network_api_key=None)
    assert s.network_enabled is False


async def test_consolidated_registers_three_tools():
    m = build_server(Settings(network_api_key="k", site_manager_api_key=None))
    names = {t.name for t in await m.list_tools()}
    assert names == {"network_get_info", "network_list", "network_get"}
    # the resource registries cover the full read surface via enums
    tools = {t.name: t for t in await m.list_tools()}
    list_enum = tools["network_list"].inputSchema["properties"]["resource"]["enum"]
    get_enum = tools["network_get"].inputSchema["properties"]["resource"]["enum"]
    for r in ("sites", "devices", "firewall_policies", "acl_rule_ordering", "wans"):
        assert r in list_enum
    for r in ("device", "network", "device_statistics", "network_references"):
        assert r in get_enum


def _net_settings():
    return Settings(
        network_api_key="k",
        network_base_url=BASE,
        network_verify_tls=False,
        site_manager_api_key=None,
    )


@respx.mock
async def test_network_list_routes_site_resource():
    route = respx.get(f"{BASE}{PATH}/sites/S1/networks").mock(
        return_value=httpx.Response(
            200, json={"offset": 0, "limit": 200, "totalCount": 1, "data": [{"id": "n1"}]}
        )
    )
    m = build_server(_net_settings())
    await m.call_tool("network_list", {"resource": "networks", "site_id": "S1"})
    assert route.called


@respx.mock
async def test_network_list_account_resource_ignores_site():
    route = respx.get(f"{BASE}{PATH}/countries").mock(
        return_value=httpx.Response(200, json=["US", "GB"])
    )
    m = build_server(_net_settings())
    await m.call_tool("network_list", {"resource": "countries"})
    assert route.called


@respx.mock
async def test_network_get_routes_with_id():
    route = respx.get(f"{BASE}{PATH}/sites/S1/networks/N1").mock(
        return_value=httpx.Response(200, json={"id": "N1"})
    )
    m = build_server(_net_settings())
    await m.call_tool(
        "network_get", {"resource": "network", "resource_id": "N1", "site_id": "S1"}
    )
    assert route.called
    assert route.calls.last.request.headers["X-API-KEY"] == "k"


async def test_network_list_site_resource_requires_site_id():
    m = build_server(_net_settings())
    # site-scoped resource without site_id should error
    with pytest.raises(Exception, match="site_id"):
        await m.call_tool("network_list", {"resource": "networks"})
