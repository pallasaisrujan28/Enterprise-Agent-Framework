"""
Fetch URL via Firecrawl, store chunks in Qdrant session memory.

Firecrawl replaces Crawl4AI. Two tools:
  fetch_and_store — single URL scrape (fast, LLM-ready markdown)
  crawl_site      — full site crawl following internal links (deep research)

Internal URL: http://firecrawl-api.tools.svc.cluster.local:3002
"""

from __future__ import annotations

import os

import httpx
from langchain_core.tools import tool

from agent.memory import working as mem

FIRECRAWL_URL = os.getenv("FIRECRAWL_URL", "http://firecrawl-api.tools.svc.cluster.local:3002")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "internal")


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {FIRECRAWL_API_KEY}", "Content-Type": "application/json"}


@tool
def fetch_and_store(url: str, session_id: str) -> str:
    """
    Fetch a URL using Firecrawl (renders JavaScript, extracts clean markdown).
    Embeds each chunk with Bedrock Titan and stores in session working memory.
    Returns the number of chunks stored.
    Always call search_memory first to avoid re-fetching pages already read.
    """
    resp = httpx.post(
        f"{FIRECRAWL_URL}/v1/scrape",
        json={"url": url, "formats": ["markdown"], "onlyMainContent": True},
        headers=_headers(),
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()

    if not data.get("success"):
        return f"Firecrawl could not fetch {url}: {data.get('error', 'unknown error')}"

    markdown = data.get("data", {}).get("markdown", "")
    if not markdown.strip():
        return f"No content extracted from {url}"

    chunk_size = 2000
    chunks = [markdown[i : i + chunk_size] for i in range(0, len(markdown), chunk_size)]
    stored = mem.store(session_id=session_id, source_url=url, chunks=chunks)
    return f"Fetched and stored {stored} chunks from {url} in session memory"


@tool
def crawl_site(url: str, session_id: str, max_pages: int = 20) -> str:
    """
    Crawl an entire website starting from url, following internal links.
    Stores all content in session working memory for semantic search.
    Use for deep research: all sections of legislation, full API docs, etc.
    max_pages limits pages crawled (default 20).
    Always call search_memory first to check if the site was already crawled.
    """
    resp = httpx.post(
        f"{FIRECRAWL_URL}/v1/crawl",
        json={
            "url": url,
            "limit": max_pages,
            "scrapeOptions": {"formats": ["markdown"], "onlyMainContent": True},
        },
        headers=_headers(),
        timeout=300,
    )
    resp.raise_for_status()
    data = resp.json()

    if not data.get("success"):
        return f"Firecrawl could not crawl {url}: {data.get('error', 'unknown error')}"

    pages = data.get("data", [])
    if not pages:
        return f"No pages found crawling {url}"

    total_stored = 0
    for page in pages:
        markdown = page.get("markdown", "")
        page_url = page.get("metadata", {}).get("sourceURL", url)
        if markdown.strip():
            chunk_size = 2000
            chunks = [markdown[i : i + chunk_size] for i in range(0, len(markdown), chunk_size)]
            total_stored += mem.store(session_id=session_id, source_url=page_url, chunks=chunks)

    return f"Crawled {len(pages)} pages from {url}, stored {total_stored} chunks in session memory"
