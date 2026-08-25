"""Query session working memory for content already fetched this session."""

from __future__ import annotations

from langchain_core.tools import tool

from agent.memory import working as mem


@tool
def search_memory(query: str, session_id: str, top_k: int = 5) -> str:
    """
    Search content already fetched and stored in this session's working memory.
    Returns the top-k most relevant chunks with source URLs and relevance scores.

    Always call this BEFORE fetch_and_store — if relevant content is already in
    memory from a page fetched earlier in this session, there is no need to
    re-fetch. This avoids redundant HTTP requests and keeps reasoning grounded
    in what the agent has already read.
    """
    results = mem.search(session_id=session_id, query=query, top_k=top_k)
    if not results:
        return "No relevant content found in session memory — try fetch_and_store."

    parts = [
        f"[score={r['score']:.3f}] {r['url']}\n{r['text'][:800]}"
        for r in results
    ]
    return "\n\n---\n\n".join(parts)
