# ui-mcp

An [MCP](https://modelcontextprotocol.io) server exposing the Ubiquiti / UniFi APIs as
tools. One server, pluggable per-API modules over a shared HTTP/auth/config core.

**Status:** read-only coverage of all four UniFi APIs — **Network** (Phase 1/1B),
**Site Manager** (Phase 2), **Protect** (Phase 3), and **Mobility** (Phase 4). See
[PROJECT_PLAN.md](PROJECT_PLAN.md) for the roadmap and deferred write endpoints.

## Setup

```bash
pip install -e ".[dev]"      # or: uv pip install -e ".[dev]"
cp .env.example .env         # then fill in UBIQUITI_NETWORK_API_KEY + base URL
```

Get a Network API key from the controller UI: **Settings → Integrations → Create API Key**.
Local consoles use self-signed certs, so `UBIQUITI_NETWORK_VERIFY_TLS=false` is the default.

## Run

```bash
ui-mcp                 # stdio transport
```

Each API is enabled only when its API key is set, so you can run a Network-only server
without Site Manager or Protect credentials.

### Register with Claude / an MCP client

```json
{
  "mcpServers": {
    "ubiquiti": {
      "command": "ui-mcp",
      "env": {
        "UBIQUITI_NETWORK_API_KEY": "your-key",
        "UBIQUITI_NETWORK_BASE_URL": "https://192.168.1.1",
        "UBIQUITI_NETWORK_VERIFY_TLS": "false"
      }
    }
  }
}
```

## Network tools (read-only)

The full read surface is exposed through **3 consolidated tools** rather than one
per endpoint, to keep the model's tool list small:

| Tool | Description |
|------|-------------|
| `network_get_info` | Controller version & capabilities |
| `network_list(resource, site_id?, max_items)` | List any collection; `resource` is an enum |
| `network_get(resource, resource_id, site_id)` | Get any single resource by id |

`network_list` resources — **account-level** (no `site_id`): `sites`,
`pending_devices`, `countries`, `dpi_applications`, `dpi_categories`;
**site-level** (require `site_id`): `devices`, `clients`, `vouchers`, `networks`,
`wifi_broadcasts`, `firewall_zones`, `firewall_policies`,
`firewall_policy_ordering`, `acl_rules`, `acl_rule_ordering`, `switch_stacks`,
`mclag_domains`, `lags`, `dns_policies`, `traffic_matching_lists`,
`radius_profiles`, `vpn_servers`, `vpn_site_to_site_tunnels`, `wans`,
`device_tags`.

`network_get` resources: `device`, `device_statistics`, `client`, `voucher`,
`network`, `network_references`, `wifi_broadcast`, `firewall_zone`,
`firewall_policy`, `acl_rule`, `switch_stack`, `mclag_domain`, `lag`,
`dns_policy`, `traffic_matching_list`.

The full Network API inventory (reads + the deferred write endpoints) is
catalogued in [docs/network_api_catalog.json](docs/network_api_catalog.json).

## Site Manager tools (Phase 2, read-only)

Cloud API at `https://api.ui.com`. Set `UBIQUITI_SITE_MANAGER_API_KEY` (from
[unifi.ui.com](https://unifi.ui.com) → **Settings → API Keys**) to enable these.

| Tool | Description |
|------|-------------|
| `sitemanager_list_hosts` | Hosts (consoles/gateways) on the account |
| `sitemanager_get_host` | Single host by id |
| `sitemanager_list_sites` | Network sites across all hosts |
| `sitemanager_list_devices` | Devices across the account (optional `host_ids` filter) |
| `sitemanager_get_isp_metrics` | ISP metrics for all sites (`5m`/`1h` interval) |
| `sitemanager_query_isp_metrics` | ISP metrics for specific sites/time ranges |

## Protect tools (Phase 3, read-only)

Local NVR API. Set `UBIQUITI_PROTECT_API_KEY` and `UBIQUITI_PROTECT_BASE_URL`
(e.g. `https://192.168.1.1`) to enable. Local NVRs use self-signed certs, so
`UBIQUITI_PROTECT_VERIFY_TLS=false` is the default.

**3 consolidated tools:**

| Tool | Description |
|------|-------------|
| `protect_get_meta_info` | Protect app/NVR meta info |
| `protect_list(resource)` | List a collection; `resource` enum: cameras, sensors, lights, chimes, sirens, speakers, viewers, liveviews, bridges, alarm_hubs, fobs, relays, link_stations, arm_profiles, users, ulp_users, nvrs |
| `protect_get(resource, device_id)` | Get one resource by id (incl. `camera_rtsps_stream` for stream URLs) |

Media-byte endpoints (snapshots, file downloads), WebSocket subscriptions, and
mutations are excluded; the full Protect API inventory is catalogued in
[docs/protect_api_catalog.json](docs/protect_api_catalog.json).

## Mobility tools (Phase 4, read-only)

Cloud API. Set `UBIQUITI_MOBILITY_API_KEY` (from [unifi.ui.com](https://unifi.ui.com),
scope `read:mobility`) to enable. Resources are workspace-scoped.

**2 consolidated tools:**

| Tool | Description |
|------|-------------|
| `mobility_list(resource, workspace_id?, device_id?)` | List `workspaces`, `workspace_admins`, `devices`, or `device_clients` (ids required per resource) |
| `mobility_get_device(workspace_id, device_id)` | Single device details |

Device write endpoints (update name / network / wireless) are deferred; the full
inventory is in [docs/mobility_api_catalog.json](docs/mobility_api_catalog.json).

> **Note:** add `UBIQUITI_MOBILITY_API_KEY=` (and optionally
> `UBIQUITI_MOBILITY_BASE_URL=https://api.ui.com`) to your `.env`.

## Test

```bash
pytest
```

## Architecture

```
src/ui_mcp/
  config.py        # per-API settings; an API is "enabled" iff its key is set
  http.py          # async client: auth, self-signed TLS, pagination, error norm
  server.py        # FastMCP instance; registers each enabled API module
  apis/network.py  # Phase 1 read-only tools
                   # apis/site_manager.py, apis/protect.py land in later phases
```

Adding an API is a new `apis/<name>.py` with a `register(mcp, settings)` function and
one line in `server.py`.
