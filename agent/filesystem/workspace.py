"""
Agent workspace — read/write to the S3 workspace bucket.

Every agent pod has an IRSA role that grants s3:GetObject and s3:PutObject
on the workspace bucket (eaf-dev-workspace-* or eaf-prod-workspace-*).
No static credentials — all auth flows through the pod's IAM role.

These are registered as LangChain @tools so the ToolRegistry can discover
and select them semantically.
"""

from __future__ import annotations

import os

import boto3
from langchain_core.tools import tool

WORKSPACE_BUCKET = os.getenv("WORKSPACE_BUCKET", "")
REGION = os.getenv("AWS_DEFAULT_REGION", "eu-west-2")

_s3 = boto3.client("s3", region_name=REGION)


@tool
def read_workspace_file(key: str) -> str:
    """
    Read a file from the agent's S3 workspace bucket. The key is a relative
    path within the bucket (e.g. 'reports/summary.md'). Returns the file
    contents as a string. Use this to access files written by previous
    agent sessions or uploaded by users.
    """
    if not WORKSPACE_BUCKET:
        return "WORKSPACE_BUCKET env var not set — filesystem tools unavailable."
    resp = _s3.get_object(Bucket=WORKSPACE_BUCKET, Key=key)
    return resp["Body"].read().decode("utf-8")


@tool
def write_workspace_file(key: str, content: str) -> str:
    """
    Write text content to a file in the agent's S3 workspace bucket.
    The key is a relative path (e.g. 'reports/summary.md'). Overwrites
    if the file already exists. Returns confirmation with the full S3 URI.
    Use this to persist research outputs, reports, or intermediate results.
    """
    if not WORKSPACE_BUCKET:
        return "WORKSPACE_BUCKET env var not set — filesystem tools unavailable."
    _s3.put_object(
        Bucket=WORKSPACE_BUCKET,
        Key=key,
        Body=content.encode("utf-8"),
        ContentType="text/plain",
    )
    return f"Written to s3://{WORKSPACE_BUCKET}/{key}"
