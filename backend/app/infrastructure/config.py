from __future__ import annotations

from pathlib import Path
from uuid import UUID

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    database_url: str = "postgresql+psycopg://fan:fan_dev_password@localhost:5432/fan"
    receipt_storage_dir: Path = Path("../storage/receipts")
    dev_user_id: UUID = UUID("00000000-0000-4000-8000-000000000001")

    receipt_parser_provider: str = "fake"

    vllm_base_url: str = "http://127.0.0.1:8001/v1"
    vllm_api_key: str = "local-dev-key"
    vllm_model: str = "local-receipt-parser"
    vllm_timeout_seconds: float = 60.0
    vllm_temperature: float = 0.0
    vllm_max_tokens: int = 1200

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


def get_settings() -> Settings:
    return Settings()
