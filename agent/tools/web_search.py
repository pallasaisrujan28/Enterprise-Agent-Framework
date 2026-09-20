"""web_search — the public web, through a config-selected backend.

HOW results are obtained is agent/tools/search_backend.py, chosen by
SEARCH_BACKEND: `duckduckgo` (the ddgs library, no service) for local, `searxng`
(the aggregating container) in the cluster. This tool only formats what comes
back, so it is identical in both environments.
"""

from __future__ import annotations

from langchain_core.tools import tool

from agent.tools import search_backend


@tool
def web_search(query: str, num_results: int = 10) -> str:
    """
    Search the public web and get back the top results (title, url, snippet).
    Use this to find current information or to identify URLs worth reading in
    full with fetch_and_store.
    """
    # SearchError propagates: ToolErrorMiddleware turns it into an observation the
    # model can read, rather than a raise that ends the turn.
    results = search_backend.search(query, num_results)
    if not results:
        return f"No web results for {query!r}."
    lines = [f"Web results for {query!r} (via {search_backend.backend_name()}):"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r['title']}\n   {r['snippet']}\n   {r['url']}")
    return "\n".join(lines)
