from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import httpx

from ai_video_control.health_policy import (
    classify_exception,
    keep_healthy_only,
    record_health_failure,
    record_health_success,
    recheck_and_restore,
    recompute_provider_state,
)
from ai_video_control.provider_runtime import get_provider_runtime_snapshot
from ai_video_control.providers.openai_compat import (
    OpenAICompatClient,
    build_character_brief_prompt,
    image_path_to_data_url,
)
from ai_video_control.settings import Settings, read_provider_settings


REPO_ROOT = Path.cwd().resolve()


_HEALTH_IMAGE_DATA_URL = (
    "data:image/png;base64,"
    + base64.b64encode(
        base64.b16decode(
            "89504E470D0A1A0A0000000D4948445200000001000000010802000000907753DE"
            "0000000C49444154789C6360000000020001E221BC330000000049454E44AE426082",
            casefold=True,
        )
    ).decode("ascii")
)


def _video_probe_image_data_url() -> str:
    for relative_path in (
        "assets/characters/qiao-ning/reference/front.jpeg",
        "assets/characters/lin-xiaoyu/reference/front.jpeg",
        "assets/characters/untitled/reference/untitled-front.jpeg",
    ):
        candidate = REPO_ROOT / relative_path
        if candidate.exists():
            return image_path_to_data_url(candidate)
    return _HEALTH_IMAGE_DATA_URL


def run_health_checks(
    *,
    provider_ids: list[str] | None = None,
    model_ids: list[str] | None = None,
    abilities: list[str] | None = None,
    include_disabled: bool = False,
) -> dict[str, Any]:
    snapshot = get_provider_runtime_snapshot()
    target_providers = []
    target_provider_set = set(provider_ids or [])
    target_model_set = set(model_ids or [])
    target_ability_set = set(abilities or [])
    for provider in snapshot["providers"]:
        if target_provider_set and provider["id"] not in target_provider_set:
            continue
        if not include_disabled and not provider.get("manual_enabled", True):
            continue
        target_providers.append(provider)

    checked_models = 0
    for provider in target_providers:
        if provider["provider_type"] in {"openai-compatible", "custom"}:
            checked_models += _check_openai_provider(
                provider=provider,
                model_entries=[
                    item
                    for item in snapshot["model_health_entries"]
                    if item["provider_id"] == provider["id"]
                ],
                target_model_set=target_model_set,
                target_ability_set=target_ability_set,
                include_disabled=include_disabled,
            )
        elif provider["provider_type"] == "comfyui":
            checked_models += _check_comfyui_provider(provider)
        elif provider["provider_type"] == "cogvideox":
            checked_models += _check_cogvideox_provider(provider)
        recompute_provider_state(provider["id"])

    refreshed = get_provider_runtime_snapshot()
    return {
        "checked_provider_count": len(target_providers),
        "checked_model_count": checked_models,
        "provider_health_summary": refreshed["provider_health_summary"],
        "model_health_entries": refreshed["model_health_entries"],
        "effective_defaults": refreshed["effective_defaults"],
    }


def apply_health_action(action: str) -> dict[str, Any]:
    if action == "keep_healthy_only":
        updated = keep_healthy_only()
        snapshot = get_provider_runtime_snapshot()
        return {
            "action": action,
            "provider_settings": updated,
            "provider_health_summary": snapshot["provider_health_summary"],
            "model_health_entries": snapshot["model_health_entries"],
            "effective_defaults": snapshot["effective_defaults"],
        }
    if action == "recheck_and_restore":
        run_health_checks(include_disabled=True)
        snapshot = get_provider_runtime_snapshot()
        updated = recheck_and_restore(
            provider_summaries=snapshot["provider_health_summary"],
            model_entries=snapshot["model_health_entries"],
        )
        refreshed = get_provider_runtime_snapshot()
        return {
            "action": action,
            "provider_settings": updated,
            "provider_health_summary": refreshed["provider_health_summary"],
            "model_health_entries": refreshed["model_health_entries"],
            "effective_defaults": refreshed["effective_defaults"],
        }
    raise ValueError(f"Unsupported health action: {action}")


