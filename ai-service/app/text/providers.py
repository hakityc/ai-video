from __future__ import annotations

import json
from typing import Any

import httpx

from app.core.config import settings


class TextModelProvider:
    def complete_json(self, prompt: str) -> dict[str, Any]:
        raise NotImplementedError


class OpenAICompatibleTextProvider(TextModelProvider):
    def __init__(self) -> None:
        self.base_url = settings.openai_base_url.rstrip("/")
        self.api_key = settings.openai_api_key
        self.model = settings.text_model
        self.client = httpx.Client(timeout=settings.ai_provider_timeout_seconds)

    def complete_json(self, prompt: str) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required for openai-compatible text provider")
        response = self.client.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.4,
                "response_format": {"type": "json_object"},
            },
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)


class HeuristicTextProvider(TextModelProvider):
    def complete_json(self, prompt: str) -> dict[str, Any]:
        lowered = prompt.lower()
        if "storyboard" in lowered or "scenes and shots" in lowered or "分镜" in prompt:
            return {
                "scenes": [
                    {
                        "summary": "夜雨中的便利店，主角独自进入店内搜索线索。",
                        "involved_character_ids": [],
                        "involved_location_ids": [],
                    },
                    {
                        "summary": "主角发现录音笔并听到关键录音，情绪迅速变化。",
                        "involved_character_ids": [],
                        "involved_location_ids": [],
                    },
                ],
                "shots": [
                    {
                        "scene_order": 1,
                        "duration": 4,
                        "description": "雨夜外景，主角推门进入便利店。",
                        "shot_type": "wide",
                        "camera_motion": "slow push in",
                        "subject_desc": "young protagonist entering convenience store",
                        "action_desc": "opens door and scans surroundings",
                        "emotion_desc": "cautious",
                        "dialogue_text": "",
                        "generation_mode": "text",
                    },
                    {
                        "scene_order": 2,
                        "duration": 4,
                        "description": "主角在货架旁发现录音笔并拿起。",
                        "shot_type": "medium",
                        "camera_motion": "handheld follow",
                        "subject_desc": "protagonist near the shelf",
                        "action_desc": "finds recorder and lifts it",
                        "emotion_desc": "tense",
                        "dialogue_text": "",
                        "generation_mode": "reference",
                    },
                ],
            }
        return {
            "theme": "秘密被意外揭开",
            "conflict": "主角必须判断是否继续追查录音中的真相",
            "twist": "录音内容指向主角最信任的人",
            "ending_hook": "录音最后一句话暗示更大的阴谋刚刚开始",
            "summary": "一个人在雨夜便利店发现录音笔，由此被卷入更危险的真相。",
        }


def build_text_provider() -> TextModelProvider:
    if settings.text_provider == "openai-compatible" and settings.openai_api_key:
        return OpenAICompatibleTextProvider()
    return HeuristicTextProvider()
