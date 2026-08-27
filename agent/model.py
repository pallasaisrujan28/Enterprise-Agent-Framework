"""
Model configuration — single place to define which model EAF uses.

Change MODEL_ID here to switch models across the entire system.
No other file needs to know the model ID or region.

Current: Claude 3.5 Sonnet via Amazon Bedrock (eu-west-2, IRSA auth).
Auth: pod IRSA role → sts:AssumeRoleWithWebIdentity → bedrock:InvokeModel
No API keys. No stored credentials.
"""

from __future__ import annotations

import os

from langchain_aws import ChatBedrockConverse

# Primary model — used for all reasoning turns.
MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")

# Fast model — used for summarisation, context compaction, cheap classification.
FAST_MODEL_ID = os.getenv("BEDROCK_FAST_MODEL", "anthropic.claude-haiku-4-5-20251001-v1:0")

REGION = os.getenv("AWS_DEFAULT_REGION", "eu-west-2")


def get_model() -> ChatBedrockConverse:
    """Return the primary reasoning model."""
    return ChatBedrockConverse(model=MODEL_ID, region_name=REGION)


def get_fast_model() -> ChatBedrockConverse:
    """Return the fast model for cheap operations (compaction, classification)."""
    return ChatBedrockConverse(model=FAST_MODEL_ID, region_name=REGION)
