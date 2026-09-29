"""The dashboard server — stdlib only, no framework, no build step.

Deliberately `http.server`. The dashboard's job is to show what the harness is
doing, and a web framework plus a bundler is more moving parts than the thing
being observed. Adding a dependency here would also breach the repository's own
rule that dependencies are bounded and reviewed: a framework for four routes
does not earn its supply-chain surface.

Static files are read from disk on EVERY request, so editing a `.css` or `.js`
file and hard-reloading shows the change. Python is NOT reloaded — this module
and everything it imports are held in memory, so a change here needs a restart.
That asymmetry surprises people, so it is stated here and in the UI footer.
"""

from __future__ import annotations

import json
import mimetypes
import os
import re
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from agent.dashboard import topology
from agent.middleware.obligations import load_obligation_policies
from agent.model import (
    FAST_MODEL_ID,
    MODEL_ID,
    REGION,
    VERIFIED_MODEL_IDS,
    VERIFIED_MODELS,
    credential_source,
)

STATIC = Path(__file__).resolve().parent / "static"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7788

# A message longer than this is refused rather than sent. Not a safety feature —
# it is a cost control. An accidental paste of a large file becomes a bill, and
# the model would truncate it anyway.
MAX_MESSAGE_CHARS = 8000

# Bound to loopback by default and stated plainly: this server has NO
# authentication. It now carries CONVERSATION CONTENT as well as component
# status, which raises the stakes on that considerably — anyone who can reach the
# port can read every exchange and spend money against the configured model.
# Binding it to 0.0.0.0 publishes both.
_NO_AUTH_WARNING = (
    "dashboard has NO authentication and now serves chat — anyone who can reach "
    "this port can read every conversation and spend against your Bedrock "
    "account. Bind to loopback unless that has been deliberately reconsidered"
)

# CONVERSATION HISTORY IS THE HARNESS'S JOB, NOT OURS.
#
# This used to keep its own Session objects with its own bounded history window.
# That was a second implementation of something create_deep_agent already has: a
# checkpointer, keyed by `thread_id`. So the dashboard now passes a thread_id and
# the graph remembers the thread — which also means the HTTP service and the
# dashboard share one notion of a conversation instead of two.
#
# The lock guards only the agent cache below. Building an agent constructs boto3
# clients and a backend, and ThreadingHTTPServer serves each request on its own
# thread, so two tabs posting at once would otherwise build two.
_AGENTS: dict[str, Any] = {}
_AGENTS_LOCK = threading.Lock()

# Which argument best identifies what a tool call actually did, per tool. The
# query for a search, the URL for a fetch — the thing worth showing so a human
# can validate the agent used fresh, relevant sources.
_ACTIVITY_ARG: dict[str, str] = {
    "searxng_web_search": "query",
    "searxngWebSearch": "query",  # camelCase, as PTC exposes it to interpreter code
    "web_search": "query",
    "search_memory": "query",
    "fetch_and_store": "url",
    "read_file": "file_path",
    "eval": "code",
    "task": "description",
    "list_recent_emails": "query",
    "read_email": "message_id",
    "list_calendar_events": "start",
}


