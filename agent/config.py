"""The one place that answers "what am I configured to do".

WHY THIS EXISTS AT ALL
Before this module, four files read `os.getenv` at import time. That has three
costs which only show up later:

  A value read at import cannot be changed by a test, so anything that depends
  on configuration becomes untestable without monkeypatching module globals.

  A default spelled in four places drifts. `AWS_DEFAULT_REGION` already had the
  same `"eu-west-2"` fallback written out twice.

  Nothing could answer "where does the credential come from". Today it is the
  environment. The moment it is Secrets Manager or a mounted file, every caller
  has to change — unless there is a seam. This is the seam.

WHAT IT IS NOT
Not a settings framework, and deliberately not pydantic: that would be a
dependency on the hot path for a dozen strings, and the repository's own rule is
that a dependency earns its supply-chain surface. It is a frozen dataclass and a
resolver function.

RESOLUTION IS LAZY AND EXPLICIT
`Config.load()` reads the environment when CALLED, not when imported, so a test
can build one directly and a server can reload without a restart. Nothing in
this module contacts the network or AWS; it only decides what the answers are.

SECRETS ARE NAMED, NEVER RETURNED
`secret_ref()` hands back the NAME of a credential source, not its value. The
AWS SDK reads the credential itself from the environment or the instance role,
which means a credential never passes through our code and so cannot be logged
by it. That is the whole reason the seam looks like this rather than a
`get_secret() -> str`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from typing import Literal

# Providers this build knows how to construct. Adding one means adding a module
# under agent/models/ and a branch in agent.models.build — nothing else.
Provider = Literal["bedrock", "echo"]

DEFAULT_REGION = "eu-west-2"

# Verified invocable on eu-west-2 on 2026-09-19, by calling Converse and reading
# the reply. NOT chosen from documentation: `anthropic.claude-sonnet-4-6`, which
# k8s/deployment.yaml still named, fails with AccessDeniedException on this
# account, and every Anthropic id fails the same way. Pick from the list in
# docs or from `agent models` output, never from memory.
DEFAULT_MODEL = "openai.gpt-oss-120b-1:0"

# The cheap model, for work that is not the answer: a retrieval-gate judge, a
# summariser, a title. Separate so the expensive model is not the default for
# everything by accident.
DEFAULT_FAST_MODEL = "amazon.nova-lite-v1:0"

# gpt-oss spends output tokens on a reasoning block BEFORE the answer, and the
# budget is shared. At maxTokens=16 it produced a reasoning block and NO answer
# at all — a silently empty reply rather than an error. This floor is high
# enough that reasoning cannot consume the whole budget; agent/models/bedrock.py
# reports it when it happens anyway.
DEFAULT_MAX_TOKENS = 1024

MIN_SAFE_MAX_TOKENS = 256


@dataclass(frozen=True)
class Config:
    """Everything the harness needs to know before it can run a turn."""

    provider: Provider = "bedrock"
    region: str = DEFAULT_REGION
    model: str = DEFAULT_MODEL
    fast_model: str = DEFAULT_FAST_MODEL
    max_tokens: int = DEFAULT_MAX_TOKENS
    temperature: float = 0.2
    # Where skills are loaded from. A path, so a test can point at a fixture.
    skills_dir: str = "skills"

    @staticmethod
    def load(env: dict[str, str] | None = None) -> Config:
        """Read configuration from the environment.

        `env` is injectable so a test never has to mutate `os.environ`.

        AWS_REGION is preferred over AWS_DEFAULT_REGION because that is the
        precedence the AWS SDKs themselves use; getting it backwards would mean
        our client and boto3's client disagreed about the region, which fails as
        a confusing model-not-found rather than as a config error.
        """
        source = os.environ if env is None else env

        provider_name = source.get("AGENT_PROVIDER", "bedrock").strip().lower()
        provider: Provider = "echo" if provider_name == "echo" else "bedrock"

        return Config(
            provider=provider,
            region=(source.get("AWS_REGION") or source.get("AWS_DEFAULT_REGION") or "").strip()
            or DEFAULT_REGION,
            model=source.get("BEDROCK_MODEL_ID", "").strip() or DEFAULT_MODEL,
            fast_model=source.get("BEDROCK_FAST_MODEL", "").strip() or DEFAULT_FAST_MODEL,
            max_tokens=_positive_int(source.get("AGENT_MAX_TOKENS"), DEFAULT_MAX_TOKENS),
            temperature=_float(source.get("AGENT_TEMPERATURE"), 0.2),
            skills_dir=source.get("AGENT_SKILLS_DIR", "").strip() or "skills",
        )

    def with_model(self, model: str) -> Config:
        """A copy naming a different model.

        The dashboard's model switcher needs this. Returning a copy rather than
        mutating means one request cannot change the model another request is
        already using — the config is shared, and a frozen value that is replaced
        rather than edited makes that safe without a lock.
        """
        return replace(self, model=model)

    def secret_ref(self) -> str:
        """Where the provider's credential comes from — the SOURCE, not the value.

        Rendered in the dashboard so it is possible to see that a credential is
        ambient without ever displaying one. Returns a description, deliberately
        not a secret; there is no function here that returns a secret.
        """
        if self.provider == "echo":
            return "none — the echo provider makes no calls"
        if os.environ.get("AWS_ACCESS_KEY_ID"):
            return "AWS_ACCESS_KEY_ID from the environment"
        if os.environ.get("AWS_PROFILE"):
            return f"AWS_PROFILE={os.environ['AWS_PROFILE']}"
        if os.environ.get("AWS_WEB_IDENTITY_TOKEN_FILE"):
            return "web identity token file (IRSA / Pod Identity)"
        return "the default AWS credential chain"

    def warnings(self) -> tuple[str, ...]:
        """Configuration that is legal but will behave badly.

        Surfaced rather than silently corrected, because a silent correction
        means the value in the config is not the value in use.
        """
        notes: list[str] = []
        if self.max_tokens < MIN_SAFE_MAX_TOKENS:
            notes.append(
                f"AGENT_MAX_TOKENS={self.max_tokens} is below {MIN_SAFE_MAX_TOKENS}; a "
                "reasoning model can spend the whole budget before it writes any answer"
            )
        if self.provider == "echo":
            notes.append(
                "provider is 'echo' — replies are generated locally and no model is called"
            )
        return tuple(notes)


def _positive_int(raw: str | None, fallback: int) -> int:
    """Parse, and fall back rather than raise.

    A malformed value in the environment should not stop the process from
    starting: the fallback is safe, and `warnings()` is where a bad value gets
    reported. Refusing to boot over a typo in an optional tuning knob costs more
    than it saves.
    """
    if raw is None or not raw.strip():
        return fallback
    try:
        value = int(raw)
    except ValueError:
        return fallback
    return value if value > 0 else fallback


def _float(raw: str | None, fallback: float) -> float:
    if raw is None or not raw.strip():
        return fallback
    try:
        return float(raw)
    except ValueError:
        return fallback
