# ubiquiti-mcp

An [MCP](https://modelcontextprotocol.io) server exposing the Ubiquiti / UniFi APIs as
tools. One server, pluggable per-API modules over a shared HTTP/auth/config core.

**Status:** Phase 1 — read-only **Network** API. See [PROJECT_PLAN.md](PROJECT_PLAN.md)
for the roadmap (Site Manager → Protect → Mobility).

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

## Test

```bash
pytest
```

## Architecture

```
src/ubiquiti_mcp/
  config.py        # per-API settings; an API is "enabled" iff its key is set
  http.py          # async client: auth, self-signed TLS, pagination, error norm
  server.py        # FastMCP instance; registers each enabled API module
  apis/network.py  # Phase 1 read-only tools
                   # apis/site_manager.py, apis/protect.py land in later phases
```

Adding an API is a new `apis/<name>.py` with a `register(mcp, settings)` function and
one line in `server.py`.
