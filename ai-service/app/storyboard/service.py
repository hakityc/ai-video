from __future__ import annotations

import json

from app.models.schemas import StoryboardResponse
from app.text.providers import build_text_provider


def generate_storyboard(payload: dict) -> StoryboardResponse:
    provider = build_text_provider()
    prompt = (
        "你是分镜导演。根据以下 JSON 输入，返回严格 JSON，包含 scenes 和 shots。"
        "每个 shot 必须包含 scene_order, duration, description, shot_type, camera_motion, subject_desc, "
        "action_desc, emotion_desc, dialogue_text, generation_mode。\n"
        "duration 必须是 3 到 8 的整数。\n"
        f"输入:\n{json.dumps(payload, ensure_ascii=False)}"
    )
    result = provider.complete_json(prompt)
    return StoryboardResponse.model_validate(result)
