from __future__ import annotations

import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Callable

from ai_video_control.storage import get_task_record, list_task_records, upsert_task_record

EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="aivideo-web")


def submit_task(kind: str, label: str, fn: Callable[[], Any]) -> dict[str, Any]:
    task_id = uuid.uuid4().hex
    payload = {
        "id": task_id,
        "kind": kind,
        "label": label,
        "status": "queued",
        "created_at": _now(),
        "started_at": None,
        "ended_at": None,
        "result": None,
        "error": None,
    }
    _write_task(task_id, payload)
    EXECUTOR.submit(_run_task, task_id, fn)
    return payload


def list_tasks(limit: int = 20) -> list[dict[str, Any]]:
    _migrate_legacy_tasks_if_needed()
    return list_task_records(limit)


def get_task(task_id: str) -> dict[str, Any]:
    _migrate_legacy_tasks_if_needed()
    payload = get_task_record(task_id)
    if payload is None:
        raise FileNotFoundError(task_id)
    return payload


def _run_task(task_id: str, fn: Callable[[], Any]) -> None:
    payload = get_task(task_id)
    payload["status"] = "running"
    payload["started_at"] = _now()
    _write_task(task_id, payload)
    from ai_video_control.ws_manager import manager
    manager.sync_broadcast({"type": "state_updated"})
    try:
        result = fn()
        payload["status"] = "succeeded"
        payload["result"] = result
    except Exception as exc:  # noqa: BLE001
        payload["status"] = "failed"
        payload["error"] = {
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    payload["ended_at"] = _now()
    _write_task(task_id, payload)
    manager.sync_broadcast({"type": "state_updated"})


def _write_task(task_id: str, payload: dict[str, Any]) -> None:
    upsert_task_record(payload)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _migrate_legacy_tasks_if_needed() -> None:
    """One-time migration: import any old JSON task files into the database."""
    if list_task_records(1):
        return
    import json
    from pathlib import Path
    from ai_video_control.paths import DB_DIR
    task_dir = DB_DIR / "tasks"
    if not task_dir.exists():
        return
    for path in sorted(task_dir.glob("*.json")):
        try:
            upsert_task_record(json.loads(path.read_text(encoding="utf-8")))
        except Exception:  # noqa: BLE001
            pass
