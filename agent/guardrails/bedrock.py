"""
Bedrock Guardrails integration — validates input and output text against
a Bedrock Guardrail resource before the agent responds.

Why this is separate from policies/loader.py:
  policies/loader.py — regex-based platform rules, always runs, no API call
  this module — Bedrock Guardrails API, ML-based content safety, optional

Bedrock Guardrails covers:
  - Topic blocking (configurable — see guardrails/content_safety.yaml)
  - PII detection and redaction
  - Harmful content filtering (hate, violence, sexual content)
  - Prompt attack detection (jailbreak, prompt injection)

The guardrail is applied TWICE per turn:
  1. On the user's INPUT before the agent processes it
  2. On the agent's OUTPUT before it is returned

A blocked response raises GuardrailBlocked. The caller should surface a
safe fallback message — never the blocked content.

Requires:
  BEDROCK_GUARDRAIL_ID env var (the Bedrock Guardrail resource ID)
  BEDROCK_GUARDRAIL_VERSION env var (default: "DRAFT")
"""

from __future__ import annotations

import os

import boto3

GUARDRAIL_ID = os.getenv("BEDROCK_GUARDRAIL_ID", "")
GUARDRAIL_VERSION = os.getenv("BEDROCK_GUARDRAIL_VERSION", "DRAFT")
REGION = os.getenv("AWS_DEFAULT_REGION", "eu-west-2")

_bedrock = boto3.client("bedrock-runtime", region_name=REGION)


class GuardrailBlocked(RuntimeError):
    """Raised when Bedrock Guardrails blocks the content."""

    def __init__(self, source: str, action: str, reasons: list[str]) -> None:
        self.source = source   # "INPUT" or "OUTPUT"
        self.action = action
        self.reasons = reasons
        super().__init__(f"Guardrail blocked {source}: {'; '.join(reasons)}")


def check(text: str, source: str = "OUTPUT") -> str:
    """
    Apply the Bedrock Guardrail to *text*.

    Returns the (possibly redacted) text if the guardrail allows it.
    Raises GuardrailBlocked if the guardrail blocks it.

    If BEDROCK_GUARDRAIL_ID is not set the text passes through unchanged
    (guardrails are optional — the gate.py obligation engine is always on).
    """
    if not GUARDRAIL_ID:
        return text

    resp = _bedrock.apply_guardrail(
        guardrailIdentifier=GUARDRAIL_ID,
        guardrailVersion=GUARDRAIL_VERSION,
        source=source,
        content=[{"text": {"text": text}}],
    )

    action = resp.get("action", "NONE")
    if action == "GUARDRAIL_INTERVENED":
        reasons = [
            assessment.get("type", "unknown")
            for assessment in resp.get("assessments", [{}])[0].get("contentPolicy", {}).get("filters", [])
            if assessment.get("action") == "BLOCKED"
        ]
        raise GuardrailBlocked(source=source, action=action, reasons=reasons or ["unspecified"])

    # Return the (potentially PII-redacted) output
    outputs = resp.get("outputs", [])
    if outputs:
        return outputs[0].get("text", text)
    return text
