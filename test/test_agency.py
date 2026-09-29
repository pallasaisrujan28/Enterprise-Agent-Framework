"""Tests for the learning-agency tools: save_note, manage_memory, create_skill.

No Neo4j and no LLM: the memory tools are driven with `semantic` monkeypatched,
and skill authoring writes to a tmp dir via AGENT_SKILLS_DIR. These pin the
behaviour that matters — graceful memory-off, the search/update/forget routing,
and that skill authoring refuses bad names and never clobbers an existing skill.
"""

from __future__ import annotations

import importlib

import pytest

from agent.memory import semantic
from agent.memory import tools as memory_tools

# ── save_note ─────────────────────────────────────────────────────────────────


def test_save_note_off_is_graceful(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(semantic, "memory_enabled", lambda: False)
    out = memory_tools.save_note.invoke({"subject": "alex", "content": "likes mornings"})
    assert "off" in out.lower()


def test_save_note_saves_when_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(semantic, "memory_enabled", lambda: True)
    saved: dict = {}
    monkeypatch.setattr(semantic, "save_fact", lambda s, c: saved.update({"s": s, "c": c}))
    out = memory_tools.save_note.invoke({"subject": "alex", "content": "likes mornings"})
    assert "saved to memory" in out.lower()
    assert saved == {"s": "alex", "c": "likes mornings"}


def test_save_note_needs_both_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(semantic, "memory_enabled", lambda: True)
    out = memory_tools.save_note.invoke({"subject": "", "content": "x"})
    assert "subject" in out.lower()


# ── manage_memory ─────────────────────────────────────────────────────────────


def test_manage_search_lists_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(semantic, "memory_enabled", lambda: True)
    monkeypatch.setattr(semantic, "search_facts", lambda q: [("u1", "Alex likes mornings")])
    out = memory_tools.manage_memory.invoke({"action": "search", "query": "alex"})
    assert "#u1" in out and "mornings" in out


def test_manage_forget_routes_to_delete(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(semantic, "memory_enabled", lambda: True)
    seen: dict = {}
    monkeypatch.setattr(semantic, "forget_fact", lambda uuid: seen.update({"uuid": uuid}) or True)
    out = memory_tools.manage_memory.invoke({"action": "forget", "id": "u1"})
    assert "forgotten" in out.lower()
    assert seen == {"uuid": "u1"}


def test_manage_update_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(semantic, "memory_enabled", lambda: True)
    monkeypatch.setattr(semantic, "update_fact", lambda uuid, text: True)
    out = memory_tools.manage_memory.invoke({"action": "update", "id": "u1", "content": "new"})
    assert "updated" in out.lower()


def test_manage_bad_action(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(semantic, "memory_enabled", lambda: True)
    out = memory_tools.manage_memory.invoke({"action": "nonsense"})
    assert "search, update, forget" in out


# ── create_skill ──────────────────────────────────────────────────────────────


@pytest.fixture
def author(monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.setenv("AGENT_SKILLS_DIR", str(tmp_path))
    import agent.skills_engine.author as mod

    return importlib.reload(mod)


def test_create_skill_writes_valid_file(author) -> None:
    out = author.write_skill("Weekly Review", "run my weekly review", "1. do x\n2. do y")
    assert "created skill 'weekly-review'" in out.lower()
    path = author.skills_dir() / "weekly-review" / "SKILL.md"
    assert path.exists()
    text = path.read_text()
    assert "name: weekly-review" in text  # slug matches dir, spec-compliant
    assert "description: run my weekly review" in text


def test_create_skill_refuses_overwrite(author) -> None:
    author.write_skill("dup", "d", "body")
    out = author.write_skill("dup", "d2", "body2")
    assert "already exists" in out.lower()


def test_create_skill_rejects_bad_name(author) -> None:
    assert "slug" in author.write_skill("!!!", "d", "b").lower()


def test_create_skill_needs_body(author) -> None:
    assert "body" in author.write_skill("ok-name", "desc", "  ").lower()
