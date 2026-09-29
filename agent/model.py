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

from botocore.config import Config
from langchain_aws import ChatBedrockConverse

# Bounded retry + timeout for every Bedrock call. WHY: the shared account gets
# throttled (429), and botocore's default is up to ~10 adaptive retries with
# exponential backoff — a single throttled call was measured taking 60+ seconds,
# which landed on the critical path of the memory retrieval gate and made turns
# take minutes. A small retry budget + a read timeout means a throttle FAILS FAST
# (a few seconds) instead of backing off for a minute; the caller (e.g. the gate,
# which fails open) recovers gracefully rather than hanging the turn.
_BEDROCK_CONFIG = Config(
    retries={"max_attempts": int(os.getenv("BEDROCK_MAX_ATTEMPTS", "2")), "mode": "standard"},
    read_timeout=int(os.getenv("BEDROCK_READ_TIMEOUT", "30")),
    connect_timeout=10,
)

# Primary model — used for all reasoning turns.
#
# History: gpt-oss-120b (a "harmony"-format reasoning model) leaked tool calls
# into the TEXT channel, so the loop read `{"query":…}` as the answer and cut off.
# nova-pro fixed the tool calling but is a modest model. deepseek.v3.2 is the
# upgrade: a strong agentic model that reasons INTERNALLY (no separate reasoning
# block to blow the token budget), returns clean text, and — verified with a live
# Bedrock tool-call probe — emits proper structured tool calls (stopReason
# tool_use), which is exactly what an agent driving many tools needs. Served from
# account 744496272436 in ap-northeast-1 (set AWS_DEFAULT_REGION accordingly).
#
# Now kimi-k3. Head-to-head on real Gmail tasks (2026-09-28, 10 callable models
# on account 436; Claude/GPT are AccessDenied there): kimi-k3 was the only one
# that searched with sender/date filters, reported "not found" honestly AND
# invented no contact details on the hard case; deepseek.v3.2 invented phone
# numbers in both runs and was ~2.5x slower. Served via the `global.` cross-region
# inference profile, so requests (including email text) may be processed outside
# ap-northeast-1. mistral-large-3 is the fast/cheap alternative in the picker.
# Override with BEDROCK_MODEL_ID to A/B.
MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "global.moonshotai.kimi-k3")

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
    {
        "id": "openai.gpt-oss-120b-1:0",
        "note": "strong reasoning; leaks tool calls as text",
        "reasoning": True,
    },
    {"id": "openai.gpt-oss-20b-1:0", "note": "cheaper, same family", "reasoning": True},
    {"id": "amazon.nova-pro-v1:0", "note": "reliable tool calling, modest", "reasoning": False},
    {"id": "amazon.nova-lite-v1:0", "note": "routing default — fast, cheap", "reasoning": False},
    {"id": "amazon.nova-micro-v1:0", "note": "cheapest, crispest", "reasoning": False},
    {
        "id": "global.moonshotai.kimi-k3",
        "note": "default — best grounding + filtered search in eval",
        "reasoning": False,
    },
    {
        "id": "mistral.mistral-large-3-675b-instruct",
        "note": "fast, cheap, good targeted search",
        "reasoning": False,
    },
    {
        "id": "deepseek.v3.2",
        "note": "previous default — invented contact details in eval",
        "reasoning": False,
    },
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


def bedrock_config() -> Config:
    """The shared bounded retry/timeout config, for callers that build their own
    Bedrock client (e.g. the Graphiti memory clients)."""
    return _BEDROCK_CONFIG


def get_model() -> ChatBedrockConverse:
    """Return the primary reasoning model."""
    return ChatBedrockConverse(model=MODEL_ID, region_name=REGION, config=_BEDROCK_CONFIG)


def get_fast_model() -> ChatBedrockConverse:
    """Return the fast model for cheap operations (compaction, classification)."""
    return ChatBedrockConverse(model=FAST_MODEL_ID, region_name=REGION, config=_BEDROCK_CONFIG)


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
    return ChatBedrockConverse(model=model_id, region_name=REGION, config=_BEDROCK_CONFIG)
