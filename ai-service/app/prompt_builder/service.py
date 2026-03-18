from __future__ import annotations

from typing import Any

from app.models.schemas import PromptPayload


def build_shot_prompt(shot: dict[str, Any], project: dict[str, Any], characters: list[dict[str, Any]], locations: list[dict[str, Any]]) -> PromptPayload:
    reference_images: list[str] = []
    for character in characters:
        for item in character.get("reference_assets", []):
            url = item.get("url")
            if url:
                reference_images.append(url)
    for location in locations:
        for item in location.get("reference_assets", []):
            url = item.get("url")
            if url:
                reference_images.append(url)
    return PromptPayload(
        scene=locations[0]["description"] if locations else shot.get("description", ""),
        character=", ".join([item["name"] for item in characters]) or shot.get("subject_desc", ""),
        action=shot.get("action_desc", ""),
        emotion=shot.get("emotion_desc", ""),
        style=project.get("style", "cinematic"),
        camera=shot.get("camera_motion", ""),
        duration=int(shot.get("duration", 4)),
        dialogue=shot.get("dialogue_text", ""),
        reference_images=reference_images[:4],
    )
