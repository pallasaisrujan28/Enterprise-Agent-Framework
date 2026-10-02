"""Tool catalog: deferred tools are hidden until find_tools unlocks them.

No Bedrock: semantic ranking is driven by a tiny fake embedder (bag of concept
words), which is enough to pin the behaviour that matters — meaning beats exact
words, keyword fallback when the embedder fails, the relative cutoff, and the
middleware hiding/unhiding schemas per thread state.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from langchain_core.messages import SystemMessage
from langchain_core.tools import tool

from agent.middleware.tool_catalog import ToolCatalog, ToolCatalogMiddleware, _union


@tool
def list_recent_emails(query: str = "") -> str:
    """List the user's Gmail messages matching a search."""
    return ""


@tool
def list_calendar_events(days: int = 7) -> str:
    """List upcoming Google Calendar events."""
    return ""


@tool
def update_soul(rule: str) -> str:
    """Persist a standing behaviour rule for the assistant's persona."""
    return ""


_CONCEPTS = {
    "mail": {"gmail", "email", "emails", "inbox", "messages", "mail"},
    "time": {"calendar", "events", "schedule", "meeting", "meetings", "agenda"},
    "self": {"persona", "behaviour", "rule", "soul"},
}


def _fake_embed(text: str) -> list[float]:
    words = set(text.lower().replace("_", " ").replace(".", " ").split())
    return [float(len(words & c)) for c in _CONCEPTS.values()]


def _catalog(embed: Any = _fake_embed) -> ToolCatalog:
    tools = [list_recent_emails, list_calendar_events, update_soul]
    areas = {
        "list_recent_emails": "email",
        "list_calendar_events": "calendar",
        "update_soul": "persona rules",
    }
    return ToolCatalog(tools, areas, embed=embed)


def test_semantic_match_without_shared_keywords() -> None:
    # "agenda"/"meetings" never appear in the calendar tool's text.
    assert [n for n, _ in _catalog().search("what meetings are on my agenda")] == [
        "list_calendar_events"
    ]


def test_relative_cutoff_keeps_only_close_matches() -> None:
    assert [n for n, _ in _catalog().search("check my inbox")] == ["list_recent_emails"]


def test_falls_back_to_keywords_when_embedder_fails() -> None:
    def broken(_: str) -> list[float]:
        raise RuntimeError("bedrock down")

    assert [n for n, _ in _catalog(broken).search("gmail messages")] == ["list_recent_emails"]


def test_no_match_returns_nothing() -> None:
    def broken(_: str) -> list[float]:
        raise RuntimeError("down")

    assert _catalog(broken).search("zzz qqq") == []


def test_unlocks_accumulate() -> None:
    assert _union(["a"], ["b", "a"]) == ["a", "b"]
    assert _union(None, ["a"]) == ["a"]


def _request(unlocked: list[str]) -> Any:
    tools = [
        SimpleNamespace(name=n)
        for n in ("ls", "list_recent_emails", "list_calendar_events", "update_soul")
    ]

    class Req(SimpleNamespace):
        def override(self, **kw: Any) -> Any:
            return Req(**{**self.__dict__, **kw})

    return Req(
        tools=tools,
        state={"unlocked_tools": unlocked},
        system_message=SystemMessage(content="base"),
    )


def test_middleware_hides_deferred_until_unlocked() -> None:
    mw = ToolCatalogMiddleware(_catalog())
    seen: list[Any] = []
    mw.wrap_model_call(_request([]), lambda r: seen.append(r))
    mw.wrap_model_call(_request(["list_recent_emails"]), lambda r: seen.append(r))

    assert [t.name for t in seen[0].tools] == ["ls"]
    assert [t.name for t in seen[1].tools] == ["ls", "list_recent_emails"]
    assert "find_tools" in seen[0].system_message.content
    assert "email" in seen[0].system_message.content
    assert [t.name for t in mw.tools] == ["find_tools"]


def test_a_match_loads_its_whole_area() -> None:
    cat = ToolCatalog(
        [list_recent_emails, list_calendar_events, update_soul],
        {
            "list_recent_emails": "email",
            "list_calendar_events": "email",
            "update_soul": "persona rules",
        },
    )
    assert cat.expand(["list_recent_emails"]) == ["list_recent_emails", "list_calendar_events"]
    assert cat.expand([]) == []


def test_find_tools_unlocks_via_state_update() -> None:
    mw = ToolCatalogMiddleware(_catalog())
    find = mw.tools[0]
    runtime = SimpleNamespace(tool_call_id="c1", state={})
    cmd = find.func(query="read my email", runtime=runtime)  # type: ignore[attr-defined]
    assert cmd.update["unlocked_tools"] == ["list_recent_emails"]
    msg = cmd.update["messages"][0]
    assert msg.tool_call_id == "c1" and "list_recent_emails" in msg.content
