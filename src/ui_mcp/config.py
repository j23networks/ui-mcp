"""Configuration for each Ubiquiti API.

Each API is configured independently via env vars (prefix ``UBIQUITI_``). An API is
considered "enabled" only when its API key is present; tools for disabled APIs are
not registered, so a user can run a Network-only server without Site Manager creds.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="UBIQUITI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Network API (local controller) ---
    network_api_key: str | None = None
    network_base_url: str = "https://192.168.1.1"
    network_verify_tls: bool = False

    # --- Site Manager API (cloud) [Phase 2] ---
    site_manager_api_key: str | None = None
    site_manager_base_url: str = "https://api.ui.com"

    # --- Protect API (local NVR) [Phase 3] ---
    protect_api_key: str | None = None
    protect_base_url: str | None = None
    protect_verify_tls: bool = False

    # --- Mobility API (cloud) [Phase 4] ---
    mobility_api_key: str | None = None
    mobility_base_url: str = "https://api.ui.com"

    @property
    def network_enabled(self) -> bool:
        return bool(self.network_api_key)

    @property
    def site_manager_enabled(self) -> bool:
        return bool(self.site_manager_api_key)

    @property
    def protect_enabled(self) -> bool:
        return bool(self.protect_api_key and self.protect_base_url)

    @property
    def mobility_enabled(self) -> bool:
        return bool(self.mobility_api_key)


def load_settings() -> Settings:
    return Settings()
