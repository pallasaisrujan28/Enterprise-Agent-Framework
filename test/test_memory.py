"""Tests for the two memory fixes — no network, no Neo4j.

Both pin behaviour that shipped wrong and would regress silently:

  - the retrieval gate must fire on references to the ASSISTANT'S own prior
    session actions ("what else did you consider"), not only the user's
    biography. It returned False for exactly that, so durable recall never ran
    even though the facts were stored.
  - consolidation must strip the reasoning-model scratchpad before writing, or
    the graph fills with "Assistant: .<reasoning>Attempt to fetch…" noise.

The gate is exercised with a fake router (a stand-in chat model); the stripper
is a pure function.
"""

from __future__ import annotations

from typing import Any

from agent.memory import retrieval_gate
from agent.middleware.memory import _recent_exchange, _strip_reasoning


class _FakeReply:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeRouter:
    """Returns a canned JSON decision, ignoring the prompt."""

    def __init__(self, reply: str) -> None:
        self._reply = reply

    def invoke(self, _prompt: str) -> _FakeReply:
        return _FakeReply(self._reply)


# ── retrieval gate scope ──────────────────────────────────────────────────────


def test_gate_parses_a_true_decision() -> None:
    router = _FakeRouter('{"retrieve": true, "query": "iron alternatives"}')
    retrieve, query = retrieval_gate.should_retrieve(router, "what other irons?")
    assert retrieve is True
    assert query == "iron alternatives"


def test_gate_parses_a_false_decision() -> None:
    router = _FakeRouter('{"retrieve": false, "query": ""}')
    retrieve, _ = retrieval_gate.should_retrieve(router, "what is 2+2?")
    assert retrieve is False


def test_gate_fails_open_on_garbage() -> None:
    """A reply with no JSON must recall anyway — a stale memory beats a lost one."""
    router = _FakeRouter("I think, therefore I am")
    retrieve, query = retrieval_gate.should_retrieve(router, "the acme deadline")
    assert retrieve is True
    assert query == "the acme deadline"  # falls open to the raw message


def test_gate_prompt_covers_the_assistants_own_prior_actions() -> None:
    """The scope broadening is in the prompt itself — pin it so it can't silently
    revert to the biography-only wording that ignored 'what did you consider'."""
    prompt = retrieval_gate._GATE_PROMPT.lower()
    assert "what else did you consider" in prompt or "options you showed" in prompt
    assert "assistant" in prompt


# ── consolidation reasoning-strip ─────────────────────────────────────────────


def test_strip_reasoning_removes_a_closed_block() -> None:
    text = "Here is the answer.<reasoning>let me think hard about this</reasoning>"
    assert _strip_reasoning(text) == "Here is the answer"


def test_strip_reasoning_removes_an_unclosed_block() -> None:
    # gpt-oss sometimes runs the reasoning to the end with no closing tag.
    text = "<reasoning>Attempt to fetch the Amazon page and click add to basket"
    assert _strip_reasoning(text) == ""


def test_strip_reasoning_keeps_a_plain_answer() -> None:
    assert _strip_reasoning("The Russell Hobbs iron is 3100W.") == "The Russell Hobbs iron is 3100W"


class _Msg:
    def __init__(self, mtype: str, text: str) -> None:
        self.type = mtype
        self.text = text


def test_recent_exchange_strips_reasoning_from_assistant_turns() -> None:
    messages: list[Any] = [
        _Msg("human", "add the iron to my cart"),
        _Msg("ai", ".<reasoning>Attempt to fetch Amazon search page</reasoning>Added it."),
    ]
    out = _recent_exchange(messages, pairs=3)
    assert "<reasoning>" not in out
    assert "Attempt to fetch" not in out
    assert "Added it" in out  # trailing "." is trimmed by the stripper, that's fine
    assert "User: add the iron to my cart" in out


# ── consolidation window + quality gate ──────────────────────────────────────


def test_recent_exchange_keeps_the_user_question_in_an_agentic_turn() -> None:
    """Many assistant messages per turn must not push the user line out — the
    stored episode began with 'Assistant:' and Graphiti lost what was asked."""
    messages: list[Any] = [_Msg("human", "pull what I sent to simon moore")]
    messages += [_Msg("ai", f"Let me search step {i}") for i in range(10)]
    out = _recent_exchange(messages, pairs=3)
    assert out.startswith("User: pull what I sent to simon moore")


def test_strip_reasoning_removes_deepseek_tool_markup() -> None:
    text = "Let me search.\n<｜DSML｜function_calls"
    assert "DSML" not in _strip_reasoning(text)


def test_quality_gate_skips_error_answers() -> None:
    from agent.middleware.memory import _worth_remembering

    msgs: list[Any] = [
        _Msg("human", "check my gmail"),
        _Msg("ai", "I can't access your Gmail directly right now because it isn't connected."),
    ]
    keep, reason = _worth_remembering(msgs)
    assert keep is False and "error" in reason


def test_quality_gate_keeps_a_substantive_answer() -> None:
    from agent.middleware.memory import _worth_remembering

    msgs: list[Any] = [
        _Msg("human", "who is my recruiter at astrazeneca?"),
        _Msg("ai", "Your recruiter is Simon Moore; he sent the offer on 14 Sep 2026."),
    ]
    assert _worth_remembering(msgs)[0] is True


# ── ontology + compact episodes ───────────────────────────────────────────────


class _AiMsg(_Msg):
    def __init__(self, text: str, tool_calls: list[dict] | None = None) -> None:
        super().__init__("ai", text)
        self.tool_calls = tool_calls or []


