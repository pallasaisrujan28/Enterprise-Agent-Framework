"""Guards on the site-discovery capability: REA plug-in, source policy, roster.

Nothing here spawns REA, Node or a browser, and nothing touches the network:
robots.txt fetches and DNS are monkeypatched. The live end-to-end run is
scripts/dev/probe_site_discovery.py.

What is guarded, because each is a correctness hinge:
  - AGENT_REA gating: off by default, so CI never needs Node or Chrome.
  - REA is pinned and only a curated web subset of its ~207 tools is exposed.
  - the REA subprocess gets the safe default env, never this process's secrets.
  - robots.txt matching follows RFC 9309 (wildcards, $, groups, longest match);
    the first hand-written check in this project got wildcards wrong.
  - unknown (403, network error) means no automated access, and a human entry
    in policies/sources.yaml beats robots.txt.
  - the site-discovery subagent appears only when enabled, returns a typed
    SiteRecipe, and carries the policy-first and no-bypass rules.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent.tools import rea_mcp, source_policy

# ── REA plug-in config ──────────────────────────────────────────────────────


@pytest.mark.parametrize("value", ["on", "1", "true", "yes", "ON"])
def test_rea_enabled_when_flag_set(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("AGENT_REA", value)
    assert rea_mcp.rea_enabled() is True


@pytest.mark.parametrize("value", ["", "off", "0", "false"])
def test_rea_disabled_by_default(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("AGENT_REA", value)
    assert rea_mcp.rea_enabled() is False


def test_default_server_is_pinned_npx(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REA_MCP_COMMAND", raising=False)
    command, args = rea_mcp._command_and_args()
    assert command == "npx"
    assert f"rea-agents@{rea_mcp.REA_VERSION}" in args
    assert "@latest" not in " ".join(args)
    assert args[-1] == "mcp"


def test_command_override_replaces_the_launcher(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REA_MCP_COMMAND", "node")
    monkeypatch.setenv("REA_MCP_ARGS", "/opt/rea/scripts/rea.mjs mcp")
    assert rea_mcp._command_and_args() == ("node", ["/opt/rea/scripts/rea.mjs", "mcp"])


def test_command_override_keeps_quoted_paths_with_spaces(monkeypatch: pytest.MonkeyPatch) -> None:
    # Regression: str.split broke "/Users/me/My Projects/rea.mjs" into two args.
    monkeypatch.setenv("REA_MCP_COMMAND", "node")
    monkeypatch.setenv("REA_MCP_ARGS", '"/Users/me/My Projects/rea.mjs" mcp')
    assert rea_mcp._command_and_args()[1] == ["/Users/me/My Projects/rea.mjs", "mcp"]


def test_curated_tools_are_web_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REA_MCP_TOOLS", raising=False)
    exposed = rea_mcp._expose()
    assert {"capture_browser_scenario", "inspect_web_page", "inspect_analysis_view"} <= exposed
    # Tools that run or attach to local programs stay off.
    for name in ("capture_process", "capture_electron_scenario", "inspect_adb_devices"):
        assert name not in exposed
    assert len(exposed) < 15


def test_subprocess_env_is_safe_and_node_dir_first(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "do-not-leak")
    monkeypatch.setenv("REA_NODE_DIR", "/opt/node24/bin")
    env = rea_mcp._env()
    assert "AWS_SECRET_ACCESS_KEY" not in env
    assert env["PATH"].startswith("/opt/node24/bin")


# ── robots.txt matching (RFC 9309) ──────────────────────────────────────────

ROBOTS = """
User-agent: Googlebot
Disallow: /private-for-google/

