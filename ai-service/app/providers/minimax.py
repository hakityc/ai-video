from __future__ import annotations

import time

import httpx

from app.core.config import settings
from app.models.schemas import PromptPayload, VideoResult, VideoSubmission


class MiniMaxProvider:
    provider_name = "minimax"

    def __init__(self) -> None:
        if not settings.minimax_api_key:
            raise RuntimeError("MINIMAX_API_KEY is required")
        self.client = httpx.Client(
            timeout=settings.ai_provider_timeout_seconds,
            headers={"Authorization": f"Bearer {settings.minimax_api_key}"},
        )

    def submit(self, prompt: PromptPayload) -> VideoSubmission:
        payload: dict[str, object] = {
            "prompt": self._compose_prompt(prompt),
            "model": settings.minimax_video_model,
            "duration": prompt.duration,
            "resolution": "1080P",
        }
        if prompt.reference_images:
            payload["subject_reference"] = [
                {
                    "type": "character",
                    "image": prompt.reference_images[:1],
                }
            ]
        response = self.client.post(f"{settings.minimax_api_base.rstrip('/')}/v1/video_generation", json=payload)
        response.raise_for_status()
        data = response.json()
        return VideoSubmission(
            provider=self.provider_name,
            model=settings.minimax_video_model,
            external_id=data["task_id"],
            raw_payload=data,
        )

    def poll(self, submission: VideoSubmission) -> VideoResult:
        query_url = f"{settings.minimax_api_base.rstrip('/')}/v1/query/video_generation"
        file_url = f"{settings.minimax_api_base.rstrip('/')}/v1/files/retrieve"
        while True:
            response = self.client.get(query_url, params={"task_id": submission.external_id})
            response.raise_for_status()
            data = response.json()
            status = data.get("status", "")
            if status == "Success":
                file_id = data["file_id"]
                file_response = self.client.get(file_url, params={"file_id": file_id})
                file_response.raise_for_status()
                download_url = file_response.json()["file"]["download_url"]
                video_response = self.client.get(download_url)
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
            if status == "Fail":
                raise RuntimeError(data.get("error_message", "MiniMax generation failed"))
            time.sleep(settings.poll_interval_seconds)

    def _compose_prompt(self, prompt: PromptPayload) -> str:
        return (
            f"Scene: {prompt.scene}. Characters: {prompt.character}. Action: {prompt.action}. "
            f"Emotion: {prompt.emotion}. Style: {prompt.style}. Camera: {prompt.camera}. "
            f"Dialogue: {prompt.dialogue}."
        )
