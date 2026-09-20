"""Model connectors. One import site for the rest of the harness.

Everything above this package depends on `ChatModel` and on `build()`. Nothing
above it imports `agent.models.bedrock`, mentions boto3, or names a provider —
which is what makes "we could swap the provider" a true statement rather than an
intention.

Adding a provider is: a module here, a branch in `build()`, and a value in
`agent.config.Provider`. Three edits, none of them outside this package.
"""

from agent.config import Config
from agent.models.base import (
    ChatModel,
    Chunk,
    Completion,
    Message,
    ModelError,
    Usage,
)

__all__ = [
    "ChatModel",
    "Chunk",
    "Completion",
    "Message",
    "ModelError",
    "Usage",
    "build",
    "verified_models",
]

# EVERY ID HERE WAS VERIFIED BY CALLING CONVERSE IN eu-west-2 AND READING THE
# REPLY. Not a catalogue, not from documentation, and not a copy of
# ListFoundationModels — which is the point:
#
#   LISTED IS NOT CALLABLE. ListFoundationModels reports 46 text models in this
#   region as ON_DEMAND. 43 answer. The three that refuse are all Anthropic, and
#   two of them refuse on BILLING (INVALID_PAYMENT_INSTRUMENT) rather than on IAM
#   or model access — so no permission change fixes them, and an id that looks
#   perfectly plausible in review had never once answered a request.
#
# Curated rather than exhaustive: this is what the dashboard's picker offers and
# what the chat endpoint validates against, so it is the models we would actually
# reach for, one per useful niche. Anything callable can be added — the bar is
# having called it.
#
# `reasoning` marks a model that spends output budget thinking BEFORE it answers,
# which is why agent.config keeps a floor under max_tokens: too small a budget
# returns a successful call with an empty reply.
#
# Deliberately absent: every anthropic.* id. Two fail on billing and one on
# access. `anthropic.claude-opus-4-6-v1` DOES answer here (1.15s) and is the sole
# working exception — left off because it was not asked for and it is the
# priciest thing in the region, not because it is broken. One line to add.
verified_models: tuple[dict[str, str | bool], ...] = (
    {"id": "openai.gpt-oss-120b-1:0", "note": "default — strongest verified", "reasoning": True},
    {"id": "openai.gpt-oss-20b-1:0", "note": "cheaper, same family", "reasoning": True},
    {"id": "amazon.nova-pro-v1:0", "note": "no reasoning block", "reasoning": False},
    {"id": "amazon.nova-lite-v1:0", "note": "routing default — fast, cheap", "reasoning": False},
    {
        "id": "amazon.nova-micro-v1:0",
        "note": "cheapest, crispest short replies",
        "reasoning": False,
    },
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


def build(config: Config | None = None) -> ChatModel:
    """The model this configuration asks for.

    Imports the adapter inside the branch, so choosing `echo` does not require
    boto3 to be installed and a missing optional dependency can only break the
    provider that needs it.
    """
    resolved = config or Config.load()

    if resolved.provider == "echo":
        from agent.models.echo import EchoModel

        return EchoModel(resolved)

    from agent.models.bedrock import BedrockModel

    return BedrockModel(resolved)
