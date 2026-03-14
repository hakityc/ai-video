from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from ai_video_control.provider_runtime import (
    aggregate_provider_abilities,
    build_model_health_entries,
    build_provider_health_summary,
)
from ai_video_control.settings import read_provider_settings, update_provider_settings
from ai_video_control.storage import (
    append_health_event,
    list_model_health_states,
    list_provider_health_states,
    list_provider_model_policies,
    upsert_model_health_state,
    upsert_provider_health_state,
    upsert_provider_model_policy,
)


FATAL_CONFIG = "fatal_config"
FATAL_MODEL = "fatal_model"
FATAL_CAPABILITY = "fatal_capability"
TRANSIENT = "transient"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def classify_exception(exc: Exception) -> dict[str, str]:
    message = str(exc)
    lowered = message.lower()

    if isinstance(exc, httpx.TimeoutException):
        return {
            "error_class": TRANSIENT,
            "error_code": "timeout",
            "reason": message or "request timeout",
        }
    if isinstance(exc, (httpx.ConnectError, httpx.NetworkError, httpx.RemoteProtocolError)):
        return {
            "error_class": TRANSIENT,
            "error_code": "network_error",
            "reason": message or "network error",
        }
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        text = exc.response.text[:500]
        if status_code in {401, 403}:
            error_class = FATAL_CONFIG
        elif status_code == 404 or "model not found" in text.lower() or "does not exist" in text.lower():
            error_class = FATAL_MODEL
        elif status_code == 400:
            if "model" in text.lower() and ("not found" in text.lower() or "does not exist" in text.lower()):
                error_class = FATAL_MODEL
            else:
                error_class = FATAL_CAPABILITY
        elif status_code == 429 or status_code >= 500:
            error_class = TRANSIENT
        else:
            error_class = FATAL_CAPABILITY
        return {
            "error_class": error_class,
            "error_code": str(status_code),
            "reason": text or message or f"http {status_code}",
        }
    if isinstance(exc, ValueError):
        if "json" in lowered or "parse" in lowered or "content" in lowered:
            return {
                "error_class": FATAL_CAPABILITY,
                "error_code": "invalid_response",
                "reason": message,
            }
        if "required" in lowered or "missing" in lowered or "invalid" in lowered:
            return {
                "error_class": FATAL_CONFIG,
                "error_code": "invalid_config",
                "reason": message,
            }
    if isinstance(exc, RuntimeError) and (
        "required" in lowered or "install" in lowered or "dependencies" in lowered
    ):
        return {
            "error_class": FATAL_CONFIG,
            "error_code": "runtime_missing_dependency",
            "reason": message,
        }
    return {
        "error_class": FATAL_CAPABILITY,
        "error_code": exc.__class__.__name__.lower(),
        "reason": message or exc.__class__.__name__,
    }


def record_health_success(
    *,
    provider_id: str,
    model_id: str,
    kind: str,
    ability: str,
    source: str,
    details: dict[str, Any] | None = None,
) -> None:
    now = utc_now()
    upsert_model_health_state(
        {
            "provider_id": provider_id,
            "model_id": model_id,
            "kind": kind,
            "ability": ability,
            "status": "healthy",
            "error_class": None,
            "error_code": None,
            "consecutive_failures": 0,
            "last_checked_at": now,
            "last_healthy_at": now,
            "reason": None,
            "details": details,
        }
    )
    append_health_event(
        {
            "created_at": now,
            "source": source,
            "provider_id": provider_id,
            "model_id": model_id,
            "kind": kind,
            "ability": ability,
            "status": "healthy",
            "error_class": None,
            "error_code": None,
            "message": "ok",
            "details": details,
        }
    )
    recompute_provider_state(provider_id)