def _text_of(content: Any) -> str:
    """Flatten a message's content (str, or a list of content blocks) to text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                parts.append(str(block.get("text") or block.get("content") or ""))
            else:
                parts.append(str(block))
        return "".join(parts)
    return str(content or "")


# DeepSeek on Bedrock sometimes echoes its tool-call markup into the text
# content ("<｜DSML｜function_calls…") even though the call itself is parsed
# correctly. It is transport noise, never part of the answer.
_DSML = re.compile(r"<[｜|]DSML[｜|][^\n]*", re.IGNORECASE)


_NARRATION_CHARS = 300


def _this_turn(messages: list[Any]) -> list[Any]:
    """Messages produced by the CURRENT turn: everything after the last human
    message. The checkpointer returns the whole thread, so without this slice
    the reply and activity would include earlier turns."""
    for i in range(len(messages) - 1, -1, -1):
        if getattr(messages[i], "type", "") == "human":
            return messages[i + 1 :]
    return messages


def _turn_reply(messages: list[Any]) -> str:
    """The full answer for this turn: the text of EVERY assistant message in it,
    in order. Agents often write the substantive answer in one message, then make
    a bookkeeping tool call (write_todos), then close with a short summary — so
    taking only the last message drops the content the user actually asked for."""
    parts: list[str] = []
    for m in _this_turn(messages):
        if getattr(m, "type", "") != "ai":
            continue
        text = _DSML.sub("", _text_of(getattr(m, "content", ""))).strip()
        # "Let me search…" before a tool call is progress narration — the live
        # tool rows already show it. Substantive text written alongside a tool
        # call (e.g. the answer, then a write_todos update) is kept.
        if getattr(m, "tool_calls", None) and len(text) < _NARRATION_CHARS:
            continue
        if text:
            parts.append(text)
    return "\n\n".join(parts)


# How a tool call is SHOWN: a kind label, an optional subtitle (the path or
# target), and the input as the command-like text a person would type. Unknown
# tools fall back to their name + pretty-printed args, so nothing is hidden.
_MAX_VIEW_CHARS = 6000


def _clip(text: str, limit: int = _MAX_VIEW_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n… [{len(text) - limit} more chars not shown]"


def _tool_view(name: str, args: Any) -> dict[str, str]:
    """{icon, label, subtitle, input} for one call. `icon` (not `kind`) because
    the view is spread into SSE frames, whose `kind` is the frame type."""
    view = _tool_view_raw(name, args)
    view["icon"] = view.pop("kind")
    return view


def _tool_view_raw(name: str, args: Any) -> dict[str, str]:
    a = args if isinstance(args, dict) else {}

    def g(key: str, default: str = "") -> str:
        v = a.get(key)
        return default if v is None else str(v)

    if name == "ls":
        return {"kind": "command", "label": "List", "subtitle": "", "input": f"ls {g('path', '/')}"}
    if name == "read_file":
        rng = ""
        if a.get("offset") is not None or a.get("limit") is not None:
            rng = f"  (offset {g('offset', '0')}, limit {g('limit', '-')})"
        return {"kind": "file", "label": "Read file", "subtitle": "", "input": g("file_path") + rng}
    if name == "write_file":
        return {
            "kind": "file",
            "label": "Write file",
            "subtitle": g("file_path"),
            "input": g("content"),
        }
    if name == "edit_file":
        diff = f"- {g('old_string')}\n+ {g('new_string')}"
        return {"kind": "file", "label": "Edit file", "subtitle": g("file_path"), "input": diff}
    if name == "delete":
        return {
            "kind": "command",
            "label": "Delete",
            "subtitle": "",
            "input": f"rm {g('path') or g('file_path')}",
        }
    if name == "glob":
        return {
            "kind": "command",
            "label": "Find files",
            "subtitle": g("path"),
            "input": f"glob {g('pattern')}",
        }
    if name == "grep":
        where = g("path") or g("glob")
        return {
            "kind": "command",
            "label": "Search files",
            "subtitle": where,
            "input": f"grep {g('pattern')!r}",
        }
    if name == "execute":
        return {"kind": "command", "label": "Command", "subtitle": "", "input": g("command")}
    if name == "eval":
        return {"kind": "code", "label": "Code", "subtitle": "interpreter", "input": g("code")}
    if name == "task":
        return {
            "kind": "agent",
            "label": "Subagent",
            "subtitle": g("subagent_type"),
            "input": g("description"),
        }
    if name in ("searxng_web_search", "searxngWebSearch", "web_search"):
        return {"kind": "web", "label": "Web search", "subtitle": "", "input": g("query")}
    if name in ("fetch_url", "fetch_and_store"):
        return {"kind": "web", "label": "Fetch", "subtitle": "", "input": g("url")}
    if name == "list_recent_emails":
        return {
            "kind": "mail",
            "label": "Email search",
            "subtitle": f"limit {g('limit', '10')}",
            "input": g("query") or "in:inbox",
        }
    if name == "read_email":
        return {"kind": "mail", "label": "Read email", "subtitle": "", "input": g("message_id")}
    if name == "list_calendar_events":
        span = " → ".join(x for x in (g("start"), g("end")) if x) or "upcoming"
        return {"kind": "calendar", "label": "Calendar", "subtitle": "", "input": span}
    if name == "write_todos":
        marks = {"completed": "[x]", "in_progress": "[~]"}
        todos = a.get("todos") or []
        lines = [
            f"{marks.get(str(t.get('status')), '[ ]')} {t.get('content', '')}"
            for t in todos
            if isinstance(t, dict)
        ]
        return {"kind": "plan", "label": "Plan", "subtitle": "", "input": "\n".join(lines)}
    pretty = json.dumps(a, indent=2, ensure_ascii=False, default=str) if a else ""
    return {"kind": "tool", "label": name, "subtitle": "", "input": pretty}


def _tool_status(output: str) -> str:
    """Classify a tool result for the UI from its output text alone: ok/warn/error.

    Tools in this harness report honestly (ToolErrorMiddleware turns a failure
    into a readable "this tool is unavailable…" message), so the words are enough.
    """
    low = (output or "").lower()
    if low.startswith("error") or "failed" in low or "timed out" in low or "unavailable" in low:
        return "error"
    if "no results" in low or "not found" in low:
        return "warn"
    return "ok"


def _tool_summary(output: str) -> str:
    """A one-line gist of a tool's output — its first sentence, truncated."""
    text = (output or "").strip().replace("\n", " ")
    first = text.split(". ", 1)[0]
    return first[:120] + ("…" if len(first) > 120 else "")


