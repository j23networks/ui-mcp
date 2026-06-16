"""Tests for the Site Manager cloud API: cursor pagination + error envelope."""

from __future__ import annotations

import httpx
import pytest
import respx

from ui_mcp.config import Settings
from ui_mcp.http import UbiquitiAPIError, UbiquitiClient

BASE = "https://api.ui.com"
PATH = "/v1"


def make_client() -> UbiquitiClient:
    return UbiquitiClient(BASE, "key-abc", verify_tls=True, api_path=PATH)


@respx.mock
async def test_token_collection_follows_next_token():
    route = respx.get(f"{BASE}{PATH}/hosts")
    route.side_effect = [
        httpx.Response(200, json={"data": [1, 2], "httpStatusCode": 200, "nextToken": "tok1"}),
        httpx.Response(200, json={"data": [3], "httpStatusCode": 200, "nextToken": ""}),
    ]
    c = make_client()
    try:
        items = await c.get_token_collection("/hosts", page_size=2)
    finally:
        await c.aclose()
    assert items == [1, 2, 3]
    assert route.call_count == 2
    # First request must not send a nextToken; second must send the cursor.
    assert "nextToken" not in route.calls[0].request.url.params
    assert route.calls[1].request.url.params["nextToken"] == "tok1"


@respx.mock
async def test_token_collection_stops_with_no_next_token():
    respx.get(f"{BASE}{PATH}/sites").mock(
        return_value=httpx.Response(200, json={"data": [1, 2], "httpStatusCode": 200})
    )
    c = make_client()
    try:
        items = await c.get_token_collection("/sites")
    finally:
        await c.aclose()
    assert items == [1, 2]


@respx.mock
async def test_token_collection_respects_max_items():
    route = respx.get(f"{BASE}{PATH}/devices")
    route.side_effect = [
        httpx.Response(200, json={"data": [1, 2, 3], "nextToken": "more"}),
        httpx.Response(200, json={"data": [4, 5, 6], "nextToken": "more2"}),
    ]
    c = make_client()
    try:
        items = await c.get_token_collection("/devices", page_size=3, max_items=4)
    finally:
        await c.aclose()
    assert items == [1, 2, 3, 4]
    assert route.call_count == 2  # stops once max_items reached


@respx.mock
async def test_error_envelope_message_surfaced():
    respx.get(f"{BASE}{PATH}/hosts/x").mock(
        return_value=httpx.Response(
            404, json={"code": "NOT_FOUND", "httpStatusCode": 404, "message": "thing not found"}
        )
    )
    c = make_client()
    try:
        with pytest.raises(UbiquitiAPIError) as exc:
            await c.get("/hosts/x")
    finally:
        await c.aclose()
    assert exc.value.status == 404
    assert "thing not found" in str(exc.value)


@respx.mock
async def test_post_sends_json_body():
    route = respx.post(f"{BASE}{PATH}/isp-metrics/1h/query").mock(
        return_value=httpx.Response(200, json={"data": {"ok": True}, "httpStatusCode": 200})
    )
    c = make_client()
    try:
        env = await c.post("/isp-metrics/1h/query", json={"sites": [{"hostId": "h1"}]})
    finally:
        await c.aclose()
    assert env["data"] == {"ok": True}
    import json as _json

    assert _json.loads(route.calls.last.request.content)["sites"][0]["hostId"] == "h1"


def test_disabled_site_manager_registers_no_tools():
    s = Settings(site_manager_api_key=None)
    assert s.site_manager_enabled is False
