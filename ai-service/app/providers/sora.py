from __future__ import annotations

import time

import httpx

from app.core.config import settings
from app.models.schemas import PromptPayload, VideoResult, VideoSubmission


class SoraProvider:
    provider_name = "sora"

    def __init__(self) -> None:
        if not settings.openai_video_api_key:
            raise RuntimeError("OPENAI_VIDEO_API_KEY is required")
        self.client = httpx.Client(
            timeout=settings.ai_provider_timeout_seconds,
            headers={
                "Authorization": f"Bearer {settings.openai_video_api_key}",
            },
        )

    def submit(self, prompt: PromptPayload) -> VideoSubmission:
        response = self.client.post(
            f"{settings.openai_base_url.rstrip('/')}/videos",
            files={
                "model": (None, settings.openai_video_model),
                "prompt": (None, self._compose_prompt(prompt)),
                "size": (None, "720x1280"),
                "seconds": (None, str(prompt.duration)),
            },
        )
        response.raise_for_status()
        data = response.json()
        return VideoSubmission(
            provider=self.provider_name,
            model=settings.openai_video_model,
            external_id=data["id"],
            raw_payload=data,
        )

    def poll(self, submission: VideoSubmission) -> VideoResult:
        while True:
            response = self.client.get(f"{settings.openai_base_url.rstrip('/')}/videos/{submission.external_id}")
            response.raise_for_status()
            data = response.json()
            status = data.get("status")
            if status == "completed":
                content_response = self.client.get(f"{settings.openai_base_url.rstrip('/')}/videos/{submission.external_id}/content")
                content_response.raise_for_status()
                return VideoResult(
                    provider=self.provider_name,
                    model=submission.model,
                    external_id=submission.external_id,
                    status="completed",
                    file_bytes=content_response.content,
                    mime_type=content_response.headers.get("Content-Type", "video/mp4"),
                    raw_payload=data,
                )
            if status == "failed":
                error_payload = data.get("error") or {}
                raise RuntimeError(error_payload.get("message", "Sora generation failed"))
            time.sleep(settings.poll_interval_seconds)

    def _compose_prompt(self, prompt: PromptPayload) -> str:
        return f"{prompt.scene}. {prompt.character}. {prompt.action}. {prompt.emotion}. {prompt.style}. {prompt.camera}."
