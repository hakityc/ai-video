from __future__ import annotations

from copy import deepcopy
from typing import Any

from ai_video_control.model_registry import get_model_registry
from ai_video_control.settings import (
    LOCKED_PROVIDER_DEFAULT_MODELS,
    LOCKED_PROVIDER_ID,
    Settings,
    read_provider_settings,
)
from ai_video_control.storage import (
    list_model_health_states,
    list_provider_health_states,
    list_provider_model_policies,
    upsert_provider_model_policy,
)


OPENAI_PROVIDER_TYPES = {"openai-compatible", "custom"}
HEALTHY_MODEL_STATUSES = {"healthy"}
FALLBACK_MODEL_STATUSES = {"unknown", "degraded"}
BLOCKED_MODEL_STATUSES = {"unhealthy", "disabled_auto", "disabled_manual"}
BLOCKED_PROVIDER_STATUSES = {"unhealthy", "disabled_auto", "disabled_manual"}

TEXT_ABILITIES = ("script_text", "character_text_json")
IMAGE_ABILITIES = ("character_image_generation", "shortform_image_generation")
VIDEO_ABILITIES = ("shortform_video_generation",)

TASK_REQUIREMENTS: dict[str, dict[str, str]] = {
    "script_generation": {"text": "script_text"},
    "storyboard_generation": {"text": "script_text"},
    "character_generation": {
        "text": "character_text_json",
        "image": "character_image_generation",
    },
    "shortform_generation": {
        "text": "script_text",
        "image": "shortform_image_generation",
        "video": "shortform_video_generation",
    },
    "review_text": {"text": "script_text"},
}


def supported_abilities_for(provider_type: str, kind: str) -> list[str]:
    if provider_type in OPENAI_PROVIDER_TYPES:
        if kind == "text":
            return list(TEXT_ABILITIES)
        if kind == "image":
            return list(IMAGE_ABILITIES)
        if kind == "video":
            return list(VIDEO_ABILITIES)
    if provider_type == "comfyui" and kind == "video":
        return ["shortform_video_generation"]
    if provider_type == "cogvideox" and kind == "video":
        return ["shortform_video_generation"]
    return []


def get_provider_runtime_snapshot() -> dict[str, Any]:
    provider_state = read_provider_settings()
    providers = provider_state.get("providers", [])
    registry = get_model_registry()
    sync_provider_model_policies(providers, registry.get("provider_model_groups", []))
    policies = list_provider_model_policies()
    provider_health = list_provider_health_states()
    model_health = list_model_health_states()
    provider_lookup = {provider["id"]: provider for provider in providers}

    model_entries = build_model_health_entries(
        providers=providers,
        policies=policies,
        model_health_states=model_health,
    )
    provider_summary = build_provider_health_summary(
        providers=providers,
        provider_health_states=provider_health,
        model_entries=model_entries,
    )
    effective_defaults = build_effective_defaults(
        selected_provider_id=str(provider_state.get("selected_provider_id") or "").strip(),
        providers=providers,
        policies=policies,
        model_entries=model_entries,
    )
    return {
        "selected_provider_id": provider_state.get("selected_provider_id", ""),
        "providers": providers,
        "provider_lookup": provider_lookup,
        "provider_model_groups": registry.get("provider_model_groups", []),
        "provider_model_policies": policies,
        "provider_health_states": provider_health,
        "model_health_states": model_health,
        "model_health_entries": model_entries,
        "provider_health_summary": provider_summary,
        "effective_defaults": effective_defaults,
    }


