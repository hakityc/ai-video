from __future__ import annotations

import json

from app.models.schemas import StoryCardResponse
from app.text.providers import build_text_provider


def generate_story_card(payload: dict) -> StoryCardResponse:
    provider = build_text_provider()
    prompt = (
        "你是剧情短视频编剧。根据以下 JSON 输入，返回严格 JSON，字段必须包含 "
        "theme, conflict, twist, ending_hook, summary。\n"
        f"输入:\n{json.dumps(payload, ensure_ascii=False)}"
    )
    result = provider.complete_json(prompt)
    return StoryCardResponse.model_validate(result)
