"""UniFi Network Integration API — read-only tools (Phases 1 & 1B).

Local controller API, base ``https://<console>/proxy/network/integration/v1``,
auth via ``X-API-KEY``.

- **Phase 1** hand-wires the core read tools (info, sites, devices, clients,
  vouchers).
- **Phase 1B** adds read-only coverage of the rest of the API (networks, WiFi,
  firewall, ACL, switching, DNS, traffic-matching, VPN, WANs, RADIUS, DPI, …) via
  declarative tables, since they share a few signature shapes.

Mutating endpoints (create/update/delete, device/client actions) are intentionally
deferred. The full endpoint inventory — reads and writes — lives in
``docs/network_api_catalog.json`` for wiring those later.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..config import Settings
from ..http import UbiquitiClient

API_PATH = "/proxy/network/integration/v1"


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
    async def network_list_sites() -> Any:
        """List the local sites managed by this UniFi Network console.

        Returns site id and metadata. Most other Network tools require a ``site_id``
        from this list.
        """
        c = client()
        try:
            return await c.get_collection("/sites")
        finally:
            await c.aclose()

    @mcp.tool()
    async def network_list_devices(site_id: str, max_items: int = 200) -> Any:
        """List UniFi devices (gateways, switches, access points) adopted in a site.

        Args:
            site_id: Site id from ``network_list_sites``.
            max_items: Cap on devices returned (avoids flooding context on large fleets).
        """
        c = client()
        try:
            return await c.get_collection(f"/sites/{site_id}/devices", max_items=max_items)
        finally:
            await c.aclose()

    @mcp.tool()
    async def network_get_device(site_id: str, device_id: str) -> Any:
        """Get full metadata for a single device in a site.

        Args:
            site_id: Site id from ``network_list_sites``.
            device_id: Device id from ``network_list_devices``.
        """
        c = client()
        try:
            return await c.get(f"/sites/{site_id}/devices/{device_id}")
        finally:
            await c.aclose()

    @mcp.tool()
    async def network_get_device_stats(site_id: str, device_id: str) -> Any:
        """Get the latest statistics/metrics for a device (uptime, load, throughput).

        Args:
            site_id: Site id from ``network_list_sites``.
            device_id: Device id from ``network_list_devices``.
        """
        c = client()
        try:
            return await c.get(f"/sites/{site_id}/devices/{device_id}/statistics/latest")
        finally:
            await c.aclose()

    @mcp.tool()
    async def network_list_clients(site_id: str, max_items: int = 200) -> Any:
        """List clients currently connected to a site's network.

        Args:
            site_id: Site id from ``network_list_sites``.
            max_items: Cap on clients returned (avoids flooding context).
        """
        c = client()
        try:
            return await c.get_collection(f"/sites/{site_id}/clients", max_items=max_items)
        finally:
            await c.aclose()

    @mcp.tool()
    async def network_get_client(site_id: str, client_id: str) -> Any:
        """Get details for a specific connected client.

        Args:
            site_id: Site id from ``network_list_sites``.
            client_id: Client id from ``network_list_clients``.
        """
        c = client()
        try:
            return await c.get(f"/sites/{site_id}/clients/{client_id}")
        finally:
            await c.aclose()

    @mcp.tool()
    async def network_list_vouchers(site_id: str, max_items: int = 200) -> Any:
        """List hotspot vouchers for a site.

        Args:
            site_id: Site id from ``network_list_sites``.
            max_items: Cap on vouchers returned.
        """
        c = client()
        try:
            return await c.get_collection(
                f"/sites/{site_id}/hotspot/vouchers", max_items=max_items
            )
        finally:
            await c.aclose()

    # --------------------------------------------------------------------- #
    # Phase 1B — read-only coverage of the remaining Network endpoints.
    # Driven by declarative tables grouped by signature shape, so adding an
    # endpoint is a one-line table entry rather than a new function. Paths are
    # relative to API_PATH (which already ends in /v1). See
    # docs/network_api_catalog.json for the full inventory incl. write ops.
    # --------------------------------------------------------------------- #

    def _account_list(path: str):
        async def tool(max_items: int = 200) -> Any:
            c = client()
            try:
                return await c.get_collection(path, max_items=max_items)
            finally:
                await c.aclose()

        return tool

    def _site_list(path: str):
        async def tool(site_id: str, max_items: int = 200) -> Any:
            c = client()
            try:
                return await c.get_collection(
                    path.format(site_id=site_id), max_items=max_items
                )
            finally:
                await c.aclose()

        return tool

    def _site_get(path: str):
        async def tool(site_id: str) -> Any:
            c = client()
            try:
                return await c.get(path.format(site_id=site_id))
            finally:
                await c.aclose()

        return tool

    def _resource_get(path: str):
        async def tool(site_id: str, resource_id: str) -> Any:
            c = client()
            try:
                return await c.get(
                    path.format(site_id=site_id, resource_id=resource_id)
                )
            finally:
                await c.aclose()

        return tool

    # name, path (relative to /v1), description
    account_lists = [
        ("network_list_pending_devices", "/pending-devices",
         "List devices pending adoption (seen but not yet adopted) across the account."),
        ("network_list_countries", "/countries",
         "List the country codes supported by the Network API."),
        ("network_list_dpi_applications", "/dpi/applications",
         "List DPI (deep packet inspection) applications known to the controller."),
        ("network_list_dpi_categories", "/dpi/categories",
         "List DPI application categories."),
    ]
    site_lists = [
        ("network_list_networks", "/sites/{site_id}/networks",
         "List networks (LANs/VLANs) in a site. site_id from network_list_sites."),
        ("network_list_wifi_broadcasts", "/sites/{site_id}/wifi/broadcasts",
         "List WiFi broadcasts (SSIDs) in a site. site_id from network_list_sites."),
        ("network_list_firewall_zones", "/sites/{site_id}/firewall/zones",
         "List firewall zones in a site."),
        ("network_list_firewall_policies", "/sites/{site_id}/firewall/policies",
         "List firewall policies in a site."),
        ("network_list_acl_rules", "/sites/{site_id}/acl-rules",
         "List access-control (ACL) rules in a site."),
        ("network_list_switch_stacks", "/sites/{site_id}/switching/switch-stacks",
         "List switch stacks in a site."),
        ("network_list_mclag_domains", "/sites/{site_id}/switching/mc-lag-domains",
         "List MC-LAG domains in a site."),
        ("network_list_lags", "/sites/{site_id}/switching/lags",
         "List link-aggregation groups (LAGs) in a site."),
        ("network_list_dns_policies", "/sites/{site_id}/dns/policies",
         "List DNS policies in a site."),
        ("network_list_traffic_matching_lists", "/sites/{site_id}/traffic-matching-lists",
         "List traffic-matching lists in a site."),
        ("network_list_radius_profiles", "/sites/{site_id}/radius/profiles",
         "List RADIUS profiles in a site."),
        ("network_list_vpn_servers", "/sites/{site_id}/vpn/servers",
         "List VPN servers configured in a site."),
        ("network_list_vpn_site_to_site_tunnels", "/sites/{site_id}/vpn/site-to-site-tunnels",
         "List site-to-site VPN tunnels in a site."),
        ("network_list_wans", "/sites/{site_id}/wans",
         "List WAN connections in a site."),
        ("network_list_device_tags", "/sites/{site_id}/device-tags",
         "List device tags defined in a site."),
    ]
    site_gets = [
        ("network_get_firewall_policy_ordering", "/sites/{site_id}/firewall/policies/ordering",
         "Get the user-defined evaluation order of firewall policies for a site."),
        ("network_get_acl_rule_ordering", "/sites/{site_id}/acl-rules/ordering",
         "Get the user-defined evaluation order of ACL rules for a site."),
    ]
    resource_gets = [
        ("network_get_network", "/sites/{site_id}/networks/{resource_id}",
         "Get one network. resource_id is a network id from network_list_networks."),
        ("network_get_network_references", "/sites/{site_id}/networks/{resource_id}/references",
         "Get objects referencing a network. resource_id is a network id."),
        ("network_get_wifi_broadcast", "/sites/{site_id}/wifi/broadcasts/{resource_id}",
         "Get one WiFi broadcast. resource_id from network_list_wifi_broadcasts."),
        ("network_get_firewall_zone", "/sites/{site_id}/firewall/zones/{resource_id}",
         "Get one firewall zone. resource_id from network_list_firewall_zones."),
        ("network_get_firewall_policy", "/sites/{site_id}/firewall/policies/{resource_id}",
         "Get one firewall policy. resource_id from network_list_firewall_policies."),
        ("network_get_acl_rule", "/sites/{site_id}/acl-rules/{resource_id}",
         "Get one ACL rule. resource_id from network_list_acl_rules."),
        ("network_get_switch_stack", "/sites/{site_id}/switching/switch-stacks/{resource_id}",
         "Get one switch stack. resource_id from network_list_switch_stacks."),
        ("network_get_mclag_domain", "/sites/{site_id}/switching/mc-lag-domains/{resource_id}",
         "Get one MC-LAG domain. resource_id from network_list_mclag_domains."),
        ("network_get_lag", "/sites/{site_id}/switching/lags/{resource_id}",
         "Get one LAG. resource_id from network_list_lags."),
        ("network_get_dns_policy", "/sites/{site_id}/dns/policies/{resource_id}",
         "Get one DNS policy. resource_id from network_list_dns_policies."),
        ("network_get_traffic_matching_list", "/sites/{site_id}/traffic-matching-lists/{resource_id}",
         "Get one traffic-matching list. resource_id from network_list_traffic_matching_lists."),
        ("network_get_voucher", "/sites/{site_id}/hotspot/vouchers/{resource_id}",
         "Get one hotspot voucher. resource_id is a voucher id from network_list_vouchers."),
    ]

    for _table, _factory in (
        (account_lists, _account_list),
        (site_lists, _site_list),
        (site_gets, _site_get),
        (resource_gets, _resource_get),
    ):
        for _name, _path, _doc in _table:
            _fn = _factory(_path)
            _fn.__name__ = _name
            mcp.tool(name=_name, description=_doc)(_fn)
