"""Gmail write — create drafts, and send a draft only after the user says Send.

TWO STEPS, ON PURPOSE.
  draft_email   creates a Gmail DRAFT (new message, or a reply in an existing
                thread). Reversible and harmless: nothing leaves the mailbox.
                Returns the draft id and exactly what it contains.
  send_draft    sends one draft. It is listed in `interrupt_on` in
                agent/brain.py, so HumanInTheLoopMiddleware PAUSES the graph
                before it runs; the dashboard shows the draft with two buttons,
                Send and Don't send, and only Send resumes the call. A typed
                "yes" in chat does not send — the decision is a button, enforced
                by the graph, not by the prompt.

Scope: gmail.compose (drafts + send). Nothing here can delete, archive, label or
edit existing mail. Best-effort like the read tools: a missing scope, an
unconnected account or an API error returns a sentence, never an exception.
"""

from __future__ import annotations

import base64
import re
from email.message import EmailMessage
from typing import Any

from langchain_core.tools import tool

from agent.tools import google_auth
from agent.tools.gmail import _header

_ADDRESS = re.compile(r"^[^@\s,<>]+@[^@\s,<>]+\.[^@\s,<>]+$")
_PREVIEW_CHARS = 1200


def _service() -> tuple[Any, str | None]:
    """(gmail service, None) or (None, a readable reason it's unavailable)."""
    try:
        from googleapiclient.discovery import build
    except ImportError:
        return None, google_auth.INSTALL_HINT
    creds = google_auth.load_credentials()
    if creds is None:
        return None, google_auth.SETUP_HINT
    if not google_auth.has_scope(creds, google_auth.GMAIL_COMPOSE):
        return None, google_auth.RECONNECT_FOR_COMPOSE
    return build("gmail", "v1", credentials=creds, cache_discovery=False), None


def _addresses(raw: str) -> tuple[list[str], list[str]]:
    """(valid, invalid) from a comma/semicolon separated list. Accepts
    'Name <a@b.com>' and bare 'a@b.com'."""
    valid: list[str] = []
    invalid: list[str] = []
    for part in re.split(r"[,;]", raw or ""):
        part = part.strip()
        if not part:
            continue
        m = re.search(r"<([^>]+)>", part)
        addr = (m.group(1) if m else part).strip()
        (valid if _ADDRESS.match(addr) else invalid).append(part)
    return valid, invalid


def build_message(
    to: str, subject: str, body: str, cc: str = "", reply: dict[str, str] | None = None
) -> EmailMessage:
    """The MIME message for a draft. `reply` carries the original's Message-ID
    and Subject so Gmail threads it as a reply."""
    msg = EmailMessage()
    msg["To"] = to
    if cc:
        msg["Cc"] = cc
    subj = subject.strip()
    if reply:
        orig = reply.get("subject", "")
        if not subj:
            subj = orig if orig.lower().startswith("re:") else f"Re: {orig}".strip()
        if reply.get("message_id"):
            msg["In-Reply-To"] = reply["message_id"]
            refs = (reply.get("references", "") + " " + reply["message_id"]).strip()
            msg["References"] = refs
    msg["Subject"] = subj
    msg.set_content(body)
    return msg


def describe_draft(to: str, cc: str, subject: str, body: str) -> str:
    text = (
        body
        if len(body) <= _PREVIEW_CHARS
        else body[:_PREVIEW_CHARS] + "\n… [rest of the body not shown]"
    )
    head = f"To: {to}" + (f"\nCc: {cc}" if cc else "") + f"\nSubject: {subject}"
    return f"{head}\n\n{text}"


