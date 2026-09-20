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

# EVERY ID HERE WAS VERIFIED BY CALLING CONVERSE IN eu-west-2 AND READING THE
# REPLY. Not a catalogue, and deliberately not a copy of ListFoundationModels —
# which is the point: LISTED IS NOT CALLABLE. Bedrock lists 46 text models in this
# region as ON_DEMAND and 43 answer. All three that refuse are Anthropic, and two
# refuse on BILLING (INVALID_PAYMENT_INSTRUMENT) rather than IAM, so no permission
# change fixes them — an id that looks perfectly plausible in review had never
# once answered a request.
#
# Curated rather than exhaustive: this is what the dashboard's model picker offers
# and what its chat endpoint validates against. Anything callable may be added;
# the bar is having called it.
#
# `reasoning` marks a model that spends output budget thinking BEFORE it answers.
# Too small a max-tokens then returns a successful call with an empty reply.
#
# Deliberately absent: every anthropic.* id. `anthropic.claude-opus-4-6-v1` does
# answer here (~1.15s) and is the sole working exception — left off because it is
# the priciest model in the region, not because it is broken. One line to add.
VERIFIED_MODELS: tuple[dict[str, str | bool], ...] = (
    {"id": "openai.gpt-oss-120b-1:0", "note": "default — strongest verified", "reasoning": True},
    {"id": "openai.gpt-oss-20b-1:0", "note": "cheaper, same family", "reasoning": True},
    {"id": "amazon.nova-pro-v1:0", "note": "no reasoning block", "reasoning": False},
    {"id": "amazon.nova-lite-v1:0", "note": "routing default — fast, cheap", "reasoning": False},
    {"id": "amazon.nova-micro-v1:0", "note": "cheapest, crispest", "reasoning": False},
    {"id": "deepseek.v3.2", "note": "strong general reasoning", "reasoning": False},
    {"id": "zai.glm-5", "note": "GLM flagship", "reasoning": False},
    {"id": "zai.glm-4.7-flash", "note": "GLM, low latency", "reasoning": False},
    {"id": "qwen.qwen3-235b-a22b-2507-v1:0", "note": "large Qwen MoE", "reasoning": False},
    {"id": "qwen.qwen3-coder-480b-a35b-v1:0", "note": "code-specialised", "reasoning": False},
    {"id": "minimax.minimax-m2.5", "note": "reasons at length", "reasoning": True},
    {"id": "moonshotai.kimi-k2.5", "note": "slowest verified — ~2.7s", "reasoning": False},
    {"id": "meta.llama3-70b-instruct-v1:0", "note": "open weights baseline", "reasoning": False},
    {"id": "mistral.mistral-large-2402-v1:0", "note": "Mistral flagship", "reasoning": False},
    {"id": "nvidia.nemotron-super-3-120b", "note": "Nemotron, large", "reasoning": False},
)

VERIFIED_MODEL_IDS = frozenset(str(entry["id"]) for entry in VERIFIED_MODELS)


def credential_source() -> str:
    """Where the AWS credential comes from — the SOURCE, never the value.

    Rendered in the dashboard so it is possible to see that a credential is
    ambient without displaying one. There is deliberately no function anywhere
    that returns a secret.
    """
    if os.environ.get("AWS_ACCESS_KEY_ID"):
        return "AWS_ACCESS_KEY_ID from the environment"
    if os.environ.get("AWS_PROFILE"):
        return f"AWS_PROFILE={os.environ['AWS_PROFILE']}"
    if os.environ.get("AWS_WEB_IDENTITY_TOKEN_FILE"):
        return "web identity token file (IRSA / Pod Identity)"
    return "the default AWS credential chain"


def get_model() -> ChatBedrockConverse:
    """Return the primary reasoning model."""
    return ChatBedrockConverse(model=MODEL_ID, region_name=REGION)


def get_fast_model() -> ChatBedrockConverse:
    """Return the fast model for cheap operations (compaction, classification)."""
    return ChatBedrockConverse(model=FAST_MODEL_ID, region_name=REGION)


def get_model_named(model_id: str) -> ChatBedrockConverse:
    """A model by id, refusing anything not on the verified list.

    The dashboard lets a conversation switch model. An arbitrary id would reach
    Bedrock and fail there, and the resulting AccessDenied or ValidationException
    is far less clear than refusing it here with the list of what does work.
    """
    if model_id not in VERIFIED_MODEL_IDS:
        raise ValueError(
            f"{model_id} is not a verified model. Verified: {sorted(VERIFIED_MODEL_IDS)}"
        )
    return ChatBedrockConverse(model=model_id, region_name=REGION)
