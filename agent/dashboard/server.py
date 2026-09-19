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
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from agent.dashboard import topology

STATIC = Path(__file__).resolve().parent / "static"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7788

# Bound to loopback by default and stated plainly: this server has NO
# authentication. It exposes what the harness knows about itself, which includes
# component status and, once chat exists, conversation content. Binding it to
# 0.0.0.0 publishes that to the network.
_NO_AUTH_WARNING = (
    "dashboard has no authentication — bind to loopback only unless that has "
    "been deliberately reconsidered"
)


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

        if route in ("/", "/index.html"):
            self._serve_static("index.html")
            return

        self._serve_static(route.lstrip("/"))

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