def record_health_failure(
    *,
    provider_id: str,
    model_id: str,
    kind: str,
    ability: str,
    source: str,
    exc: Exception,
    details: dict[str, Any] | None = None,
) -> None:
    now = utc_now()
    classification = classify_exception(exc)
    previous = next(
        (
            item
            for item in list_model_health_states()
            if item["provider_id"] == provider_id
            and item["model_id"] == model_id
            and item["kind"] == kind
            and item["ability"] == ability
        ),
        None,
    )
    failure_count = int(previous.get("consecutive_failures", 0) if previous else 0) + 1
    status = next_model_status(classification["error_class"], failure_count)
    upsert_model_health_state(
        {
            "provider_id": provider_id,
            "model_id": model_id,
            "kind": kind,
            "ability": ability,
            "status": status,
            "error_class": classification["error_class"],
            "error_code": classification["error_code"],
            "consecutive_failures": failure_count,
            "last_checked_at": now,
            "last_healthy_at": previous.get("last_healthy_at") if previous else None,
            "reason": classification["reason"],
            "details": details,
        }
    )
    append_health_event(
        {
            "created_at": now,
            "source": source,
            "provider_id": provider_id,
            "model_id": model_id,
            "kind": kind,
            "ability": ability,
            "status": status,
            "error_class": classification["error_class"],
            "error_code": classification["error_code"],
            "message": classification["reason"],
            "details": details,
        }
    )
    recompute_provider_state(provider_id)


def next_model_status(error_class: str, failure_count: int) -> str:
    if error_class in {FATAL_CONFIG, FATAL_MODEL, FATAL_CAPABILITY}:
        return "unhealthy"
    if failure_count >= 2:
        return "disabled_auto"
    return "degraded"


def recompute_provider_state(provider_id: str) -> dict[str, Any] | None:
    provider_state = read_provider_settings()
    providers = provider_state.get("providers", [])
    provider = next((item for item in providers if item["id"] == provider_id), None)
    if provider is None:
        return None

    policies = [item for item in list_provider_model_policies() if item["provider_id"] == provider_id]
    model_health = [item for item in list_model_health_states() if item["provider_id"] == provider_id]
    entries = build_model_health_entries(
        providers=providers,
        policies=policies,
        model_health_states=model_health,
    )
    summary = build_provider_health_summary(
        providers=[provider],
        provider_health_states=list_provider_health_states(),
        model_entries=entries,
    )[0]

    now = utc_now()
    previous = next(
        (item for item in list_provider_health_states() if item["provider_id"] == provider_id),
        None,
    )
    last_healthy_at = previous.get("last_healthy_at") if previous else None
    if summary["status"] == "healthy":
        last_healthy_at = now

    failure_count = previous.get("consecutive_failures", 0) if previous else 0
    if summary["status"] == "healthy":
        failure_count = 0
    elif summary["status"] in {"degraded", "unhealthy", "disabled_auto"}:
        failure_count = int(failure_count) + 1

    payload = {
        "provider_id": provider_id,
        "status": summary["status"],
        "last_checked_at": now,
        "last_healthy_at": last_healthy_at,
        "consecutive_failures": failure_count,
        "reason": summary.get("reason"),
        "details": {"ability_summary": summary.get("ability_summary", [])},
    }
    upsert_provider_health_state(payload)
    return payload


