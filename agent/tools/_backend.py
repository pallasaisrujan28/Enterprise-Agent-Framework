"""Shared plumbing for config-selected tool backends.

Two tools reach the outside world through a backend chosen by config: fetching (a
URL to markdown) and search (a query to results). Both follow the ADR-019 rule —
the implementation is selected by an env var, local vs cluster, with no code
change.

WHAT THEY SHARE LIVES HERE, AND ONLY THAT. How the choice is read, and the error
type the tool layer catches. The implementations and their dispatch stay in each
module: scrape/crawl and search have different shapes, and a generic dispatcher
would be more indirection than the one-line if/else it replaced. Extracting the
dispatch too would be the "unnecessary duplicate code" cure that costs more than
the disease.
"""

from __future__ import annotations

import os


class BackendError(RuntimeError):
    """A backend call failed in a way the tool reports to the model, not raises.

    ToolErrorMiddleware turns a raised BackendError into an observation the model
    can read and work around, rather than an exception that ends the turn.
    `FetchError` and `SearchError` subclass this so a caller can still catch one
    specifically, while shared handling can catch the base.
    """


def chosen(env_var: str, default: str, known: set[str]) -> str:
    """The configured backend name, falling back to default if unset or unknown.

    Validating against `known` here is why each module's `backend_name()` is just
    the stored value: an unknown FETCH_BACKEND=foo degrades to the default rather
    than silently disabling the tool by matching no branch.
    """
    name = os.getenv(env_var, default).strip().lower()
    return name if name in known else default
