"""check_source_policy — may the agent automate access to this site?

WHY A TOOL AND NOT A PROMPT RULE.
Site discovery is generic on purpose: the agent finds and learns sources it was
never told about. What it may DO with a source is not generic. Some sites forbid
automated access in their terms, some disallow their internal API in
robots.txt, some block non-browser clients outright. A prompt rule ("respect
robots.txt") leaves the parsing to the model, which gets wildcards wrong — the
first hand-written check in this project did too. So the decision is code:

  1. policies/sources.yaml — what a human decided for a domain. Wins.
  2. robots.txt, matched per RFC 9309 for the `*` group.
  3. Anything that cannot be determined is "unknown", and unknown means NO
     automated access. Zoopla's robots.txt answers 403 to non-browser clients;
     treating that as "no rules, so allowed" would be exactly backwards.

The verdict says whether a site may be accessed automatically (a scheduled
watch, a reused JSON endpoint). It is not a legal opinion: robots.txt is not the
terms of service, which is why the result carries `terms_reviewed`.

SSRF. The tool fetches a URL the model chose, from inside the cluster, so it
refuses non-http(s) schemes and hosts that resolve to private, loopback or
link-local addresses.
"""

from __future__ import annotations

import ipaddress
import json
import re
import socket
import time
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx
import yaml
from langchain_core.tools import tool

POLICY_FILE = Path(__file__).parents[2] / "policies" / "sources.yaml"
_UA = "EAF-agent/0.1 (+site policy check)"
_TTL_S = 3600
_robots_cache: dict[str, tuple[float, int, str]] = {}

# Access values a human can set in policies/sources.yaml.
AUTOMATED_OK = {"api", "feed", "allowed"}
NO_AUTOMATION = {"email-alert", "user-session-only", "blocked"}


@lru_cache(maxsize=1)
def _policies() -> list[dict[str, Any]]:
    if not POLICY_FILE.exists():
        return []
    data = yaml.safe_load(POLICY_FILE.read_text(encoding="utf-8")) or {}
    return list(data.get("sources", []))


def policy_for(host: str) -> dict[str, Any] | None:
    """The sources.yaml entry for host or a parent domain (most specific wins)."""
    host = host.lower().rstrip(".")
    matches = [p for p in _policies() if host == p["domain"] or host.endswith("." + p["domain"])]
    return max(matches, key=lambda p: len(p["domain"]), default=None)


def _rule_regex(pattern: str) -> re.Pattern[str]:
    """robots.txt path pattern -> regex. `*` = any run of characters, `$` = end."""
    anchored = pattern.endswith("$")
    body = re.escape(pattern[:-1] if anchored else pattern).replace(r"\*", ".*")
    return re.compile(body + ("$" if anchored else ""))


def parse_robots(text: str, agent: str = "*") -> list[tuple[str, str]]:
    """(allow|disallow, pattern) rules of the group(s) naming `agent`.

    Consecutive User-agent lines share one group; a User-agent line after a
    rule starts a new group (RFC 9309 §2.1).
    """
    rules: list[tuple[str, str]] = []
    agents: list[str] = []
    in_rules = False
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        key, value = (part.strip() for part in line.split(":", 1))
        key = key.lower()
        if key == "user-agent":
            if in_rules:
                agents, in_rules = [], False
            agents.append(value.lower())
        elif key in ("allow", "disallow"):
            in_rules = True
            if agent in agents and value:
                rules.append((key, value))
    return rules


def robots_allows(rules: list[tuple[str, str]], path: str) -> bool:
    """Longest matching pattern wins; allow wins a tie; no match means allowed."""
    best_len, allowed = -1, True
    for kind, pattern in rules:
        more_specific = len(pattern) > best_len or (len(pattern) == best_len and kind == "allow")
        if more_specific and _rule_regex(pattern).match(path):
            best_len, allowed = len(pattern), kind == "allow"
    return allowed


def _is_public_host(host: str) -> bool:
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return False
    return True


def _fetch_robots(origin: str) -> tuple[int, str]:
    cached = _robots_cache.get(origin)
    if cached and time.monotonic() - cached[0] < _TTL_S:
        return cached[1], cached[2]
    try:
        resp = httpx.get(
            origin + "/robots.txt", headers={"User-Agent": _UA}, timeout=10, follow_redirects=True
        )
        status, text = resp.status_code, resp.text if resp.status_code == 200 else ""
    except httpx.HTTPError:
        status, text = 0, ""
    _robots_cache[origin] = (time.monotonic(), status, text)
    return status, text


def evaluate(url: str) -> dict[str, Any]:
    """The policy verdict for one URL. Pure apart from the robots.txt fetch."""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return {
            "url": url,
            "verdict": "deny",
            "automated_access": False,
            "reason": "Only public http(s) URLs can be checked.",
        }
    host = parts.hostname
    path = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
    result: dict[str, Any] = {"url": url, "host": host, "path": path}

    if not POLICY_FILE.exists():
        # Fail closed: without the human decisions, robots.txt alone would let
        # the agent automate sites an operator has ruled out.
        result.update(
            verdict="unknown",
            automated_access=False,
            reason=f"Source policy file {POLICY_FILE.name} is missing from this deployment.",
        )
        return result

    policy = policy_for(host)
    if policy:
        access = policy.get("access", "")
        result.update(
            policy_access=access,
            terms_reviewed=bool(policy.get("terms_reviewed", False)),
            policy_note=policy.get("reason", ""),
            alternative=policy.get("alternative", ""),
        )
        if access in NO_AUTOMATION:
            result.update(
                verdict="deny",
                automated_access=False,
                reason=f"policies/sources.yaml sets {policy['domain']} to '{access}'.",
            )
            return result
    else:
        result["terms_reviewed"] = False

    if not _is_public_host(host):
        result.update(
            verdict="deny",
            automated_access=False,
            reason="Host does not resolve to a public address.",
        )
        return result

    status, text = _fetch_robots(f"{parts.scheme}://{parts.netloc}")
    result["robots_status"] = status
    if status == 404:
        verdict, reason = "allow", "No robots.txt (404)."
    elif status == 200:
        allowed = robots_allows(parse_robots(text), path)
        verdict = "allow" if allowed else "deny"
        reason = f"robots.txt {'allows' if allowed else 'disallows'} {path} for '*'."
    else:
        verdict, reason = (
            "unknown",
            (
                f"robots.txt could not be read (HTTP {status or 'error'}); the site may block "
                "non-browser clients. Unknown means no automated access."
            ),
        )
    result.update(verdict=verdict, automated_access=verdict == "allow", reason=reason)
    if verdict == "allow" and not result.get("terms_reviewed"):
        result["note"] = (
            "robots.txt is not the terms of service. Before a recurring watch, ask the "
            "user to confirm the site's terms permit automated access."
        )
    return result


@tool
def check_source_policy(url: str) -> str:
    """
    Check whether automated access to a website URL is permitted BEFORE you
    discover or reuse its endpoints. Returns JSON with verdict (allow, deny or
    unknown), automated_access (true only for allow), the reason, and any
    alternative the operator recorded (for example: use the site's email alerts).
    Check the exact URL or endpoint you intend to call. Treat deny and unknown
    as "do not automate": report it and use the alternative instead.
    """
    return json.dumps(evaluate(url))
