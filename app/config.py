"""Application configuration (P1-T01).

Loads runtime settings from environment (prefix ``TESTAGENT_``) with sane
defaults. Owns the location of the per-job isolated workspace root (P1-T03)
and the persistent data dir / SQLite path (P1-T02).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TESTAGENT_", env_file=".env", extra="ignore"
    )

    app_name: str = "TestAgent Lab — 判卷场"
    app_version: str = "0.1.0"

    # Root for per-job isolated workspaces (P1-T03).
    workspace_root: Path = Path("./var/workspace")
    # Root for persistent data: SQLite db, log index (P1-T02).
    data_dir: Path = Path("./var/data")

    @property
    def db_path(self) -> Path:
        return self.data_dir / "testagent.db"

    def ensure_dirs(self) -> None:
        """Create runtime directories if missing. Called on app startup."""
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