def _tool_activity(messages: list[Any]) -> list[dict[str, str]]:
    """Every tool call in a turn as [{tool, detail, output, status, summary}].

    Reads from the finished messages, pairing each AIMessage `tool_call` with the
    `ToolMessage` that carried its result (matched by tool_call_id) — the same
    enrichment waku's dashboard does, so a call renders as a status row (ok/warn/
    error) with a one-line summary and an expandable raw output. `detail` is the
    single most informative argument (a query, a URL), truncated.
    """
    # tool_call_id -> output text, from the ToolMessages in this turn.
    results: dict[str, str] = {}
    for m in messages:
        if getattr(m, "type", "") == "tool":
            results[str(getattr(m, "tool_call_id", ""))] = _text_of(getattr(m, "content", ""))

    steps: list[dict[str, str]] = []
    for m in messages:
        for call in getattr(m, "tool_calls", None) or []:
            name = call.get("name", "?")
            args = call.get("args") or {}
            key = _ACTIVITY_ARG.get(name)
            detail = ""
            if key and isinstance(args, dict) and args.get(key) is not None:
                detail = str(args[key])
            elif isinstance(args, dict) and args:
                # Fall back to the first arg value so unknown tools still show
                # something rather than a bare name.
                detail = str(next(iter(args.values())))
            if len(detail) > 200:
                detail = detail[:200] + "…"
            output = results.get(str(call.get("id", "")), "")
            view = _tool_view(name, args)
            steps.append(
                {
                    "id": str(call.get("id", "")),
                    "tool": name,
                    "detail": detail,
                    "output": _clip(output),
                    "status": _tool_status(output),
                    "summary": _tool_summary(output),
                    **view,
                    "input": _clip(view["input"]),
                }
            )
    return steps


def _agent_for(model_id: str = ""):
    """The agent for this model, built once and reused.

    Keyed by model so switching model in the picker gets its own instance rather
    than silently reusing the previous model's.
    """
    from agent import brain

    with _AGENTS_LOCK:
        existing = _AGENTS.get(model_id)
        if existing is None:
            existing = brain.build_agent(model_id or None)
            _AGENTS[model_id] = existing
        return existing


