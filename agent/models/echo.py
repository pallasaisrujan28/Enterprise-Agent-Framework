"""A model that makes no calls — for tests, and for looking at the UI offline.

WHY A FAKE PROVIDER IS PART OF THE PRODUCT, NOT JUST THE TESTS
It is reachable with `AGENT_PROVIDER=echo`, deliberately. Two things that would
otherwise be impossible:

  The whole turn — skills, gate, streaming, the dock — can be exercised with no
  credentials, no spend and no network. The gate's behaviour on a blocked draft
  is much easier to demonstrate against a reply you control.

  It proves the seam is real. If the harness only ever ran against Bedrock, the
  abstraction would drift into a Bedrock-shaped hole without anyone noticing.
  A second implementation is what keeps the first one honest.

IT NEVER PRETENDS TO BE A MODEL
The reply says what it is. A fake that produced plausible prose would be a
liability: it would get screenshotted, quoted, or mistaken for a working
integration. Every reply here is visibly mechanical, and `Config.warnings()`
reports that the provider is echo so the dashboard can say so too.
"""

from __future__ import annotations

from collections.abc import Generator

from agent.config import Config
from agent.models.base import Chunk, Completion, Message, Usage

NAME = "echo"

# Roughly four characters per token. Good enough for a usage figure that is
# clearly synthetic, and it keeps the ledger's arithmetic exercised.
_CHARS_PER_TOKEN = 4


class EchoModel:
    """A `ChatModel` that answers deterministically from the prompt alone."""

    def __init__(self, config: Config | None = None) -> None:
        self._config = config or Config(provider="echo")

    @property
    def name(self) -> str:
        return NAME

    def _reply(self, messages: tuple[Message, ...], system: str) -> str:
        """A reply that reports what it was given.

        Deliberately useful as a diagnostic: it shows how many messages were in
        context and how long the system prompt was, which is exactly what you
        want to check when working on prompt assembly and do not care what the
        model says.
        """
        last = messages[-1].text if messages else ""
        return (
            f"[echo provider — no model was called]\n\n"
            f"You said: {last}\n\n"
            f"Context this turn: {len(messages)} message(s), "
            f"{len(system)} characters of system prompt."
        )

    def complete(self, messages: tuple[Message, ...], system: str = "") -> Completion:
        text = self._reply(messages, system)
        return Completion(
            model=NAME,
            text=text,
            usage=self._usage(messages, system, text),
            stop_reason="end_turn",
        )

    def stream(
        self, messages: tuple[Message, ...], system: str = ""
    ) -> Generator[Chunk, None, Completion]:
        """Streamed a word at a time, so the frontend's incremental path is real.

        If this returned the whole reply in one chunk, the dock's streaming
        rendering would never be exercised without credentials — and that is the
        part most likely to be broken.
        """
        text = self._reply(messages, system)
        words = text.split(" ")
        for index, word in enumerate(words):
            yield Chunk("text", word if index == len(words) - 1 else word + " ")
        return Completion(
            model=NAME,
            text=text,
            usage=self._usage(messages, system, text),
            stop_reason="end_turn",
        )

    @staticmethod
    def _usage(messages: tuple[Message, ...], system: str, reply: str) -> Usage:
        prompt_chars = len(system) + sum(len(m.text) for m in messages)
        return Usage(
            input_tokens=prompt_chars // _CHARS_PER_TOKEN,
            output_tokens=len(reply) // _CHARS_PER_TOKEN,
            latency_ms=0,
        )