def test_ontology_passes_graphitis_own_validation() -> None:
    """Graphiti rejects entity fields that collide with EntityNode's (name,
    summary, …) — at write time, in the background, where it'd be a silent loss."""
    from graphiti_core.utils.ontology_utils.entity_types_utils import validate_entity_types

    from agent.memory import ontology

    assert validate_entity_types(ontology.ENTITY_TYPES)
    for pair, names in ontology.EDGE_TYPE_MAP.items():
        for name in names:
            assert name in ontology.EDGE_TYPES, (pair, name)
    for model in [*ontology.ENTITY_TYPES.values(), *ontology.EDGE_TYPES.values()]:
        assert model.__doc__, f"{model.__name__} needs a docstring — it IS the description"


def test_episode_drops_tool_narration_and_caps_long_answers() -> None:
    messages: list[Any] = [
        _Msg("human", "what did I send simon?"),
        _AiMsg("Let me search your mail:", tool_calls=[{"name": "list_recent_emails"}]),
        _AiMsg("x" * 5000),
    ]
    out = _recent_exchange(messages, pairs=3)
    assert "Let me search" not in out
    assert len(out) < 1400
    assert out.endswith("[…]")


def test_substantive_text_alongside_a_tool_call_is_kept() -> None:
    """The model often writes the real answer in the same message as a
    write_todos call — that must not be mistaken for narration."""
    answer = "Simon Moore is your recruiter at AstraZeneca. " * 10
    messages: list[Any] = [
        _Msg("human", "who is simon?"),
        _AiMsg(answer, tool_calls=[{"name": "write_todos"}]),
    ]
    assert "Simon Moore is your recruiter" in _recent_exchange(messages, pairs=3)


# ── hygiene (dry-run judge parsing, episode rule) ─────────────────────────────


def test_hygiene_parses_judge_reply_and_ignores_bad_indexes() -> None:
    from agent.memory.hygiene import _parse_drop

    reply = 'sure: {"drop": [{"i": 0, "why": "about assistant"}, {"i": 99, "why": "x"}]}'
    assert _parse_drop(reply, 3) == [(0, "about assistant")]


def test_hygiene_flags_nothing_when_judge_reply_is_unparseable() -> None:
    import pytest

    from agent.memory.hygiene import _parse_drop

    with pytest.raises(ValueError):
        _parse_drop("I think they all look fine", 3)


def test_hygiene_flags_failure_episodes_but_keeps_real_ones() -> None:
    from agent.memory.hygiene import _episode_is_junk

    bad = "User: check gmail\nAssistant: I can't access your Gmail directly right now."
    also_bad = (
        "User: astrazeneca mail\nAssistant: It looks like Gmail access isn't currently configured."
    )
    assert _episode_is_junk(also_bad)
    good = "User: who is simon?\nAssistant: Simon Moore is your recruiter at AstraZeneca."
    assert _episode_is_junk(bad)
    assert _episode_is_junk(good) == ""


# ── notes: edge-less entities must be recallable ─────────────────────────────
# Regression: a saved note ("user-visa-timeline: granted 5 Aug 2026 …") became a
# single entity with a summary and NO fact edges. Recall searched edges only, so
# the note was stored but never came back.


def _fake_runtime() -> Any:
    import asyncio
    import threading
    from types import SimpleNamespace

    from agent.memory.semantic import _GraphitiRuntime

    edge = SimpleNamespace(uuid="e1", fact="The user shops for groceries at Tesco.")
    note = SimpleNamespace(uuid="n1", name="user-visa-timeline", summary="Granted 5 Aug 2026.")
    linked = SimpleNamespace(uuid="n2", name="Tesco", summary="A supermarket.")
    blank = SimpleNamespace(uuid="n3", name="£769", summary="")
    calls: list[tuple[str, dict[str, Any]]] = []

    class Driver:
        async def execute_query(self, cypher: str, **kw: Any) -> Any:
            calls.append((cypher, kw))
            if "UNWIND" in cypher:  # which candidates have no edges
                return SimpleNamespace(records=[{"uuid": "n1"}])
            return SimpleNamespace(records=[{"n": 1}])

    class Graphiti:
        driver = Driver()

        async def search_(self, query: str, config: Any, group_ids: Any, **_: Any) -> Any:
            if config.edge_config is not None:
                return SimpleNamespace(edges=[edge], nodes=[])
            return SimpleNamespace(edges=[], nodes=[note, linked, blank])

    rt = object.__new__(_GraphitiRuntime)
    rt._loop = asyncio.new_event_loop()
    threading.Thread(target=rt._loop.run_forever, daemon=True).start()
    rt._graphiti = Graphiti()
    rt.calls = calls
    return rt


def test_recall_includes_edgeless_notes_but_not_linked_entities() -> None:
    rt = _fake_runtime()
    facts = rt.recall("visa start date")
    assert facts == [
        "The user shops for groceries at Tesco.",
        "user-visa-timeline: Granted 5 Aug 2026.",
    ]


def test_notes_get_prefixed_ids_that_update_and_forget_route_to_the_entity() -> None:
    from agent.memory.semantic import NOTE_PREFIX

    rt = _fake_runtime()
    ids = [i for i, _ in rt.search_facts("visa")]
    assert ids == ["e1", f"{NOTE_PREFIX}n1"]

    assert rt.update_fact(f"{NOTE_PREFIX}n1", "Granted 6 Aug 2026.")
    cypher, kw = rt.calls[-1]
    assert "SET n.summary" in cypher and kw["uuid"] == "n1"

    assert rt.forget_fact(f"{NOTE_PREFIX}n1")
    cypher, kw = rt.calls[-1]
    assert "DETACH DELETE" in cypher and "NOT (n)-[:RELATES_TO]-()" in cypher

    assert rt.forget_fact("e1")
    assert "RELATES_TO {uuid: $uuid}" in rt.calls[-1][0]
