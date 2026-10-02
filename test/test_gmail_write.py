"""Gmail write: drafts are created, and send_draft only runs after a Send click.

No Google and no Bedrock: the Gmail service is a fake, and the agent runs on a
scripted fake model. The end-to-end tests drive the REAL graph built by
build_agent, so they pin the safety property itself — the graph pauses before
send_draft, Don't send never sends, Send sends exactly once.
"""

from __future__ import annotations

import base64
from email import message_from_bytes
from typing import Any

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langgraph.types import Command

from agent.tools import gmail_write, google_auth


class FakeGmail:
    def __init__(self) -> None:
        self.created: list[dict[str, Any]] = []
        self.sent: list[str] = []
        self._next: Any = None

    def users(self) -> FakeGmail:
        return self

    def drafts(self) -> FakeGmail:
        return self

    def messages(self) -> FakeGmail:
        return self

    def create(self, userId: str, body: dict[str, Any]) -> FakeGmail:  # noqa: N803
        self.created.append(body)
        self._next = {"id": "d-1"}
        return self

    def send(self, userId: str, body: dict[str, Any]) -> FakeGmail:  # noqa: N803
        self.sent.append(body["id"])
        self._next = {"id": "m-9", "threadId": "t-9"}
        return self

    def get(self, userId: str, id: str, **_: Any) -> FakeGmail:  # noqa: A002, N803
        self._next = {
            "threadId": "t-orig",
            "payload": {
                "headers": [
                    {"name": "Message-ID", "value": "<orig@mail>"},
                    {"name": "Subject", "value": "Interview slots"},
                    {"name": "To", "value": "sasha@monday.com"},
                ],
                "body": {"data": base64.urlsafe_b64encode(b"Tuesday works.").decode()},
                "mimeType": "text/plain",
            },
            "message": {
                "payload": {
                    "headers": [
                        {"name": "To", "value": "sasha@monday.com"},
                        {"name": "Subject", "value": "Re: Interview slots"},
                    ],
                    "mimeType": "text/plain",
                    "body": {"data": base64.urlsafe_b64encode(b"Tuesday works.").decode()},
                }
            },
        }
        return self

    def execute(self) -> Any:
        return self._next


@pytest.fixture
def gmail(monkeypatch: pytest.MonkeyPatch) -> FakeGmail:
    fake = FakeGmail()
    monkeypatch.setattr(gmail_write, "_service", lambda: (fake, None))
    return fake


def test_draft_is_created_not_sent(gmail: FakeGmail) -> None:
    out = gmail_write.draft_email.invoke({"to": "a@b.com", "subject": "Hi", "body": "Hello"})
    assert "NOT sent" in out and "draft_id: d-1" in out
    assert gmail.sent == []
    raw = gmail.created[0]["message"]["raw"]
    msg = message_from_bytes(base64.urlsafe_b64decode(raw))
    assert msg["To"] == "a@b.com" and msg["Subject"] == "Hi"


def test_reply_draft_threads_and_fills_subject(gmail: FakeGmail) -> None:
    gmail_write.draft_email.invoke(
        {"to": "sasha@monday.com", "subject": "", "body": "Tue?", "reply_to_message_id": "x"}
    )
    body = gmail.created[0]
    assert body["message"]["threadId"] == "t-orig"
    msg = message_from_bytes(base64.urlsafe_b64decode(body["message"]["raw"]))
    assert msg["Subject"] == "Re: Interview slots"
    assert msg["In-Reply-To"] == "<orig@mail>"


def test_invalid_or_missing_recipients_are_refused(gmail: FakeGmail) -> None:
    assert "invalid" in gmail_write.draft_email.invoke(
        {"to": "not-an-address", "subject": "s", "body": "b"}
    )
    assert "at least one" in gmail_write.draft_email.invoke(
        {"to": " , ", "subject": "s", "body": "b"}
    )
    assert gmail.created == []


