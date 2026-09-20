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
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from agent import turn as turn_lib
from agent.config import Config
from agent.dashboard import topology
from agent.models import verified_models

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

# Sessions live in this process and die with it. A dict plus a lock rather than
# anything cleverer, because ThreadingHTTPServer serves each request on its own
# thread and two browser tabs posting at once would otherwise race on creation.
# Stated rather than hidden: the Postgres checkpointer the topology names is not
# wired, so restarting the server loses every conversation.
_SESSIONS: dict[str, turn_lib.Session] = {}
_SESSIONS_LOCK = threading.Lock()


def _session(session_id: str) -> turn_lib.Session:
    with _SESSIONS_LOCK:
        existing = _SESSIONS.get(session_id)
        if existing is None:
            existing = turn_lib.Session(id=session_id)
            _SESSIONS[session_id] = existing
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
        """New chat, or read a thread back. Deliberately two actions.

        waku's equivalent grew to five (new / switch / history / all / live) with
        a comment about the paths drifting apart. Ours has what the UI uses and
        nothing speculative.
        """
        action = str(body.get("action", ""))

        if action == "new":
            fresh = f"s{len(_SESSIONS) + 1}"
            self._send_json({"ok": True, "session": _session(fresh).id})
            return

        if action == "history":
            session = _session(str(body.get("session", "default")))
            self._send_json(
                {
                    "ok": True,
                    "session": session.id,
                    "turns": [t.as_dict() for t in session.turns],
                }
            )
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

        config = Config.load()
        # A model override is checked against the VERIFIED list, not passed
        # through. An arbitrary id would reach Bedrock and fail there, and the
        # resulting AccessDenied is far less clear than refusing it here.
        requested = str(body.get("model", "")).strip()
        if requested:
            allowed = {str(entry["id"]) for entry in verified_models}
            if requested not in allowed:
                self._send_json(
                    {"error": f"{requested} is not a verified model", "allowed": sorted(allowed)},
                    status=400,
                )
                return
            config = config.with_model(requested)

        session = _session(str(body.get("session", "default")))

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        # Without this a reverse proxy will buffer the whole response and the
        # stream arrives as one lump, which looks exactly like a slow model.
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        stream = turn_lib.respond(message, session, config)
        try:
            while True:
                try:
                    event = next(stream)
                except StopIteration:
                    break
                frame = {"kind": event.kind, **event.payload}
                if event.supersedes_draft:
                    # Computed on the server so the browser does not have to
                    # reimplement the rule about when a streamed draft is void.
                    frame["supersedes_draft"] = True
                self._send_frame(frame)
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

    Credentials are described, never returned — `Config.secret_ref()` names the
    SOURCE. There is deliberately no endpoint that can return a secret value, so
    a future bug cannot turn one into a leak.
    """
    config = Config.load()
    skillset = turn_lib.load_skills(config)
    return {
        "provider": config.provider,
        "model": config.model,
        "fast_model": config.fast_model,
        "region": config.region,
        "max_tokens": config.max_tokens,
        "credential_source": config.secret_ref(),
        "warnings": list(config.warnings()),
        "verified_models": [dict(entry) for entry in verified_models],
        "skills": [
            {"name": s.name, "description": s.description, "obligations": len(s.obligations)}
            for s in skillset.skills
        ],
        "history_turns": turn_lib.HISTORY_TURNS,
        "persistence": "in memory — conversations are lost when the server restarts",
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