def _check_openai_provider(
    *,
    provider: dict[str, Any],
    model_entries: list[dict[str, Any]],
    target_model_set: set[str],
    target_ability_set: set[str],
    include_disabled: bool,
) -> int:
    checked = 0
    settings = Settings(
        openai_base_url=provider.get("base_url"),
        openai_api_key=provider.get("api_key"),
    )
    if not settings.openai_base_url or not settings.openai_api_key:
        for entry in model_entries:
            if target_model_set and entry["model_id"] not in target_model_set:
                continue
            if not include_disabled and not entry.get("manual_enabled", True):
                continue
            for ability_state in entry.get("ability_states", []):
                if target_ability_set and ability_state["ability"] not in target_ability_set:
                    continue
                checked += 1
                record_health_failure(
                    provider_id=entry["provider_id"],
                    model_id=entry["model_id"],
                    kind=entry["kind"],
                    ability=ability_state["ability"],
                    source="active_probe",
                    exc=RuntimeError("OPENAI_BASE_URL and OPENAI_API_KEY are required"),
                )
        return checked

    for entry in model_entries:
        if target_model_set and entry["model_id"] not in target_model_set:
            continue
        if not include_disabled and not entry.get("manual_enabled", True):
            continue
        for ability_state in entry.get("ability_states", []):
            ability = ability_state["ability"]
            if target_ability_set and ability not in target_ability_set:
                continue
            checked += 1
            try:
                _probe_openai_ability(
                    provider=provider,
                    settings=settings,
                    model_id=entry["model_id"],
                    kind=entry["kind"],
                    ability=ability,
                )
                record_health_success(
                    provider_id=entry["provider_id"],
                    model_id=entry["model_id"],
                    kind=entry["kind"],
                    ability=ability,
                    source="active_probe",
                )
            except Exception as exc:  # noqa: BLE001
                record_health_failure(
                    provider_id=entry["provider_id"],
                    model_id=entry["model_id"],
                    kind=entry["kind"],
                    ability=ability,
                    source="active_probe",
                    exc=exc,
                )
    return checked


def _probe_openai_ability(
    *,
    provider: dict[str, Any],
    settings: Settings,
    model_id: str,
    kind: str,
    ability: str,
) -> None:
    runtime_settings = settings.model_copy(
        update={
            "openai_model": model_id if kind == "text" else settings.openai_model,
            "openai_image_model": model_id if kind == "image" else settings.openai_image_model,
            "openai_video_model": model_id if kind == "video" else settings.openai_video_model,
        }
    )
    client = OpenAICompatClient(runtime_settings)
    if ability == "script_text":
        content = client.chat_text("只回复“ok”。", model=model_id, max_tokens=16)
        if not content.strip():
            raise ValueError("empty content from text model")
        return
    if ability == "character_text_json":
        payload = client.chat_json(build_character_brief_prompt("health check detective"), model=model_id)
        for key in (
            "name",
            "face",
            "hair",
            "body",
            "outfit",
            "accessories",
            "style_descriptors",
            "negative_prompt",
        ):
            if key not in payload:
                raise ValueError(f"character brief missing key: {key}")
        return
    if ability in {"character_image_generation", "shortform_image_generation"}:
        response = client._request(
            "POST",
            "/images/generations",
            json={
                "model": model_id,
                "prompt": "health check studio portrait",
                "size": "1024x1024",
            },
        )
        data = response.json()
        if not data.get("data"):
            raise ValueError("image generation probe returned empty data")
        return
    if ability == "shortform_video_generation":
        response = client._request(
            "POST",
            "/contents/generations/tasks",
            json={
                "model": model_id,
                "ratio": "16:9",
                "duration": 5,
                "resolution": "480p",
                "content": [
                    {"type": "text", "text": "health check clip"},
                    {
                        "type": "image_url",
                        "role": "first_frame",
                        "image_url": {"url": _video_probe_image_data_url()},
                    },
                ],
            },
        )
        data = response.json()
        if not data.get("id") and not data.get("task_id"):
            raise ValueError("video generation probe returned no task id")
        return
    raise ValueError(f"Unsupported ability probe: {ability}")


def _check_comfyui_provider(provider: dict[str, Any]) -> int:
    model_id = "__comfyui__"
    try:
        with httpx.Client(timeout=8.0) as client:
            response = client.get(provider.get("base_url", ""))
        if response.status_code >= 500:
            raise RuntimeError(f"ComfyUI returned {response.status_code}")
        record_health_success(
            provider_id=provider["id"],
            model_id=model_id,
            kind="video",
            ability="shortform_video_generation",
            source="active_probe",
        )
    except Exception as exc:  # noqa: BLE001
        record_health_failure(
            provider_id=provider["id"],
            model_id=model_id,
            kind="video",
            ability="shortform_video_generation",
            source="active_probe",
            exc=exc,
        )
    return 1


def _check_cogvideox_provider(provider: dict[str, Any]) -> int:
    model_id = provider.get("default_models", {}).get("local") or provider.get("local_model") or "local"
    try:
        import diffusers  # noqa: F401
        import torch  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        record_health_failure(
            provider_id=provider["id"],
            model_id=model_id,
            kind="video",
            ability="shortform_video_generation",
            source="active_probe",
            exc=exc,
        )
        return 1

    record_health_success(
        provider_id=provider["id"],
        model_id=model_id,
        kind="video",
        ability="shortform_video_generation",
        source="active_probe",
    )
    return 1
