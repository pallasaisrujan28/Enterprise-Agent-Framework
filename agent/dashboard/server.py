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

        self._send_json({"error": f"no such endpoint: {route}"}, status=404)

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
        for chunk, meta in agent.stream(
            {"messages": [{"role": "user", "content": message}]},
            config=run_config,
            stream_mode="messages",
        ):
            if meta.get("langgraph_node") != "model":
                continue
            for call in getattr(chunk, "tool_calls", None) or []:
                name = call.get("name")
                if name and name not in tools_called:
                    tools_called.append(name)
                    self._send_frame({"kind": "tool", "tool": name})

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

            meta = getattr(chunk, "usage_metadata", None)
            if meta:
                usage = {
                    "input_tokens": int(meta.get("input_tokens", 0)),
                    "output_tokens": int(meta.get("output_tokens", 0)),
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
        final = values.get("messages", [])
        reply = getattr(final[-1], "text", "") if final else ""

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
        self._send_frame(
            {
                "kind": "done",
                "reply": reply,
                "draft": verdict.get("draft", ""),
                "refused": refused,
                "gate": verdict,
                "policies": verdict.get("policies", []),
                "tools": tools_called,
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
