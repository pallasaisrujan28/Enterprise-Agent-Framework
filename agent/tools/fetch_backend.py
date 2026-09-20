"""How a URL becomes markdown — a backend chosen by config, not by code.

WHY THIS SEAM EXISTS
The fetch tools need one thing from the outside world: given a URL, return clean
markdown. In the cluster that is Firecrawl, which renders JavaScript in a real
browser. Locally, Firecrawl is a poor fit — its full stack is six services (API,
worker, Playwright, Redis, Postgres, RabbitMQ), and the lightweight community
fork ships images with no resolvable manifest, so they cannot be trusted to even
pull on an arm64 laptop.

So fetching follows the same rule as object storage and models in ADR-019:
**reach it through an interface whose implementation is selected by config.**
`FETCH_BACKEND=direct` locally, `FETCH_BACKEND=firecrawl` in the cluster. The
fetch tools do not change between environments; one env var does.

WHAT THE `direct` BACKEND CAN AND CANNOT DO — STATED, NOT DISCOVERED
It fetches the HTML with httpx and extracts the main article with trafilatura. No
browser, no service, no spend. The honest limit: it does NOT run JavaScript, so a
page that renders its content client-side (a single-page app, an infinite-scroll
feed) comes back thin or empty. For the documentation and legislation pages this
agent actually reads, static extraction is the right tool. For a JS-heavy target,
that is precisely when you point FETCH_BACKEND at a real Firecrawl.

This is not a deepagents component — deepagents has no web-fetch — so per
coding-standards.md it is legitimately ours. trafilatura is a mature extraction
library, not hand-rolled crawling.
"""

from __future__ import annotations

import os

import httpx

FETCH_BACKEND = os.getenv("FETCH_BACKEND", "direct").strip().lower()

FIRECRAWL_URL = os.getenv("FIRECRAWL_URL", "http://firecrawl-api.tools.svc.cluster.local:3002")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "internal")

# A browser sends one; some sites serve a stub or a 403 to a client that does not.
_UA = "Mozilla/5.0 (compatible; EAF-agent/0.1; +local)"


class FetchError(RuntimeError):
    """A fetch failed in a way the tool should report to the model, not raise.

    The tool layer turns this into an "Error running ..." observation via
    ToolErrorMiddleware, so the model can read it and carry on rather than the
    turn ending.
    """


# ── the direct backend: httpx + trafilatura, no service ──────────────────────


def _direct_scrape(url: str) -> str:
    import trafilatura

    try:
        resp = httpx.get(url, headers={"User-Agent": _UA}, timeout=30, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise FetchError(f"could not fetch {url}: {exc}") from exc

    markdown = trafilatura.extract(
        resp.text,
        output_format="markdown",
        include_links=True,
        include_tables=True,
        url=url,
    )
    if not markdown or not markdown.strip():
        # Almost always a JS-rendered page. Say so, because the failure is
        # specific and the fix is a different backend, not a retry.
        raise FetchError(
            f"no readable content extracted from {url} — the page may render its "
            "content with JavaScript, which the direct fetch backend does not run. "
            "Set FETCH_BACKEND=firecrawl for such pages."
        )
    return markdown


def _direct_crawl(url: str, max_pages: int) -> list[tuple[str, str]]:
    """Same-domain shallow crawl using trafilatura's focused crawler.

    A real crawler feature of the library, not hand-rolled link-following. It
    stays on the seed's domain and stops at max_pages, which is the behaviour the
    crawl tool documents.
    """
    from trafilatura import extract
    from trafilatura.spider import focused_crawler

    try:
        to_visit, known = focused_crawler(url, max_seen_urls=max_pages, max_known_urls=max_pages)
    except Exception as exc:  # noqa: BLE001 - the library raises assorted network errors
        raise FetchError(f"could not crawl {url}: {exc}") from exc

    pages: list[tuple[str, str]] = []
    for page_url in list(known)[:max_pages]:
        try:
            resp = httpx.get(
                page_url, headers={"User-Agent": _UA}, timeout=30, follow_redirects=True
            )
            resp.raise_for_status()
        except httpx.HTTPError:
            continue
        md = extract(resp.text, output_format="markdown", url=page_url)
        if md and md.strip():
            pages.append((page_url, md))
    if not pages:
        raise FetchError(f"crawl of {url} found no readable pages")
    return pages


# ── the firecrawl backend: the cluster's rendering service ───────────────────


def _firecrawl_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {FIRECRAWL_API_KEY}", "Content-Type": "application/json"}


def _firecrawl_scrape(url: str) -> str:
    try:
        resp = httpx.post(
            f"{FIRECRAWL_URL}/v1/scrape",
            json={"url": url, "formats": ["markdown"], "onlyMainContent": True},
            headers=_firecrawl_headers(),
            timeout=60,
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise FetchError(f"Firecrawl could not fetch {url}: {exc}") from exc

    data = resp.json()
    if not data.get("success"):
        raise FetchError(f"Firecrawl could not fetch {url}: {data.get('error', 'unknown error')}")
    markdown = data.get("data", {}).get("markdown", "")
    if not markdown.strip():
        raise FetchError(f"Firecrawl extracted no content from {url}")
    return markdown


def _firecrawl_crawl(url: str, max_pages: int) -> list[tuple[str, str]]:
    try:
        resp = httpx.post(
            f"{FIRECRAWL_URL}/v1/crawl",
            json={
                "url": url,
                "limit": max_pages,
                "scrapeOptions": {"formats": ["markdown"], "onlyMainContent": True},
            },
            headers=_firecrawl_headers(),
            timeout=300,
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise FetchError(f"Firecrawl could not crawl {url}: {exc}") from exc

    data = resp.json()
    if not data.get("success"):
        raise FetchError(f"Firecrawl could not crawl {url}: {data.get('error', 'unknown error')}")
    pages = []
    for page in data.get("data", []):
        md = page.get("markdown", "")
        page_url = page.get("metadata", {}).get("sourceURL", url)
        if md.strip():
            pages.append((page_url, md))
    if not pages:
        raise FetchError(f"Firecrawl crawl of {url} returned no pages")
    return pages


# ── the interface the tools call ─────────────────────────────────────────────


def scrape(url: str) -> str:
    """One URL to markdown, via the configured backend."""
    if FETCH_BACKEND == "firecrawl":
        return _firecrawl_scrape(url)
    return _direct_scrape(url)


def crawl(url: str, max_pages: int) -> list[tuple[str, str]]:
    """A site to a list of (url, markdown), via the configured backend."""
    if FETCH_BACKEND == "firecrawl":
        return _firecrawl_crawl(url, max_pages)
    return _direct_crawl(url, max_pages)


def backend_name() -> str:
    return "firecrawl" if FETCH_BACKEND == "firecrawl" else "direct"