class Handler(BaseHTTPRequestHandler):
    # Quieter than the default, which logs a line per static asset.
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        if self.path.startswith("/api/"):
            super().log_message(format, *args)

    def _send(self, body: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        # Static assets are re-read per request; telling the browser not to cache
        # is what makes a hard reload actually show an edit.
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: object, status: int = 200) -> None:
        # sort_keys so the response is byte-stable for a given input. The repo
        # treats non-deterministic serialisation as a correctness problem, and a
        # stable payload is also what lets a test pin the shape.
        body = json.dumps(payload, sort_keys=True, indent=2, default=str).encode()
        self._send(body, "application/json", status)

    def do_GET(self) -> None:  # noqa: N802 — BaseHTTPRequestHandler's contract
        route = urlparse(self.path).path

        if route == "/api/topology":
            self._send_json(topology.describe())
            return

        if route == "/api/config":
            self._send_json(_describe_config())
            return

        if route == "/api/memory":
            self._send_json(_describe_memory())
            return

        # The Dockerfile's HEALTHCHECK has curled /health since it was written
        # and nothing served it, so the container was always one failed probe
        # away from being restarted forever. Deliberately does NOT call Bedrock:
        # a liveness probe that depends on a third party restarts your pod when
        # the third party has an outage.
        if route == "/health":
            self._send_json({"ok": True})
            return

        if route in ("/", "/index.html"):
            self._serve_static("index.html")
            return

        self._serve_static(route.lstrip("/"))

    # ── chat ──────────────────────────────────────────────────────────────────

    def do_POST(self) -> None:  # noqa: N802 — BaseHTTPRequestHandler's contract
        route = urlparse(self.path).path
        body = self._read_json()
        if body is None:
            return

        if route == "/api/chat/stream":
            self._chat_stream(body)
            return
        if route == "/api/session":
            self._session_action(body)
            return
        if route == "/api/connect/google":
            self._connect_google()
            return

        self._send_json({"error": f"no such endpoint: {route}"}, status=404)

    def _connect_google(self) -> None:
        """Run the one-time Google Calendar OAuth flow from the dashboard.

        LOOPBACK ONLY. connect() opens a browser and a localhost redirect server,
        which only makes sense when the dashboard runs on the user's own machine.
        Refusing it on a non-loopback bind stops a remote/cluster caller from
        trying to pop a browser on a headless server — that path needs the web
        OAuth connector (see docs/references/cluster-oauth.md), not this.
        """
        client_ip = self.client_address[0] if self.client_address else ""
        if client_ip not in ("127.0.0.1", "::1", "localhost"):
            self._send_json(
                {
                    "error": "connect is available only on the local dashboard; a "
                    "deployed instance needs the web OAuth connector",
                },
                status=403,
            )
            return
        try:
            from agent.tools import google_auth

            message = google_auth.connect()
        except Exception as exc:  # noqa: BLE001 — report, never 500 the endpoint
            message = f"connect failed: {type(exc).__name__}: {exc}"
        self._send_json({"message": message, "connected": _google_connected()})

    def _read_json(self) -> dict[str, Any] | None:
        """Read a JSON body, or answer the error and return None.

        Content-Length is required and bounded. Reading until EOF on a socket
        with no length would let one request hold a thread open indefinitely,
        which on a threaded server is all it takes to exhaust it.
        """
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json({"error": "Content-Length is not a number"}, status=400)
            return None

        if length <= 0:
            self._send_json({"error": "a request body is required"}, status=400)
            return None
        if length > MAX_MESSAGE_CHARS * 4:
            self._send_json({"error": "request body too large"}, status=413)
            return None

        try:
            payload = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            self._send_json({"error": f"body is not valid JSON: {exc}"}, status=400)
            return None

        if not isinstance(payload, dict):
            self._send_json({"error": "body must be a JSON object"}, status=400)
            return None
        return payload

    def _session_action(self, body: dict[str, Any]) -> None:
        """New chat, or read a thread back.

        A "session" here is a LangGraph `thread_id`. Creating one is just choosing
        a new id — the checkpointer materialises the thread on first use — and
        reading history is asking the graph for that thread's state rather than
        keeping a parallel copy.
        """
        action = str(body.get("action", ""))

        if action == "new":
            self._send_json({"ok": True, "session": f"web-{uuid.uuid4().hex[:12]}"})
            return

        if action == "history":
            thread = str(body.get("session", "default"))
            try:
                state = _agent_for().get_state({"configurable": {"thread_id": thread}})
                messages = state.values.get("messages", []) if state else []
                self._send_json(
                    {
                        "ok": True,
                        "session": thread,
                        "messages": [
                            {"role": getattr(m, "type", "?"), "text": getattr(m, "text", "")}
                            for m in messages
                        ],
                    }
                )
            except Exception as exc:  # noqa: BLE001 - reported, not swallowed
                self._send_json({"error": f"{type(exc).__name__}: {exc}"}, status=500)
            return

        self._send_json({"error": f"unknown action: {action!r}"}, status=400)

    def _chat_stream(self, body: dict[str, Any]) -> None:
        """One turn, streamed as SSE over a POST.

        SSE over POST rather than EventSource, because EventSource can only issue
        a GET and a message does not belong in a query string — it would land in
        access logs and in browser history. The frame format is still SSE, so the
        client is a plain `fetch` plus a reader, exactly as waku does it.
        """
        message = str(body.get("message", "")).strip()
        if not message:
            self._send_json({"error": "message is required"}, status=400)
            return
        if len(message) > MAX_MESSAGE_CHARS:
            self._send_json(
                {"error": f"message is longer than {MAX_MESSAGE_CHARS} characters"},
                status=413,
            )
            return

        # Checked against the verified list here rather than passed through: an
        # arbitrary id reaches Bedrock and fails there, and that error is far less
        # useful than refusing it with the list of what does work.
        requested = str(body.get("model", "")).strip()
        if requested and requested not in VERIFIED_MODEL_IDS:
            self._send_json(
                {
                    "error": f"{requested} is not a verified model",
                    "allowed": sorted(VERIFIED_MODEL_IDS),
                },
                status=400,
            )
            return

        thread = str(body.get("session", "default"))

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        # Without this a reverse proxy will buffer the whole response and the
        # stream arrives as one lump, which looks exactly like a slow model.
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        try:
            self._run_turn(message, thread, requested)
        except BrokenPipeError:
            # The reader closed the tab mid-turn. Not an error — but the turn is
            # abandoned here rather than finished, so nothing is recorded, which
            # is why this is caught and not merely ignored.
            return
        except Exception as exc:  # noqa: BLE001 - the stream must not 500 silently
            # Headers are already sent, so a 500 is no longer possible. The only
            # honest option left is to say so inside the stream.
            self._send_frame(
                {
                    "kind": "error",
                    "error": f"{type(exc).__name__}: {exc}",
                    "hint": "this is a harness defect, not a model failure",
                    "supersedes_draft": True,
                }
            )

    def _run_turn(self, message: str, thread: str, model_id: str) -> None:
        """Drive the deepagents graph and translate it into SSE frames.

        THE ORDERING IS THE HONEST PART, and it is why this cannot simply forward
        raw graph events. Text streams out BEFORE the obligation gate has judged it
        — the gate runs in `after_agent`, so it cannot see an answer until the
        answer exists. The frames therefore label the stream a DRAFT, and the
        `gate` frame that follows either confirms it or withdraws it. Holding
        everything back until the gate ran would be the opposite lie: several
        silent seconds, then a gated answer presented as if it had been checked all
        along.

        `supersedes_draft` is computed here so the browser does not have to
        reimplement the rule for when a streamed draft is void.
        """
        agent = _agent_for(model_id)
        run_config = {"configurable": {"thread_id": thread}}

        self._send_frame(
            {
                "kind": "start",
                "model": model_id or MODEL_ID,
                "provider": "bedrock",
                "router": FAST_MODEL_ID,
                "thread": thread,
            }
        )

        usage: dict[str, int] = {}
        tools_called: list[str] = []

        # stream_mode="messages" is LangGraph's own token stream. Reasoning blocks
        # arrive as content blocks alongside text, and they are forwarded as a
        # SEPARATE frame kind — the model's scratchpad must never be rendered as
        # the answer.
        #
        # ONLY the "model" node is forwarded. The stream carries EVERY model call
        # in the graph, and the obligation gate's routing call is one of them — so
        # without this filter the router's "NONE" or a skill name leaked into the
        # answer, appended right after the reply. langgraph_node names the source.
        # subgraphs=True makes the stream ALSO yield chunks from inside subagents
        # (the `task`/browsing/research delegates), which otherwise run as an
        # opaque gap. Each item becomes (namespace, (chunk, meta)); a NON-EMPTY
        # namespace means the chunk came from a subagent's own graph. We surface a
        # subagent's TOOL activity live so delegation is visible, but never stream
        # its text as the answer — a subagent's prose is its private reasoning;
        # only its final result returns to the parent, which the parent then
        # synthesises as top-level "model" text (handled below, unchanged).
        seen_subagent: set[tuple[str, str]] = set()
        # Tool-call ARGS stream in fragments (tool_call_chunks). Accumulate them
        # per call id so a finished call's card can show its exact input the
        # moment its result arrives, not only at the end of the turn.
        call_name: dict[str, str] = {}
        call_args: dict[str, str] = {}
        index_to_id: dict[int, str] = {}
        for ns, payload in agent.stream(
            {"messages": [{"role": "user", "content": message}]},
            config=run_config,
            stream_mode="messages",
            subgraphs=True,
        ):
            chunk, meta = payload

            if ns:  # inside a subagent
                label = str(ns[-1]).split(":")[0] if ns else "subagent"
                for call in getattr(chunk, "tool_calls", None) or []:
                    name = call.get("name")
                    key = (label, str(name))
                    if name and key not in seen_subagent:
                        seen_subagent.add(key)
                        self._send_frame({"kind": "subagent", "agent": label, "tool": name})
                continue

            # Tool RESULTS arrive from the "tools" node as ToolMessages — surface
            # them live as status rows (ok/warn/error + one-line summary) BEFORE
            # the model-only filter below drops them. This is the waku-style rich
            # tool display; the final `activity` frame carries the full detail.
            if getattr(chunk, "type", "") == "tool":
                out = _text_of(getattr(chunk, "content", ""))
                cid = str(getattr(chunk, "tool_call_id", "") or "")
                name = getattr(chunk, "name", None) or call_name.get(cid, "?")
                try:
                    args = json.loads(call_args.get(cid) or "{}")
                except ValueError:
                    args = {}
                view = _tool_view(name, args)
                self._send_frame(
                    {
                        "kind": "tool_result",
                        "id": cid,
                        "tool": name,
                        "status": _tool_status(out),
                        "summary": _tool_summary(out),
                        "output": _clip(out),
                        **view,
                        "input": _clip(view["input"]),
                    }
                )
                continue

            if meta.get("langgraph_node") != "model":
                continue
            # One `tool` frame per CALL (not per tool name — the old dedup hid
            # the second list_recent_emails). The first chunk of a call carries
            # its id and name; later chunks carry only the index + arg text.
            for part in getattr(chunk, "tool_call_chunks", None) or []:
                idx = part.get("index")
                cid = part.get("id")
                if cid:
                    if isinstance(idx, int):
                        index_to_id[idx] = cid
                    if cid not in call_name:
                        name = part.get("name") or "?"
                        call_name[cid] = name
                        call_args[cid] = ""
                        if name not in tools_called:
                            tools_called.append(name)
                        view = _tool_view(name, {})
                        self._send_frame(
                            {
                                "kind": "tool",
                                "id": cid,
                                "tool": name,
                                "label": view["label"],
                                "icon": view["icon"],
                            }
                        )
                elif isinstance(idx, int):
                    cid = index_to_id.get(idx, "")
                if cid and part.get("args"):
                    call_args[cid] = call_args.get(cid, "") + str(part["args"])
            # Some providers deliver a whole, parsed call instead of chunks.
            for call in getattr(chunk, "tool_calls", None) or []:
                cid = str(call.get("id") or "")
                name = call.get("name") or ""
                if cid and name and cid not in call_name:
                    call_name[cid] = name
                    call_args[cid] = json.dumps(call.get("args") or {})
                    if name not in tools_called:
                        tools_called.append(name)
                    view = _tool_view(name, {})
                    self._send_frame(
                        {
                            "kind": "tool",
                            "id": cid,
                            "tool": name,
                            "label": view["label"],
                            "icon": view["icon"],
                        }
                    )

            content = getattr(chunk, "content", None)
            if isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "text" and block.get("text"):
                        self._send_frame({"kind": "text", "delta": block["text"]})
                    elif "reasoning_content" in block:
                        reasoning = block["reasoning_content"]
                        text = (
                            reasoning.get("text", "") if isinstance(reasoning, dict) else reasoning
                        )
                        if text:
                            self._send_frame({"kind": "reasoning", "delta": text})
            elif isinstance(content, str) and content:
                self._send_frame({"kind": "text", "delta": content})

            usage_meta = getattr(chunk, "usage_metadata", None)
            if usage_meta:
                usage = {
                    "input_tokens": int(usage_meta.get("input_tokens", 0)),
                    "output_tokens": int(usage_meta.get("output_tokens", 0)),
                }

        # The verdict lives on graph state, written by ObligationGateMiddleware in
        # after_agent, so it is read once the stream has ended rather than inferred
        # from the messages.
        state = agent.get_state(run_config)
        values = state.values if state else {}
        verdict = values.get("obligation_verdict") or {
            "decision": "not-reached",
            "reason": "the gate did not record a verdict for this turn",
        }
        # The checkpointer returns the WHOLE thread. Slice to this turn, and join
        # every assistant message in it — not just the last one, which is often a
        # short closing summary after the real content (the "content vanished,
        # only the summary is left" bug).
        final = _this_turn(values.get("messages", []))
        reply = _turn_reply(final)

        # What the agent actually DID — every tool call with its key argument, in
        # order. This is the "show the searches and links" view: web_search shows
        # the query, fetch_and_store shows the URL. Read from the final messages,
        # where tool-call args are complete (the stream carries them in fragments).
        activity = _tool_activity(final)
        if activity:
            self._send_frame({"kind": "activity", "steps": activity})

        self._send_frame(
            {
                "kind": "gate",
                "decision": verdict.get("decision"),
                "reason": verdict.get("reason"),
                "blocking": verdict.get("blocking", []),
                "observed": verdict.get("observed", []),
            }
        )

        refused = verdict.get("decision") == "block"

        # One line to stdout summarising what the turn actually did, because the
        # rich per-turn detail otherwise only exists as SSE frames in the browser
        # — the terminal saw nothing but the HTTP access line. Tool calls are the
        # observable signal: `read_file` means a skill was opened, `write_todos`
        # means it planned, `task` would mean a sub-agent (none is wired today).
        skill_reads = "read_file" in tools_called
        planned = "write_todos" in tools_called
        print(
            f"turn thread={thread} tools={tools_called or '[]'} "
            f"skill_read={skill_reads} planned={planned} "
            f"gate={verdict.get('decision')} policies={verdict.get('policies', [])} "
            f"usage={usage or '{}'}",
            flush=True,
        )
        # The step-by-step trail, one line each, so the terminal shows exactly
        # which queries were searched and which URLs were fetched — the detail
        # needed to validate whether the answer came from fresh sources.
        for step in activity:
            print(f"  · {step['tool']}: {step['detail']}", flush=True)

        self._send_frame(
            {
                "kind": "done",
                "reply": reply,
                "draft": verdict.get("draft", ""),
                "refused": refused,
                "gate": verdict,
                "policies": verdict.get("policies", []),
                "tools": tools_called,
                "activity": activity,
                "model": model_id or MODEL_ID,
                "usage": usage,
                # A blocked turn has already streamed the withheld text to the
                # screen. Leaving it there with a refusal underneath would show
                # the user exactly the answer the gate refused to deliver.
                "supersedes_draft": refused,
            }
        )

    def _send_frame(self, payload: dict[str, Any]) -> None:
        """One SSE frame. Flushed immediately, or it is not streaming."""
        body = json.dumps(payload, default=str)
        self.wfile.write(f"data: {body}\n\n".encode())
        self.wfile.flush()

    def _serve_static(self, relative: str) -> None:
        """Serve one file from the static directory, refusing to escape it.

        `Path.resolve()` then a containment check, rather than stripping `..`
        from the string. String stripping is defeated by encodings and symlinks;
        comparing resolved paths is not.
        """
        target = (STATIC / relative).resolve()
        try:
            target.relative_to(STATIC)
        except ValueError:
            self._send(b"forbidden", "text/plain", 403)
            return

        if not target.is_file():
            self._send(b"not found", "text/plain", 404)
            return

        content_type, _ = mimetypes.guess_type(target.name)
        self._send(target.read_bytes(), content_type or "application/octet-stream")


