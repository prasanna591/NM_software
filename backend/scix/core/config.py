"""Application configuration."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]
PROFILES_DIR = Path(os.environ.get("SCIX_PROFILES_DIR", REPO_ROOT / "profiles"))
STORAGE_DIR = Path(os.environ.get("SCIX_STORAGE_DIR", REPO_ROOT / ".scix-storage"))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SCIX_", env_file=".env", extra="ignore")

    app_name: str = "SCIX Scientific Research Platform"
    environment: str = "development"
    debug: bool = False
    # S1 L6 brand vs S2 "SCIX". See docs/10-open-questions.md Q2 -- both are
    # configurable so an institution can override the display brand at Stage 4.
    product_name: str = "NM Scientific Research Studio"
    platform_name: str = "SCIX"
    api_prefix: str = "/api"
    app_version: str = "1.4.0"

    database_url: str = "postgresql+psycopg://scix:scix@localhost:5433/scix"
    sql_echo: bool = False

    # ADR 0001: cell values are Parquet in a content store. Local filesystem in
    # development; S3/MinIO in production.
    storage_dir: Path = STORAGE_DIR
    storage_backend: str = "local"

    # S2 3.9 / ADR 0003: 600 DPI is the near-universal journal requirement.
    default_dpi: int = 600
    default_figure_width_mm: float = 85.0
    default_figure_height_mm: float = 65.0
    default_significance_level: float = 0.05

    max_upload_bytes: int = 512 * 1024 * 1024  # Q9 -- unspecified in source; chosen here

    cors_origins: list[str] = ["http://localhost:3000"]

    profiles_dir: Path = PROFILES_DIR


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    return settings
