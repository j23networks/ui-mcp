"""Tests for the shared HTTP core and the Network module, with mocked HTTP."""

from __future__ import annotations

import httpx
import pytest
import respx

from ubiquiti_mcp.config import Settings
from ubiquiti_mcp.http import UbiquitiAPIError, UbiquitiClient

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
