from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import uvicorn

from ai_video_control.paths import REPO_ROOT
from ai_video_control.ws_manager import manager

from ai_video_control.web_service import (
    analyze_video_job_plan,
    create_video_job,
    ensure_character_generation_text_model_supported,
    get_app_state,
    generate_character_assets,
    generate_story_script,
    refresh_model_catalog,
    save_provider_connections,
    save_settings,
    read_text_file,
    render_shortform,
    render_video_job,
    resolve_repo_path,
    run_bridge_frame_selection,
    run_episode_review,
    run_keyframe_review,
    run_master_scene_review,
    generate_storyboard_outline,
    search_shortform_candidates,
)
from ai_video_control.web_tasks import get_task, list_tasks, submit_task
from ai_video_control.healthcheck import apply_health_action, run_health_checks

DIST_DIR = REPO_ROOT / "apps" / "admin-react" / "dist"

app = FastAPI(title="AI Video Studio Console")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SettingsPayload(BaseModel):
    OPENAI_BASE_URL: str = ""
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = ""
    TEXT_MODEL_OPTIONS: str = ""
    OPENAI_IMAGE_MODEL: str = ""
    IMAGE_MODEL_OPTIONS: str = ""
    OPENAI_VIDEO_MODEL: str = ""
    VIDEO_MODEL_OPTIONS: str = ""
    OPENAI_VIDEO_RATIO: str = ""
    OPENAI_VIDEO_DURATION: str = ""
    OPENAI_VIDEO_RESOLUTION: str = ""
    COMFYUI_URL: str = ""
    COGVIDEOX_MODEL_ID: str = ""


class ProviderSettingsPayload(BaseModel):
    selected_provider_id: str = ""
    providers: list[dict[str, Any]] = Field(default_factory=list)


class ProviderHealthRunPayload(BaseModel):
    provider_ids: list[str] = Field(default_factory=list)
    model_ids: list[str] = Field(default_factory=list)
    abilities: list[str] = Field(default_factory=list)
    include_disabled: bool = False


class ProviderHealthActionPayload(BaseModel):
    action: str


class ScriptGenerationPayload(BaseModel):
    slug: str = ""
    title: str
    concept: str
    tone: str = ""
    text_model: str = ""
    length_profile: str = "short"
    seed_text: str = ""


class CharacterGenerationPayload(BaseModel):
    slug: str
    concept: str
    text_model: str = ""
    image_model: str = ""
    reference_preset: str = "standard"
    reference_image: str = ""


class JobCreationPayload(BaseModel):
    job_id: str
    character_path: str
    provider: str
    scene_brief: str
    input_image: str | None = None
    reference_images: list[str] = Field(default_factory=list)
    script_path: str | None = None
    storyboard_notes: str = ""
    camera_plan: str = ""
    seed: int = 42
    fps: int = 16
    num_frames: int = 81


class StoryboardGenerationPayload(BaseModel):
    character_path: str
    script_path: str
    brief: str = ""
    text_model: str = ""
    shot_count: int = 4


class JobRenderPayload(BaseModel):
    job_path: str
    provider_override: str | None = None


class EpisodeActionPayload(BaseModel):
    spec_path: str
    image_model: str = ""
    video_model: str = ""
    ratio: str = ""
    duration: int | None = None
    resolution: str = ""


class QaActionPayload(BaseModel):
    episode_dir: str
    context: str = ""


class MasterSceneReviewPayload(BaseModel):
    spec_path: str
    candidate_image: str
    context: str = ""


class BridgeFramePayload(BaseModel):
    video_path: str
    anchor_image: str
    context: str = ""
    tail_ratio: float = Field(default=0.2, gt=0, le=1)
    max_candidates: int = Field(default=6, ge=1)


@app.get("/api/state")
def api_state() -> dict[str, Any]:
    return {
        "app": get_app_state(),
        "tasks": list_tasks(),
    }


@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/api/tasks")
def api_tasks() -> dict[str, Any]:
    return {"tasks": list_tasks()}


