"""Live probe of the site-discovery capability. Not part of CI.

Level 1 (default, no model, no cost): drives the REAL plug-ins the subagent
gets — check_source_policy and REA over MCP via agent/tools/rea_mcp.py — through
the discovery method: policy -> capture -> find JSON endpoint -> policy on the
endpoint -> reuse it without a browser -> verify.

Level 2 (--agent, calls Bedrock and bills): builds the real harness with
AGENT_REA=on and asks it a discovery question end to end.

    export AGENT_REA=on
    export REA_BROWSER_EXECUTABLE="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    # REA needs Node ^22.19 || ^24.11 || >=26; point at one if the system Node is not:
    export REA_MCP_COMMAND=/path/to/node24/bin/node
    export REA_MCP_ARGS="/path/to/node_modules/rea-agents/scripts/rea.mjs mcp"
    uv run python scripts/dev/probe_site_discovery.py [--agent]
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx

TARGET = "https://quotes.toscrape.com/scroll"
PORTALS = [
    "https://www.rightmove.co.uk/property-to-rent/find.html?locationIdentifier=REGION%5E93953",
    "https://www.zoopla.co.uk/to-rent/property/hackney/",
    "https://www.spareroom.co.uk/flatshare/bristol",
    "https://www.openrent.co.uk/properties-to-rent/hackney",
]


def _text(result: object) -> str:
    """MCP tool output -> the JSON text REA returned."""
    if isinstance(result, str):
        return result
    if isinstance(result, list):
        return "".join(
            b.get("text", "") if isinstance(b, dict) else getattr(b, "text", str(b)) for b in result
        )
    return str(result)


def _json_endpoints(evidence: dict) -> list[tuple[str, dict]]:
    items = evidence["normalized_result"]["events"]["items"]
    urls = {
        i["transaction_id"]: i["url"]["url"]
        for i in items
        if i.get("resource_type") in ("xhr", "fetch")
    }
    found = []
    for i in items:
        body = i.get("body") or {}
        if i.get("kind") != "network-content" or i.get("transaction_id") not in urls:
            continue
        if body.get("state") != "captured":
            continue
        raw = body["content"]
        text = base64.b64decode(raw).decode() if body.get("encoding") == "base64" else raw
        try:
            found.append((urls[i["transaction_id"]], json.loads(text)))
        except ValueError:
            continue
    return found


def level1() -> int:
    from agent.tools.rea_mcp import browser_executable, build_rea_tools, rea_enabled
    from agent.tools.source_policy import evaluate

    checks: dict[str, bool] = {}
    print("policy on portals:")
    for url in PORTALS:
        v = evaluate(url)
        print(f"  {v['verdict']:7} {url}\n          {v['reason']}")
    checks["rightmove search page denied by sources.yaml"] = (
        evaluate(PORTALS[0])["verdict"] == "deny"
    )
    checks["zoopla denied"] = evaluate(PORTALS[1])["verdict"] in ("deny", "unknown")

    print(f"\npolicy on target: {evaluate(TARGET)['verdict']}")
    if not (rea_enabled() and browser_executable()):
        print("AGENT_REA and REA_BROWSER_EXECUTABLE must be set for the capture step.")
        return 1
    tools = {t.name: t for t in build_rea_tools()}
    print(f"REA tools exposed to the subagent: {sorted(tools)}")
    scenario = {
        "browser": {"mode": "launch", "executable_path": browser_executable()},
        "start_url": {"url": TARGET},
        "actions": [
            {
                "step_id": "rows",
                "action": "wait_for",
                "locator": {"kind": "css", "selector": ".quote"},
                "state": "visible",
                "timeout_ms": 15000,
            }
        ],
        "capture": {"at_end": ["url"], "network": {"response_body": True}},
    }
    evidence = json.loads(_text(tools["capture_browser_scenario"].invoke(scenario)))
    print(f"evidence: {evidence.get('evidence_id')}")
    endpoints = _json_endpoints(evidence)
    checks["JSON endpoint discovered"] = bool(endpoints)
    if not endpoints:
        return _report(checks)
    url, first = endpoints[0]
    print(f"discovered: GET {url}  keys={sorted(first)}")
    checks["endpoint allowed by policy"] = evaluate(url)["verdict"] == "allow"

    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    query["page"] = str(int(query.get("page", "1")) + 1)
    nxt = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))
    resp = httpx.get(nxt, timeout=15, headers={"User-Agent": "EAF-probe/0.1"})
    data = resp.json() if resp.status_code == 200 else {}
    rows = data.get("quotes", [])
    checks["direct reuse 200 without a browser"] = resp.status_code == 200
    checks["same shape"] = set(data) == set(first)
    checks["page advanced"] = data.get("page") == first.get("page", 0) + 1
    checks["rows have fields"] = bool(rows) and all(r.get("text") and r.get("author") for r in rows)
    print(f"reused: GET {nxt} -> {len(rows)} rows")
    return _report(checks)


def level2() -> int:
    from agent.brain import build_agent

    agent = build_agent()
    question = (
        "Get the first 5 quotes tagged 'love' from quotes.toscrape.com. I want text and "
        "author. Work out how the site serves its data, and tell me the endpoint you used."
    )
    used: list[str] = []
    last = None
    # subgraphs=True streams the subagent's own steps too, so a long discovery
    # run is visible as it happens instead of a silent wait.
    for namespace, update in agent.stream(
        {"messages": [{"role": "user", "content": question}]},
        config={"configurable": {"thread_id": "probe-site-discovery"}, "recursion_limit": 80},
        stream_mode="updates",
        subgraphs=True,
    ):
        where = "sub" if namespace else "main"
        for node in update.values():
            for m in (node or {}).get("messages", []) if isinstance(node, dict) else []:
                for c in getattr(m, "tool_calls", None) or []:
                    if c["name"] == "task":
                        used.append(c["args"].get("subagent_type", "?"))
                    args = json.dumps(c["args"])[:160]
                    print(f"[{where}] tool {c['name']} {args}", flush=True)
                if not namespace and getattr(m, "type", "") == "ai" and not m.tool_calls:
                    last = m
    print("\ntask() delegations:", used)
    print("\nANSWER:\n", getattr(last, "content", "(none)"))
    return 0 if "site-discovery" in used else 1


def _report(checks: dict[str, bool]) -> int:
    for name, ok in checks.items():
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", action="store_true", help="run the full agent (calls Bedrock)")
    sys.exit(level2() if parser.parse_args().agent else level1())
