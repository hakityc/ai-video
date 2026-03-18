from __future__ import annotations

from typing import Protocol

from app.models.schemas import PromptPayload, VideoResult, VideoSubmission


class VideoProvider(Protocol):
    provider_name: str

    def submit(self, prompt: PromptPayload) -> VideoSubmission:
        ...

    def poll(self, submission: VideoSubmission) -> VideoResult:
        ...
