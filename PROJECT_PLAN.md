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
| **Mobility** | — | — | — | **No public developer API found (2026-06).** Blocked pending UI publishing one. Confirm product. |

## Phases

- **Phase 0 — Core scaffolding** ✅ *(this commit)*
  MCP skeleton, multi-API config/secrets, shared async HTTP client (auth injection,
  pagination unwrap, error normalization, self-signed TLS handling).

- **Phase 1 — Network API (read-only)** 🚧 *(this commit)*
  Tools: app info, list sites, list/get devices, device stats, list/get clients,
  list vouchers. Mutations (device/client actions, voucher create/delete) deferred.

- **Phase 2 — Site Manager** ⬜
  Cloud auth, hosts/sites/devices/ISP metrics. Read-only. Reuses core.
  Note: a mature read-only Site Manager MCP already exists (`us-all/unifi-mcp-server`) —
  evaluate fork vs. build before starting.

- **Phase 3 — Protect** ⬜
  Cameras, events, recordings, sensors. Surface metadata + URLs, not media bytes.

- **Phase 4 — Mobility** ⬜ *(blocked)*
  Spike first: confirm a public API exists and is reachable.

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