def _tracing_status() -> str:
    """Whether LangSmith tracing is on — by env, the way LangChain enables it.

    LangGraph/LangChain auto-trace to LangSmith when `LANGSMITH_TRACING` (or the
    legacy `LANGCHAIN_TRACING_V2`) is truthy and an API key is present. No code
    wires it; it is purely environment, so this only reports what the env says.
    """
    on = (os.getenv("LANGSMITH_TRACING") or os.getenv("LANGCHAIN_TRACING_V2") or "").lower() in (
        "1",
        "true",
        "yes",
    )
    has_key = bool(os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY"))
    if on and has_key:
        project = os.getenv("LANGSMITH_PROJECT") or os.getenv("LANGCHAIN_PROJECT") or "default"
        return f"LangSmith tracing ON (project={project})"
    if on and not has_key:
        return "LangSmith tracing requested but no API key set"
    return "off — set LANGSMITH_TRACING=true and LANGSMITH_API_KEY to enable"


def _describe_memory() -> dict[str, Any]:
    """The durable-memory graph for the UI: facts, episodes, entities.

    Off (AGENT_MEMORY unset) returns enabled=False so the UI can say so rather
    than error. A connection/query failure is reported in `error`, not raised —
    the memory view must degrade to a message, never take the dashboard down.
    """
    from agent.memory import semantic

    if not semantic.memory_enabled():
        return {"enabled": False, "facts": [], "episodes": [], "entities": []}
    try:
        snap = semantic.snapshot()
        return {"enabled": True, **snap}
    except Exception as exc:  # noqa: BLE001 — reported to the UI, not raised
        return {
            "enabled": True,
            "error": f"{type(exc).__name__}: {exc}",
            "facts": [],
            "episodes": [],
            "entities": [],
        }


def _google_connected() -> bool:
    """Whether Google is connected (one token grants calendar + gmail read).
    Guarded — a connector probe must never break the config endpoint."""
    try:
        from agent.tools import google_auth

        return google_auth.is_connected()
    except Exception:  # noqa: BLE001
        return False


def _describe_config() -> dict[str, Any]:
    """What the harness is configured to do, for the UI to state plainly.

    Credentials are described, never returned — `credential_source()` names the
    SOURCE. There is deliberately no endpoint that can return a secret value, so a
    future bug cannot turn one into a leak.
    """
    policyset = load_obligation_policies()
    return {
        "provider": "bedrock",
        "harness": "deepagents",
        "model": MODEL_ID,
        "fast_model": FAST_MODEL_ID,
        "region": REGION,
        "credential_source": credential_source(),
        "tracing": _tracing_status(),
        # Connector status — a boolean per integration, never a token. Calendar
        # and Gmail share one Google sign-in, so both reflect the same token.
        "connectors": {
            "google_calendar": _google_connected(),
            "gmail": _google_connected(),
        },
        "verified_models": [dict(entry) for entry in VERIFIED_MODELS],
        "policies": [
            {"name": p.name, "description": p.description, "obligations": len(p.obligations)}
            for p in policyset.policies
        ],
        "persistence": (
            "the graph checkpointer. AGENTCORE_MEMORY_ID unset means an in-process "
            "MemorySaver, so threads are lost when the server restarts"
        ),
    }


def serve(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    """Run until interrupted."""
    server = ThreadingHTTPServer((host, port), Handler)
    if host not in ("127.0.0.1", "localhost", "::1"):
        print(f"WARNING: {_NO_AUTH_WARNING}")
    print(f"dashboard → http://{host}:{port}  (Ctrl-C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopping")
    finally:
        server.server_close()
