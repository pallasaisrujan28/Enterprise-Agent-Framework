"""
EAF S3 Backend — full BackendProtocol implementation.

Provides read, write, ls, grep, glob, edit, delete, upload, download
backed by an S3 bucket. Used as the /workspace backend in brain.py's
CompositeBackend so the agent's workspace files persist across pod restarts.

All paths the agent uses start with /workspace/ (e.g. /workspace/reports/summary.md).
The backend strips that prefix and maps to S3 keys internally.

Auth: IRSA (pod service account annotation) — no stored credentials.
"""

# mypy: ignore-errors

from __future__ import annotations

import asyncio
import fnmatch
import re

import boto3
from botocore.exceptions import ClientError
from deepagents.backends.protocol import (
    BackendProtocol,
    DeleteResult,
    EditResult,
    FileDownloadResponse,
    FileUploadResponse,
    GlobResult,
    GrepMatch,
    GrepResult,
    LsResult,
    ReadResult,
    WriteResult,
)


class EAFBackend(BackendProtocol):
    """
    S3-backed workspace for the EAF agent.

    Implements the full deepagents BackendProtocol so the agent can:
      - read / write / edit / delete workspace files
      - ls (list) directories
      - grep (search content across files)
      - glob (find files by pattern)
      - upload / download binary files

    Plugged into CompositeBackend in brain.py:
        "/workspace" → EAFBackend(bucket=WORKSPACE_BUCKET)
    """

    def __init__(self, bucket: str, region: str = "eu-west-2") -> None:
        self.bucket = bucket
        self._s3 = boto3.client("s3", region_name=region)

    # ── Key helpers ───────────────────────────────────────────────────────────

    def _key(self, path: str) -> str:
        """Strip /workspace/ prefix — return bare S3 key."""
        clean = path.lstrip("/")
        if clean.startswith("workspace/"):
            clean = clean[len("workspace/") :]
        return clean

    def _path(self, key: str) -> str:
        """Convert S3 key → agent-facing path."""
        return f"/workspace/{key}"

    # ── READ ──────────────────────────────────────────────────────────────────

    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> ReadResult:
        try:
            resp = self._s3.get_object(Bucket=self.bucket, Key=self._key(file_path))
            raw = resp["Body"].read().decode("utf-8")
        except ClientError as exc:
            if exc.response["Error"]["Code"] in ("NoSuchKey", "404"):
                raise FileNotFoundError(f"File not found: {file_path}") from exc
            raise

        lines = raw.splitlines(keepends=True)
        sliced = lines[offset : offset + limit]
        return ReadResult(content="".join(sliced), truncated=len(lines) > offset + limit)

    async def aread(self, file_path: str, offset: int = 0, limit: int = 2000) -> ReadResult:
        return await asyncio.to_thread(self.read, file_path, offset, limit)

    # ── WRITE ─────────────────────────────────────────────────────────────────

    def write(self, file_path: str, content: str) -> WriteResult:
        self._s3.put_object(
            Bucket=self.bucket,
            Key=self._key(file_path),
            Body=content.encode("utf-8"),
            ContentType="text/plain; charset=utf-8",
        )
        return WriteResult(path=file_path)

    async def awrite(self, file_path: str, content: str) -> WriteResult:
        return await asyncio.to_thread(self.write, file_path, content)

    # ── EDIT ──────────────────────────────────────────────────────────────────

    def edit(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> EditResult:
        result = self.read(file_path)
        content = result.content
        if old_string not in content:
            raise ValueError(
                f"old_string not found in {file_path}. "
                "Read the file first to verify the exact content."
            )
        new_content = (
            content.replace(old_string, new_string)
            if replace_all
            else content.replace(old_string, new_string, 1)
        )
        self.write(file_path, new_content)
        return EditResult(path=file_path)

    async def aedit(
        self, file_path: str, old_string: str, new_string: str, replace_all: bool = False
    ) -> EditResult:
        return await asyncio.to_thread(self.edit, file_path, old_string, new_string, replace_all)

    # ── DELETE ────────────────────────────────────────────────────────────────

    def delete(self, file_path: str) -> DeleteResult:
        self._s3.delete_object(Bucket=self.bucket, Key=self._key(file_path))
        return DeleteResult(path=file_path)

    async def adelete(self, file_path: str) -> DeleteResult:
        return await asyncio.to_thread(self.delete, file_path)

    # ── LS ────────────────────────────────────────────────────────────────────

    def ls(self, path: str) -> LsResult:
        prefix = self._key(path)
        if prefix and not prefix.endswith("/"):
            prefix += "/"

        resp = self._s3.list_objects_v2(Bucket=self.bucket, Prefix=prefix, Delimiter="/")
        dirs = [cp["Prefix"][len(prefix) :].rstrip("/") for cp in resp.get("CommonPrefixes", [])]
        files = [
            obj["Key"][len(prefix) :]
            for obj in resp.get("Contents", [])
            if not obj["Key"].endswith("/") and obj["Key"] != prefix
        ]
        return LsResult(path=path, dirs=dirs, files=files)

    async def als(self, path: str) -> LsResult:
        return await asyncio.to_thread(self.ls, path)

    # ── GREP ──────────────────────────────────────────────────────────────────

    def grep(
        self,
        pattern: str,
        path: str | None = None,
        glob: str | None = None,
        *,
        max_count: int | None = None,
    ) -> GrepResult:
        search_prefix = self._key(path or "")
        paginator = self._s3.get_paginator("list_objects_v2")
        compiled = re.compile(pattern)
        matches: list[GrepMatch] = []

        for page in paginator.paginate(Bucket=self.bucket, Prefix=search_prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if glob and not fnmatch.fnmatch(key.split("/")[-1], glob):
                    continue
                try:
                    raw = (
                        self._s3.get_object(Bucket=self.bucket, Key=key)["Body"]
                        .read()
                        .decode("utf-8", errors="replace")
                    )
                except ClientError:
                    continue
                for line_num, line in enumerate(raw.splitlines(), start=1):
                    if compiled.search(line):
                        matches.append(GrepMatch(file=self._path(key), line=line_num, content=line))
                        if max_count and len(matches) >= max_count:
                            return GrepResult(matches=matches)

        return GrepResult(matches=matches)

    async def agrep(
        self,
        pattern: str,
        path: str | None = None,
        glob: str | None = None,
        *,
        max_count: int | None = None,
    ) -> GrepResult:
        return await asyncio.to_thread(self.grep, pattern, path, glob, max_count=max_count)

    # ── GLOB ──────────────────────────────────────────────────────────────────

    def glob(self, pattern: str, path: str | None = None) -> GlobResult:
        search_prefix = self._key(path or "")
        paginator = self._s3.get_paginator("list_objects_v2")
        matched: list[str] = []

        for page in paginator.paginate(Bucket=self.bucket, Prefix=search_prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                relative = key[len(search_prefix) :].lstrip("/") if search_prefix else key
                if fnmatch.fnmatch(relative, pattern):
                    matched.append(self._path(key))

        return GlobResult(paths=matched)

    async def aglob(self, pattern: str, path: str | None = None) -> GlobResult:
        return await asyncio.to_thread(self.glob, pattern, path)

    # ── UPLOAD / DOWNLOAD ─────────────────────────────────────────────────────

    def upload_files(self, files: list[tuple[str, bytes]]) -> list[FileUploadResponse]:
        results = []
        for path, data in files:
            self._s3.put_object(Bucket=self.bucket, Key=self._key(path), Body=data)
            results.append(FileUploadResponse(path=path))
        return results

    async def aupload_files(self, files: list[tuple[str, bytes]]) -> list[FileUploadResponse]:
        return await asyncio.to_thread(self.upload_files, files)

    def download_files(self, paths: list[str]) -> list[FileDownloadResponse]:
        results = []
        for path in paths:
            data = self._s3.get_object(Bucket=self.bucket, Key=self._key(path))["Body"].read()
            results.append(FileDownloadResponse(path=path, content=data))
        return results

    async def adownload_files(self, paths: list[str]) -> list[FileDownloadResponse]:
        return await asyncio.to_thread(self.download_files, paths)
