from __future__ import annotations

from io import BytesIO

from minio import Minio

from app.core.config import settings


class ObjectStorage:
    def __init__(self) -> None:
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_use_ssl,
        )

    def upload_bytes(self, object_key: str, payload: bytes, content_type: str) -> str:
        self.client.put_object(
            settings.minio_bucket,
            object_key,
            BytesIO(payload),
            length=len(payload),
            content_type=content_type,
        )
        scheme = "https" if settings.minio_use_ssl else "http"
        return f"{scheme}://{settings.minio_endpoint}/{settings.minio_bucket}/{object_key}"


storage = ObjectStorage()
