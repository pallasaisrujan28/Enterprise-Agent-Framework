"""
Model configuration — single place to define which model EAF uses.

Change MODEL_ID here to switch models across the entire system.
No other file needs to know the model ID or region.

Current: gpt-oss-120b via Amazon Bedrock (eu-west-2, IRSA auth).
Auth: pod IRSA role → sts:AssumeRoleWithWebIdentity → bedrock:InvokeModel
No API keys. No stored credentials.

THESE IDS WERE VERIFIED BY CALLING THEM, NOT READ FROM DOCUMENTATION.

Both previous defaults were Anthropic and both failed. `claude-3-5-sonnet-
20241022-v2:0` does not exist in eu-west-2 at all ("The provided model
identifier is invalid"), and `claude-haiku-4-5-20251001-v1:0` rejects on-demand
invocation. Neither had ever answered a request, which is not a thing a code
review catches — the ids look perfectly plausible.

Three further traps worth knowing before changing a value here:

  LISTED IS NOT CALLABLE. ListFoundationModels reports 46 text models in
  eu-west-2 as ON_DEMAND; 43 actually answer. Three Anthropic ids are listed and
  refuse — two on billing (INVALID_PAYMENT_INSTRUMENT, which no IAM or
  model-access change will fix) and one on access.

  A REASONING MODEL SPENDS OUTPUT BUDGET BEFORE IT ANSWERS. gpt-oss emits a
  reasoning block first, sharing the max-tokens budget with the reply, so too
  small a budget returns a successful call with an empty answer.

  agent/models/verified_models IS THE AUTHORITATIVE LIST. It is what the
  dashboard's picker offers and what its chat endpoint validates against. Keep
  this file's defaults inside that list.
"""

from __future__ import annotations

import os

from langchain_aws import ChatBedrockConverse

# Primary model — used for all reasoning turns. Verified: 0.35s, emits a
# reasoning block before the answer.
MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "openai.gpt-oss-120b-1:0")

# Fast model — summarisation, context compaction, cheap classification. Verified,
# and already carrying the dashboard's skill routing.
FAST_MODEL_ID = os.getenv("BEDROCK_FAST_MODEL", "amazon.nova-lite-v1:0")

REGION = os.getenv("AWS_DEFAULT_REGION", "eu-west-2")


def get_model() -> ChatBedrockConverse:
    """Return the primary reasoning model."""
    return ChatBedrockConverse(model=MODEL_ID, region_name=REGION)


def get_fast_model() -> ChatBedrockConverse:
    """Return the fast model for cheap operations (compaction, classification)."""
    return ChatBedrockConverse(model=FAST_MODEL_ID, region_name=REGION)
