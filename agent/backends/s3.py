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
import os
import re

import boto3
from botocore.exceptions import ClientError
from deepagents.backends.protocol import (
    BackendProtocol,
    DeleteResult,
    EditResult,
    FileDownloadResponse,
    FileInfo,
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

        # Credentials: in the cluster this is IRSA — no explicit keys, boto3's
        # default chain resolves the pod role. Locally the store is MinIO, which
        # does NOT know the ambient AWS/Bedrock credentials; sending them yields
        # "InvalidAccessKeyId". So when dedicated workspace-store keys are provided
        # (S3_ACCESS_KEY_ID / S3_SECRET_ACCESS_KEY, as docker-compose sets for
        # MinIO), use THOSE for the S3 client. When they are absent, fall back to
        # the default chain unchanged, so the cluster's IRSA path is untouched.
        #
        # The endpoint itself needs no handling here — boto3 reads
        # AWS_ENDPOINT_URL_S3 natively, which is how the same client talks to
        # MinIO locally and real S3 in the cluster.
        access_key = os.getenv("S3_ACCESS_KEY_ID")
        secret_key = os.getenv("S3_SECRET_ACCESS_KEY")
        client_kwargs: dict[str, str] = {"region_name": region}
        if access_key and secret_key:
            client_kwargs["aws_access_key_id"] = access_key
            client_kwargs["aws_secret_access_key"] = secret_key
        self._s3 = boto3.client("s3", **client_kwargs)

    # ── Key helpers ───────────────────────────────────────────────────────────

    def _key(self, path: str) -> str:
        """Strip the /workspace prefix — return the bare S3 key.

        Handles the bare root ("/workspace" or "workspace") → "" as well as the
        "/workspace/…" form. Missing the no-trailing-slash root case mapped it to
        the literal prefix "workspace", so an ls/grep/glob at the workspace root
        searched a prefix no key has and silently returned nothing.
        """
        clean = path.lstrip("/")
        if clean == "workspace":
            return ""
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
                # The protocol convention is to REPORT a missing file via the
                # error field, not raise — the filesystem middleware turns this
                # into a readable observation.
                return ReadResult(error=f"File not found: {file_path}")
            return ReadResult(error=str(exc))

        # A non-positive limit is a "peek nothing" request: return with no window.
        if limit <= 0:
            return ReadResult(no_lines_requested=True)

        lines = raw.splitlines(keepends=True)
        start = max(offset, 0)
        window = lines[start : start + limit]

        # Empty file, or an offset past the end: valid, but there is no line
        # window to describe, so leave the pagination fields unset.
        if not window:
            return ReadResult(file_data={"content": "", "encoding": "utf-8"})

        start_line = start + 1
        end_line = start + len(window)
        return ReadResult(
            file_data={"content": "".join(window), "encoding": "utf-8"},
            total_lines=len(lines),
            start_line=start_line,
            end_line=end_line,
            next_offset=end_line,  # 0-indexed line after the last shown == end_line
        )

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
        # Fetch the whole object directly rather than via read(), whose default
        # 2000-line window would silently drop the tail of a large file and
        # corrupt it on write-back.
        try:
            raw = (
                self._s3.get_object(Bucket=self.bucket, Key=self._key(file_path))["Body"]
                .read()
                .decode("utf-8")
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] in ("NoSuchKey", "404"):
                return EditResult(error=f"File not found: {file_path}")
            return EditResult(error=str(exc))

        if old_string not in raw:
            return EditResult(
                error=(
                    f"old_string not found in {file_path}. "
                    "Read the file first to verify the exact content."
                )
            )

        occurrences = raw.count(old_string) if replace_all else 1
        new_content = (
            raw.replace(old_string, new_string)
            if replace_all
            else raw.replace(old_string, new_string, 1)
        )
        self.write(file_path, new_content)
        return EditResult(path=file_path, occurrences=occurrences)

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
        # The protocol wants a flat list of FileInfo entries (absolute paths),
        # directories flagged with is_dir — not the old path/dirs/files shape.
        entries: list[FileInfo] = [
            {"path": self._path(cp["Prefix"]), "is_dir": True}
            for cp in resp.get("CommonPrefixes", [])
        ]
        for obj in resp.get("Contents", []):
            if obj["Key"].endswith("/") or obj["Key"] == prefix:
                continue
            entries.append(
                {"path": self._path(obj["Key"]), "is_dir": False, "size": obj.get("Size", 0)}
            )
        return LsResult(entries=entries)

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
                        # GrepMatch is a TypedDict keyed path/line/text — not the
                        # old file/line/content positional form.
                        matches.append(GrepMatch(path=self._path(key), line=line_num, text=line))
                        if max_count and len(matches) >= max_count:
                            return GrepResult(matches=matches, truncated=True)

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
        matched: list[FileInfo] = []

        for page in paginator.paginate(Bucket=self.bucket, Prefix=search_prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                relative = key[len(search_prefix) :].lstrip("/") if search_prefix else key
                if fnmatch.fnmatch(relative, pattern):
                    # GlobResult carries FileInfo entries (absolute paths), not a
                    # bare list of path strings.
                    matched.append(
                        {"path": self._path(key), "is_dir": False, "size": obj.get("Size", 0)}
                    )

        return GlobResult(matches=matched)

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
