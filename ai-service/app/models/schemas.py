from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class StoryCardResponse(BaseModel):
    theme: str
    conflict: str
    twist: str
    ending_hook: str
    summary: str


class SceneResponse(BaseModel):
    summary: str
    involved_character_ids: list[str] = Field(default_factory=list)
    involved_location_ids: list[str] = Field(default_factory=list)


class ShotResponse(BaseModel):
    scene_order: int
    duration: int
    description: str
    shot_type: str
    camera_motion: str
    subject_desc: str
    action_desc: str
    emotion_desc: str
    dialogue_text: str = ""
    generation_mode: str = "text"


class StoryboardResponse(BaseModel):
    scenes: list[SceneResponse]
    shots: list[ShotResponse]


class PromptPayload(BaseModel):
    scene: str
    character: str
    action: str
    emotion: str
    style: str
    camera: str
    duration: int
    dialogue: str = ""
    reference_images: list[str] = Field(default_factory=list)


class VideoSubmission(BaseModel):
    provider: str
    model: str
    external_id: str
    raw_payload: dict[str, Any]


class VideoResult(BaseModel):
    provider: str
    model: str
    external_id: str
    status: str
    file_bytes: bytes
    mime_type: str
    raw_payload: dict[str, Any]
