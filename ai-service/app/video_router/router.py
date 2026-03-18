from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings
from app.models.schemas import PromptPayload


@dataclass(slots=True)
class RoutingDecision:
    provider: str
    model: str


def route_provider(prompt: PromptPayload, task_payload: dict, has_human_reference: bool) -> RoutingDecision:
    high_quality = bool(task_payload.get("high_quality"))
    has_reference = bool(prompt.reference_images)
    if has_reference or has_human_reference:
        return RoutingDecision("minimax", settings.minimax_video_model)
    if prompt.duration >= 7:
        if settings.openai_video_api_key:
            return RoutingDecision("sora", settings.openai_video_model)
    if high_quality and settings.runway_api_key:
        return RoutingDecision("runway", settings.runway_video_model)
    if settings.minimax_api_key:
        return RoutingDecision("minimax", settings.minimax_video_model)
    if settings.runway_api_key:
        return RoutingDecision("runway", settings.runway_video_model)
    if settings.openai_video_api_key:
        return RoutingDecision("sora", settings.openai_video_model)
    raise RuntimeError("no enabled video provider is configured")
