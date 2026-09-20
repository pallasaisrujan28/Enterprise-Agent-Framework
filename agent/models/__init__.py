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

# Verified by calling Converse in eu-west-2 and reading the reply back, on
# 2026-09-19 and again on 2026-08-30. NOT a catalogue and not from documentation:
# every Anthropic id fails with AccessDeniedException on these accounts, and
# k8s/deployment.yaml named two of them. If a model is not on this list, it has
# not been tried — check before offering it.
#
# `reasoning` marks a model that spends output budget thinking before it answers,
# which is why agent.config sets a floor on max_tokens.
verified_models: tuple[dict[str, str | bool], ...] = (
    {"id": "openai.gpt-oss-120b-1:0", "note": "default — strongest verified", "reasoning": True},
    {"id": "openai.gpt-oss-20b-1:0", "note": "cheaper, same family", "reasoning": True},
    {"id": "amazon.nova-pro-v1:0", "note": "no reasoning block", "reasoning": False},
    {"id": "amazon.nova-lite-v1:0", "note": "fast and cheap", "reasoning": False},
    {"id": "amazon.nova-micro-v1:0", "note": "cheapest", "reasoning": False},
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
