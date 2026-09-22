"""Guards on model selection and the fetch backend.

Two small surfaces that each caused a real failure and would fail silently again:

  - an unverified model id reaching Bedrock. Every anthropic.* id fails on our
    accounts, two on billing; the guard refuses off-list ids up front with a
    useful message instead of a cryptic Bedrock error.
  - the fetch backend extracting nothing. A JS-rendered page returns empty
    markdown, which must be a clear FetchError (the fix is a different backend),
    not a silent empty store.

No network: get_model_named's refusal path raises before constructing a client,
and the fetch tests drive trafilatura with in-memory HTML.
"""

from __future__ import annotations

from typing import Any

import pytest

from agent import model

# ── model guard ──────────────────────────────────────────────────────────────


def test_verified_ids_frozenset_matches_the_list() -> None:
    """The set the endpoint checks against must not drift from the rendered list."""
    assert frozenset(str(e["id"]) for e in model.VERIFIED_MODELS) == model.VERIFIED_MODEL_IDS


def test_get_model_named_refuses_an_unverified_id() -> None:
    """The refusal happens locally, before any client is built — so no network."""
    with pytest.raises(ValueError) as caught:
        model.get_model_named("anthropic.claude-3-5-sonnet-20241022-v2:0")
    assert "not a verified model" in str(caught.value)


def test_no_anthropic_id_is_verified() -> None:
    """They fail on these accounts; keeping them off the list is the guard."""
    assert not any("anthropic" in i for i in model.VERIFIED_MODEL_IDS)


def test_credential_source_names_a_source_never_a_secret(monkeypatch: Any) -> None:
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAEXAMPLENOTREAL")
    source = model.credential_source()
    assert "AWS_ACCESS_KEY_ID" in source
    assert "AKIAEXAMPLENOTREAL" not in source  # the value must never appear


# ── fetch backend ────────────────────────────────────────────────────────────

_ARTICLE_HTML = """<!doctype html><html><head><title>T</title></head><body>
<article><h1>Amazon Bedrock</h1>
<p>Amazon Bedrock is a fully managed service developed by Amazon Web Services
that offers foundation models through a single API. It supports models from
several providers and is used to build generative AI applications.</p>
<p>This second paragraph exists so the extractor has enough text to return
something substantial rather than discarding a one-line page.</p>
</article></body></html>"""


class _Resp:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:  # noqa: D401 - stub
        return None


def test_direct_scrape_extracts_markdown(monkeypatch: Any) -> None:
    from agent.tools import fetch_backend

    monkeypatch.setattr(fetch_backend, "FETCH_BACKEND", "direct")
    monkeypatch.setattr(fetch_backend.httpx, "get", lambda *a, **k: _Resp(_ARTICLE_HTML))

    md = fetch_backend.scrape("https://example.com/bedrock")
    assert "Amazon Bedrock" in md
    assert "Amazon Web Services" in md


def test_direct_scrape_raises_fetcherror_on_empty_page(monkeypatch: Any) -> None:
    """A JS-only page yields no extractable text. That must be a clear error
    pointing at the fix (a real Firecrawl), not a silent empty store."""
    from agent.tools import fetch_backend

    monkeypatch.setattr(fetch_backend, "FETCH_BACKEND", "direct")
    monkeypatch.setattr(
        fetch_backend.httpx, "get", lambda *a, **k: _Resp("<html><body></body></html>")
    )

    with pytest.raises(fetch_backend.FetchError) as caught:
        fetch_backend.scrape("https://spa.example.com")
    assert "JavaScript" in str(caught.value)


def test_fetch_backend_is_selected_by_config(monkeypatch: Any) -> None:
    from agent.tools import fetch_backend

    monkeypatch.setattr(fetch_backend, "FETCH_BACKEND", "firecrawl")
    assert fetch_backend.backend_name() == "firecrawl"
    monkeypatch.setattr(fetch_backend, "FETCH_BACKEND", "direct")
    assert fetch_backend.backend_name() == "direct"


# Web search moved to the SearXNG MCP server (agent/tools/searxng_mcp.py); the
# old config-selected DuckDuckGo/SearXNG backend and its tests were removed with
# it. The MCP path needs a live subprocess + SearXNG instance, so it is exercised
# by scripts/local_check.py rather than a unit test here.
