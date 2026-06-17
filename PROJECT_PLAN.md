# Ubiquiti MCP Server — Project Plan

An MCP server exposing the Ubiquiti / UniFi APIs as tools. Built in Python on the
official `mcp` SDK (FastMCP). One server, pluggable per-API modules sharing a common
HTTP/auth/config core.

## API landscape

| API | Host / locality | Auth | Base | Notes |
|-----|-----------------|------|------|-------|
| **Network** | Local controller | `X-API-KEY` header | `https://<console>/proxy/network/integration/v1/` | Official, OpenAPI-documented, v9.3+. Self-signed TLS. |
| **Site Manager** | Cloud | `X-API-Key` header | `https://api.ui.com/v1/` | Read-only today (write "coming"). `429` rate limiting. |
| **Protect** | Local NVR | API key | separate base path | Larger, media-heavy, less version-stable. |
| **Mobility** | Cloud | `X-API-Key` header | `https://api.ui.com/v1/mobility/` | **Public API now published (v1.0.0).** Workspaces/devices/clients + device-config writes. Scope-based (`read:mobility`). |

## Phases

- **Phase 0 — Core scaffolding** ✅
  MCP skeleton, multi-API config/secrets, shared async HTTP client (auth injection,
  pagination unwrap, error normalization, self-signed TLS handling).

- **Phase 1 / 1B — Network API (full read-only coverage)** ✅
  Covers the entire read surface — app info, sites, devices (+stats, +pending),
  clients, vouchers, networks (+references), WiFi broadcasts, firewall
  zones/policies (+ordering), ACL rules (+ordering), switching (switch stacks,
  MC-LAG, LAGs), DNS policies, traffic-matching lists, VPN servers & site-to-site
  tunnels, WANs, RADIUS profiles, DPI apps/categories, device tags, countries.

  **Consolidated** into 3 parameterized tools — `network_get_info`,
  `network_list(resource, …)`, `network_get(resource, resource_id, site_id)` —
  driven by a resource registry with `Literal` enums (replacing the original 41
  one-tool-per-endpoint design, to keep the model's tool list small). The complete
  endpoint inventory — all 78 ops, reads **and** the 36 deferred writes
  (create/update/delete, device/client/port actions, Cloud Connector) — is in
  `docs/network_api_catalog.json` so mutations can be wired later without
  re-scraping the docs.

- **Phase 2 — Site Manager (read-only)** ✅
  Cloud API (`https://api.ui.com/v1`, `X-API-KEY`). **Consolidated** into 4 tools:
  `sitemanager_list(resource)` (hosts/sites/devices), `sitemanager_get_host`,
  `sitemanager_get_isp_metrics`, `sitemanager_query_isp_metrics`. Cursor pagination
  (`pageSize`/`nextToken`) and the `{data, httpStatusCode, traceId, nextToken}`
  envelope handled in the shared client. SD-WAN config endpoints deferred (not in
  original scope). Builds on Phase 0 core (added `post` + `get_token_collection`).

- **Phase 3 — Protect (read-only)** ✅
  Local NVR API (`https://<nvr>/proxy/protect/integration/v1`, `X-API-KEY`).
  Covers cameras, sensors, lights, chimes, sirens, speakers, viewers, liveviews,
  bridges, alarm-hubs, fobs, relays, link-stations, users, ulp-users, arm-profiles,
  NVRs, meta info, and camera RTSPS stream URLs. **Consolidated** into 3 tools:
  `protect_get_meta_info`, `protect_list(resource)`, `protect_get(resource,
  device_id)`. Lists return plain JSON arrays. Media bytes (`/snapshot`,
  `/files/{type}`), WebSocket subscriptions (`/subscribe/*`), and the connector
  passthrough are intentionally excluded. Full inventory (78 ops: 37 read +
  41 writes/streams) in `docs/protect_api_catalog.json`.

- **Phase 4 — Mobility (read-only)** ✅
  Cloud API (`https://api.ui.com/v1/mobility`, `X-API-KEY`, scope `read:mobility`).
  Covers workspaces, workspace admins, devices, device, device clients.
  **Consolidated** into 2 tools: `mobility_list(resource, …)` and
  `mobility_get_device(…)`. Workspace-scoped; list resources page by `limit`/
  `offset` (shared client's `get_paged_collection`). The 3 device write endpoints
  (PUT name / network / wireless, scope `write:mobility`) are deferred — see
  `docs/mobility_api_catalog.json` for the full 8-endpoint inventory.

## Effort (one experienced dev)

| Phase | Read-only | + Mutations |
|-------|-----------|-------------|
| 0 Core | 0.5–1 day | — |
| 1 Network | ~2 days | +1–2 days |
| 2 Site Manager | 2–3 days | n/a (API read-only) |
| 3 Protect | 4–6 days | — |
| 4 Mobility | unknown (spike) | — |

**Solid v1 (Network + Site Manager, read-only): ~1–1.5 weeks.**

## Open items
1. Pull the live Network OpenAPI spec from a controller (Settings → Integrations) to
   confirm exact tool count and enable codegen instead of hand-wiring.
2. Confirm what "Mobility" refers to and whether a public API exists.
