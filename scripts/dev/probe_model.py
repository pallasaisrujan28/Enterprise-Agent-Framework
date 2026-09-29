"""Probe access to a Bedrock model using a bearer API key, across regions.

Usage:
    AWS_BEARER_TOKEN_BEDROCK=... .venv/bin/python scripts/probe_model.py <model_id>

Prints, per region, whether Converse answers, or the error class. Never prints
the token.
"""

from __future__ import annotations

import os
import sys

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

MODEL = sys.argv[1] if len(sys.argv) > 1 else "moonshotai.kimi-k3"
REGIONS = [
    "us-east-1",
    "us-west-2",
    "eu-west-2",
    "eu-central-1",
    "ap-southeast-1",
    "ap-northeast-1",
]

if not os.getenv("AWS_BEARER_TOKEN_BEDROCK"):
    print("AWS_BEARER_TOKEN_BEDROCK not set")
    sys.exit(1)

# Make sure any ambient AWS keys don't shadow the bearer token.
for var in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN", "AWS_PROFILE"):
    os.environ.pop(var, None)

print(f"probing model: {MODEL}")
for region in REGIONS:
    try:
        client = boto3.client(
            "bedrock-runtime", region_name=region, config=Config(retries={"max_attempts": 0})
        )
        resp = client.converse(
            modelId=MODEL,
            messages=[{"role": "user", "content": [{"text": "Reply with the single word: OK"}]}],
            inferenceConfig={"maxTokens": 16, "temperature": 0},
        )
        text = resp["output"]["message"]["content"][0].get("text", "").strip()
        print(f"  {region:16} ✅ ANSWERED -> {text!r}")
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "?")
        msg = exc.response.get("Error", {}).get("Message", str(exc))
        print(f"  {region:16} ❌ {code}: {msg[:120]}")
    except Exception as exc:  # noqa: BLE001
        print(f"  {region:16} ⚠️  {type(exc).__name__}: {str(exc)[:120]}")
