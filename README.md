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

**Phase 1 — core:**

| Tool | Description |
|------|-------------|
| `network_get_info` | Controller version & capabilities |
| `network_list_sites` | Local sites (source of `site_id`) |
| `network_list_devices` | Devices in a site |
| `network_get_device` | Single device metadata |
| `network_get_device_stats` | Latest device metrics |
| `network_list_clients` | Connected clients in a site |
| `network_get_client` | Single client details |
| `network_list_vouchers` | Hotspot vouchers in a site |

**Phase 1B — full read-only coverage (33 more tools):** networks (+references),
WiFi broadcasts, firewall zones/policies (+ordering), ACL rules (+ordering),
switching (switch stacks, MC-LAG domains, LAGs), DNS policies, traffic-matching
lists, VPN servers & site-to-site tunnels, WANs, RADIUS profiles, DPI
apps/categories, device tags, pending devices, countries, and voucher detail —
as `network_list_*` / `network_get_*` tools. The full Network API inventory
(reads + the deferred write endpoints) is catalogued in
[docs/network_api_catalog.json](docs/network_api_catalog.json).

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

34 read tools — `protect_list_*` and `protect_get_*` — covering cameras, sensors,
lights, chimes, sirens, speakers, viewers, liveviews, bridges, alarm-hubs, fobs,
relays, link-stations, users, ULP users, arm profiles, NVRs, and meta info, plus
`protect_get_camera_rtsps_stream` (stream URLs, not video). Media-byte endpoints
(snapshots, file downloads), WebSocket subscriptions, and mutations are excluded;
the full Protect API inventory is catalogued in
[docs/protect_api_catalog.json](docs/protect_api_catalog.json).

## Mobility tools (Phase 4, read-only)

Cloud API. Set `UBIQUITI_MOBILITY_API_KEY` (from [unifi.ui.com](https://unifi.ui.com),
scope `read:mobility`) to enable. Resources are workspace-scoped.

| Tool | Description |
|------|-------------|
| `mobility_list_workspaces` | Workspaces on the account (source of `workspace_id`) |
| `mobility_list_workspace_admins` | Admins of a workspace |
| `mobility_list_devices` | Devices in a workspace |
| `mobility_get_device` | Single device details |
| `mobility_list_device_clients` | Clients connected to a device |

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
