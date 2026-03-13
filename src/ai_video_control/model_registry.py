from __future__ import annotations

import json
import re
import subprocess
import urllib.error
import urllib.request
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from ai_video_control.storage import read_cache_entry, upsert_cache_value


MODEL_REGISTRY_CACHE_KEY = "provider_model_registry_v1"
HTTP_HEADERS = {
    "User-Agent": "AI-Video-Studio-Console/1.0",
}


def get_model_registry(force_refresh: bool = False) -> dict[str, Any]:
    cached = read_cache_entry(MODEL_REGISTRY_CACHE_KEY)
    if cached and not force_refresh:
        try:
            payload = json.loads(cached["value"])
            if isinstance(payload, dict):
                return payload
        except json.JSONDecodeError:
            pass

    if force_refresh or not cached:
        try:
            registry = refresh_model_registry()
            save_model_registry(registry)
            return registry
        except Exception:
            if cached:
                try:
                    payload = json.loads(cached["value"])
                    if isinstance(payload, dict):
                        return payload
                except json.JSONDecodeError:
                    pass

    registry = build_static_model_registry()
    save_model_registry(registry)
    return registry


def save_model_registry(payload: dict[str, Any]) -> None:
    upsert_cache_value(MODEL_REGISTRY_CACHE_KEY, json.dumps(payload, ensure_ascii=False))


def refresh_model_registry() -> dict[str, Any]:
    registry = build_static_model_registry()
    groups = {item["provider_id"]: item for item in registry["provider_model_groups"]}

    zynk_group = groups.get("zynkapi")
    if zynk_group:
        try:
            zynk_models = _fetch_zynk_models()
            _merge_model_lists(zynk_group["models"], zynk_models)
            zynk_group["total_models"] = zynk_models["raw_total"] or zynk_group["total_models"]
            zynk_group["source_status"] = "live"
        except Exception:
            pass

    bigmodel_group = groups.get("bigmodel")
    if bigmodel_group:
        try:
            bigmodel_models = _fetch_bigmodel_models()
            _merge_model_lists(bigmodel_group["models"], bigmodel_models)
            bigmodel_group["total_models"] = sum(len(bigmodel_models[kind]) for kind in ("text", "image", "video"))
            bigmodel_group["source_status"] = "live"
        except Exception:
            pass

    siliconflow_group = groups.get("siliconflow")
    if siliconflow_group:
        try:
            siliconflow_models = _fetch_siliconflow_models()
            _merge_model_lists(siliconflow_group["models"], siliconflow_models)
            siliconflow_group["total_models"] = sum(len(siliconflow_group["models"][kind]) for kind in ("text", "image", "video"))
            siliconflow_group["source_status"] = "live" if siliconflow_models["text"] else "curated"
        except Exception:
            pass

    registry["updated_at"] = _iso_now()
    return registry


def build_static_model_registry() -> dict[str, Any]:
    return {
        "updated_at": _iso_now(),
        "provider_model_groups": deepcopy(_STATIC_PROVIDER_MODEL_GROUPS),
    }


def _merge_model_lists(target: dict[str, list[str]], incoming: dict[str, Any]) -> None:
    for kind in ("text", "image", "video"):
        current = target.get(kind, [])
        target[kind] = _merge_unique(current, incoming.get(kind, []))


