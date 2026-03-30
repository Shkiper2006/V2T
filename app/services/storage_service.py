from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import boto3

from app.config import get_settings


class StorageService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def save_bytes(self, data: bytes, suffix: str = ".ogg") -> str:
        file_name = f"{uuid4().hex}{suffix}"
        if self.settings.storage_backend == "s3":
            return self._save_to_s3(file_name=file_name, data=data)
        return self._save_to_local(file_name=file_name, data=data)

    def download_bytes(self, uri: str) -> bytes:
        if uri.startswith("s3://"):
            return self._download_from_s3(uri)
        return Path(uri).read_bytes()

    def _save_to_local(self, file_name: str, data: bytes) -> str:
        root = Path(self.settings.local_storage_path)
        root.mkdir(parents=True, exist_ok=True)
        path = root / file_name
        path.write_bytes(data)
        return str(path)

    def _save_to_s3(self, file_name: str, data: bytes) -> str:
        if not self.settings.s3_bucket:
            raise ValueError("S3_BUCKET is required when STORAGE_BACKEND=s3")

        client = boto3.client(
            "s3",
            endpoint_url=self.settings.s3_endpoint_url or None,
            aws_access_key_id=self.settings.s3_access_key_id or None,
            aws_secret_access_key=self.settings.s3_secret_access_key or None,
        )
        key = f"voice/{file_name}"
        client.put_object(Bucket=self.settings.s3_bucket, Key=key, Body=data)
        return f"s3://{self.settings.s3_bucket}/{key}"

    def _download_from_s3(self, uri: str) -> bytes:
        _, path = uri.split("s3://", maxsplit=1)
        bucket, key = path.split("/", maxsplit=1)

        client = boto3.client(
            "s3",
            endpoint_url=self.settings.s3_endpoint_url or None,
            aws_access_key_id=self.settings.s3_access_key_id or None,
            aws_secret_access_key=self.settings.s3_secret_access_key or None,
        )
        response = client.get_object(Bucket=bucket, Key=key)
        return response["Body"].read()
