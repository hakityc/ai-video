from __future__ import annotations

import json
import os
from collections import OrderedDict
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from pydantic import BaseModel

from ai_video_control.storage import read_settings_map, upsert_settings_map


KNOWN_SETTINGS_KEYS = [
    "OPENAI_BASE_URL",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "TEXT_MODEL_OPTIONS",
    "OPENAI_IMAGE_MODEL",
    "IMAGE_MODEL_OPTIONS",
    "OPENAI_VIDEO_MODEL",
    "VIDEO_MODEL_OPTIONS",
    "OPENAI_VIDEO_RATIO",
    "OPENAI_VIDEO_DURATION",
    "OPENAI_VIDEO_RESOLUTION",
    "COMFYUI_URL",
    "COGVIDEOX_MODEL_ID",
    "PROVIDER_CONNECTIONS_JSON",
    "ACTIVE_PROVIDER_ID",
]

LOCKED_PROVIDER_ID = "volcengine-ark"
LOCKED_PROVIDER_DEFAULT_MODELS = {
    "text": "doubao-seed-2-0-pro-260215",
    "image": "doubao-seedream-3-0-t2i-250415",
    "video": "doubao-seedance-1-5-pro-251215",
    "local": "",
}


class Settings(BaseModel):
    openai_base_url: Optional[str] = None
    openai_api_key: Optional[str] = None
    openai_model: Optional[str] = None
    text_model_options: Optional[str] = None
    openai_image_model: Optional[str] = None
    image_model_options: Optional[str] = None
    openai_video_model: Optional[str] = None
    video_model_options: Optional[str] = None
    openai_video_ratio: Optional[str] = None
    openai_video_duration: Optional[str] = None
    openai_video_resolution: Optional[str] = None
    comfyui_url: Optional[str] = None
    cogvideox_model_id: Optional[str] = None
    provider_connections_json: Optional[str] = None
    active_provider_id: Optional[str] = None

    def masked(self) -> dict[str, str]:
        return {
            "OPENAI_BASE_URL": self.openai_base_url or "",
            "OPENAI_API_KEY": _mask_secret(self.openai_api_key),
            "OPENAI_MODEL": self.openai_model or "",
            "TEXT_MODEL_OPTIONS": self.text_model_options or "",
            "OPENAI_IMAGE_MODEL": self.openai_image_model or "",
            "IMAGE_MODEL_OPTIONS": self.image_model_options or "",
            "OPENAI_VIDEO_MODEL": self.openai_video_model or "",
            "VIDEO_MODEL_OPTIONS": self.video_model_options or "",
            "OPENAI_VIDEO_RATIO": self.openai_video_ratio or "",
            "OPENAI_VIDEO_DURATION": self.openai_video_duration or "",
            "OPENAI_VIDEO_RESOLUTION": self.openai_video_resolution or "",
            "COMFYUI_URL": self.comfyui_url or "",
            "COGVIDEOX_MODEL_ID": self.cogvideox_model_id or "",
            "PROVIDER_CONNECTIONS_JSON": self.provider_connections_json or "",
            "ACTIVE_PROVIDER_ID": self.active_provider_id or "",
        }

    def raw(self) -> dict[str, str]:
        return {
            "OPENAI_BASE_URL": self.openai_base_url or "",
            "OPENAI_API_KEY": self.openai_api_key or "",
            "OPENAI_MODEL": self.openai_model or "",
            "TEXT_MODEL_OPTIONS": self.text_model_options or "",
            "OPENAI_IMAGE_MODEL": self.openai_image_model or "",
            "IMAGE_MODEL_OPTIONS": self.image_model_options or "",
            "OPENAI_VIDEO_MODEL": self.openai_video_model or "",
            "VIDEO_MODEL_OPTIONS": self.video_model_options or "",
            "OPENAI_VIDEO_RATIO": self.openai_video_ratio or "",
            "OPENAI_VIDEO_DURATION": self.openai_video_duration or "",
            "OPENAI_VIDEO_RESOLUTION": self.openai_video_resolution or "",
            "COMFYUI_URL": self.comfyui_url or "",
            "COGVIDEOX_MODEL_ID": self.cogvideox_model_id or "",
            "PROVIDER_CONNECTIONS_JSON": self.provider_connections_json or "",
            "ACTIVE_PROVIDER_ID": self.active_provider_id or "",
        }