def test_old_read_only_token_asks_to_reconnect(monkeypatch: pytest.MonkeyPatch) -> None:
    class Creds:
        granted_scopes = ["https://www.googleapis.com/auth/gmail.readonly"]

    monkeypatch.setattr(google_auth, "load_credentials", lambda: Creds())
    out = gmail_write.draft_email.invoke({"to": "a@b.com", "subject": "s", "body": "b"})
    assert out == google_auth.RECONNECT_FOR_COMPOSE


def test_approval_description_shows_the_real_draft(gmail: FakeGmail) -> None:
    text = gmail_write.send_approval_description({"args": {"draft_id": "d-1"}}, {}, None)
    assert (
        "To: sasha@monday.com" in text
        and "Re: Interview slots" in text
        and "Tuesday works." in text
    )


# ── end to end through the real graph ────────────────────────────────────────


def _agent(monkeypatch: pytest.MonkeyPatch) -> Any:
    import agent.brain as brain

    script = iter(
        [
            AIMessage(
                content="",
                tool_calls=[{"name": "send_draft", "args": {"draft_id": "d-1"}, "id": "s1"}],
            ),
            AIMessage(content="done"),
        ]
    )

    class Fake(GenericFakeChatModel):
        def bind_tools(self, tools: Any, **kw: Any) -> Any:
            return self

    # disable_streaming: the dashboard streams, and the fake model cannot stream a
    # tool-call-only message; invoke semantics are what matter here.
    monkeypatch.setattr(brain, "get_model", lambda: Fake(messages=script, disable_streaming=True))
    monkeypatch.setattr(brain, "build_search_tools", lambda: [])
    return brain.build_agent()


@pytest.mark.parametrize(("decision", "expect_sent"), [("reject", []), ("approve", ["d-1"])])
def test_send_pauses_until_the_user_decides(
    monkeypatch: pytest.MonkeyPatch, gmail: FakeGmail, decision: str, expect_sent: list[str]
) -> None:
    agent = _agent(monkeypatch)
    cfg = {"configurable": {"thread_id": f"t-send-{decision}"}}
    agent.invoke({"messages": [{"role": "user", "content": "send it"}]}, config=cfg)

    pending = agent.get_state(cfg).interrupts
    assert pending, "the graph must pause before send_draft"
    assert pending[0].value["action_requests"][0]["name"] == "send_draft"
    assert gmail.sent == [], "nothing may be sent before the decision"

    agent.invoke(Command(resume={pending[0].id: {"decisions": [{"type": decision}]}}), config=cfg)
    assert gmail.sent == expect_sent
    assert not agent.get_state(cfg).interrupts


def test_dashboard_pauses_shows_buttons_then_resumes(
    monkeypatch: pytest.MonkeyPatch, gmail: FakeGmail
) -> None:
    """The dashboard turn ends with an `approval` frame (Send / Don't send) and
    no gate verdict; the Send click resumes the same thread and sends once."""
    from agent.dashboard import server

    agent = _agent(monkeypatch)
    monkeypatch.setattr(server, "_agent_for", lambda model_id="": agent)
    frames: list[dict[str, Any]] = []
    handler = object.__new__(server.Handler)
    handler._send_frame = frames.append  # type: ignore[method-assign]

    handler._run_turn("send it", "t-dash", "")
    kinds = [f["kind"] for f in frames]
    assert "approval" in kinds and "gate" not in kinds
    approval = next(f for f in frames if f["kind"] == "approval")
    assert approval["actions"][0]["name"] == "send_draft"
    assert "Re: Interview slots" in approval["actions"][0]["description"]
    assert frames[-1]["kind"] == "done" and frames[-1]["awaiting_approval"] is True
    assert server._pending_interrupts(agent, "t-dash") and gmail.sent == []

    frames.clear()
    handler._run_turn("", "t-dash", "", "approve")
    assert gmail.sent == ["d-1"]
    assert not server._pending_interrupts(agent, "t-dash")
    assert frames[-1]["kind"] == "done" and not frames[-1].get("awaiting_approval")
