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


def _s3_client() -> boto3.client:  # type: ignore[valid-type]
    """An S3 client that can address MinIO locally and S3 in cluster.

    ADR-019 requires object storage to be reachable through the S3 API so that
    swapping MinIO for S3 is "a config change and never a code change". That was
    not true: this module built a plain client, which always talks to real AWS, so
    the local stack could not be used at all.

    Endpoint is the easy half — boto3 reads AWS_ENDPOINT_URL_S3 itself. Credentials
    are the awkward half, because boto3 has NO per-service credential resolution:
    one set of keys serves every client in the process. Bedrock needs real AWS
    credentials and MinIO needs its own, so with a single pair one of the two
    always fails — Bedrock with no credentials, or MinIO with InvalidAccessKeyId.

    Hence the optional S3-only override. Unset, which is the cluster case, this is
    exactly the old behaviour: the default chain, so IRSA still applies and no
    static credential appears anywhere. Set, which is the local case, S3 talks to
    MinIO while Bedrock keeps using the real credentials.
    """
    access_key = os.getenv("S3_ACCESS_KEY_ID", "")
    secret_key = os.getenv("S3_SECRET_ACCESS_KEY", "")
    if access_key and secret_key:
        return boto3.client(
            "s3",
            region_name=REGION,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            # A local MinIO has no session token, and inheriting the ambient one
            # would be sent alongside the override keys and rejected.
            aws_session_token=None,
        )
    return boto3.client("s3", region_name=REGION)


_s3 = _s3_client()


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
