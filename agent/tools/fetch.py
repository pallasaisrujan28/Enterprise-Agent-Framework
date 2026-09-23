"""fetch_url — read a web page as clean markdown, straight into context.

WHY THIS RETURNS CONTENT INSTEAD OF STORING IT.
The old fetch tool embedded pages into a Qdrant vector store and a companion
`search_memory` tool queried them back. That was a vector-DB scratchpad, and it
was the wrong tool for the job: the leading assistants don't use a vector DB to
hold a page they just read — they put the text in the model's context and let it
reason over it (context-stuffing), or navigate with agentic search. So this tool
now simply returns the page's markdown. Oversized pages are capped here, and the
harness's SummarizationMiddleware handles context pressure on long turns.

HOW A URL BECOMES MARKDOWN is still agent/tools/fetch_backend.py, chosen by
FETCH_BACKEND: `direct` (httpx + trafilatura, no service) locally, `firecrawl`
(JS-rendering service) in the cluster. Same tool in both environments.
"""

from __future__ import annotations

from langchain_core.tools import tool

from agent.tools import fetch_backend

# A single page rarely needs more than this, and it keeps one fetch from
# swallowing the whole context window. The model can fetch a more specific URL
# if it needs a section that was cut.
_MAX_CHARS = 20000


@tool
def fetch_url(url: str) -> str:
    """
    Fetch a web page and return its main content as clean markdown.

    Use this after web search to read a promising result in full. The text is
    returned directly for you to reason over — there is no separate memory to
    query. Very long pages are truncated; fetch a more specific URL if you need
    a section that was cut.
    """
    # FetchError is allowed to propagate: ToolErrorMiddleware turns it into an
    # observation the model can read, rather than a raise that ends the turn.
    markdown = fetch_backend.scrape(url)
    if len(markdown) > _MAX_CHARS:
        markdown = markdown[:_MAX_CHARS] + "\n\n[truncated — fetch a more specific URL for more]"
    return f"Content of {url}:\n\n{markdown}"
