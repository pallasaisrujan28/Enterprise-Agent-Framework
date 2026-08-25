"""
Session working memory — stores semantic chunks of retrieved web content in
Qdrant so the agent can query them across multi-hop reasoning without
re-fetching pages it has already read.

Every chunk is keyed by session_id so different threads never see each
other's memory.
"""

from __future__ import annotations

import json
import os
import uuid

import boto3
from qdrant_client import QdrantClient
from qdrant_client import models as qm

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant.tools.svc.cluster.local:6333")
EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"
COLLECTION = "agent_session_memory"
VECTOR_SIZE = 512

_bedrock = boto3.client("bedrock-runtime", region_name=os.getenv("AWS_DEFAULT_REGION", "eu-west-2"))
_qdrant = QdrantClient(url=QDRANT_URL)


def embed(text: str) -> list[float]:
    resp = _bedrock.invoke_model(
        modelId=EMBEDDING_MODEL,
        body=json.dumps({"inputText": text[:2048], "dimensions": VECTOR_SIZE, "normalize": True}),
    )
    return json.loads(resp["body"].read())["embedding"]


def ensure_collection() -> None:
    existing = {c.name for c in _qdrant.get_collections().collections}
    if COLLECTION not in existing:
        _qdrant.create_collection(
            COLLECTION,
            vectors_config=qm.VectorParams(size=VECTOR_SIZE, distance=qm.Distance.COSINE),
        )


def store(session_id: str, source_url: str, chunks: list[str]) -> int:
    """Embed and upsert text chunks. Returns the number of chunks stored."""
    ensure_collection()
    points = [
        qm.PointStruct(
            id=str(uuid.uuid4()),
            vector=embed(chunk),
            payload={"session_id": session_id, "url": source_url, "text": chunk[:4096]},
        )
        for chunk in chunks
        if chunk.strip()
    ]
    if points:
        _qdrant.upsert(collection_name=COLLECTION, points=points)
    return len(points)


def search(session_id: str, query: str, top_k: int = 5) -> list[dict]:
    """Return top-k chunks most similar to query within this session."""
    try:
        existing = {c.name for c in _qdrant.get_collections().collections}
        if COLLECTION not in existing:
            return []
    except Exception:
        return []

    from qdrant_client.models import FieldCondition, Filter, MatchValue

    results = _qdrant.search(  # type: ignore[union-attr]
        collection_name=COLLECTION,
        query_vector=embed(query),
        query_filter=Filter(
            must=[FieldCondition(key="session_id", match=MatchValue(value=session_id))]
        ),
        limit=top_k,
        with_payload=True,
    )
    return [
        {
            "score": hit.score,
            "url": (hit.payload or {}).get("url"),
            "text": (hit.payload or {}).get("text", ""),
        }
        for hit in results
    ]
