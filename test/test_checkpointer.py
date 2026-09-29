"""The checkpointer must actually persist when CHECKPOINT_DB is set.

Regression: every run used the in-RAM MemorySaver (AgentCore's saver isn't
installed), so the dashboard forgot all threads on restart.
"""

from __future__ import annotations

import warnings

import pytest

from agent.memory.checkpointer import get_checkpointer


def test_sqlite_saver_persists_across_instances(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    pytest.importorskip("langgraph.checkpoint.sqlite")
    from langgraph.checkpoint.base import empty_checkpoint

    db = tmp_path / "cp.sqlite"
    monkeypatch.delenv("AGENTCORE_MEMORY_ID", raising=False)
    monkeypatch.setenv("CHECKPOINT_DB", str(db))

    config = {"configurable": {"thread_id": "t1", "checkpoint_ns": ""}}
    first = get_checkpointer()
    first.put(config, empty_checkpoint(), {"source": "input", "step": 0}, {})

    second = get_checkpointer()  # a "restarted process"
    assert second.get_tuple(config) is not None
    assert (db.stat().st_mode & 0o777) == 0o600


def test_falls_back_to_memory_saver_with_a_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    from langgraph.checkpoint.memory import MemorySaver

    monkeypatch.delenv("AGENTCORE_MEMORY_ID", raising=False)
    monkeypatch.delenv("CHECKPOINT_DB", raising=False)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        saver = get_checkpointer()
    assert isinstance(saver, MemorySaver)
    assert any("NOT persist" in str(w.message) for w in caught)
