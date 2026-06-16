"""FastMCP server wiring. Registers each enabled API module's tools."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .apis import network, protect, site_manager
from .config import Settings, load_settings


def build_server(settings: Settings | None = None) -> FastMCP:
    settings = settings or load_settings()
    mcp = FastMCP("ui-mcp")

    # Each module is inert unless its API key is configured.
    network.register(mcp, settings)  # Phase 1 — Network (local, read-only)
    site_manager.register(mcp, settings)  # Phase 2 — Site Manager (cloud, read-only)
    protect.register(mcp, settings)  # Phase 3 — Protect (local NVR, read-only)

    return mcp
