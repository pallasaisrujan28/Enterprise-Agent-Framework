"""
Platform policy loader — loads YAML policy files from policies/ and
evaluates an action or output against them.

Relationship to gate.py:
  gate.py  — evaluates skill-level obligations (per-skill, per-turn)
  this module — evaluates platform-level policies (always-on, cross-cutting)

Platform policies cover things that are not specific to any skill:
  - Data residency (no data leaves eu-west-2)
  - No PII in log output
  - No credential exposure in responses
  - No calls to non-approved external services

Policies are loaded once at startup from the policies/ directory.
Each policy file contains a list of rules with an id, description,
action (allow/deny/log), and a pattern or condition to match against.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

POLICIES_DIR = Path(__file__).parents[2] / "policies"


@dataclass(frozen=True)
class Rule:
    id: str
    description: str
    action: str  # "deny" | "log" | "allow"
    pattern: str = ""  # regex matched against the text being evaluated

    def matches(self, text: str) -> bool:
        if not self.pattern:
            return False
        return bool(re.search(self.pattern, text, re.IGNORECASE))


@dataclass
class Policy:
    name: str
    version: str
    rules: list[Rule] = field(default_factory=list)


def load_policies(directory: Path = POLICIES_DIR) -> list[Policy]:
    """Load all YAML policy files from *directory*."""
    policies: list[Policy] = []
    if not directory.exists():
        return policies
    for path in sorted(directory.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text())
        rules = [Rule(**r) for r in raw.get("rules", [])]
        policies.append(Policy(name=raw["name"], version=raw.get("version", "0"), rules=rules))
    return policies


@dataclass(frozen=True)
class PolicyViolation:
    policy: str
    rule_id: str
    description: str
    action: str


def evaluate(text: str, policies: list[Policy]) -> list[PolicyViolation]:
    """
    Check *text* against all rules in *policies*.
    Returns violations — empty list means the text is clean.
    Caller decides what to do with 'log' vs 'deny' actions.
    """
    violations = []
    for policy in policies:
        for rule in policy.rules:
            if rule.matches(text):
                violations.append(
                    PolicyViolation(
                        policy=policy.name,
                        rule_id=rule.id,
                        description=rule.description,
                        action=rule.action,
                    )
                )
    return violations