@tool
def draft_email(
    to: str, subject: str, body: str, cc: str = "", reply_to_message_id: str = ""
) -> str:
    """Create a Gmail DRAFT — nothing is sent. Use for a new email, or for a reply
    by passing reply_to_message_id (an id from list_recent_emails / read_email),
    which threads it and fills "Re: <subject>" if subject is empty.
    `to` and `cc` are comma-separated addresses. Returns the draft id and its exact
    content; show it to the user. To send, call send_draft(draft_id) — the user
    then gets Send / Don't send buttons and the email goes only if they press Send.
    """
    service, reason = _service()
    if service is None:
        return reason or google_auth.SETUP_HINT
    valid, invalid = _addresses(to)
    cc_valid, cc_invalid = _addresses(cc)
    if invalid or cc_invalid:
        return f"Not drafted — these addresses look invalid: {', '.join(invalid + cc_invalid)}."
    if not valid:
        return "Not drafted — `to` needs at least one email address."
    if not (body or "").strip():
        return "Not drafted — the body is empty."

    reply: dict[str, str] | None = None
    thread_id = ""
    rid = (reply_to_message_id or "").strip()
    try:
        if rid:
            orig = (
                service.users()
                .messages()
                .get(
                    userId="me",
                    id=rid,
                    format="metadata",
                    metadataHeaders=["Message-ID", "Subject", "References"],
                )
                .execute()
            )
            headers = (orig.get("payload") or {}).get("headers", [])
            reply = {
                "message_id": _header(headers, "Message-ID"),
                "subject": _header(headers, "Subject"),
                "references": _header(headers, "References"),
            }
            thread_id = orig.get("threadId", "")
        msg = build_message(", ".join(valid), subject, body, ", ".join(cc_valid), reply)
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        payload: dict[str, Any] = {"message": {"raw": raw}}
        if thread_id:
            payload["message"]["threadId"] = thread_id
        draft = service.users().drafts().create(userId="me", body=payload).execute()
    except Exception as exc:  # noqa: BLE001
        return google_auth.api_error_message(exc, "Gmail")

    preview = describe_draft(str(msg["To"]), str(msg["Cc"] or ""), str(msg["Subject"]), body)
    kind = "Reply draft" if rid else "Draft"
    return (
        f"{kind} created (NOT sent). draft_id: {draft.get('id')}\n\n{preview}\n\n"
        "To send it, call send_draft with this draft_id; the user confirms with a button."
    )


@tool
def send_draft(draft_id: str) -> str:
    """Send ONE existing Gmail draft by its draft_id (from draft_email). The user
    is shown the draft with Send / Don't send buttons first; this only runs if
    they press Send. Never call it unless the user asked to send."""
    service, reason = _service()
    if service is None:
        return reason or google_auth.SETUP_HINT
    did = (draft_id or "").strip()
    if not did:
        return "send_draft needs the draft_id returned by draft_email."
    try:
        sent = service.users().drafts().send(userId="me", body={"id": did}).execute()
    except Exception as exc:  # noqa: BLE001
        return google_auth.api_error_message(exc, "Gmail")
    print(f"gmail: sent draft {did} as message {sent.get('id')}", flush=True)
    return f"Sent. message id: {sent.get('id')} (thread {sent.get('threadId', '?')})."


def send_approval_description(tool_call: Any, state: Any, runtime: Any) -> str:
    """What the Send / Don't send prompt shows: the draft's real headers and body,
    fetched from Gmail — not the model's summary of it."""
    did = str((tool_call.get("args") or {}).get("draft_id", "")).strip()
    service, reason = _service()
    if service is None or not did:
        return f"Send Gmail draft {did or '(no id)'}?" + (f"\n({reason})" if reason else "")
    try:
        d = service.users().drafts().get(userId="me", id=did, format="full").execute()
        payload = (d.get("message") or {}).get("payload") or {}
        headers = payload.get("headers", [])
        from agent.tools.gmail import _body_text

        return describe_draft(
            _header(headers, "To"),
            _header(headers, "Cc"),
            _header(headers, "Subject"),
            _body_text(payload),
        )
    except Exception as exc:  # noqa: BLE001
        return f"Send Gmail draft {did}? (could not load a preview: {google_auth.api_error_message(exc, 'Gmail')})"