def keep_healthy_only() -> dict[str, Any]:
    provider_state = read_provider_settings()
    providers = provider_state.get("providers", [])
    provider_summaries = build_provider_health_summary(
        providers=providers,
        provider_health_states=list_provider_health_states(),
        model_entries=build_model_health_entries(
            providers=providers,
            policies=list_provider_model_policies(),
            model_health_states=list_model_health_states(),
        ),
    )
    provider_summary_lookup = {item["provider_id"]: item for item in provider_summaries}
    model_entries = build_model_health_entries(
        providers=providers,
        policies=list_provider_model_policies(),
        model_health_states=list_model_health_states(),
    )
    best_by_provider_kind: dict[tuple[str, str], str] = {}
    for entry in model_entries:
        if entry["overall_status"] != "healthy" or not entry["manual_enabled"]:
            continue
        key = (entry["provider_id"], entry["kind"])
        best_by_provider_kind.setdefault(key, entry["model_id"])

    updated_providers: list[dict[str, Any]] = []
    for provider in providers:
        next_provider = dict(provider)
        summary = provider_summary_lookup.get(provider["id"], {})
        if summary.get("status") in {"unhealthy", "disabled_auto"}:
            next_provider["manual_enabled"] = False
            next_provider["enabled"] = False
        defaults = dict(next_provider.get("default_models", {}))
        for kind in ("text", "image", "video"):
            model_id = str(defaults.get(kind) or "").strip()
            if not model_id:
                fallback = best_by_provider_kind.get((provider["id"], kind))
                if fallback:
                    defaults[kind] = fallback
                continue
            entry = next(
                (
                    item
                    for item in model_entries
                    if item["provider_id"] == provider["id"]
                    and item["kind"] == kind
                    and item["model_id"] == model_id
                ),
                None,
            )
            if entry is None or entry["overall_status"] != "healthy":
                defaults[kind] = best_by_provider_kind.get((provider["id"], kind), "")
        next_provider["default_models"] = defaults
        next_provider["text_model"] = defaults.get("text", "")
        next_provider["image_model"] = defaults.get("image", "")
        next_provider["video_model"] = defaults.get("video", "")
        next_provider["local_model"] = defaults.get("local", next_provider.get("local_model", ""))
        updated_providers.append(next_provider)

    for entry in model_entries:
        upsert_provider_model_policy(
            {
                "provider_id": entry["provider_id"],
                "model_id": entry["model_id"],
                "kind": entry["kind"],
                "manual_enabled": entry["overall_status"] == "healthy",
                "supported_abilities": entry["supported_abilities"],
            }
        )

    selected_provider_id = provider_state.get("selected_provider_id", "")
    if not any(item["id"] == selected_provider_id and item.get("manual_enabled", True) for item in updated_providers):
        selected_provider_id = next(
            (item["id"] for item in updated_providers if item.get("manual_enabled", True)),
            updated_providers[0]["id"] if updated_providers else "",
        )
    return update_provider_settings(selected_provider_id, updated_providers)


def recheck_and_restore(
    provider_summaries: list[dict[str, Any]],
    model_entries: list[dict[str, Any]],
) -> dict[str, Any]:
    provider_state = read_provider_settings()
    providers = provider_state.get("providers", [])
    summary_lookup = {item["provider_id"]: item for item in provider_summaries}
    model_lookup = {
        (item["provider_id"], item["kind"], item["model_id"]): item for item in model_entries
    }
    updated_providers: list[dict[str, Any]] = []
    for provider in providers:
        next_provider = dict(provider)
        summary = summary_lookup.get(provider["id"])
        if summary and summary["status"] in {"healthy", "degraded"}:
            next_provider["manual_enabled"] = True
            next_provider["enabled"] = True
        updated_providers.append(next_provider)

    for entry in model_entries:
        if entry["overall_status"] == "healthy":
            upsert_provider_model_policy(
                {
                    "provider_id": entry["provider_id"],
                    "model_id": entry["model_id"],
                    "kind": entry["kind"],
                    "manual_enabled": True,
                    "supported_abilities": entry["supported_abilities"],
                }
            )
        elif (entry["provider_id"], entry["kind"], entry["model_id"]) in model_lookup:
            upsert_provider_model_policy(
                {
                    "provider_id": entry["provider_id"],
                    "model_id": entry["model_id"],
                    "kind": entry["kind"],
                    "manual_enabled": False,
                    "supported_abilities": entry["supported_abilities"],
                }
            )

    selected_provider_id = provider_state.get("selected_provider_id", "")
    if not any(item["id"] == selected_provider_id and item.get("manual_enabled", True) for item in updated_providers):
        selected_provider_id = next(
            (item["id"] for item in updated_providers if item.get("manual_enabled", True)),
            updated_providers[0]["id"] if updated_providers else "",
        )
    return update_provider_settings(selected_provider_id, updated_providers)
