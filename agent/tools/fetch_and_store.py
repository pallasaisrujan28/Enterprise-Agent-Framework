"""Fetch URL → clean markdown via Crawl4AI, store chunks in Qdrant session memory."""

from __future__ import annotations

import os

import httpx
from langchain_core.tools import tool

from agent.memory import working as mem

CRAWL4AI_URL = os.getenv("CRAWL4AI_URL", "http://crawl4ai.tools.svc.cluster.local:11235")


@tool
def fetch_and_store(url: str, session_id: str) -> str:
    """
    Fetch a URL using Crawl4AI (renders JavaScript, extracts clean markdown,
    chunks the content semantically). Embeds each chunk with Bedrock Titan
    and stores them in session working memory (Qdrant) under session_id.
    Returns the number of chunks stored.

    Use this to read a page in full detail and make its content searchable
    across the rest of this multi-hop research session without re-fetching.
    Always call search_memory first to check if the page was already fetched.
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

    raw_chunks = resp.json().get("results", [{}])[0].get("chunks", [])
    if not raw_chunks:
        return f"No content extracted from {url}"

    text_chunks = [
        (chunk.get("text", "") if isinstance(chunk, dict) else str(chunk))
        for chunk in raw_chunks
    ]
    stored = mem.store(session_id=session_id, source_url=url, chunks=text_chunks)
    return f"Stored {stored} chunks from {url} in session memory"
