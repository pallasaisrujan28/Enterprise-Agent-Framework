"""
S3 backend adapter for deepagents FilesystemMiddleware.
Auth via pod IRSA — no stored credentials.
"""

from __future__ import annotations

import boto3


class S3WorkspaceBackend:
    """S3 backend for deepagents FilesystemMiddleware."""

    def __init__(self, bucket: str, region: str = "eu-west-2") -> None:
        self.bucket = bucket
        self._s3 = boto3.client("s3", region_name=region)

    def read(self, path: str) -> str:
        resp = self._s3.get_object(Bucket=self.bucket, Key=path.lstrip("/"))
        return resp["Body"].read().decode("utf-8")

    def write(self, path: str, content: str) -> None:
        self._s3.put_object(
            Bucket=self.bucket,
            Key=path.lstrip("/"),
            Body=content.encode("utf-8"),
            ContentType="text/plain",
        )

    def list(self, prefix: str = "") -> list[str]:
        resp = self._s3.list_objects_v2(Bucket=self.bucket, Prefix=prefix.lstrip("/"))
        return [obj["Key"] for obj in resp.get("Contents", [])]

    def exists(self, path: str) -> bool:
        try:
            self._s3.head_object(Bucket=self.bucket, Key=path.lstrip("/"))
            return True
        except self._s3.exceptions.ClientError:
            return False
