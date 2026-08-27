"""
Cognito token manager for AgentCore Gateway authentication.

The agent authenticates with the Gateway using the OAuth 2.0
client_credentials flow:
  1. Read Secrets Manager → { client_id, client_secret, token_endpoint, scope }
  2. POST client credentials to Cognito token endpoint → JWT access token
  3. Cache the token; refresh automatically before expiry
  4. All MCP calls to AgentCore Gateway include: Authorization: Bearer <token>

Why Cognito, not just IAM SigV4?
  Cognito JWT scopes give fine-grained per-tool access control that IAM alone
  cannot express cleanly. A future agent or external consumer can be given a
  different client with a narrower scope (e.g. memory only, no web_search).
  IAM policies still apply on top — the IRSA role has InvokeAgentGateway.

Required env vars:
  GATEWAY_CLIENT_CREDS_SECRET  — Secrets Manager ARN or name (set by Terraform
                                  SSM → K8s deployment env injection)
  AWS_DEFAULT_REGION           — must be eu-west-2
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass

import boto3
import httpx

_REGION = os.getenv("AWS_DEFAULT_REGION", "eu-west-2")
_SECRET_NAME = os.getenv("GATEWAY_CLIENT_CREDS_SECRET", "")

_sm = boto3.client("secretsmanager", region_name=_REGION)


@dataclass
class _TokenCache:
    access_token: str = ""
    expires_at: float = 0.0


_cache = _TokenCache()
_REFRESH_BUFFER = 60  # refresh 60 seconds before expiry


def _load_credentials() -> dict:
    if not _SECRET_NAME:
        raise RuntimeError(
            "GATEWAY_CLIENT_CREDS_SECRET env var not set. "
            "Set it to the ARN of the Secrets Manager secret created by Terraform."
        )
    resp = _sm.get_secret_value(SecretId=_SECRET_NAME)
    return json.loads(resp["SecretString"])


def get_token() -> str:
    """
    Return a valid Cognito JWT access token for the AgentCore Gateway.
    Uses the cached token if still valid; fetches a new one otherwise.
    Thread-safe for single-process use (uvicorn single-worker mode).
    """
    now = time.time()
    if _cache.access_token and now < (_cache.expires_at - _REFRESH_BUFFER):
        return _cache.access_token

    creds = _load_credentials()
    resp = httpx.post(
        creds["token_endpoint"],
        data={
            "grant_type": "client_credentials",
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
            "scope": creds["scope"],
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    resp.raise_for_status()
    body = resp.json()

    _cache.access_token = body["access_token"]
    _cache.expires_at = now + body.get("expires_in", 3600)
    return _cache.access_token


def auth_headers() -> dict[str, str]:
    """Return Authorization header dict for an AgentCore Gateway MCP call."""
    return {"Authorization": f"Bearer {get_token()}"}