@app.get("/api/tasks/{task_id}")
def api_task(task_id: str) -> dict[str, Any]:
    try:
        return get_task(task_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Task not found") from exc


@app.post("/api/settings")
def api_save_settings(payload: SettingsPayload) -> dict[str, Any]:
    return {"settings": save_settings(payload.model_dump())}


@app.post("/api/providers")
def api_save_providers(payload: ProviderSettingsPayload) -> dict[str, Any]:
    return save_provider_connections(payload.selected_provider_id, payload.providers)


@app.post("/api/providers/health/run")
def api_run_provider_health(payload: ProviderHealthRunPayload) -> dict[str, Any]:
    return {
        "health_report": run_health_checks(
            provider_ids=payload.provider_ids or None,
            model_ids=payload.model_ids or None,
            abilities=payload.abilities or None,
            include_disabled=payload.include_disabled,
        )
    }


@app.post("/api/providers/health/apply")
def api_apply_provider_health(payload: ProviderHealthActionPayload) -> dict[str, Any]:
    return apply_health_action(payload.action)


@app.post("/api/models/refresh")
def api_refresh_models() -> dict[str, Any]:
    return {"health_report": refresh_model_catalog(), "state": get_app_state()}


@app.post("/api/scripts/generate")
def api_generate_script(payload: ScriptGenerationPayload) -> dict[str, Any]:
    task = submit_task(
        kind="generate_script",
        label=f"文案生成 {payload.title}",
        fn=lambda: generate_story_script(
            payload.slug,
            payload.title,
            payload.concept,
            payload.tone,
            payload.text_model or None,
            payload.length_profile or None,
            payload.seed_text,
        ),
        task_payload=payload.model_dump(),
    )
    return {"task": task}


@app.post("/api/characters/generate")
def api_generate_character(payload: CharacterGenerationPayload) -> dict[str, Any]:
    try:
        ensure_character_generation_text_model_supported(payload.text_model or None)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    task = submit_task(
        kind="generate_character",
        label=f"角色生成 {payload.slug}",
        fn=lambda: generate_character_assets(
            payload.slug,
            payload.concept,
            payload.text_model or None,
            payload.image_model or None,
            payload.reference_preset,
            payload.reference_image or None,
        ),
        task_payload=payload.model_dump(),
    )
    return {"task": task}


@app.post("/api/jobs/create")
def api_create_job(payload: JobCreationPayload) -> dict[str, Any]:
    return {"job": create_video_job(**payload.model_dump())}


@app.post("/api/jobs/preflight")
def api_preflight_job(payload: JobCreationPayload) -> dict[str, Any]:
    return {"analysis": analyze_video_job_plan(**payload.model_dump())}


@app.post("/api/storyboards/generate")
def api_generate_storyboard(payload: StoryboardGenerationPayload) -> dict[str, Any]:
    return {
        "storyboard": generate_storyboard_outline(
            character_path=payload.character_path,
            script_path=payload.script_path,
            brief=payload.brief,
            text_model=payload.text_model or None,
            shot_count=payload.shot_count,
        )
    }


@app.post("/api/jobs/render")
def api_render_job(payload: JobRenderPayload) -> dict[str, Any]:
    task = submit_task(
        kind="render_job",
        label=f"渲染任务 {payload.job_path}",
        fn=lambda: render_video_job(payload.job_path, payload.provider_override),
        task_payload=payload.model_dump(),
    )
    return {"task": task}


@app.post("/api/episodes/search-keyframes")
def api_search_keyframes(payload: EpisodeActionPayload) -> dict[str, Any]:
    task = submit_task(
        kind="search_keyframes",
        label=f"候选搜索 {payload.spec_path}",
        fn=lambda: search_shortform_candidates(
            payload.spec_path,
            image_model=payload.image_model or None,
            video_model=payload.video_model or None,
            ratio=payload.ratio or None,
            duration=payload.duration,
            resolution=payload.resolution or None,
        ),
    )
    return {"task": task}


@app.post("/api/episodes/render")
def api_render_episode(payload: EpisodeActionPayload) -> dict[str, Any]:
    task = submit_task(
        kind="render_shortform",
        label=f"整集渲染 {payload.spec_path}",
        fn=lambda: render_shortform(
            payload.spec_path,
            image_model=payload.image_model or None,
            video_model=payload.video_model or None,
            ratio=payload.ratio or None,
            duration=payload.duration,
            resolution=payload.resolution or None,
        ),
        task_payload=payload.model_dump(),
    )
    return {"task": task}


@app.post("/api/qa/review-episode")
def api_review_episode(payload: QaActionPayload) -> dict[str, Any]:
    task = submit_task(
        kind="review_episode",
        label=f"剧集复核 {payload.episode_dir}",
        fn=lambda: run_episode_review(payload.episode_dir, payload.context),
    )
    return {"task": task}


@app.post("/api/qa/review-keyframes")
def api_review_keyframes(payload: QaActionPayload) -> dict[str, Any]:
    task = submit_task(
        kind="review_keyframes",
        label=f"关键帧复核 {payload.episode_dir}",
        fn=lambda: run_keyframe_review(payload.episode_dir, payload.context),
    )
    return {"task": task}


@app.post("/api/qa/review-master-scene")
def api_review_master_scene(payload: MasterSceneReviewPayload) -> dict[str, Any]:
    task = submit_task(
        kind="review_master_scene",
        label=f"主场景复核 {payload.candidate_image}",
        fn=lambda: run_master_scene_review(payload.spec_path, payload.candidate_image, payload.context),
    )
    return {"task": task}


@app.post("/api/qa/select-bridge-frame")
def api_select_bridge_frame(payload: BridgeFramePayload) -> dict[str, Any]:
    task = submit_task(
        kind="select_bridge_frame",
        label=f"桥接帧筛选 {payload.video_path}",
        fn=lambda: run_bridge_frame_selection(
            payload.video_path,
            payload.anchor_image,
            payload.context,
            payload.tail_ratio,
            payload.max_candidates,
        ),
    )
    return {"task": task}


@app.get("/api/text")
def api_text(path: str) -> dict[str, Any]:
    try:
        return read_text_file(path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="File not found") from exc


@app.get("/api/files/{relative_path:path}")
def api_files(relative_path: str) -> FileResponse:
    try:
        file_path = resolve_repo_path(relative_path)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=404, detail="File not found") from exc
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)


if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")


@app.get("/{full_path:path}")
def spa(full_path: str) -> FileResponse:
    index_path = DIST_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(
            status_code=503,
            detail="Frontend bundle not found. Build frontend/admin-react before starting the web app.",
        )
    return FileResponse(index_path)


def main() -> None:
    uvicorn.run("ai_video_control.webapp:app", host="0.0.0.0", port=4180, reload=False)