def sync_provider_model_policies(
    providers: list[dict[str, Any]],
    provider_model_groups: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    existing = {
        (item["provider_id"], item["model_id"], item["kind"]): item
        for item in list_provider_model_policies()
    }
    grouped_catalog = {item["provider_id"]: item for item in provider_model_groups}
    synced: list[dict[str, Any]] = []
    for provider in providers:
        provider_id = provider["id"]
        provider_type = provider["provider_type"]
        group = grouped_catalog.get(provider_id, {})
        models_by_kind = {
            "text": list(group.get("models", {}).get("text", [])),
            "image": list(group.get("models", {}).get("image", [])),
            "video": list(group.get("models", {}).get("video", [])),
        }
        defaults = provider.get("default_models", {})
        locked_allowed_models = {
            defaults.get("text") or LOCKED_PROVIDER_DEFAULT_MODELS["text"],
            defaults.get("image") or LOCKED_PROVIDER_DEFAULT_MODELS["image"],
            defaults.get("video") or LOCKED_PROVIDER_DEFAULT_MODELS["video"],
        } if provider_id == LOCKED_PROVIDER_ID else set()
        for kind in ("text", "image", "video"):
            default_model = str(defaults.get(kind) or "").strip()
            if default_model and default_model not in models_by_kind[kind]:
                models_by_kind[kind].insert(0, default_model)
        local_model = str(defaults.get("local") or provider.get("local_model") or "").strip()
        if provider_type == "cogvideox" and local_model:
            if local_model not in models_by_kind["video"]:
                models_by_kind["video"].insert(0, local_model)
        if provider_type == "comfyui" and not models_by_kind["video"]:
            models_by_kind["video"].append("__comfyui__")

        for kind, model_ids in models_by_kind.items():
            for model_id in model_ids:
                key = (provider_id, model_id, kind)
                current = existing.get(key)
                payload = {
                    "provider_id": provider_id,
                    "model_id": model_id,
                    "kind": kind,
                    "manual_enabled": (
                        model_id in locked_allowed_models
                        if provider_id == LOCKED_PROVIDER_ID
                        else (current["manual_enabled"] if current else True)
                    ),
                    "supported_abilities": supported_abilities_for(provider_type, kind),
                }
                upsert_provider_model_policy(payload)
                synced.append(payload)
    return synced


def build_model_health_entries(
    *,
    providers: list[dict[str, Any]],
    policies: list[dict[str, Any]],
    model_health_states: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    provider_lookup = {provider["id"]: provider for provider in providers}
    state_lookup = {
        (item["provider_id"], item["model_id"], item["kind"], item["ability"]): item
        for item in model_health_states
    }
    entries: list[dict[str, Any]] = []
    for policy in policies:
        provider = provider_lookup.get(policy["provider_id"])
        if provider is None:
            continue
        abilities = list(policy.get("supported_abilities") or [])
        ability_states = []
        for ability in abilities:
            state = state_lookup.get((policy["provider_id"], policy["model_id"], policy["kind"], ability))
            ability_states.append(
                {
                    "ability": ability,
                    "status": state["status"] if state else "unknown",
                    "reason": state.get("reason") if state else None,
                    "error_class": state.get("error_class") if state else None,
                    "error_code": state.get("error_code") if state else None,
                    "last_checked_at": state.get("last_checked_at") if state else None,
                    "last_healthy_at": state.get("last_healthy_at") if state else None,
                    "consecutive_failures": state.get("consecutive_failures", 0) if state else 0,
                }
            )
        overall_status = overall_model_status(
            provider_manual_enabled=bool(provider.get("manual_enabled", True)),
            model_manual_enabled=bool(policy.get("manual_enabled", True)),
            ability_states=ability_states,
        )
        entries.append(
            {
                "provider_id": policy["provider_id"],
                "provider_name": provider["name"],
                "provider_type": provider["provider_type"],
                "provider_manual_enabled": bool(provider.get("manual_enabled", True)),
                "model_id": policy["model_id"],
                "kind": policy["kind"],
                "manual_enabled": bool(policy.get("manual_enabled", True)),
                "supported_abilities": abilities,
                "ability_states": ability_states,
                "overall_status": overall_status,
                "reason": first_non_empty([item.get("reason") for item in ability_states]),
            }
        )
    return entries


def build_provider_health_summary(
    *,
    providers: list[dict[str, Any]],
    provider_health_states: list[dict[str, Any]],
    model_entries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    state_lookup = {item["provider_id"]: item for item in provider_health_states}
    entries_by_provider: dict[str, list[dict[str, Any]]] = {}
    for item in model_entries:
        entries_by_provider.setdefault(item["provider_id"], []).append(item)

    summaries: list[dict[str, Any]] = []
    for provider in providers:
        provider_id = provider["id"]
        models = entries_by_provider.get(provider_id, [])
        state = state_lookup.get(provider_id)
        status = provider_overall_status(provider, models, state)
        ability_summary = aggregate_provider_abilities(models)
        summaries.append(
            {
                "provider_id": provider_id,
                "provider_name": provider["name"],
                "provider_type": provider["provider_type"],
                "manual_enabled": bool(provider.get("manual_enabled", True)),
                "status": status,
                "reason": (
                    None
                    if status == "healthy"
                    else (
                        state.get("reason")
                        if state and state.get("reason")
                        else first_non_empty([item.get("reason") for item in models])
                    )
                ),
                "last_checked_at": state.get("last_checked_at") if state else None,
                "last_healthy_at": state.get("last_healthy_at") if state else None,
                "consecutive_failures": state.get("consecutive_failures", 0) if state else 0,
                "default_models": deepcopy(provider.get("default_models", {})),
                "ability_summary": ability_summary,
            }
        )
    return summaries


def build_effective_defaults(
    *,
    selected_provider_id: str,
    providers: list[dict[str, Any]],
    policies: list[dict[str, Any]],
    model_entries: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "script_generation": _serialize_resolved_defaults(resolve_task_defaults(
            task_name="script_generation",
            selected_provider_id=selected_provider_id,
            providers=providers,
            policies=policies,
            model_entries=model_entries,
        )),
        "character_generation": _serialize_resolved_defaults(resolve_task_defaults(
            task_name="character_generation",
            selected_provider_id=selected_provider_id,
            providers=providers,
            policies=policies,
            model_entries=model_entries,
        )),
        "shortform_generation": _serialize_resolved_defaults(resolve_task_defaults(
            task_name="shortform_generation",
            selected_provider_id=selected_provider_id,
            providers=providers,
            policies=policies,
            model_entries=model_entries,
        )),
    }


def resolve_task_defaults(
    *,
    task_name: str,
    selected_provider_id: str,
    providers: list[dict[str, Any]],
    policies: list[dict[str, Any]],
    model_entries: list[dict[str, Any]],
    provider_id_override: str | None = None,
    text_model: str | None = None,
    image_model: str | None = None,
    video_model: str | None = None,
) -> dict[str, Any] | None:
    requirements = TASK_REQUIREMENTS[task_name]
    providers_by_id = {provider["id"]: provider for provider in providers}
    policy_lookup = {
        (item["provider_id"], item["kind"], item["model_id"]): item for item in policies
    }
    entries_by_key = {
        (item["provider_id"], item["kind"], item["model_id"]): item for item in model_entries
    }
    override_map = {"text": text_model, "image": image_model, "video": video_model}
    candidate_provider_ids = ordered_provider_candidates(
        selected_provider_id=selected_provider_id,
        providers=providers,
        policies=policies,
        override_map=override_map,
        provider_id_override=provider_id_override,
    )

    last_reason = None
    for provider_id in candidate_provider_ids:
        provider = providers_by_id[provider_id]
        if provider["provider_type"] not in OPENAI_PROVIDER_TYPES:
            continue
        if not provider.get("manual_enabled", True):
            last_reason = f"Provider `{provider['name']}` 已被手动禁用。"
            continue
        chosen_models: dict[str, str] = {}
        blocked_reasons: list[str] = []
        for kind, ability in requirements.items():
            explicit_model = override_map.get(kind)
            model = choose_model_for_provider(
                provider=provider,
                kind=kind,
                ability=ability,
                explicit_model=explicit_model,
                policy_lookup=policy_lookup,
                entries_by_key=entries_by_key,
            )
            if model is None:
                blocked_reasons.append(f"{provider['name']} 缺少可用的 {kind} 模型（能力 `{ability}`）")
                continue
            chosen_models[kind] = model
        if blocked_reasons:
            last_reason = "；".join(blocked_reasons)
            continue
        settings = Settings(
            openai_base_url=provider.get("base_url"),
            openai_api_key=provider.get("api_key"),
            openai_model=chosen_models.get("text"),
            openai_image_model=chosen_models.get("image"),
            openai_video_model=chosen_models.get("video"),
            cogvideox_model_id=provider.get("default_models", {}).get("local") or provider.get("local_model"),
            provider_connections_json="",
            active_provider_id=provider["id"],
        )
        return {
            "provider_id": provider["id"],
            "provider_name": provider["name"],
            "provider_type": provider["provider_type"],
            "settings": settings,
            "models": chosen_models,
        }

    if provider_id_override:
        raise ValueError(last_reason or f"Provider `{provider_id_override}` 没有可用模型。")
    if any(str(value or "").strip() for value in override_map.values()):
        raise ValueError(last_reason or "指定模型当前不可用。")
    return None


def resolve_openai_runtime(
    task_name: str,
    *,
    provider_id: str | None = None,
    text_model: str | None = None,
    image_model: str | None = None,
    video_model: str | None = None,
) -> dict[str, Any]:
    snapshot = get_provider_runtime_snapshot()
    resolved = resolve_task_defaults(
        task_name=task_name,
        selected_provider_id=str(snapshot.get("selected_provider_id") or ""),
        providers=snapshot["providers"],
        policies=snapshot["provider_model_policies"],
        model_entries=snapshot["model_health_entries"],
        provider_id_override=provider_id,
        text_model=text_model,
        image_model=image_model,
        video_model=video_model,
    )
    if resolved is None:
        raise ValueError(f"未找到可用于 `{task_name}` 的健康 provider/model 组合。请先运行健康检查。")
    return resolved


def ordered_provider_candidates(
    *,
    selected_provider_id: str,
    providers: list[dict[str, Any]],
    policies: list[dict[str, Any]],
    override_map: dict[str, str | None],
    provider_id_override: str | None = None,
) -> list[str]:
    if provider_id_override:
        return [provider_id_override]

    explicit_models = {kind: str(value or "").strip() for kind, value in override_map.items() if str(value or "").strip()}
    if explicit_models:
        candidates = []
        for provider in providers:
            matches_all = True
            for kind, model_id in explicit_models.items():
                if not any(
                    item["provider_id"] == provider["id"] and item["kind"] == kind and item["model_id"] == model_id
                    for item in policies
                ):
                    matches_all = False
                    break
            if matches_all:
                candidates.append(provider["id"])
        return candidates

    preferred: list[str] = []
    if selected_provider_id:
        preferred.append(selected_provider_id)
    preferred.extend(
        provider["id"] for provider in providers if provider["id"] != selected_provider_id
    )
    return preferred


def choose_model_for_provider(
    *,
    provider: dict[str, Any],
    kind: str,
    ability: str,
    explicit_model: str | None,
    policy_lookup: dict[tuple[str, str, str], dict[str, Any]],
    entries_by_key: dict[tuple[str, str, str], dict[str, Any]],
) -> str | None:
    provider_id = provider["id"]
    if explicit_model:
        return explicit_model if model_is_eligible(provider_id, kind, explicit_model, ability, policy_lookup, entries_by_key) else None

    defaults = provider.get("default_models", {})
    preferred_models = [defaults.get(kind)]
    if kind == "video" and provider["provider_type"] == "cogvideox":
        preferred_models.append(defaults.get("local"))

    candidate_models = [
        model_id
        for (candidate_provider_id, candidate_kind, model_id), _policy in policy_lookup.items()
        if candidate_provider_id == provider_id and candidate_kind == kind
    ]

    ordered_models = [model for model in preferred_models if model] + candidate_models
    seen: set[str] = set()
    best_fallback: str | None = None
    for model_id in ordered_models:
        if model_id in seen:
            continue
        seen.add(model_id)
        key = (provider_id, kind, model_id)
        entry = entries_by_key.get(key)
        if entry is None:
            continue
        if entry["overall_status"] in BLOCKED_MODEL_STATUSES:
            continue
        ability_status = ability_status_for(entry, ability)
        if ability_status == "healthy":
            return model_id
        if ability_status in FALLBACK_MODEL_STATUSES and best_fallback is None:
            best_fallback = model_id
    return best_fallback


def model_is_eligible(
    provider_id: str,
    kind: str,
    model_id: str,
    ability: str,
    policy_lookup: dict[tuple[str, str, str], dict[str, Any]],
    entries_by_key: dict[tuple[str, str, str], dict[str, Any]],
) -> bool:
    policy = policy_lookup.get((provider_id, kind, model_id))
    if policy is None or not policy.get("manual_enabled", True):
        return False
    entry = entries_by_key.get((provider_id, kind, model_id))
    if entry is None:
        return False
    if entry["overall_status"] in BLOCKED_MODEL_STATUSES:
        return False
    return ability_status_for(entry, ability) in HEALTHY_MODEL_STATUSES | FALLBACK_MODEL_STATUSES


def overall_model_status(
    *,
    provider_manual_enabled: bool,
    model_manual_enabled: bool,
    ability_states: list[dict[str, Any]],
) -> str:
    if not provider_manual_enabled or not model_manual_enabled:
        return "disabled_manual"
    statuses = [item["status"] for item in ability_states]
    if not statuses:
        return "unknown"
    if any(status in {"unhealthy", "disabled_auto"} for status in statuses):
        return "unhealthy"
    if all(status == "healthy" for status in statuses):
        return "healthy"
    if any(status == "healthy" for status in statuses):
        return "degraded"
    if any(status == "degraded" for status in statuses):
        return "degraded"
    return "unknown"


def provider_overall_status(
    provider: dict[str, Any],
    model_entries: list[dict[str, Any]],
    state: dict[str, Any] | None,
) -> str:
    if not provider.get("manual_enabled", True):
        return "disabled_manual"
    if state and state.get("status") in {"disabled_auto", "unhealthy"}:
        return state["status"]
    ability_summary = aggregate_provider_abilities(model_entries)
    statuses = [item["status"] for item in ability_summary]
    if not statuses:
        return state.get("status", "unknown") if state else "unknown"
    if all(status in {"unhealthy", "disabled_auto", "disabled_manual"} for status in statuses):
        return "unhealthy"
    if all(status == "healthy" for status in statuses):
        return "healthy"
    if any(status == "healthy" for status in statuses):
        return "degraded"
    if any(status == "degraded" for status in statuses):
        return "degraded"
    return state.get("status", "unknown") if state else "unknown"


def aggregate_provider_abilities(model_entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    abilities: dict[str, dict[str, Any]] = {}
    for entry in model_entries:
        if not entry.get("provider_manual_enabled", True) or not entry.get("manual_enabled", True):
            continue
        for ability_state in entry.get("ability_states", []):
            current = abilities.get(ability_state["ability"])
            next_rank = ability_rank(ability_state["status"])
            if current is None or next_rank > ability_rank(current["status"]):
                abilities[ability_state["ability"]] = {
                    "ability": ability_state["ability"],
                    "status": ability_state["status"],
                    "model_id": entry["model_id"],
                    "kind": entry["kind"],
                    "reason": ability_state.get("reason"),
                }
    return sorted(abilities.values(), key=lambda item: item["ability"])


def ability_status_for(entry: dict[str, Any], ability: str) -> str:
    for ability_state in entry.get("ability_states", []):
        if ability_state["ability"] == ability:
            return ability_state["status"]
    return "unknown"


def ability_rank(status: str) -> int:
    if status == "healthy":
        return 4
    if status == "degraded":
        return 3
    if status == "unknown":
        return 2
    if status == "disabled_auto":
        return 1
    return 0


def first_non_empty(values: list[str | None]) -> str | None:
    for value in values:
        if value:
            return value
    return None


def _serialize_resolved_defaults(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if payload is None:
        return None
    return {
        "provider_id": payload["provider_id"],
        "provider_name": payload["provider_name"],
        "provider_type": payload["provider_type"],
        "models": dict(payload["models"]),
    }
