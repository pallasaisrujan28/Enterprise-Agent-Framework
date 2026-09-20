"""Makes `python -m agent` work.

The Dockerfile has ended with `CMD ["/app/.venv/bin/python", "-m", "agent"]`
since it was written, and this module did not exist — so the image built, pushed
and then failed at startup with "No module named agent.__main__". Exactly the
same defect the `agent` console script had before agent/cli.py was created, in
the other direction.

Delegates rather than duplicating: one argument parser, one dispatch table, two
ways in.
"""

from __future__ import annotations

from agent.cli import main

if __name__ == "__main__":
    main()