def env_file_path() -> Path:
    return Path.cwd() / ".env"


def _load_env_file() -> None:
    root_env = env_file_path()
    if root_env.exists():
        load_dotenv(root_env, override=False)
    else:
        load_dotenv(override=False)


def _mask_secret(value: Optional[str]) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return value[:4] + "*" * (len(value) - 8) + value[-4:]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    _load_env_file()
    _bootstrap_database_from_env()
    values = _read_combined_settings()
    return Settings(
        openai_base_url=values.get("OPENAI_BASE_URL"),
        openai_api_key=values.get("OPENAI_API_KEY"),
        openai_model=values.get("OPENAI_MODEL"),
        text_model_options=values.get("TEXT_MODEL_OPTIONS"),
        openai_image_model=values.get("OPENAI_IMAGE_MODEL"),
        image_model_options=values.get("IMAGE_MODEL_OPTIONS"),
        openai_video_model=values.get("OPENAI_VIDEO_MODEL"),
        video_model_options=values.get("VIDEO_MODEL_OPTIONS"),
        openai_video_ratio=values.get("OPENAI_VIDEO_RATIO"),
        openai_video_duration=values.get("OPENAI_VIDEO_DURATION"),
        openai_video_resolution=values.get("OPENAI_VIDEO_RESOLUTION"),
        comfyui_url=values.get("COMFYUI_URL"),
        cogvideox_model_id=values.get("COGVIDEOX_MODEL_ID"),
        provider_connections_json=values.get("PROVIDER_CONNECTIONS_JSON"),
        active_provider_id=values.get("ACTIVE_PROVIDER_ID"),
    )


def read_raw_settings() -> dict[str, str]:
    return get_settings().raw()


def update_settings(values: dict[str, str]) -> dict[str, str]:
    normalized = OrderedDict(
        (key, "" if value is None else str(value))
        for key, value in values.items()
    )

    upsert_settings_map(dict(normalized))
    merged = _read_combined_settings()
    merged.update(dict(normalized))
    _write_env_file(merged)

    for key, value in normalized.items():
        os.environ[key] = value

    get_settings.cache_clear()
    return read_raw_settings()


def read_provider_settings() -> dict[str, Any]:
    raw = read_raw_settings()
    providers = _parse_provider_list(raw.get("PROVIDER_CONNECTIONS_JSON", ""))
    if not providers:
        providers = _default_provider_list(raw)
    providers, selected_provider_id = _enforce_locked_provider_mode(providers, raw)

    return {
        "selected_provider_id": selected_provider_id,
        "providers": providers,
    }


def update_provider_settings(selected_provider_id: str, providers: list[dict[str, Any]]) -> dict[str, Any]:
    normalized = [_normalize_provider(item) for item in providers if item.get("name") or item.get("id")]
    if not normalized:
        normalized = _default_provider_list(read_raw_settings())
    raw = read_raw_settings()
    normalized, selected_provider_id = _enforce_locked_provider_mode(normalized, raw)
    selected = next((item for item in normalized if item["id"] == selected_provider_id), normalized[0])

    saved = update_settings(
        {
            "PROVIDER_CONNECTIONS_JSON": json.dumps(normalized, ensure_ascii=False),
            "ACTIVE_PROVIDER_ID": selected_provider_id,
            "OPENAI_BASE_URL": selected.get("base_url", ""),
            "OPENAI_API_KEY": selected.get("api_key", ""),
            "OPENAI_MODEL": selected.get("default_models", {}).get("text", ""),
            "OPENAI_IMAGE_MODEL": selected.get("default_models", {}).get("image", ""),
            "OPENAI_VIDEO_MODEL": selected.get("default_models", {}).get("video", ""),
        }
    )

    return {
        "selected_provider_id": selected_provider_id,
        "providers": normalized,
        "settings": saved,
    }


def _bootstrap_database_from_env() -> None:
    database_values = read_settings_map()
    missing_values = {}
    for key in KNOWN_SETTINGS_KEYS:
        env_value = os.getenv(key)
        if key not in database_values and env_value is not None:
            missing_values[key] = env_value
    if missing_values:
        upsert_settings_map(missing_values)


