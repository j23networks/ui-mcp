"""UniFi Network Integration API — read-only tools (consolidated).

Local controller API, base ``https://<console>/proxy/network/integration/v1``,
auth via ``X-API-KEY``.

Rather than one tool per endpoint, the read surface is exposed through three
tools driven by a resource registry:

- ``network_get_info`` — controller app info (a true singleton).
- ``network_list(resource, ...)`` — any collection endpoint, selected by a
  ``resource`` enum (account-level resources ignore ``site_id``; site-level ones
  require it).
- ``network_get(resource, resource_id, site_id)`` — any single resource by id.

This keeps the model's tool list small while covering the same endpoints. The
full API inventory, including the deferred write endpoints, is in
``docs/network_api_catalog.json``.

Note: this module intentionally avoids ``from __future__ import annotations`` so
the dynamically-built ``Literal`` enums below are real annotation objects that
FastMCP can introspect into JSON-schema enums.
"""

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from ..config import Settings
from ..http import UbiquitiClient

API_PATH = "/proxy/network/integration/v1"

# resource key -> (path relative to API_PATH, level). "account" resources are not
# scoped to a site; "site" resources require a site_id (from resource="sites").
_LIST: dict[str, tuple[str, str]] = {
    "sites": ("/sites", "account"),
    "pending_devices": ("/pending-devices", "account"),
    "countries": ("/countries", "account"),
    "dpi_applications": ("/dpi/applications", "account"),
    "dpi_categories": ("/dpi/categories", "account"),
    "devices": ("/sites/{site_id}/devices", "site"),
    "clients": ("/sites/{site_id}/clients", "site"),
    "vouchers": ("/sites/{site_id}/hotspot/vouchers", "site"),
    "networks": ("/sites/{site_id}/networks", "site"),
    "wifi_broadcasts": ("/sites/{site_id}/wifi/broadcasts", "site"),
    "firewall_zones": ("/sites/{site_id}/firewall/zones", "site"),
    "firewall_policies": ("/sites/{site_id}/firewall/policies", "site"),
    "firewall_policy_ordering": ("/sites/{site_id}/firewall/policies/ordering", "site"),
    "acl_rules": ("/sites/{site_id}/acl-rules", "site"),
    "acl_rule_ordering": ("/sites/{site_id}/acl-rules/ordering", "site"),
    "switch_stacks": ("/sites/{site_id}/switching/switch-stacks", "site"),
    "mclag_domains": ("/sites/{site_id}/switching/mc-lag-domains", "site"),
    "lags": ("/sites/{site_id}/switching/lags", "site"),
    "dns_policies": ("/sites/{site_id}/dns/policies", "site"),
    "traffic_matching_lists": ("/sites/{site_id}/traffic-matching-lists", "site"),
    "radius_profiles": ("/sites/{site_id}/radius/profiles", "site"),
    "vpn_servers": ("/sites/{site_id}/vpn/servers", "site"),
    "vpn_site_to_site_tunnels": ("/sites/{site_id}/vpn/site-to-site-tunnels", "site"),
    "wans": ("/sites/{site_id}/wans", "site"),
    "device_tags": ("/sites/{site_id}/device-tags", "site"),
}

# resource key -> path relative to API_PATH (all site-scoped, take a resource id)
_GET: dict[str, str] = {
    "device": "/sites/{site_id}/devices/{id}",
    "device_statistics": "/sites/{site_id}/devices/{id}/statistics/latest",
    "client": "/sites/{site_id}/clients/{id}",
    "voucher": "/sites/{site_id}/hotspot/vouchers/{id}",
    "network": "/sites/{site_id}/networks/{id}",
    "network_references": "/sites/{site_id}/networks/{id}/references",
    "wifi_broadcast": "/sites/{site_id}/wifi/broadcasts/{id}",
    "firewall_zone": "/sites/{site_id}/firewall/zones/{id}",
    "firewall_policy": "/sites/{site_id}/firewall/policies/{id}",
    "acl_rule": "/sites/{site_id}/acl-rules/{id}",
    "switch_stack": "/sites/{site_id}/switching/switch-stacks/{id}",
    "mclag_domain": "/sites/{site_id}/switching/mc-lag-domains/{id}",
    "lag": "/sites/{site_id}/switching/lags/{id}",
    "dns_policy": "/sites/{site_id}/dns/policies/{id}",
    "traffic_matching_list": "/sites/{site_id}/traffic-matching-lists/{id}",
}

# Build Literal enums from the registries so the allowed values surface in each
# tool's JSON schema (and can't drift from the registry).
ListResource = Literal[tuple(_LIST)]  # type: ignore[valid-type]
GetResource = Literal[tuple(_GET)]  # type: ignore[valid-type]

_ACCOUNT_RESOURCES = sorted(k for k, (_, lvl) in _LIST.items() if lvl == "account")


def register(mcp: FastMCP, settings: Settings) -> None:
    if not settings.network_enabled:
        return

    def client() -> UbiquitiClient:
        return UbiquitiClient(
            settings.network_base_url,
            settings.network_api_key,  # type: ignore[arg-type]
            verify_tls=settings.network_verify_tls,
            api_path=API_PATH,
        )

    @mcp.tool()
    async def network_get_info() -> Any:
        """Get the UniFi Network controller's application info (version, capabilities).

        Use this first to confirm connectivity and the API version the console exposes.
        """
        c = client()
        try:
            return await c.get("/info")
        finally:
            await c.aclose()

    @mcp.tool()
    async def network_list(
        resource: ListResource, site_id: str | None = None, max_items: int = 200
    ) -> Any:
        """List a Network resource collection.

        Account-level resources (``sites``, ``pending_devices``, ``countries``,
        ``dpi_applications``, ``dpi_categories``) ignore ``site_id``. All other
        resources are site-scoped and require ``site_id`` — get one from
        ``network_list`` with ``resource="sites"``.

        Args:
            resource: Which collection to list (see the enum of allowed values).
            site_id: Site id; required for site-level resources.
            max_items: Cap on items returned (follows pagination up to this many).
        """
        path, level = _LIST[resource]
        if level == "site" and not site_id:
            raise ValueError(
                f"resource '{resource}' is site-scoped and requires site_id "
                f"(account-level resources: {', '.join(_ACCOUNT_RESOURCES)})"
            )
        target = path.format(site_id=site_id) if level == "site" else path
        c = client()
        try:
            return await c.get_collection(target, max_items=max_items)
        finally:
            await c.aclose()

    @mcp.tool()
    async def network_get(resource: GetResource, resource_id: str, site_id: str) -> Any:
        """Get a single Network resource by id, within a site.

        Args:
            resource: Which resource type to fetch (see the enum of allowed values).
            resource_id: The id of the resource (e.g. a device/network/policy id
                from the corresponding ``network_list`` call). For
                ``network_references`` and ``device_statistics`` it's the network
                / device id respectively.
            site_id: Site id from ``network_list`` with ``resource="sites"``.
        """
        c = client()
        try:
            return await c.get(_GET[resource].format(site_id=site_id, id=resource_id))
        finally:
            await c.aclose()