def _fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers=HTTP_HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            return response.read().decode("utf-8", "ignore")
    except urllib.error.URLError:
        result = subprocess.run(
            ["curl", "-Ls", url],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout


def _fetch_json(url: str) -> Any:
    return json.loads(_fetch_text(url))


def _fetch_zynk_models() -> dict[str, Any]:
    payload = _fetch_json("https://zynkapi.com/api/pricing")
    data = payload.get("data", []) if isinstance(payload, dict) else []
    names = []
    for item in data:
        if not isinstance(item, dict):
            continue
        name = str(item.get("model_name") or "").strip()
        if not name:
            continue
        names.append(name)

    curated = {
        "text": _preferred_models(
            names,
            [
                "deepseek-v3.1",
                "deepseek-r1",
                "claude-sonnet-4",
                "claude-opus-4.1",
                "gpt-4.1",
                "gpt-4o",
                "gemini-2.5-pro",
                "gemini-2.5-flash",
            ],
        ),
        "image": _preferred_models(
            names,
            [
                "gpt-image-1",
                "gemini-2.0-flash-exp-image-generation",
                "gemini-2.5-flash-image-preview",
                "imagen-4.0-fast-generate-001",
                "imagen-4.0-ultra-generate-001",
            ],
        ),
        "video": _preferred_models(
            names,
            [
                "veo-3.1-fast-generate-preview",
                "veo-3.1-generate-preview",
                "veo3-fast",
                "veo3-pro",
                "veo2-fast",
                "veo2-pro",
            ],
        ),
        "raw_total": len(set(names)),
    }
    return curated


def _fetch_bigmodel_models() -> dict[str, list[str]]:
    text_page = _fetch_text("https://docs.bigmodel.cn/cn/guide/models/text/glm-4.5")
    image_page = _fetch_text("https://docs.bigmodel.cn/cn/guide/models/image/cogview-4")
    video_page = _fetch_text("https://docs.bigmodel.cn/cn/guide/models/video/cogvideox")

    text_models = _extract_models(
        text_page,
        [
            r"GLM-[0-9.]+(?:-flash)?",
            r"glm-[a-z0-9.-]+",
        ],
    )
    image_models = _extract_models(
        image_page,
        [
            r"cogview-[a-z0-9.-]+",
            r"CogView-[A-Za-z0-9.-]+",
            r"glm-image",
        ],
    )
    video_models = _extract_models(
        video_page,
        [
            r"cogvideox-[a-z0-9.-]+",
            r"CogVideoX-[A-Za-z0-9.-]+",
        ],
    )

    return {
        "text": _preferred_models(
            text_models,
            [
                "GLM-4.7",
                "GLM-4.6",
                "glm-4.5",
                "glm-4-5-air",
                "glm-4-5-flash",
                "glm-4.7-flash",
                "glm-z1-air",
                "glm-z1-flash",
            ],
        ),
        "image": _preferred_models(
            image_models,
            [
                "cogview-4-250304",
                "cogview-4",
                "cogview-3-flash",
                "glm-image",
            ],
        ),
        "video": _preferred_models(
            video_models,
            [
                "cogvideox-flash",
                "cogvideox-3",
                "CogVideoX-Flash",
                "CogVideoX-3",
            ],
        ),
    }


def _fetch_siliconflow_models() -> dict[str, list[str]]:
    try:
        page = _fetch_text("https://docs.siliconflow.cn/quickstart/models")
    except urllib.error.URLError:
        return {"text": [], "image": [], "video": []}

    tokens = _extract_models(
        page,
        [
            r"Qwen/[A-Za-z0-9._/-]+",
            r"deepseek-ai/[A-Za-z0-9._/-]+",
            r"THUDM/[A-Za-z0-9._/-]+",
            r"Kwai-[A-Za-z0-9._/-]+",
            r"Wan-[A-Za-z0-9._/-]+",
            r"black-forest-labs/[A-Za-z0-9._/-]+",
        ],
    )

    return {
        "text": _preferred_models(
            tokens,
            [
                "deepseek-ai/DeepSeek-V3",
                "deepseek-ai/DeepSeek-R1",
                "Qwen/Qwen2.5-72B-Instruct",
                "Qwen/Qwen2-72B-Instruct",
                "THUDM/glm-4-9b-chat",
            ],
        ),
        "image": _preferred_models(
            tokens,
            [
                "black-forest-labs/FLUX.1-schnell",
            ],
        ),
        "video": _preferred_models(
            tokens,
            [
                "Wan-AI/Wan2.2-I2V-A14B",
            ],
        ),
    }


def _extract_models(content: str, patterns: list[str]) -> list[str]:
    results: list[str] = []
    for pattern in patterns:
        results.extend(re.findall(pattern, content, flags=re.IGNORECASE))
    return _unique_non_empty(results)


def _preferred_models(source: list[str], priorities: list[str]) -> list[str]:
    by_lower = {item.lower(): item for item in source if item}
    chosen = []
    for priority in priorities:
        if priority.lower() in by_lower:
            chosen.append(by_lower[priority.lower()])
    return _unique_non_empty(chosen)


def _merge_unique(*lists: list[str]) -> list[str]:
    items: list[str] = []
    for values in lists:
        items.extend(values)
    return _unique_non_empty(items)


def _unique_non_empty(values: list[str]) -> list[str]:
    seen: set[str] = set()
    items: list[str] = []
    for raw in values:
        value = str(raw or "").strip()
        if not value:
            continue
        lowered = value.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        items.append(value)
    return items


def _iso_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


_STATIC_PROVIDER_MODEL_GROUPS: list[dict[str, Any]] = [
    {
        "provider_id": "volcengine-ark",
        "provider_label": "火山方舟",
        "provider_type": "openai-compatible",
        "source_label": "项目当前常用模型",
        "source_url": "https://www.volcengine.com/product/ark",
        "source_status": "curated",
        "description": "优先保留当前项目已经跑通的豆包系模型，避免链路不兼容。",
        "total_models": 6,
        "models": {
            "text": [
                "doubao-seed-2-0-pro-260215",
                "doubao-1-5-thinking-pro",
            ],
            "image": [
                "doubao-seedream-3-0-t2i-250415",
            ],
            "video": [
                "doubao-seedance-1-5-pro-251215",
                "doubao-seedance-1-5-lite-250428",
            ],
        },
    },
    {
        "provider_id": "siliconflow",
        "provider_label": "硅基流动",
        "provider_type": "openai-compatible",
        "source_label": "官方文档模型页",
        "source_url": "https://docs.siliconflow.cn/quickstart/models",
        "source_status": "curated",
        "description": "先展示与你当前工作流强相关的文本模型，后续可继续扩展。",
        "total_models": 5,
        "models": {
            "text": [
                "deepseek-ai/DeepSeek-V3",
                "deepseek-ai/DeepSeek-R1",
                "Qwen/Qwen2.5-72B-Instruct",
                "THUDM/glm-4-9b-chat",
            ],
            "image": [],
            "video": [],
        },
    },
    {
        "provider_id": "zynkapi",
        "provider_label": "Zynk API",
        "provider_type": "openai-compatible",
        "source_label": "官方价格与模型接口",
        "source_url": "https://zynkapi.com/api/pricing",
        "source_status": "curated",
        "description": "从公开接口抓取后，只保留适合当前视频工作流快速选型的一组常用模型。",
        "total_models": 8,
        "models": {
            "text": [
                "deepseek-v3.1",
                "deepseek-r1",
                "claude-sonnet-4",
                "gpt-4.1",
                "gpt-4o",
            ],
            "image": [
                "gpt-image-1",
                "gemini-2.0-flash-exp-image-generation",
            ],
            "video": [
                "veo-3.1-fast-generate-preview",
            ],
        },
    },
    {
        "provider_id": "bigmodel",
        "provider_label": "智谱开放平台",
        "provider_type": "openai-compatible",
        "source_label": "官方模型文档",
        "source_url": "https://docs.bigmodel.cn/cn/guide/models/text/glm-4.5",
        "source_status": "curated",
        "description": "按官方文档整理出文本、图像和视频三类常用模型。",
        "total_models": 8,
        "models": {
            "text": [
                "GLM-4.7",
                "GLM-4.6",
                "glm-4.5",
                "glm-4-5-air",
                "glm-4-5-flash",
            ],
            "image": [
                "cogview-4-250304",
                "cogview-3-flash",
                "glm-image",
            ],
            "video": [
                "cogvideox-flash",
            ],
        },
    },
    {
        "provider_id": "openai-compatible",
        "provider_label": "OpenAI 兼容通用",
        "provider_type": "openai-compatible",
        "source_label": "通用兼容入口",
        "source_url": "https://platform.openai.com/docs/models",
        "source_status": "curated",
        "description": "给自定义 OpenAI 兼容平台一个通用起步模型集。",
        "total_models": 5,
        "models": {
            "text": [
                "gpt-4.1",
                "gpt-4o",
            ],
            "image": [
                "gpt-image-1",
            ],
            "video": [],
        },
    },
    {
        "provider_id": "cogvideox-local",
        "provider_label": "CogVideoX 本地",
        "provider_type": "cogvideox",
        "source_label": "本地模型常用项",
        "source_url": "https://github.com/THUDM/CogVideo",
        "source_status": "curated",
        "description": "本地视频渲染模型，适合离线环境。",
        "total_models": 2,
        "models": {
            "text": [],
            "image": [],
            "video": [
                "THUDM/CogVideoX-5b-I2V",
                "THUDM/CogVideoX1.5-5B",
            ],
        },
    },
]