def _read_combined_settings() -> dict[str, str]:
    database_values = read_settings_map()
    result = {}
    for key in KNOWN_SETTINGS_KEYS:
        result[key] = database_values.get(key, os.getenv(key, ""))
    return result


def _write_env_file(values: dict[str, str]) -> None:
    env_path = env_file_path()
    current_lines = []
    if env_path.exists():
        current_lines = env_path.read_text(encoding="utf-8").splitlines()

    normalized = OrderedDict((key, values.get(key, "")) for key in KNOWN_SETTINGS_KEYS)

    seen = set()
    rendered_lines = []
    for line in current_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            rendered_lines.append(line)
            continue
        key, _sep, _rest = line.partition("=")
        env_key = key.strip()
        if env_key in normalized:
            rendered_lines.append(f'{env_key}="{_escape_env_value(normalized[env_key])}"')
            seen.add(env_key)
        else:
            rendered_lines.append(line)

    for key, value in normalized.items():
        if key not in seen:
            rendered_lines.append(f'{key}="{_escape_env_value(value)}"')

    env_path.write_text("\n".join(rendered_lines).rstrip() + "\n", encoding="utf-8")


def _parse_provider_list(raw_json: str) -> list[dict[str, Any]]:
    if not raw_json.strip():
        return []
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    return [_normalize_provider(item) for item in payload if isinstance(item, dict)]


def _default_provider_list(raw: dict[str, str]) -> list[dict[str, Any]]:
    return [
        _normalize_provider(
            {
                "id": "volcengine-ark",
                "name": "火山方舟",
                "provider_type": "openai-compatible",
                "manual_enabled": bool(raw.get("OPENAI_BASE_URL")),
                "base_url": raw.get("OPENAI_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"),
                "api_key": raw.get("OPENAI_API_KEY", ""),
                "default_models": {
                    "text": raw.get("OPENAI_MODEL", LOCKED_PROVIDER_DEFAULT_MODELS["text"]),
                    "image": raw.get("OPENAI_IMAGE_MODEL", LOCKED_PROVIDER_DEFAULT_MODELS["image"]),
                    "video": raw.get("OPENAI_VIDEO_MODEL", LOCKED_PROVIDER_DEFAULT_MODELS["video"]),
                    "local": "",
                },
                "note": "适合统一接入文案、角色和视频模型。",
            }
        ),
        _normalize_provider(
            {
                "id": "siliconflow",
                "name": "硅基流动",
                "provider_type": "openai-compatible",
                "manual_enabled": False,
                "base_url": "https://api.siliconflow.cn/v1",
                "note": "适合补充模型来源和成本控制。",
            }
        ),
        _normalize_provider(
            {
                "id": "openai-compatible",
                "name": "OpenAI 兼容",
                "provider_type": "openai-compatible",
                "manual_enabled": False,
                "base_url": "https://api.openai.com/v1",
                "note": "适合任意兼容 OpenAI 协议的平台。",
            }
        ),
        _normalize_provider(
            {
                "id": "zynkapi",
                "name": "Zynk API",
                "provider_type": "openai-compatible",
                "manual_enabled": False,
                "base_url": "https://zynkapi.com/v1",
                "default_models": {
                    "text": "deepseek-chat",
                    "image": "dall-e-3",
                    "video": "",
                    "local": "",
                },
                "note": "官方公开为 OpenAI 兼容入口，适合统一接文本和图片模型。",
            }
        ),
        _normalize_provider(
            {
                "id": "bigmodel",
                "name": "智谱开放平台",
                "provider_type": "openai-compatible",
                "manual_enabled": False,
                "base_url": "https://open.bigmodel.cn/api/paas/v4",
                "default_models": {
                    "text": "glm-4-flash",
                    "image": "",
                    "video": "",
                    "local": "",
                },
                "note": "智谱通用 API 网关入口。",
            }
        ),
        _normalize_provider(
            {
                "id": "comfyui-local",
                "name": "ComfyUI",
                "provider_type": "comfyui",
                "manual_enabled": bool(raw.get("COMFYUI_URL")),
                "base_url": raw.get("COMFYUI_URL", "http://127.0.0.1:8188"),
                "note": "本地工作流渲染服务。",
            }
        ),
        _normalize_provider(
            {
                "id": "cogvideox-local",
                "name": "CogVideoX",
                "provider_type": "cogvideox",
                "manual_enabled": bool(raw.get("COGVIDEOX_MODEL_ID")) or not raw.get("PROVIDER_CONNECTIONS_JSON"),
                "default_models": {
                    "text": "",
                    "image": "",
                    "video": "",
                    "local": raw.get("COGVIDEOX_MODEL_ID", "THUDM/CogVideoX-5b-I2V"),
                },
                "note": "本地视频生成模型。",
            }
        ),
    ]


