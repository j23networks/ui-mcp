# ui-mcp

An [MCP](https://modelcontextprotocol.io) server exposing the Ubiquiti / UniFi APIs as
tools. One server, pluggable per-API modules over a shared HTTP/auth/config core.

**Status:** Phase 1 — read-only **Network** API; Phase 2 — read-only **Site Manager**
API. See [PROJECT_PLAN.md](PROJECT_PLAN.md) for the roadmap (Protect → Mobility).

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

## Network tools (Phase 1, read-only)

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