User-agent: other
User-agent: *
Disallow: /api/*
Disallow: /*/save-search.html*
Disallow: /flatshare/*search_id=
Allow: /api/public$
Disallow: /tmp
"""


@pytest.mark.parametrize(
    ("path", "allowed"),
    [
        ("/property-to-rent/find.html?maxBedrooms=2", True),
        ("/api/_search?channel=RENT", False),
        ("/api/public", True),  # Allow + $ is more specific
        ("/api/public/more", False),  # $ anchors the allow
        ("/london/save-search.html?x=1", False),  # mid-path wildcard
        ("/flatshare/bristol", True),
        ("/flatshare/?search_id=12", False),
        ("/tmpfile", False),  # plain prefix
        ("/private-for-google/x", True),  # other group's rule does not apply to *
    ],
)
def test_robots_matching(path: str, allowed: bool) -> None:
    rules = source_policy.parse_robots(ROBOTS)
    assert source_policy.robots_allows(rules, path) is allowed


def test_shared_group_rules_apply_to_star() -> None:
    rules = source_policy.parse_robots(ROBOTS)
    assert ("disallow", "/api/*") in rules
    assert ("disallow", "/private-for-google/") not in rules


# ── verdicts ────────────────────────────────────────────────────────────────


@pytest.fixture
def offline(monkeypatch: pytest.MonkeyPatch):
    """Public DNS + a canned robots.txt per origin; no network."""
    robots: dict[str, tuple[int, str]] = {}
    source_policy._robots_cache.clear()
    monkeypatch.setattr(source_policy, "_is_public_host", lambda host: True)
    monkeypatch.setattr(
        source_policy, "_fetch_robots", lambda origin: robots.get(origin, (404, ""))
    )
    return robots


def test_unknown_robots_means_no_automation(offline) -> None:
    offline["https://blocked.example"] = (403, "")
    result = source_policy.evaluate("https://blocked.example/to-rent/")
    assert result["verdict"] == "unknown"
    assert result["automated_access"] is False


def test_missing_robots_allows_but_flags_terms(offline) -> None:
    result = source_policy.evaluate("https://open.example/listings")
    assert result["verdict"] == "allow"
    assert result["automated_access"] is True
    assert "terms" in result["note"]


def test_robots_disallow_denies(offline) -> None:
    offline["https://site.example"] = (200, ROBOTS)
    assert source_policy.evaluate("https://site.example/api/_search")["verdict"] == "deny"
    assert source_policy.evaluate("https://site.example/find.html")["verdict"] == "allow"


def test_policy_file_beats_robots(offline) -> None:
    # robots.txt would allow this page; the human policy says email alerts only.
    result = source_policy.evaluate("https://www.rightmove.co.uk/property-to-rent/find.html")
    assert result["verdict"] == "deny"
    assert result["policy_access"] == "email-alert"
    assert "alert" in result["alternative"].lower()


def test_subdomain_matches_parent_policy() -> None:
    assert source_policy.policy_for("www.zoopla.co.uk")["domain"] == "zoopla.co.uk"
    assert source_policy.policy_for("notzoopla.co.uk") is None


def test_non_http_and_private_hosts_are_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    assert source_policy.evaluate("file:///etc/passwd")["verdict"] == "deny"
    monkeypatch.setattr(source_policy, "_is_public_host", lambda host: False)
    assert source_policy.evaluate("http://metadata.internal/latest")["verdict"] == "deny"


def test_missing_policy_file_fails_closed(
    offline, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    # The Docker image once lacked policies/; robots.txt alone must not decide then.
    monkeypatch.setattr(source_policy, "POLICY_FILE", tmp_path / "absent.yaml")
    result = source_policy.evaluate("https://open.example/listings")
    assert result["verdict"] == "unknown"
    assert result["automated_access"] is False


def test_tool_returns_json(offline) -> None:
    out = json.loads(source_policy.check_source_policy.invoke({"url": "https://open.example/"}))
    assert out["verdict"] == "allow"


# ── roster and skill ────────────────────────────────────────────────────────


def _stub_builders(monkeypatch: pytest.MonkeyPatch) -> None:
    from agent.delegation import discovery, subagents

    for module in (subagents, discovery):
        monkeypatch.setattr(module, "build_search_tools", lambda: [])
    monkeypatch.setattr(subagents, "build_browser_tools", lambda: [])
    monkeypatch.setattr(discovery, "build_rea_tools", lambda: [])


def test_site_discovery_absent_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_REA", "off")
    _stub_builders(monkeypatch)
    from agent.delegation.subagents import build_subagents

    assert "site-discovery" not in {s["name"] for s in build_subagents()}


def test_site_discovery_present_and_typed_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_REA", "on")
    _stub_builders(monkeypatch)
    from agent.delegation.discovery import SITE_DISCOVERY_PROMPT, SiteRecipe
    from agent.delegation.subagents import build_subagents

    spec = {s["name"]: s for s in build_subagents()}["site-discovery"]
    assert spec["response_format"] is SiteRecipe
    assert "check_source_policy" in {t.name for t in spec["tools"]}
    assert "POLICY FIRST" in SITE_DISCOVERY_PROMPT
    assert "CAPTCHA" in SITE_DISCOVERY_PROMPT
    assert "VERIFY by reuse" in SITE_DISCOVERY_PROMPT


def test_browser_line_reports_missing_executable(monkeypatch: pytest.MonkeyPatch) -> None:
    from agent.delegation import discovery

    monkeypatch.delenv("REA_BROWSER_EXECUTABLE", raising=False)
    assert "No browser executable" in discovery._browser_line()
    monkeypatch.setenv("REA_BROWSER_EXECUTABLE", "/usr/bin/chromium")
    assert "/usr/bin/chromium" in discovery._browser_line()


def test_site_discovery_skill_is_listed_by_the_harness() -> None:
    """Listed through the SAME CompositeBackend route SkillsMiddleware uses."""
    from deepagents.middleware.skills import _list_skills

    from agent.brain import _build_backend

    skills = {s["name"]: s for s in _list_skills(_build_backend(), "/skills")}
    assert "site-discovery" in skills
    assert "website" in skills["site-discovery"]["description"]


def test_authored_skills_land_where_skills_are_loaded(monkeypatch: pytest.MonkeyPatch) -> None:
    # Regression: create_skill wrote to agent/skills, which SkillsMiddleware never reads.
    from agent.brain import SKILLS_DIR
    from agent.skills_engine import author

    monkeypatch.delenv("AGENT_SKILLS_DIR", raising=False)
    assert author.skills_dir().resolve() == Path(SKILLS_DIR).resolve()