def _normalize_provider(payload: dict[str, Any]) -> dict[str, Any]:
    provider_type = str(payload.get("provider_type") or "custom").strip() or "custom"
    provider_id = str(payload.get("id") or payload.get("name") or "custom-provider").strip()
    default_models = payload.get("default_models")
    if not isinstance(default_models, dict):
        default_models = {}
    text_model = str(payload.get("text_model") or default_models.get("text") or "").strip()
    image_model = str(payload.get("image_model") or default_models.get("image") or "").strip()
    video_model = str(payload.get("video_model") or default_models.get("video") or "").strip()
    local_model = str(payload.get("local_model") or default_models.get("local") or "").strip()
    manual_enabled = bool(payload.get("manual_enabled", payload.get("enabled", True)))
    return {
        "id": provider_id,
        "name": str(payload.get("name") or provider_id).strip(),
        "provider_type": provider_type,
        "manual_enabled": manual_enabled,
        "enabled": manual_enabled,
        "base_url": str(payload.get("base_url") or "").strip(),
        "api_key": str(payload.get("api_key") or "").strip(),
        "default_models": {
            "text": text_model,
            "image": image_model,
            "video": video_model,
            "local": local_model,
        },
        "text_model": text_model,
        "image_model": image_model,
        "video_model": video_model,
        "local_model": local_model,
        "extra_config": str(payload.get("extra_config") or "").strip(),
        "note": str(payload.get("note") or "").strip(),
    }


def _enforce_locked_provider_mode(
    providers: list[dict[str, Any]],
    raw: dict[str, str],
) -> tuple[list[dict[str, Any]], str]:
    normalized = [_normalize_provider(item) for item in providers]
    provider_by_id = {item["id"]: item for item in normalized}
    locked = provider_by_id.get(LOCKED_PROVIDER_ID)
    if locked is None:
        locked = _normalize_provider(
            {
                "id": LOCKED_PROVIDER_ID,
                "name": "火山方舟",
                "provider_type": "openai-compatible",
                "manual_enabled": True,
                "base_url": "https://ark.cn-beijing.volces.com/api/v3",
                "api_key": raw.get("OPENAI_API_KEY", ""),
                "default_models": LOCKED_PROVIDER_DEFAULT_MODELS,
                "note": "单 provider 生产模式下的唯一默认入口。",
            }
        )
        normalized.append(locked)
        provider_by_id[LOCKED_PROVIDER_ID] = locked

    locked["manual_enabled"] = True
    locked["enabled"] = True
    if not str(locked.get("base_url") or "").strip():
        locked["base_url"] = "https://ark.cn-beijing.volces.com/api/v3"
    defaults = dict(locked.get("default_models") or {})
    defaults["text"] = LOCKED_PROVIDER_DEFAULT_MODELS["text"]
    defaults["image"] = LOCKED_PROVIDER_DEFAULT_MODELS["image"]
    defaults["video"] = LOCKED_PROVIDER_DEFAULT_MODELS["video"]
    defaults["local"] = defaults.get("local", "")
    locked["default_models"] = defaults
    locked["text_model"] = defaults["text"]
    locked["image_model"] = defaults["image"]
    locked["video_model"] = defaults["video"]

    for provider in normalized:
        if provider["id"] == LOCKED_PROVIDER_ID:
            continue
        provider["manual_enabled"] = False
        provider["enabled"] = False

    return normalized, LOCKED_PROVIDER_ID


def _escape_env_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
