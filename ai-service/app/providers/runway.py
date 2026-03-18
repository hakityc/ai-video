from __future__ import annotations

import time

import httpx

from app.core.config import settings
from app.models.schemas import PromptPayload, VideoResult, VideoSubmission


class RunwayProvider:
    provider_name = "runway"
    api_version = "2024-11-06"

    def __init__(self) -> None:
        if not settings.runway_api_key:
            raise RuntimeError("RUNWAY_API_KEY is required")
        self.client = httpx.Client(
            timeout=settings.ai_provider_timeout_seconds,
            headers={
                "Authorization": f"Bearer {settings.runway_api_key}",
                "X-Runway-Version": self.api_version,
                "Content-Type": "application/json",
            },
        )

    def submit(self, prompt: PromptPayload) -> VideoSubmission:
        ratio = "720:1280"
        payload: dict[str, object] = {
            "model": settings.runway_video_model,
            "promptText": self._compose_prompt(prompt),
            "duration": prompt.duration,
            "ratio": ratio,
        }
        endpoint = "/v1/text_to_video"
        if prompt.reference_images:
            endpoint = "/v1/image_to_video"
            payload["promptImage"] = prompt.reference_images[0]
        response = self.client.post(f"{settings.runway_api_base.rstrip('/')}{endpoint}", json=payload)
        response.raise_for_status()
        data = response.json()
        return VideoSubmission(
            provider=self.provider_name,
            model=settings.runway_video_model,
            external_id=data["id"],
            raw_payload=data,
        )

    def poll(self, submission: VideoSubmission) -> VideoResult:
        while True:
            response = self.client.get(f"{settings.runway_api_base.rstrip('/')}/v1/tasks/{submission.external_id}")
            response.raise_for_status()
            data = response.json()
            status = str(data.get("status", "")).lower()
            if status in {"succeeded", "completed"}:
                output = data.get("output") or []
                output_url = output[0] if isinstance(output, list) and output else data.get("url")
                if not output_url:
                    raise RuntimeError("Runway task completed without output URL")
                video_response = self.client.get(output_url)
                video_response.raise_for_status()
                return VideoResult(
                    provider=self.provider_name,
                    model=submission.model,
                    external_id=submission.external_id,
                    status="completed",
                    file_bytes=video_response.content,
                    mime_type=video_response.headers.get("Content-Type", "video/mp4"),
                    raw_payload=data,
                )
            if status in {"failed", "canceled"}:
                raise RuntimeError(data.get("failure") or "Runway generation failed")
            time.sleep(settings.poll_interval_seconds)

    def _compose_prompt(self, prompt: PromptPayload) -> str:
        return f"{prompt.scene}. {prompt.character}. {prompt.action}. {prompt.emotion}. {prompt.style}. {prompt.camera}."
