"""The dashboard's final reply must contain the whole turn's answer.

Regression: the reply was `messages[-1].text`. The agent wrote the full answer
in one message, called write_todos, then closed with a short summary — so the
UI streamed the content, then replaced it with only the summary. The thread's
earlier turns also leaked into the activity list.
"""

from __future__ import annotations

from typing import Any

from agent.dashboard.server import _this_turn, _turn_reply


class _Msg:
    def __init__(self, mtype: str, content: str, tool_calls: list | None = None) -> None:
        self.type = mtype
        self.content = content
        self.tool_calls = tool_calls or []


def _thread() -> list[Any]:
    return [
        _Msg("human", "first question"),
        _Msg("ai", "old answer"),
        _Msg("human", "pull what I sent to simon"),
        _Msg("ai", "Let me search.\n<｜DSML｜function_calls", tool_calls=[{"name": "x"}]),
        _Msg("tool", "email results"),
        _Msg("ai", "# Exact content\nHi Simon, thanks for the offer."),
        _Msg("tool", "Updated todo list"),
        _Msg("ai", "## Summary\n18 emails."),
    ]


def test_reply_keeps_content_written_before_the_closing_summary() -> None:
    reply = _turn_reply(_this_turn(_thread()))
    assert "Hi Simon, thanks for the offer." in reply
    assert "18 emails" in reply


def test_reply_excludes_earlier_turns_and_tool_markup() -> None:
    reply = _turn_reply(_this_turn(_thread()))
    assert "old answer" not in reply
    assert "DSML" not in reply
    assert "Let me search" not in reply  # narration before a tool call


def test_this_turn_starts_after_the_last_human_message() -> None:
    turn = _this_turn(_thread())
    assert all(m.type != "human" for m in turn)
    assert len(turn) == 5


# ── tool cards: what each call SHOWS ─────────────────────────────────────────


def test_tool_view_renders_filesystem_calls_as_commands() -> None:
    from agent.dashboard.server import _tool_view

    assert _tool_view("ls", {"path": "/workspace"})["input"] == "ls /workspace"
    read = _tool_view("read_file", {"file_path": "/skills/x/SKILL.md", "offset": 0, "limit": 50})
    assert read["label"] == "Read file" and "/skills/x/SKILL.md" in read["input"]
    write = _tool_view("write_file", {"file_path": "/workspace/a.md", "content": "hello"})
    assert write["subtitle"] == "/workspace/a.md" and write["input"] == "hello"


def test_tool_view_shows_plan_as_checklist_and_unknown_tools_as_json() -> None:
    from agent.dashboard.server import _tool_view

    plan = _tool_view(
        "write_todos",
        {
            "todos": [
                {"content": "search", "status": "completed"},
                {"content": "table", "status": "pending"},
            ]
        },
    )
    assert plan["input"] == "[x] search\n[ ] table"
    other = _tool_view("mystery_tool", {"a": 1})
    assert other["label"] == "mystery_tool" and '"a": 1' in other["input"]


def test_tool_view_never_uses_the_frame_kind_key() -> None:
    """The view is spread into SSE frames — a `kind` key would overwrite the
    frame type and the browser would drop the event."""
    from agent.dashboard.server import _tool_view

    assert "kind" not in _tool_view("ls", {"path": "/"})
    assert _tool_view("ls", {"path": "/"})["icon"] == "command"


def test_tool_activity_carries_input_and_clipped_output() -> None:
    from agent.dashboard.server import _tool_activity

    class _Ai:
        type = "ai"
        tool_calls = [{"id": "c1", "name": "ls", "args": {"path": "/workspace"}}]

    class _Tool:
        type = "tool"
        tool_call_id = "c1"
        content = "x" * 10000

    [step] = _tool_activity([_Ai(), _Tool()])
    assert step["input"] == "ls /workspace"
    assert step["label"] == "List"
    assert "more chars not shown" in step["output"]
