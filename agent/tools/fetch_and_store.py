"""
Fetch a URL to markdown, chunk it, and store the chunks in Qdrant session memory.

HOW A URL BECOMES MARKDOWN IS NOT DECIDED HERE. That is agent/tools/fetch_backend.py,
chosen by FETCH_BACKEND: `direct` (httpx + trafilatura, no service) for local, or
`firecrawl` (the cluster's JS-rendering service) in deployment. These tools only
chunk and store, so they are identical in both environments — the ADR-019
portability rule, applied to fetching.

Two tools:
  fetch_and_store — one URL
  crawl_site      — a whole site, following internal links (deep research)
"""

from __future__ import annotations

from langchain_core.tools import tool

from agent.memory import working as mem
from agent.tools import fetch_backend

# Chunk size for the vector store. Small enough that a search hit is a focused
# passage rather than a whole page, large enough to keep a complete thought.
_CHUNK_CHARS = 2000


def _chunk(markdown: str) -> list[str]:
    return [markdown[i : i + _CHUNK_CHARS] for i in range(0, len(markdown), _CHUNK_CHARS)]


@tool
def fetch_and_store(url: str, session_id: str) -> str:
    """
    Fetch a URL as clean markdown and store it in session working memory,
    embedding each chunk so it can be searched later. Returns how many chunks
    were stored. Always call search_memory first to avoid re-fetching a page
    already read this session.
    """
    # FetchError is allowed to propagate: ToolErrorMiddleware turns it into an
    # observation the model can read, rather than a raise that ends the turn.
    markdown = fetch_backend.scrape(url)
    stored = mem.store(session_id=session_id, source_url=url, chunks=_chunk(markdown))
    return f"Fetched and stored {stored} chunks from {url} in session memory"


@tool
def crawl_site(url: str, session_id: str, max_pages: int = 20) -> str:
    """
    Crawl a website from url, following internal links, and store every page's
    content in session working memory for semantic search. Use for deep research:
    all sections of a piece of legislation, a full set of API docs. max_pages
    caps how many pages are fetched (default 20). Call search_memory first.
    """
    pages = fetch_backend.crawl(url, max_pages)
    total = 0
    for page_url, markdown in pages:
        total += mem.store(session_id=session_id, source_url=page_url, chunks=_chunk(markdown))
    return f"Crawled {len(pages)} pages from {url}, stored {total} chunks in session memory"
