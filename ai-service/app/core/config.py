from __future__ import annotations

import os
from dataclasses import dataclass


def _get(key: str, default: str = "") -> str:
    value = os.getenv(key, "").strip()
    return value or default


def _get_bool(key: str, default: bool = False) -> bool:
    value = os.getenv(key)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _get_int(key: str, default: int) -> int:
    value = os.getenv(key)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


@dataclass(slots=True)
class Settings:
    app_env: str = _get("APP_ENV", "development")
    api_port: int = _get_int("AI_SERVICE_PORT", 8000)
    postgres_dsn: str = _get(
        "POSTGRES_DSN",
        f"postgresql://{_get('POSTGRES_USER', 'postgres')}:{_get('POSTGRES_PASSWORD', 'postgres')}@"
        f"{_get('POSTGRES_HOST', 'localhost')}:{_get('POSTGRES_PORT', '5432')}/{_get('POSTGRES_DB', 'ai_video')}"
        "?sslmode=disable",
    )
    redis_addr: str = _get("REDIS_ADDR", "localhost:6379")
    redis_password: str = _get("REDIS_PASSWORD", "")
    generation_stream: str = _get("QUEUE_STREAM_GENERATION", "stream.generation")
    generation_consumer_group: str = "generation-workers"
    generation_consumer_name: str = _get("GENERATION_CONSUMER_NAME", "ai-service-worker")
    ai_provider_timeout_seconds: int = _get_int("AI_PROVIDER_TIMEOUT_SECONDS", 60)
    poll_interval_seconds: int = _get_int("AI_PROVIDER_POLL_INTERVAL_SECONDS", 10)
    minio_endpoint: str = _get("MINIO_ENDPOINT", "localhost:9000")
    minio_access_key: str = _get("MINIO_ACCESS_KEY", "minioadmin")
    minio_secret_key: str = _get("MINIO_SECRET_KEY", "minioadmin")
    minio_bucket: str = _get("MINIO_BUCKET", "ai-video")
    minio_use_ssl: bool = _get_bool("MINIO_USE_SSL", False)
    text_provider: str = _get("TEXT_PROVIDER", "openai-compatible")
    text_model: str = _get("TEXT_MODEL", _get("OPENAI_TEXT_MODEL", "gpt-5-mini"))
    openai_base_url: str = _get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    openai_api_key: str = _get("OPENAI_API_KEY")
    openai_video_api_key: str = _get("OPENAI_VIDEO_API_KEY", _get("OPENAI_API_KEY"))
    openai_video_model: str = _get("OPENAI_VIDEO_MODEL", "sora-2")
    minimax_api_key: str = _get("MINIMAX_API_KEY")
    minimax_api_base: str = _get("MINIMAX_API_BASE", "https://api.minimaxi.com")
    minimax_video_model: str = _get("MINIMAX_VIDEO_MODEL", "MiniMax-Hailuo-02")
    runway_api_key: str = _get("RUNWAY_API_KEY")
    runway_api_base: str = _get("RUNWAY_API_BASE", "https://api.dev.runwayml.com")
    runway_video_model: str = _get("RUNWAY_VIDEO_MODEL", "gen4_turbo")
    max_parallel_tasks: int = _get_int("MAX_PARALLEL_VIDEO_TASKS", 3)


settings = Settings()
