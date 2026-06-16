"""FastMCP server wiring. Registers each enabled API module's tools."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .apis import network
from .config import Settings, load_settings


def build_server(settings: Settings | None = None) -> FastMCP:
    settings = settings or load_settings()
    mcp = FastMCP("ubiquiti-mcp")

    # Phase 1 — Network (read-only). Site Manager / Protect modules register here later.
    network.register(mcp, settings)

    return mcp
