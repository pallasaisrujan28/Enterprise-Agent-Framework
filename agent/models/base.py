"""The model seam — what the harness is allowed to know about an LLM.

WHY A SEAM AND NOT JUST A BOTO3 CALL
ADR-011 requires that code calls a proxy and never a provider SDK, and this is
the narrow point that makes it true: nothing outside `agent/models/` imports
boto3, so swapping Bedrock for anything else is a new file in this package plus
one branch in `build()`. Two concrete payoffs already:

  The tests run with no credentials and no network, against `EchoModel`, because
  the turn logic depends on this protocol rather than on Bedrock.

  A provider quirk is contained. gpt-oss returns a REASONING block before its
  answer, so `content[0]["text"]` raises KeyError; Nova returns text directly.
  That difference lives in `agent/models/bedrock.py` and nothing above it needs
  to know.

REASONING IS A SEPARATE FIELD, NOT PART OF THE ANSWER
`Completion.text` is the answer; `Completion.reasoning` is the model's thinking.
They are kept apart at the seam because concatenating them puts chain-of-thought
in front of the user as if it were the reply, and because the obligation gate
judges the ANSWER — feeding it reasoning prose would have it enforcing against
text the user never sees.

EVERYTHING IS FROZEN
A completion is a record of something that already happened. Nothing downstream
has any business editing it, and a frozen value can be handed to the gate, the
trace and the dashboard without anyone defensively copying it.
"""

from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass, field
from typing import Literal, Protocol, runtime_checkable

Role = Literal["user", "assistant"]

# What a streamed chunk carries. "reasoning" exists so a caller can show thinking
# separately, or drop it, but can never mistake it for the answer.
ChunkKind = Literal["text", "reasoning"]


class ModelError(RuntimeError):
    """A model call failed in a way the caller should show, not swallow.

    Carries a `hint` because the useful part of a Bedrock failure is usually what
    to DO about it — grant model access, pick a different id, set a region — and
    that is knowledge the adapter has and the caller does not.
    """

    def __init__(self, message: str, *, hint: str = "") -> None:
        super().__init__(message)
        self.hint = hint

    def __str__(self) -> str:
        base = super().__str__()
        return f"{base} ({self.hint})" if self.hint else base


@dataclass(frozen=True)
class Message:
    role: Role
    text: str


@dataclass(frozen=True)
class Usage:
    """Tokens as ground truth, cost derived elsewhere.

    Tokens are what the provider actually reports; a price is a number we looked
    up and which goes stale. The usage ledger (KAN-17) is where the two get
    multiplied — keeping cost out of here means a price change cannot rewrite
    history.
    """

    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True)
class Completion:
    model: str
    text: str
    reasoning: str = ""
    usage: Usage = field(default_factory=Usage)
    stop_reason: str = ""

    @property
    def spent_budget_thinking(self) -> bool:
        """True when the model reasoned until it ran out and never answered.

        This is a real failure mode, not a hypothetical: at maxTokens=16,
        gpt-oss-120b returned a reasoning block and no text at all. Without this
        flag the turn reports success and shows an empty bubble, which is the
        worst of both — it looks like the model had nothing to say.
        """
        return not self.text.strip() and bool(self.reasoning.strip())


@dataclass(frozen=True)
class Chunk:
    kind: ChunkKind
    text: str


@runtime_checkable
class ChatModel(Protocol):
    """What the harness needs from a model. Deliberately four members.

    A Protocol rather than a base class so an implementation does not have to
    import ours to satisfy it — a test double can be a plain object. `complete`
    is not defined in terms of `stream`, because a provider may implement one
    better than the other and collapsing them would hide that.
    """

    @property
    def name(self) -> str:
        """The model id, as the provider spells it. Shown in the UI and traced."""
        ...

    def complete(self, messages: tuple[Message, ...], system: str = "") -> Completion:
        """One call, one whole answer."""
        ...

    def stream(
        self, messages: tuple[Message, ...], system: str = ""
    ) -> Generator[Chunk, None, Completion]:
        """The same answer in pieces, RETURNING the completion when it ends.

        A generator return value rather than an `Iterator[Chunk]`, because usage
        and stop reason only arrive in the provider's final event and a plain
        iterator has nowhere to put them. The alternatives were worse: stashing
        usage on the adapter makes two concurrent turns overwrite each other, and
        letting the caller reassemble means the streamed path and the
        non-streamed path can drift into reporting different things.

        So a streamed turn ends with the same `Completion` a direct call would
        have produced, and the gate cannot tell which path it was handed:

            stream = model.stream(messages, system)
            completion = yield from stream          # inside a generator
        """
        ...
