"""Bedrock, behind the model seam.

THE ONLY FILE IN THE REPOSITORY THAT MAY IMPORT BOTO3 FOR GENERATION
ADR-011's proxy rule is enforced by keeping the SDK here. boto3 is imported
inside `__init__`, not at module scope, so `import agent.models` works on a
machine without it and the dependency only has to exist for the provider that
needs it.

CONVERSE, NOT INVOKE_MODEL
`converse` normalises the request and response across model families. The
alternative, `invoke_model`, takes a provider-specific JSON body — the same call
would need one body shape for gpt-oss and another for Nova, in our code. The
repo's existing embedding call uses `invoke_model` because Titan embeddings has
no Converse support, which is the exception rather than the pattern.

TWO PROVIDER QUIRKS, VERIFIED BY CALLING IT
Both of these were found by running the call, not by reading documentation:

  gpt-oss returns TWO content blocks, `reasoningContent` then `text`. Nova
  returns one `text` block. `content[0]["text"]` therefore raises KeyError on
  gpt-oss, which is exactly the sort of thing that works in testing against one
  model and breaks on a model switch. Blocks are scanned by key, never indexed.

  The reasoning block spends the SAME output budget as the answer. At
  maxTokens=16, gpt-oss-120b returned reasoning and no answer at all — a
  successful API call with an empty reply. `Completion.spent_budget_thinking`
  reports it so the turn can say what happened instead of showing a blank.
"""

from __future__ import annotations

import time
from collections.abc import Generator
from typing import TYPE_CHECKING, Any

from agent.config import Config
from agent.models.base import Chunk, Completion, Message, ModelError, Usage

if TYPE_CHECKING:  # pragma: no cover - typing only
    from collections.abc import Iterable

# Maps the AWS error code to what the reader should actually DO about it. Every
# one of these was produced by a real failed call during wiring, which is why the
# hints are specific: "access denied" on its own sends people to IAM, when the
# fix is a model-access request in the Bedrock console.
_HINTS: dict[str, str] = {
    "AccessDeniedException": (
        "this account has not been granted access to that model — request it under "
        "Bedrock > Model access, in this exact region"
    ),
    "ExpiredTokenException": "the credentials have expired — refresh them and retry",
    "ExpiredToken": "the credentials have expired — refresh them and retry",
    "UnrecognizedClientException": "the credentials are not valid for this account or region",
    "ThrottlingException": "Bedrock is throttling this account — retry, or use a smaller model",
    "ServiceUnavailableException": "Bedrock is unavailable in this region right now",
    "ModelTimeoutException": "the model took too long — try a smaller model or a shorter prompt",
    "ModelNotReadyException": "the model is still warming up — retry shortly",
}


