"""Web search tool — calls SearXNG JSON API running in the tools namespace."""

from __future__ import annotations

import os

import httpx
from langchain_core.tools import tool

SEARXNG_URL = os.getenv(
    "SEARXNG_URL", "http://searxng.tools.svc.cluster.local:8080/search"
)


@tool
def web_search(query: str, num_results: int = 10) -> str:
    """
    Search the web using SearXNG (aggregates Google, Bing, DuckDuckGo,
    Wikipedia, arXiv). Returns a list of results with title, url, and
    content snippet. Use this to find current information or to identify
    URLs worth fetching in detail.
    """
    resp = httpx.get(
        SEARXNG_URL,
        params={
            "q": query,
            "format": "json",
            "engines": "google,bing,duckduckgo,wikipedia",
            "results": num_results,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    results = [
        {"title": r.get("title"), "url": r.get("url"), "snippet": r.get("content")}
        for r in data.get("results", [])[:num_results]
    ]
    return str(results)
