"""
Application Configuration
Loads settings from environment variables and provides sensible fallbacks for SAMPLE_MODE.
"""

from __future__ import annotations

import os
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load .env if present
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


class Settings(BaseModel):
    # App & Server
    port: int = Field(default_factory=lambda: int(os.environ.get("PORT", "8000")))
    host: str = "0.0.0.0"
    debug: bool = Field(default_factory=lambda: os.environ.get("DEBUG", "false").lower() in ("1", "true", "yes"))

    # Mode: Sample vs Live
    # SAMPLE_MODE is enabled if explicitly requested OR if external credentials are missing
    sample_mode_env: bool = Field(
        default_factory=lambda: os.environ.get("SAMPLE_MODE", "false").lower() in ("1", "true", "yes")
    )

    # Zetaris (Data Layer)
    zetaris_rest_url: str = Field(default_factory=lambda: os.environ.get("ZETARIS_REST_URL", "http://localhost:8888/api/v1.0"))
    zetaris_org_id: str = Field(default_factory=lambda: os.environ.get("ZETARIS_ORG_ID", "1"))
    zetaris_api_key: str = Field(default_factory=lambda: os.environ.get("ZETARIS_API_KEY", ""))
    zetaris_base_url: str = Field(default_factory=lambda: os.environ.get("ZETARIS_BASE_URL", "http://localhost:3000"))

    # Model / LLM (Power Layer via Meterless)
    model_base_url: str = Field(default_factory=lambda: os.environ.get("MODEL_BASE_URL", "http://127.0.0.1:8088/v1"))
    model_api_key: str = Field(default_factory=lambda: os.environ.get("MODEL_API_KEY", ""))
    model_name: str = Field(default_factory=lambda: os.environ.get("NEMOTRON_MODEL", "meterless/auto"))

    # Provider selection: "meterless" (Meterless Runtime, the primary provider), "openai_compatible"
    # (MODEL_* above) or "none" (rules only). Empty = meterless. A run can override it (options.provider).
    llm_provider: str = Field(default_factory=lambda: os.environ.get("LLM_PROVIDER", "").strip().lower())

    # Meterless Runtime provider (contract v4). Base URL and token are normally saved by
    # scripts/meterless.py into provider_settings_file; these env vars are fallbacks.
    meterless_base_url: str = Field(default_factory=lambda: os.environ.get("METERLESS_BASE_URL", ""))
    meterless_runtime_token: str = Field(default_factory=lambda: os.environ.get("METERLESS_RUNTIME_TOKEN", ""))
    meterless_state_dir: str = Field(default_factory=lambda: os.environ.get("METERLESS_STATE_DIR", ""))
    meterless_model: str = Field(default_factory=lambda: os.environ.get("METERLESS_MODEL", "meterless/auto"))
    provider_settings_file: Path = Field(
        default_factory=lambda: Path(os.environ.get("PROVIDER_SETTINGS_FILE", str(ROOT_DIR / "data" / "provider_settings.json")))
    )

    # Safety, Timeouts & Limits
    sql_timeout_seconds: int = Field(default_factory=lambda: int(os.environ.get("SOURCE_TIMEOUT_SECONDS", "3")))
    model_timeout_seconds: int = Field(default_factory=lambda: int(os.environ.get("MODEL_TIMEOUT_SECONDS", "60")))
    max_sql_limit: int = 1000
    default_sql_limit: int = 200
    max_revision_cycles: int = 2

    # Paths
    logs_dir: Path = ROOT_DIR / "logs"
    data_dir: Path = ROOT_DIR / "data"

    # World Model (shared agent state, append-only SQLite event log)
    world_model_db: Path = Field(
        default_factory=lambda: Path(os.environ.get("WORLD_MODEL_DB", str(ROOT_DIR / "data" / "world_model.db")))
    )

    def is_zetaris_configured(self) -> bool:
        return bool(self.zetaris_rest_url and self.zetaris_org_id and self.zetaris_api_key)

    def is_model_configured(self) -> bool:
        return bool(self.model_base_url and self.model_api_key)


settings = Settings()
