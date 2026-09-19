"""The dashboard — a window onto the harness, not part of it.

Two rules hold this package in its place:

  It only reads. Nothing here decides anything about a turn, and nothing here
  touches memory directly. When a chat endpoint arrives it will call the
  orchestrator's own entry point, the same one the CLI uses, with no private
  path of its own.

  The diagram is rendered from data, never hand-drawn. `topology.describe()` is
  the single source, so a component cannot appear on the chart without a status
  and a reason.
"""

from agent.dashboard.server import DEFAULT_HOST, DEFAULT_PORT, serve

__all__ = ["DEFAULT_HOST", "DEFAULT_PORT", "serve"]
