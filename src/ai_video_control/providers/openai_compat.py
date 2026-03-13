from __future__ import annotations

import json
import base64
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List

import httpx
from PIL import Image

from ai_video_control.settings import Settings


class OpenAICompatClient:
    def __init__(self, settings: Settings) -> None:
        if not settings.openai_base_url or not settings.openai_api_key:
            raise RuntimeError("OPENAI_BASE_URL and OPENAI_API_KEY are required")
        self.settings = settings
        self.client = self._build_client()

    def _build_client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self.settings.openai_base_url.rstrip("/"),
            headers={
                "Authorization": f"Bearer {self.settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(connect=20.0, read=60.0, write=60.0, pool=20.0),
        )

    def _reset_client(self) -> None:
        try:
            self.client.close()
        except Exception:  # noqa: BLE001
            pass
        self.client = self._build_client()

    def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = self.client.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt == 2:
                    break
                self._reset_client()
        assert last_error is not None
        raise last_error

    def chat_json(self, prompt: str, model: str | None = None) -> Dict[str, Any]:
        payload = {
            "model": model or self.settings.openai_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 1200,
        }
        response = self._request("POST", "/chat/completions", json=payload)
        data = response.json()
        message = data["choices"][0]["message"]["content"]
        start = message.find("{")
        end = message.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("Model did not return JSON content")
        return json.loads(message[start : end + 1])

    def chat_text(self, prompt: str, model: str | None = None, max_tokens: int = 1600) -> str:
        payload = {
            "model": model or self.settings.openai_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": max_tokens,
        }
        response = self._request("POST", "/chat/completions", json=payload)
        data = response.json()
        return str(data["choices"][0]["message"]["content"]).strip()

    def chat_json_with_content(
        self,
        content: List[Dict[str, Any]],
        model: str | None = None,
        max_tokens: int = 1200,
    ) -> Dict[str, Any]:
        payload = {
            "model": model or self.settings.openai_model,
            "messages": [{"role": "user", "content": content}],
            "temperature": 0.4,
            "max_tokens": max_tokens,
        }
        response = self._request("POST", "/chat/completions", json=payload)
        data = response.json()
        message = str(data["choices"][0]["message"]["content"])
        start = message.find("{")
        end = message.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("Model did not return JSON content")
        return json.loads(message[start : end + 1])

    def generate_image_with_meta(
        self,
        prompt: str,
        output_path: Path,
        model: str | None = None,
        size: str = "1024x1024",
    ) -> Dict[str, Any]:
        payload = {
            "model": model or self.settings.openai_image_model,
            "prompt": prompt,
            "size": size,
        }
        response = self._request("POST", "/images/generations", json=payload)
        data = response.json()
        url = data["data"][0]["url"]
        image_response = self._request("GET", url)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(image_response.content)
        return {
            "output_path": str(output_path),
            "url": url,
            "response": data,
        }

    def generate_image(
        self,
        prompt: str,
        output_path: Path,
        model: str | None = None,
        size: str = "1024x1024",
    ) -> Path:
        self.generate_image_with_meta(
            prompt=prompt,
            output_path=output_path,
            model=model,
            size=size,
        )
        return output_path

    def submit_video_task(
        self,
        content: List[Dict[str, Any]],
        model: str,
        **extra: Any,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": model,
            "content": content,
        }
        payload.update(extra)
        response = self._request("POST", "/contents/generations/tasks", json=payload)
        return response.json()

    def get_video_task(self, task_id: str) -> Dict[str, Any]:
        response = self._request("GET", f"/contents/generations/tasks/{task_id}")
        return response.json()

    def download_file(self, url: str, output_path: Path) -> Path:
        response = self._request("GET", url)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(response.content)
        return output_path


def build_character_brief_prompt(concept: str) -> str:
    return (
        "Create a grounded cinematic character brief for an AI-generated shortform video protagonist. "
        "Return JSON only with keys: "
        "name, age_range, face, hair, body, outfit, accessories, style_descriptors, color_palette, "
        "negative_prompt. "
        "Each of face, hair, body, outfit, accessories, style_descriptors must be an array of short strings. "
        "color_palette must be an array of 3 to 5 specific color names or hex values. "
        "Keep the character visually distinctive, realistic, and stable across repeated generations. "
        "Avoid vague words and use exact descriptors that can be reused verbatim in later prompts. "
        f"Concept: {concept}"
    )


def image_path_to_data_url(image_path: Path, max_size: int = 1024) -> str:
    image = Image.open(image_path).convert("RGB")
    image.thumbnail((max_size, max_size))
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=88)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def build_reference_image_prompts(
    brief: Dict[str, Any],
    reference_preset: str = "standard",
) -> List[Dict[str, str]]:
    name = brief["name"]
    anchors = ", ".join(
        brief["face"] + brief["hair"] + brief["body"] + brief["outfit"] + brief["accessories"]
    )
    style = ", ".join(brief["style_descriptors"])
    common = (
        f"{name}, {anchors}, {style}, grounded cinematic live-action character design, "
        "high detail, realistic skin texture, natural anatomy, consistent face identity"
    )
    prompts = [
        {
            "suffix": "front",
            "view": "front",
            "expression": "neutral",
            "prompt": (
                f"{common}, straight-on portrait, neutral expression, chest-up, clean studio background, "
                "soft key light, character reference image"
            ),
        },
        {
            "suffix": "three-quarter",
            "view": "three-quarter",
            "expression": "calm",
            "prompt": (
                f"{common}, three-quarter portrait, calm expression, chest-up, clean studio background, "
                "soft cinematic rim light, character reference image"
            ),
        },
    ]

    if reference_preset == "turnaround":
        prompts.extend(
            [
                {
                    "suffix": "side",
                    "view": "side",
                    "expression": "neutral",
                    "prompt": (
                        f"{common}, side profile portrait, neutral expression, chest-up, clean studio background, "
                        "reference sheet lighting, consistent face identity"
                    ),
                },
                {
                    "suffix": "full-body",
                    "view": "full-body",
                    "expression": "neutral",
                    "prompt": (
                        f"{common}, full-body standing pose, neutral expression, full outfit visible, clean studio background, "
                        "character turnaround reference, same character, reference sheet layout"
                    ),
                },
            ]
        )

    return prompts
