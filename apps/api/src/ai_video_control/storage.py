from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from ai_video_control.paths import DB_DIR, DB_PATH


def ensure_database() -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                label TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                started_at TEXT,
                ended_at TEXT,
                result_json TEXT,
                error_json TEXT
            );

            CREATE TABLE IF NOT EXISTS cache_entries (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS provider_health_states (
                provider_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                last_checked_at TEXT,
                last_healthy_at TEXT,
                consecutive_failures INTEGER NOT NULL DEFAULT 0,
                reason TEXT,
                details_json TEXT,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS model_health_states (
                provider_id TEXT NOT NULL,
                model_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                ability TEXT NOT NULL,
                status TEXT NOT NULL,
                error_class TEXT,
                error_code TEXT,
                consecutive_failures INTEGER NOT NULL DEFAULT 0,
                last_checked_at TEXT,
                last_healthy_at TEXT,
                reason TEXT,
                details_json TEXT,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (provider_id, model_id, kind, ability)
            );

            CREATE TABLE IF NOT EXISTS health_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                source TEXT NOT NULL,
                provider_id TEXT,
                model_id TEXT,
                kind TEXT,
                ability TEXT,
                status TEXT NOT NULL,
                error_class TEXT,
                error_code TEXT,
                message TEXT,
                details_json TEXT
            );

            CREATE TABLE IF NOT EXISTS provider_model_policies (
                provider_id TEXT NOT NULL,
                model_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                manual_enabled INTEGER NOT NULL DEFAULT 1,
                supported_abilities_json TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (provider_id, model_id, kind)
            );
            """
        )


def read_settings_map() -> dict[str, str]:
    ensure_database()
    with _connect() as connection:
        rows = connection.execute("SELECT key, value FROM settings").fetchall()
    return {row["key"]: row["value"] for row in rows}


def upsert_settings_map(values: dict[str, str]) -> None:
    ensure_database()
    with _connect() as connection:
        connection.executemany(
            """
            INSERT INTO settings (key, value, updated_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(key) DO UPDATE SET
                value=excluded.value,
                updated_at=datetime('now')
            """,
            [(key, value) for key, value in values.items()],
        )
        connection.commit()


def read_cache_value(key: str) -> str | None:
    ensure_database()
    with _connect() as connection:
        row = connection.execute(
            """
            SELECT value
            FROM cache_entries
            WHERE key = ?
            """,
            (key,),
        ).fetchone()
    return row["value"] if row else None


def read_cache_entry(key: str) -> dict[str, str] | None:
    ensure_database()
    with _connect() as connection:
        row = connection.execute(
            """
            SELECT key, value, updated_at
            FROM cache_entries
            WHERE key = ?
            """,
            (key,),
        ).fetchone()
    if not row:
        return None
    return {
        "key": row["key"],
        "value": row["value"],
        "updated_at": row["updated_at"],
    }


def upsert_cache_value(key: str, value: str) -> None:
    ensure_database()
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO cache_entries (key, value, updated_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(key) DO UPDATE SET
                value=excluded.value,
                updated_at=datetime('now')
            """,
            (key, value),
        )
        connection.commit()


def list_provider_health_states() -> list[dict[str, Any]]:
    ensure_database()
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT provider_id, status, last_checked_at, last_healthy_at,
                   consecutive_failures, reason, details_json, updated_at
            FROM provider_health_states
            ORDER BY provider_id ASC
            """
        ).fetchall()
    return [
        {
            "provider_id": row["provider_id"],
            "status": row["status"],
            "last_checked_at": row["last_checked_at"],
            "last_healthy_at": row["last_healthy_at"],
            "consecutive_failures": row["consecutive_failures"],
            "reason": row["reason"],
            "details": json.loads(row["details_json"]) if row["details_json"] else None,
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]


def upsert_provider_health_state(payload: dict[str, Any]) -> None:
    ensure_database()
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO provider_health_states (
                provider_id, status, last_checked_at, last_healthy_at,
                consecutive_failures, reason, details_json, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(provider_id) DO UPDATE SET
                status=excluded.status,
                last_checked_at=excluded.last_checked_at,
                last_healthy_at=excluded.last_healthy_at,
                consecutive_failures=excluded.consecutive_failures,
                reason=excluded.reason,
                details_json=excluded.details_json,
                updated_at=datetime('now')
            """,
            (
                payload["provider_id"],
                payload["status"],
                payload.get("last_checked_at"),
                payload.get("last_healthy_at"),
                int(payload.get("consecutive_failures") or 0),
                payload.get("reason"),
                json.dumps(payload.get("details")) if payload.get("details") is not None else None,
            ),
        )
        connection.commit()


