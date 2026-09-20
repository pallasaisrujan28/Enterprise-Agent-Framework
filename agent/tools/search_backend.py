"""How a query becomes web results — a backend chosen by config, not by code.

The third seam, alongside the model layer and the fetch backend, and for the same
reason (ADR-019): the web_search tool needs results, and how they are obtained
differs by environment without the tool caring.

  SEARCH_BACKEND=duckduckgo   the `ddgs` library. No service, no key, no spend.
                              The default, so local works with nothing running.
  SEARCH_BACKEND=searxng      the self-hosted SearXNG in the tools namespace,
                              which aggregates several engines. Set in the
                              cluster, where the container exists.

WHY ddgs RATHER THAN waku's STDLIB SCRAPE
waku scrapes html.duckduckgo.com with urllib and a regex. It is zero-dependency
and it no longer works from here — DuckDuckGo blocks the raw HTML endpoint, and a
live probe returned zero results (waku's own code carries a comment warning of
exactly this). `ddgs` is the maintained library that handles the blocking,
rotates endpoints, and parses the response; per coding-standards.md, a maintained
library beats re-deriving a scrape that already fails.

SearXNG stays the cluster default because it aggregates Google/Bing/DDG/Wikipedia
rather than DuckDuckGo alone — broader coverage where a container is cheap. DDG is
the right local default because it needs no container at all.
"""

from __future__ import annotations

import os

import httpx

SEARCH_BACKEND = os.getenv("SEARCH_BACKEND", "duckduckgo").strip().lower()

SEARXNG_URL = os.getenv("SEARXNG_URL", "http://searxng.tools.svc.cluster.local:8080/search")


class SearchError(RuntimeError):
    """A search failed in a way the tool reports to the model, not raises."""


def _duckduckgo(query: str, max_results: int) -> list[dict[str, str]]:
    from ddgs import DDGS

    try:
        hits = list(DDGS().text(query, max_results=max_results))
    except Exception as exc:  # noqa: BLE001 - ddgs raises assorted network/rate errors
        raise SearchError(f"DuckDuckGo search failed: {exc}") from exc
    # ddgs uses title/href/body; normalise to the shape web_search renders.
    return [
        {"title": h.get("title", ""), "url": h.get("href", ""), "snippet": h.get("body", "")}
        for h in hits
    ]


def _searxng(query: str, max_results: int) -> list[dict[str, str]]:
    try:
        resp = httpx.get(
            SEARXNG_URL,
            params={
                "q": query,
                "format": "json",
                "engines": "google,bing,duckduckgo,wikipedia",
            },
            timeout=30,
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise SearchError(f"SearXNG search failed: {exc}") from exc

    results = resp.json().get("results", [])[:max_results]
    return [
        {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("content", "")}
        for r in results
    ]


def search(query: str, max_results: int = 10) -> list[dict[str, str]]:
    """Web results as [{title, url, snippet}], via the configured backend."""
    if SEARCH_BACKEND == "searxng":
        return _searxng(query, max_results)
    return _duckduckgo(query, max_results)


def backend_name() -> str:
    return "searxng" if SEARCH_BACKEND == "searxng" else "duckduckgo"