class BedrockModel:
    """A `ChatModel` over `bedrock-runtime`."""

    def __init__(self, config: Config, client: Any = None) -> None:
        """`client` is injectable so a test can drive this without AWS.

        The import sits inside the constructor: building a `BedrockModel` is the
        moment boto3 genuinely becomes required, and until then the process
        should not pay for it or fail without it.
        """
        self._config = config
        if client is not None:
            self._client = client
            return
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover - environment-dependent
            raise ModelError(
                "boto3 is not installed",
                hint="install the bedrock extra: uv sync --extra bedrock",
            ) from exc
        self._client = boto3.client("bedrock-runtime", region_name=config.region)

    @property
    def name(self) -> str:
        return self._config.model

    # ── request shaping ───────────────────────────────────────────────────────

    def _request(self, messages: tuple[Message, ...], system: str) -> dict[str, Any]:
        if not messages:
            raise ModelError("a model call needs at least one message")

        payload: dict[str, Any] = {
            "modelId": self._config.model,
            "messages": [
                {"role": message.role, "content": [{"text": message.text}]} for message in messages
            ],
            "inferenceConfig": {
                "maxTokens": self._config.max_tokens,
                "temperature": self._config.temperature,
            },
        }
        # Converse wants the system prompt as its own top-level field, and
        # rejects an empty list — so it is omitted entirely when there is none
        # rather than passed as [].
        if system.strip():
            payload["system"] = [{"text": system}]
        return payload

    @staticmethod
    def _split_blocks(blocks: Iterable[dict[str, Any]]) -> tuple[str, str]:
        """Separate the answer from the thinking.

        Scans by key. Unknown block kinds (a future toolUse, say) are ignored
        rather than raising, so a model returning something new degrades to a
        shorter answer instead of a 500.
        """
        answer: list[str] = []
        thinking: list[str] = []
        for block in blocks:
            if "text" in block:
                answer.append(block["text"])
            elif "reasoningContent" in block:
                reasoning = block["reasoningContent"]
                thinking.append(reasoning.get("reasoningText", {}).get("text", ""))
        return "".join(answer), "".join(thinking)

    def _usage(self, response: dict[str, Any], elapsed_ms: int) -> Usage:
        """Prefer the provider's own latency, fall back to ours.

        Bedrock reports `metrics.latencyMs` for the model call itself, which
        excludes our network round trip. When it is absent, wall clock is the
        honest second choice — and the two are not the same number, so whichever
        is used should be the one that was actually measured.
        """
        usage = response.get("usage", {})
        metrics = response.get("metrics", {})
        return Usage(
            input_tokens=int(usage.get("inputTokens", 0)),
            output_tokens=int(usage.get("outputTokens", 0)),
            latency_ms=int(metrics.get("latencyMs", elapsed_ms)),
        )

    # ── the two calls ─────────────────────────────────────────────────────────

    def complete(self, messages: tuple[Message, ...], system: str = "") -> Completion:
        request = self._request(messages, system)
        started = time.monotonic()
        try:
            response = self._client.converse(**request)
        except Exception as exc:
            raise self._as_model_error(exc) from exc
        elapsed_ms = int((time.monotonic() - started) * 1000)

        blocks = response.get("output", {}).get("message", {}).get("content", [])
        text, reasoning = self._split_blocks(blocks)
        return Completion(
            model=self._config.model,
            text=text,
            reasoning=reasoning,
            usage=self._usage(response, elapsed_ms),
            stop_reason=str(response.get("stopReason", "")),
        )

    def stream(
        self, messages: tuple[Message, ...], system: str = ""
    ) -> Generator[Chunk, None, Completion]:
        request = self._request(messages, system)
        started = time.monotonic()
        try:
            response = self._client.converse_stream(**request)
        except Exception as exc:
            raise self._as_model_error(exc) from exc

        answer: list[str] = []
        thinking: list[str] = []
        stop_reason = ""
        usage = Usage()

        try:
            for event in response["stream"]:
                if "contentBlockDelta" in event:
                    delta = event["contentBlockDelta"].get("delta", {})
                    if "text" in delta:
                        piece = delta["text"]
                        answer.append(piece)
                        yield Chunk("text", piece)
                    elif "reasoningContent" in delta:
                        # Streamed reasoning has no `reasoningText` wrapper — the
                        # delta carries `text` directly. Different shape from the
                        # non-streamed block, which is why both are handled
                        # explicitly rather than through one helper.
                        piece = delta["reasoningContent"].get("text", "")
                        if piece:
                            thinking.append(piece)
                            yield Chunk("reasoning", piece)
                elif "messageStop" in event:
                    stop_reason = str(event["messageStop"].get("stopReason", ""))
                elif "metadata" in event:
                    elapsed_ms = int((time.monotonic() - started) * 1000)
                    usage = self._usage(event["metadata"], elapsed_ms)
        except Exception as exc:
            # A stream can fail PART WAY, after text has already been shown. The
            # partial answer is kept and the error attached, because discarding
            # what the user already read is worse than reporting both.
            raise self._as_model_error(exc, partial="".join(answer)) from exc

        return Completion(
            model=self._config.model,
            text="".join(answer),
            reasoning="".join(thinking),
            usage=usage,
            stop_reason=stop_reason,
        )

    # ── failure translation ───────────────────────────────────────────────────

    def _as_model_error(self, exc: Exception, partial: str = "") -> ModelError:
        """Turn an SDK exception into something a person can act on.

        Botocore's own message is kept — it names the model and operation, which
        is the useful half — and a hint is added for the codes we have actually
        hit. Unknown codes pass through with no invented advice.
        """
        code = ""
        response = getattr(exc, "response", None)
        if isinstance(response, dict):
            code = str(response.get("Error", {}).get("Code", ""))
        if not code:
            code = type(exc).__name__

        hint = _HINTS.get(code, "")
        message = str(exc) or code

        # This one is not an error code but a message body, and it means something
        # different from AccessDenied: the ACCOUNT has no Bedrock entitlement at
        # all, rather than one model being ungranted.
        if "Access to Bedrock models is not allowed for this account" in message:
            hint = (
                "this AWS account is not enabled for Bedrock at all — a different "
                "account or an enablement request is needed, not a model grant"
            )
        # AccessDenied has at least three distinct causes and they need different
        # actions. This one is billing, and the generic "request model access"
        # hint sends people to a console page that will not help them.
        if "INVALID_PAYMENT_INSTRUMENT" in message:
            hint = (
                "the model is gated on billing, not on IAM — this account has no valid "
                "payment instrument, so no amount of model-access granting will fix it. "
                "Every Anthropic id fails this way here; use a verified model instead "
                "(see agent.models.verified_models)"
            )
        if "marketplace" in message.lower() and "subscribe" in message.lower():
            hint = (
                "the model needs a Marketplace subscription — the caller is missing "
                "aws-marketplace:Subscribe, which is separate from bedrock:InvokeModel"
            )
        if "credential" in message.lower() and "not locate" in message.lower():
            hint = "no AWS credentials found — export them or set AWS_PROFILE"

        if partial:
            hint = f"{hint}; the partial reply was kept" if hint else "the partial reply was kept"

        return ModelError(f"{self._config.model}: {message}", hint=hint)
