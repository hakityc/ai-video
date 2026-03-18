from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

from redis import Redis

from app.core.config import settings
from app.core.db import db
from app.models.schemas import PromptPayload
from app.prompt_builder.service import build_shot_prompt
from app.providers import MiniMaxProvider, RunwayProvider, SoraProvider
from app.storage.object_storage import storage
from app.video_router.router import route_provider


def start_generation_worker() -> threading.Thread:
    thread = threading.Thread(target=_worker_loop, name="generation-worker", daemon=True)
    thread.start()
    return thread


def _worker_loop() -> None:
    redis_client = Redis.from_url(f"redis://{settings.redis_addr}", password=settings.redis_password or None, decode_responses=True)
    try:
        redis_client.xgroup_create(settings.generation_stream, settings.generation_consumer_group, id="$", mkstream=True)
    except Exception:
        pass

    while True:
        response = redis_client.xreadgroup(
            groupname=settings.generation_consumer_group,
            consumername=settings.generation_consumer_name,
            streams={settings.generation_stream: ">"},
            count=1,
            block=5000,
        )
        if not response:
            time.sleep(1)
            continue
        for _, messages in response:
            for message_id, fields in messages:
                try:
                    payload = json.loads(fields["message"])
                    _process_generation_task(payload["id"])
                    redis_client.xack(settings.generation_stream, settings.generation_consumer_group, message_id)
                except Exception:
                    continue


def _process_generation_task(task_id: str) -> None:
    task_row = None
    try:
        with db.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT gt.id, gt.shot_id, gt.prompt_payload, s.episode_id, s.duration, s.description, s.shot_type,
                           s.camera_motion, s.subject_desc, s.action_desc, s.emotion_desc, s.dialogue_text, s.generation_mode,
                           e.project_id, p.style, p.aspect_ratio
                    FROM generation_tasks gt
                    JOIN shots s ON s.id = gt.shot_id
                    JOIN episodes e ON e.id = s.episode_id
                    JOIN projects p ON p.id = e.project_id
                    WHERE gt.id = %s
                    """,
                    (task_id,),
                )
                task_row = cur.fetchone()
                if not task_row:
                    return
                cur.execute(
                    "UPDATE generation_tasks SET status = %s, started_at = now(), updated_at = now() WHERE id = %s",
                    ("processing", task_id),
                )
                conn.commit()

        task_payload = task_row["prompt_payload"] or {}
        if isinstance(task_payload, str):
            task_payload = json.loads(task_payload)
        characters = _fetch_project_characters(task_row["project_id"])
        locations = _fetch_project_locations(task_row["project_id"])
        shot_payload = {
            "duration": task_row["duration"],
            "description": task_row["description"],
            "shot_type": task_row["shot_type"],
            "camera_motion": task_row["camera_motion"],
            "subject_desc": task_row["subject_desc"],
            "action_desc": task_row["action_desc"],
            "emotion_desc": task_row["emotion_desc"],
            "dialogue_text": task_row["dialogue_text"],
            "generation_mode": task_row["generation_mode"],
        }
        project_payload = {
            "style": task_row["style"],
            "aspect_ratio": task_row["aspect_ratio"],
        }
        prompt = build_shot_prompt(shot_payload, project_payload, characters, locations)
        decision = route_provider(prompt, task_payload, has_human_reference=bool(prompt.reference_images))
        provider = _build_provider(decision.provider)
        submission = provider.submit(prompt)
        result = provider.poll(submission)
        object_key = str(Path("projects") / str(task_row["project_id"]) / "shots" / str(task_row["shot_id"]) / f"{task_id}.mp4")
        object_url = storage.upload_bytes(object_key, result.file_bytes, result.mime_type)
        _finalize_success(task_row, task_id, prompt, decision.provider, decision.model, object_key, object_url, result.raw_payload)
    except Exception as exc:
        if task_row is not None:
            _finalize_failure(task_row, task_id, str(exc))


def _build_provider(provider_name: str):
    if provider_name == "minimax":
        return MiniMaxProvider()
    if provider_name == "runway":
        return RunwayProvider()
    if provider_name == "sora":
        return SoraProvider()
    raise RuntimeError(f"unsupported provider: {provider_name}")


def _fetch_project_characters(project_id: str) -> list[dict[str, Any]]:
    with db.connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT id::text, name, reference_assets FROM characters WHERE project_id = %s ORDER BY created_at ASC", (project_id,))
        rows = cur.fetchall()
    result = []
    for row in rows:
        result.append(
            {
                "id": row["id"],
                "name": row["name"],
                "reference_assets": row["reference_assets"] or [],
            }
        )
    return result


def _fetch_project_locations(project_id: str) -> list[dict[str, Any]]:
    with db.connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT id::text, name, description, reference_assets FROM locations WHERE project_id = %s ORDER BY created_at ASC", (project_id,))
        rows = cur.fetchall()
    result = []
    for row in rows:
        result.append(
            {
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "reference_assets": row["reference_assets"] or [],
            }
        )
    return result


def _finalize_success(task_row: dict[str, Any], task_id: str, prompt: PromptPayload, provider: str, model: str, object_key: str, object_url: str, raw_payload: dict[str, Any]) -> None:
    with db.connection() as conn, conn.cursor() as cur:
        asset_id = cur.execute(
            """
            INSERT INTO assets(id, project_id, kind, bucket, object_key, url, metadata, created_at)
            VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s::jsonb, now())
            RETURNING id
            """,
            (
                task_row["project_id"],
                "shot_video",
                settings.minio_bucket,
                object_key,
                object_url,
                json.dumps({"task_id": task_id}),
            ),
        ).fetchone()["id"]
        version_id = cur.execute(
            """
            INSERT INTO shot_versions(id, shot_id, task_id, asset_id, provider, model, is_selected, prompt_payload, metadata, created_at)
            VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, false, %s::jsonb, %s::jsonb, now())
            RETURNING id
            """,
            (
                task_row["shot_id"],
                task_id,
                asset_id,
                provider,
                model,
                prompt.model_dump_json(),
                json.dumps({"external_payload": raw_payload}),
            ),
        ).fetchone()["id"]
        cur.execute(
            """
            UPDATE generation_tasks
            SET provider = %s, model = %s, status = %s, raw_payload = %s::jsonb, output_asset_id = %s, completed_at = now(), updated_at = now()
            WHERE id = %s
            """,
            (provider, model, "success", json.dumps(raw_payload), asset_id, task_id),
        )
        cur.execute(
            """
            UPDATE shots
            SET status = %s, current_version_id = COALESCE(current_version_id, %s), updated_at = now()
            WHERE id = %s
            """,
            ("success", version_id, task_row["shot_id"]),
        )
        conn.commit()


def _finalize_failure(task_row: dict[str, Any], task_id: str, error_message: str) -> None:
    with db.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE generation_tasks
            SET status = %s, error_message = %s, completed_at = now(), updated_at = now()
            WHERE id = %s
            """,
            ("failed", error_message, task_id),
        )
        cur.execute(
            """
            UPDATE shots
            SET status = CASE
                WHEN EXISTS (
                    SELECT 1 FROM shot_versions WHERE shot_versions.shot_id = shots.id
                ) THEN shots.status
                ELSE 'failed'
            END,
            updated_at = now()
            WHERE id = %s
            """,
            (task_row["shot_id"],),
        )
        conn.commit()