def list_model_health_states() -> list[dict[str, Any]]:
    ensure_database()
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT provider_id, model_id, kind, ability, status,
                   error_class, error_code, consecutive_failures,
                   last_checked_at, last_healthy_at, reason, details_json, updated_at
            FROM model_health_states
            ORDER BY provider_id ASC, kind ASC, model_id ASC, ability ASC
            """
        ).fetchall()
    return [
        {
            "provider_id": row["provider_id"],
            "model_id": row["model_id"],
            "kind": row["kind"],
            "ability": row["ability"],
            "status": row["status"],
            "error_class": row["error_class"],
            "error_code": row["error_code"],
            "consecutive_failures": row["consecutive_failures"],
            "last_checked_at": row["last_checked_at"],
            "last_healthy_at": row["last_healthy_at"],
            "reason": row["reason"],
            "details": json.loads(row["details_json"]) if row["details_json"] else None,
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]


def upsert_model_health_state(payload: dict[str, Any]) -> None:
    ensure_database()
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO model_health_states (
                provider_id, model_id, kind, ability, status,
                error_class, error_code, consecutive_failures,
                last_checked_at, last_healthy_at, reason, details_json, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(provider_id, model_id, kind, ability) DO UPDATE SET
                status=excluded.status,
                error_class=excluded.error_class,
                error_code=excluded.error_code,
                consecutive_failures=excluded.consecutive_failures,
                last_checked_at=excluded.last_checked_at,
                last_healthy_at=excluded.last_healthy_at,
                reason=excluded.reason,
                details_json=excluded.details_json,
                updated_at=datetime('now')
            """,
            (
                payload["provider_id"],
                payload["model_id"],
                payload["kind"],
                payload["ability"],
                payload["status"],
                payload.get("error_class"),
                payload.get("error_code"),
                int(payload.get("consecutive_failures") or 0),
                payload.get("last_checked_at"),
                payload.get("last_healthy_at"),
                payload.get("reason"),
                json.dumps(payload.get("details")) if payload.get("details") is not None else None,
            ),
        )
        connection.commit()


def append_health_event(payload: dict[str, Any]) -> None:
    ensure_database()
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO health_events (
                created_at, source, provider_id, model_id, kind, ability,
                status, error_class, error_code, message, details_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["created_at"],
                payload["source"],
                payload.get("provider_id"),
                payload.get("model_id"),
                payload.get("kind"),
                payload.get("ability"),
                payload["status"],
                payload.get("error_class"),
                payload.get("error_code"),
                payload.get("message"),
                json.dumps(payload.get("details")) if payload.get("details") is not None else None,
            ),
        )
        connection.commit()


def list_provider_model_policies() -> list[dict[str, Any]]:
    ensure_database()
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT provider_id, model_id, kind, manual_enabled, supported_abilities_json, updated_at
            FROM provider_model_policies
            ORDER BY provider_id ASC, kind ASC, model_id ASC
            """
        ).fetchall()
    return [
        {
            "provider_id": row["provider_id"],
            "model_id": row["model_id"],
            "kind": row["kind"],
            "manual_enabled": bool(row["manual_enabled"]),
            "supported_abilities": json.loads(row["supported_abilities_json"]),
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]


def upsert_provider_model_policy(payload: dict[str, Any]) -> None:
    ensure_database()
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO provider_model_policies (
                provider_id, model_id, kind, manual_enabled, supported_abilities_json, updated_at
            )
            VALUES (?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(provider_id, model_id, kind) DO UPDATE SET
                manual_enabled=excluded.manual_enabled,
                supported_abilities_json=excluded.supported_abilities_json,
                updated_at=datetime('now')
            """,
            (
                payload["provider_id"],
                payload["model_id"],
                payload["kind"],
                1 if payload.get("manual_enabled", True) else 0,
                json.dumps(payload.get("supported_abilities") or []),
            ),
        )
        connection.commit()


def list_task_records(limit: int = 20) -> list[dict[str, Any]]:
    ensure_database()
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT id, kind, label, status, created_at, started_at, ended_at, result_json, error_json
            FROM tasks
            ORDER BY datetime(created_at) DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [_deserialize_task_row(row) for row in rows]


def get_task_record(task_id: str) -> dict[str, Any] | None:
    ensure_database()
    with _connect() as connection:
        row = connection.execute(
            """
            SELECT id, kind, label, status, created_at, started_at, ended_at, result_json, error_json
            FROM tasks
            WHERE id = ?
            """,
            (task_id,),
        ).fetchone()
    return _deserialize_task_row(row) if row else None


def upsert_task_record(payload: dict[str, Any]) -> None:
    ensure_database()
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO tasks (id, kind, label, status, created_at, started_at, ended_at, result_json, error_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                kind=excluded.kind,
                label=excluded.label,
                status=excluded.status,
                created_at=excluded.created_at,
                started_at=excluded.started_at,
                ended_at=excluded.ended_at,
                result_json=excluded.result_json,
                error_json=excluded.error_json
            """,
            (
                payload["id"],
                payload["kind"],
                payload["label"],
                payload["status"],
                payload["created_at"],
                payload.get("started_at"),
                payload.get("ended_at"),
                json.dumps(payload.get("result")) if payload.get("result") is not None else None,
                json.dumps(payload.get("error")) if payload.get("error") is not None else None,
            ),
        )
        connection.commit()


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _deserialize_task_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "kind": row["kind"],
        "label": row["label"],
        "status": row["status"],
        "created_at": row["created_at"],
        "started_at": row["started_at"],
        "ended_at": row["ended_at"],
        "result": json.loads(row["result_json"]) if row["result_json"] else None,
        "error": json.loads(row["error_json"]) if row["error_json"] else None,
    }
