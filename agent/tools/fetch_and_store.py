"""Fetch a URL via Crawl4AI, chunk semantically, store chunks in Qdrant."""

from __future__ import annotations

import json
import os
import uuid

import boto3
import httpx
from langchain_core.tools import tool
from qdrant_client import QdrantClient
from qdrant_client import models as qmodels

CRAWL4AI_URL = os.getenv("CRAWL4AI_URL", "http://crawl4ai.tools.svc.cluster.local:11235")
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


def _ensure_collection() -> None:
    existing = {c.name for c in _qdrant.get_collections().collections}
    if COLLECTION not in existing:
        _qdrant.create_collection(
            COLLECTION,
            vectors_config=qmodels.VectorParams(size=VECTOR_SIZE, distance=qmodels.Distance.COSINE),
        )


@tool
def fetch_and_store(url: str, session_id: str) -> str:
    """
    Fetch a URL using Crawl4AI (renders JavaScript, extracts clean markdown,
    chunks the content semantically). Embeds each chunk with Bedrock Titan
    and stores them in Qdrant under session_id for reuse across reasoning hops.
    Returns the number of chunks stored. Use this to read a page in full detail
    and make its content searchable for the rest of this session.
    """
    resp = httpx.post(
        f"{CRAWL4AI_URL}/crawl",
        json={
            "urls": [url],
            "chunking_strategy": {"type": "semantic"},
            "extraction_strategy": {"type": "markdown"},
        },
        headers={"Authorization": "Bearer internal"},
        timeout=120,
    )
    resp.raise_for_status()

    chunks = resp.json().get("results", [{}])[0].get("chunks", [])
    if not chunks:
        return f"No content extracted from {url}"

    _ensure_collection()
    points = []
    for chunk in chunks:
        text = chunk.get("text", "") if isinstance(chunk, dict) else str(chunk)
        if not text.strip():
            continue
        embedding = _embed(text)
        points.append(
            qmodels.PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={"url": url, "session_id": session_id, "text": text[:4096]},
            )
        )

    if points:
        _qdrant.upsert(collection_name=COLLECTION, points=points)

    return f"Stored {len(points)} chunks from {url} in session memory"
