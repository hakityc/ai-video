from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


REPO_ROOT = Path.cwd().resolve()
DB_DIR = REPO_ROOT / "artifacts" / "web"
DB_PATH = DB_DIR / "control-plane.db"


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
