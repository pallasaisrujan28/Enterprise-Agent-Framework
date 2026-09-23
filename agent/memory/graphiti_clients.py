"""Bedrock-backed clients for Graphiti — LLM, embedder, reranker.

Graphiti defaults to OpenAI for extraction, embeddings and reranking. We run
everything on Bedrock with our existing SigV4/SSO credentials (the same ones the
rest of the harness uses), so instead of pointing Graphiti at an OpenAI-compatible
endpoint with a short-lived bearer token, we plug in three small custom clients:

  BedrockLLMClient      entity/edge extraction + summaries, via ChatBedrockConverse
  BedrockEmbedder       Titan text embeddings (the same model our code already used)
  PassthroughReranker   a no-op cross-encoder (see its docstring for why)

This keeps memory on the one credential path and off any per-endpoint token.
"""

from __future__ import annotations

import json
from typing import Any

from graphiti_core.cross_encoder.client import CrossEncoderClient
from graphiti_core.embedder.client import EmbedderClient
from graphiti_core.llm_client.client import LLMClient
from graphiti_core.llm_client.config import LLMConfig, ModelSize
from graphiti_core.prompts.models import Message
from langchain_core.messages import HumanMessage, SystemMessage

from agent.model import get_fast_model, get_model


class BedrockLLMClient(LLMClient):
    """Graphiti's LLM calls, served by our Bedrock models.

    Graphiti asks for STRUCTURED output: `_generate_response` must return a dict
    matching `response_model` (a pydantic class). ChatBedrockConverse does this
    natively through `.with_structured_output(...)`, which drives the model's
    tool-use to fill the schema — so we hand Graphiti a parsed dict. When no
    schema is requested, we return `{"content": <text>}`, the shape Graphiti's
    unstructured path expects.

    The `medium`/`small` model split maps to our main vs fast Bedrock models, so
    Graphiti's cheap classification steps run on nova-lite and the heavy
    extraction on gpt-oss.
    """

    def __init__(self, config: LLMConfig | None = None) -> None:
        super().__init__(config or LLMConfig(), cache=False)
        self._main = get_model()
        self._fast = get_fast_model()

    async def _generate_response(
        self,
        messages: list[Message],
        response_model: type[Any] | None = None,
        max_tokens: int = 16384,
        model_size: ModelSize = ModelSize.medium,
    ) -> dict[str, Any]:
        model = self._fast if model_size == ModelSize.small else self._main
        lc_messages: list[Any] = []
        for m in messages:
            if m.role == "system":
                lc_messages.append(SystemMessage(content=m.content))
            else:
                lc_messages.append(HumanMessage(content=m.content))

        if response_model is not None:
            structured = model.with_structured_output(response_model)
            result = await structured.ainvoke(lc_messages)
            # result is a pydantic instance (or dict); normalise to a plain dict.
            if hasattr(result, "model_dump"):
                return result.model_dump()
            return dict(result) if isinstance(result, dict) else json.loads(str(result))

        reply = await model.ainvoke(lc_messages)
        return {"content": reply.text if hasattr(reply, "text") else str(reply.content)}


class BedrockEmbedder(EmbedderClient):
    """Titan text embeddings for Graphiti's vector search over entities/edges.

    Reuses the exact model the old Qdrant path used (Titan v2, 512-dim), so the
    embedding behaviour is unchanged — only what it feeds moved from a vector DB
    to Graphiti's node/edge index.
    """

    _MODEL = "amazon.titan-embed-text-v2:0"
    _DIM = 512

    def __init__(self) -> None:
        import os

        import boto3

        self._bedrock = boto3.client(
            "bedrock-runtime", region_name=os.getenv("AWS_DEFAULT_REGION", "eu-west-2")
        )

    def _embed_one(self, text: str) -> list[float]:
        resp = self._bedrock.invoke_model(
            modelId=self._MODEL,
            body=json.dumps({"inputText": text[:2048], "dimensions": self._DIM, "normalize": True}),
        )
        return json.loads(resp["body"].read())["embedding"]

    async def create(self, input_data: str | list[str] | Any) -> list[float]:
        # Graphiti calls this for a single string in practice.
        text = input_data if isinstance(input_data, str) else " ".join(map(str, input_data))
        return self._embed_one(text)

    async def create_batch(self, input_data_list: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in input_data_list]


class PassthroughReranker(CrossEncoderClient):
    """A no-op cross-encoder — returns passages in order with descending scores.

    Graphiti's default reranker is an OpenAI LLM call (needs an OpenAI key), and
    the alternatives are a local BGE model (pulls torch, ~GB) or a Gemini call.
    Reranking only REORDERS results that hybrid search (semantic + BM25 + graph)
    already found; it is a refinement, not the retrieval itself. So we start with
    a passthrough: search still works and returns relevant facts, just without a
    final cross-encoder re-sort. A real reranker (BGE local or an LLM one) can be
    swapped in later without touching the rest of memory.
    """

    async def rank(self, query: str, passages: list[str]) -> list[tuple[str, float]]:
        n = len(passages)
        return [(p, (n - i) / n) for i, p in enumerate(passages)]
