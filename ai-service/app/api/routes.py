from __future__ import annotations

from fastapi import APIRouter

from app.story.service import generate_story_card
from app.storyboard.service import generate_storyboard

router = APIRouter(prefix="/v1")


@router.post("/story-card:generate")
def story_card(payload: dict) -> dict:
    return generate_story_card(payload).model_dump()


@router.post("/storyboard:generate")
def storyboard(payload: dict) -> dict:
    return generate_storyboard(payload).model_dump()
