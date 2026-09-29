"""Live smoke test for the Playwright MCP browser plug-in.

Spawns the real MCP server + Chromium, navigates to example.com, takes an
accessibility snapshot, and prints a short proof. Not part of the pytest suite —
it needs Node, Playwright, and a Chromium download on first run. Run manually:

    AGENT_BROWSER=on BROWSER_MCP_HEADLESS=1 .venv/bin/python scripts/browser_smoke.py
"""

from __future__ import annotations

import sys

from agent.tools.browser_mcp import build_browser_tools


def main() -> int:
    tools = {t.name: t for t in build_browser_tools()}
    print(f"exposed tools: {sorted(tools)}")

    missing = {"browser_navigate", "browser_snapshot"} - set(tools)
    if missing:
        print(f"FAIL: missing expected tools: {missing}")
        return 1

    nav = tools["browser_navigate"].invoke({"url": "https://example.com"})
    print(f"navigate ok: {str(nav)[:120]!r}")

    snap = str(tools["browser_snapshot"].invoke({}))
    print(f"snapshot length: {len(snap)} chars")
    ok = "example" in snap.lower()
    print("PASS" if ok else "FAIL: 'example' not found in snapshot")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
