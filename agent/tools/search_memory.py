"""Search session working memory (Qdrant) for content already fetched."""

from __future__ import annotations

import json
import os

import boto3
from langchain_core.tools import tool
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant.tools.svc.cluster.local:6333")
EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"
COLLECTION = "agent_session_memory"
VECTOR_SIZE = 512

_bedrock = boto3.client("bedrock-runtime", region_name="eu-west-2")
_qdrant = QdrantClient(url=QDRANT_URL)


def _embed(text: str) -> list[float]:
    resp = _bedrock.invoke_model(
        modelId=EMBEDDING_MODEL,
        body=json.dumps({"inputText": text[:2048], "dimensions": VECTOR_SIZE, "normalize": True}),
    )
    return json.loads(resp["body"].read())["embedding"]


@tool
def search_memory(query: str, session_id: str, top_k: int = 5) -> str:
    """
    Search content already fetched and stored in this session's working memory.
    Returns the top-k most relevant chunks with source URLs and relevance scores.
    Always call this before fetch_and_store to avoid re-fetching pages already
    read in this session.
    """
    try:
        existing = {c.name for c in _qdrant.get_collections().collections}
        if COLLECTION not in existing:
            return "Session memory is empty — no pages fetched yet."
    except Exception:
        return "Session memory is empty."

    query_emb = _embed(query)
    results = _qdrant.search(
        collection_name=COLLECTION,
        query_vector=query_emb,
        query_filter=Filter(
            must=[FieldCondition(key="session_id", match=MatchValue(value=session_id))]
        ),
        limit=top_k,
        with_payload=True,
    )

    if not results:
        return "No relevant content found in session memory."

    parts = []
    for hit in results:
        payload = hit.payload or {}
        parts.append(
            f"[score={hit.score:.3f}] {payload.get('url', 'unknown')}\n"
            f"{payload.get('text', '')[:800]}"
        )
    return "\n\n---\n\n".join(parts)
