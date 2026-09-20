"""One turn, one door.

EVERY CHANNEL COMES THROUGH `respond`
The dashboard calls it, the CLI calls it, and anything added later calls it. That
is not tidiness: it is the only way the gate, the trace and consolidation can be
guaranteed to run. waku learned this the hard way and ended up with a single
`respond()`; our own dashboard package already promised it in writing ("it will
call the orchestrator's own entry point, the same one the CLI uses, with no
private path of its own") before the function existed. This is that function.

IT IS A GENERATOR, AND THE RETURN VALUE IS THE RECORD
`respond` yields `Event`s as the turn progresses and RETURNS a `Turn`. A caller
that wants to stream iterates it; a caller that does not calls `run()`, which
drains it. Both get the identical `Turn`, so a streamed turn and a batch turn
cannot diverge in what they record.

THE ORDER OF EVENTS IS THE HONEST PART
Text is streamed BEFORE the gate has judged it, because that is physically how it
works: the gate needs a finished draft. So the text events are labelled a DRAFT,
and the `gate` event that follows either confirms or withdraws it. The
alternative — hold everything back until the gate has run — is a worse lie in the
other direction: it would show nothing for several seconds and then present a
gated answer as if it had been checked all along. A caller that discards the
draft on a block is showing the truth; one that leaves it on screen is not, and
`Event.supersedes_draft` says which is which.

WHAT IS NOT HERE, DELIBERATELY
No retrieval, no tools, no consolidation, no trace persistence. Those are
separate tickets and each is a lie if stubbed: a retrieval gate that always
returns "skip" would report a decision it never made. The topology marks them
missing and this module does not pretend otherwise.
"""

from __future__ import annotations

import time
from collections.abc import Generator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from agent import gate
from agent.config import Config
from agent.models import ChatModel, Message, ModelError, build
from agent.skills_engine import Draft, Skill, SkillSet, load_skillset

EventKind = Literal["start", "reasoning", "text", "gate", "done", "error"]

# How many turns of history go into the prompt. The topology records that working
# memory "grows with the conversation instead of staying flat" — this is the
# window that fixes it. Pairs, not messages: half a turn in context is worse than
# none, because the model sees a question with no answer and treats it as unmet.
HISTORY_TURNS = 8

PERSONA = (
    "You are the Enterprise Agent Framework assistant. Answer accurately and "
    "concisely. If you do not know something, say so rather than guessing. When a "
    "skill's procedure applies to the question, follow it exactly."
)


@dataclass(frozen=True)
class Event:
    """One thing that happened, on its way to whoever is watching."""

    kind: EventKind
    payload: dict[str, Any] = field(default_factory=dict)

    @property
    def supersedes_draft(self) -> bool:
        """True when what was streamed must be REPLACED, not appended to.

        The one bit of protocol a frontend cannot infer. A blocked turn has
        already streamed a draft to the screen; leaving it there and adding a
        refusal below would show the user an answer the gate refused to deliver.
        """
        if self.kind == "error":
            return True
        return self.kind == "done" and bool(self.payload.get("refused"))


@dataclass(frozen=True)
class Turn:
    """The completed record of one turn. What a trace would persist."""

    message: str
    reply: str
    model: str
    provider: str
    # The draft the model produced, kept even when it was refused — a refusal
    # without the text that caused it is unauditable.
    draft: str
    refused: bool
    gate_decision: str
    gate_reason: str
    blocking: tuple[str, ...] = ()
    observed: tuple[str, ...] = ()
    skills_triggered: tuple[str, ...] = ()
    trigger_reason: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    reasoning_chars: int = 0
    at: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "message": self.message,
            "reply": self.reply,
            "model": self.model,
            "provider": self.provider,
            "draft": self.draft,
            "refused": self.refused,
            "gate": {
                "decision": self.gate_decision,
                "reason": self.gate_reason,
                "blocking": list(self.blocking),
                "observed": list(self.observed),
            },
            "skills": list(self.skills_triggered),
            "trigger_reason": self.trigger_reason,
            "usage": {
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "latency_ms": self.latency_ms,
                "reasoning_chars": self.reasoning_chars,
            },
            "at": self.at,
        }


@dataclass
class Session:
    """Conversation history for one thread.

    In memory and lost on restart, which is stated rather than hidden: the
    Postgres checkpointer the topology mentions is not wired, and a Session that
    silently forgot would be indistinguishable from one that persisted badly.
    """

    id: str = "default"
    turns: list[Turn] = field(default_factory=list)

    def messages(self, latest: str) -> tuple[Message, ...]:
        """The prompt's message list: recent history, then what was just said.

        Only DELIVERED replies go back into context. A refused draft must not
        become history the model can build on — that would let a blocked answer
        influence the next turn, which is exactly what the gate refused.
        """
        history: list[Message] = []
        for turn in self.turns[-HISTORY_TURNS:]:
            history.append(Message("user", turn.message))
            history.append(Message("assistant", turn.reply))
        history.append(Message("user", latest))
        return tuple(history)


def load_skills(config: Config) -> SkillSet:
    """Skills from disk, or an empty set when there are none.

    A missing directory is not an error: a harness with no skills is a valid
    harness, just one with nothing to enforce. A malformed skill IS an error and
    is allowed to raise, because a skill whose obligations cannot be parsed must
    not be treated as absent — that would silently drop enforcement.
    """
    directory = Path(config.skills_dir)
    if not directory.is_dir():
        return SkillSet(skills=(), version="none")
    return load_skillset(directory)


def _trigger_lexically(message: str, skillset: SkillSet) -> tuple[tuple[Skill, ...], str]:
    """Word overlap between the message and a skill's name and description.

    THIS IS THE FALLBACK, NOT THE MECHANISM, because it measured as far too weak
    to rely on. "What does the Equality Act 2010 require of employers?" shares no
    word with "legislation advice / Answering questions about UK statute", so
    `legislation_advice` never fired and the gate sat dead on precisely the
    traffic it exists to police. Real questions name the statute, not the
    category.

    Kept because it needs no model call, so it still works when the judge is
    unavailable, and under-triggering loudly beats not answering at all.
    """
    if not skillset.skills:
        return (), "no skills are loaded"

    words = {
        word.strip(".,?!:;\"'()").lower() for word in message.split() if len(word.strip()) >= 4
    }

    triggered: list[Skill] = []
    reasons: list[str] = []
    for skill in skillset.skills:
        vocabulary = {
            token.strip(".,").lower()
            for token in f"{skill.name.replace('_', ' ')} {skill.description}".split()
            if len(token) >= 4
        }
        overlap = words & vocabulary
        if overlap:
            triggered.append(skill)
            reasons.append(f"{skill.name} matched {sorted(overlap)}")

    if not triggered:
        return (), "no skill matched the message lexically"
    return tuple(triggered), "lexical: " + "; ".join(reasons)


def _trigger_with_judge(
    message: str, skillset: SkillSet, judge: ChatModel
) -> tuple[tuple[Skill, ...], str]:
    """Ask a cheap model which skills apply, from the one-line index.

    This is what `Skill.index_line()` was built for: one line per skill is enough
    for a small model to route on, and it costs a fraction of the main call
    (nova-micro, a couple of hundred tokens). It reads the CATEGORY of the
    question rather than matching its words, which is why it catches "Equality
    Act 2010" as a legislation question when lexical matching cannot.

    The reply is not trusted. Only names that exist in the skillset are accepted,
    so a hallucinated skill name is dropped rather than becoming a KeyError or,
    worse, silently enabling nothing while reporting success.
    """
    prompt = (
        "Which of these skills apply to the user's message? A skill applies if "
        "its description covers the KIND of question being asked.\n\n"
        f"{skillset.index_block()}\n\n"
        f"User message: {message}\n\n"
        "Reply with the applicable skill names, comma separated, and nothing "
        "else. Reply with exactly NONE if none of them apply."
    )
    completion = judge.complete((Message("user", prompt),))
    answer = completion.text.strip()

    named = {
        token.strip().strip(".,`'\"").lower() for token in answer.replace("\n", ",").split(",")
    }
    triggered = tuple(skill for skill in skillset.skills if skill.name.lower() in named)

    if not triggered:
        return (), f"{judge.name} judged that no skill applies (said: {answer[:60]!r})"
    names = ", ".join(skill.name for skill in triggered)
    return triggered, f"{judge.name} selected {names}"


def _trigger(
    message: str, skillset: SkillSet, config: Config, judge: ChatModel | None = None
) -> tuple[tuple[Skill, ...], str]:
    """Which skills apply, and why — the reason is rendered, never discarded.

    A skill that fires invisibly is how a gate starts refusing traffic nobody can
    explain, so every path here returns a sentence that says what decided.

    Falls back to lexical matching when the judge call fails. That direction is
    chosen deliberately: a failed judge must not take the whole turn down, and
    under-enforcing while SAYING SO is better than a turn that errors out. The
    alternative — treating judge failure as "no skills apply" — would silently
    disable the gate on exactly the kind of transient error nobody notices.
    """
    if not skillset.skills:
        return (), "no skills are loaded, so there are no obligations to enforce"

    if judge is None:
        return _trigger_lexically(message, skillset)

    try:
        return _trigger_with_judge(message, skillset, judge)
    except ModelError as exc:
        skills, reason = _trigger_lexically(message, skillset)
        return skills, f"judge unavailable ({exc}); fell back to {reason}"


def _judge_for(config: Config, injected_model: ChatModel | None) -> ChatModel | None:
    """The cheap model used for routing, or None to route lexically.

    Returns None when a model was INJECTED, which is the test case: a test that
    hands in a fake model is testing the turn, and silently building a second
    real model behind its back would make it need credentials. Also None for the
    echo provider, where a judge would answer with echo's own diagnostic text and
    match nothing — going straight to lexical is honest rather than pretending a
    judgement happened.
    """
    if injected_model is not None or config.provider == "echo":
        return None
    try:
        return build(config.with_model(config.fast_model))
    except ModelError:
        return None


def build_system_prompt(
    skillset: SkillSet,
    triggered: tuple[Skill, ...],
    model: str = "",
    provider: str = "",
) -> str:
    """Assemble the system prompt — this is "working memory" on the chart.

    Order is deliberate and is the cheap half of context engineering: the stable
    parts first, the volatile parts last. Persona and the skill index are
    identical on every turn, so a provider doing prefix caching can reuse them;
    putting the clock at the top would invalidate the prefix every single turn.

    The index of ALL skills is always present, while only triggered skills
    contribute their body. That is progressive disclosure: one line each so the
    model knows what exists, full procedure only for what is in play.
    """
    parts = [PERSONA]

    # A MODEL DOES NOT KNOW WHAT MODEL IT IS, and will confidently say otherwise.
    # Asked "what model is this", gpt-oss-120b answered "I'm ChatGPT, built on
    # OpenAI's GPT-4 architecture" — it has no introspective access to its own
    # identity, so it pattern-matches the question against a training corpus full
    # of ChatGPT transcripts. The harness knows the true answer and was simply
    # not passing it on.
    #
    # Sits with the persona rather than near the clock because it is stable for
    # the conversation, so it stays inside the cacheable prefix. Switching model
    # mid-conversation invalidates that prefix, which is correct — it is a
    # different model.
    if model:
        parts.append(
            f"You are running on the model `{model}`"
            + (f", served via {provider}" if provider else "")
            + ". If you are asked which model or which provider you are, answer "
            "with exactly that. Do NOT infer it from your training data: models "
            "have no introspective access to their own identity and reliably "
            "misreport it."
        )

    if skillset.skills:
        parts.append("Skills available to you:\n" + skillset.index_block())

    for skill in triggered:
        parts.append(
            f"--- SKILL IN FORCE: {skill.name} (v{skill.version}) ---\n{skill.body.strip()}"
        )

    if triggered:
        # Said plainly because the model cannot see the gate and will otherwise
        # produce a confident answer that gets refused on the way out. Telling it
        # the obligations exist is not enforcement — the gate is — but it turns
        # most refusals into compliance instead.
        obligations = sorted({ob.kind for skill in triggered for ob in skill.obligations})
        parts.append(
            "These obligations are checked OUTSIDE you, after you answer, and a "
            "failure means your answer is refused rather than shown: "
            + ", ".join(obligations)
            + ". Satisfy them in your answer."
        )

    parts.append(f"The current time is {datetime.now(UTC).isoformat(timespec='seconds')}.")
    return "\n\n".join(parts)


def _draft_from(text: str) -> Draft:
    """Build the structured Draft the gate judges.

    THE WEAKEST LINK IN THE CHAIN, AND WORTH BEING BLUNT ABOUT IT. The gate checks
    fields; the model returns prose; something has to bridge that, and right now
    it is inference from the text. Two consequences:

      A model that mentions a URL in passing gets credit for citing it.

      `asked_user` is inferred from a question mark. Under-detecting is the
      direction that can only cause a refusal, never a false delivery, which is
      why the test is this conservative.

    Getting `asked_user` wrong was not hypothetical. It was hardcoded False here,
    which made `must_ask_when_missing` impossible to satisfy — the model did
    exactly what the skill's procedure told it to do, asked for the as-at date,
    and was refused for not asking. The gate was right and this function was
    wrong; an obligation that cannot be satisfied is worse than one that is not
    checked, because it looks like enforcement while being a dead end.

    The real fix is a structured response — the model returning fields rather than
    prose — which needs the tool path (KAN-12). Until then this is inference, and
    it is labelled as inference wherever it is shown.
    """
    urls = tuple(
        token.strip(".,);:\"'")
        for token in text.split()
        if token.startswith(("http://", "https://"))
    )
    # A question mark anywhere is a weak signal on its own, so it is paired with
    # the answer being SHORT: a long essay containing a rhetorical question has
    # not asked the user anything, whereas a clarifying question is brief by
    # nature. Crude, and deliberately biased towards not claiming a question.
    asked = "?" in text and len(text) < 600
    return Draft(answer=text, citations=urls, asked_user=asked)


def respond(
    message: str,
    session: Session | None = None,
    config: Config | None = None,
    model: ChatModel | None = None,
    judge: ChatModel | None = None,
) -> Generator[Event, None, Turn]:
    """Run one turn, yielding progress, returning the record.

    `config`, `model` and `judge` are injectable so a test can run the whole turn
    with no credentials and no network — the reason the model seam exists at all.

    `judge` is separate from `model` because they are separate decisions: the
    judge routes on the skill index with a cheap model, the model answers. A test
    that injects only `model` gets lexical routing, which is honest — it is what
    happens in production when the judge is unavailable.
    """
    resolved = config or Config.load()
    thread = session or Session()
    llm = model or build(resolved)
    started = time.monotonic()

    skillset = load_skills(resolved)
    router = judge or _judge_for(resolved, model)
    triggered, trigger_reason = _trigger(message, skillset, resolved, router)
    system = build_system_prompt(skillset, triggered, llm.name, resolved.provider)

    yield Event(
        "start",
        {
            "model": llm.name,
            "provider": resolved.provider,
            "skills": [skill.name for skill in triggered],
            "trigger_reason": trigger_reason,
            "system_prompt_chars": len(system),
            "history_turns": len(thread.turns[-HISTORY_TURNS:]),
        },
    )

    messages = thread.messages(message)

    try:
        stream = llm.stream(messages, system)
        while True:
            try:
                chunk = next(stream)
            except StopIteration as stop:
                completion = stop.value
                break
            yield Event(chunk.kind, {"delta": chunk.text})
    except ModelError as exc:
        yield Event("error", {"error": str(exc), "hint": exc.hint})
        return _failed_turn(message, thread, resolved, llm, str(exc), started)

    draft_text = completion.text.strip()

    # A successful call that produced no answer. Reported as what it is rather
    # than shown as an empty bubble, because the cause is fixable and specific.
    if not draft_text:
        detail = (
            "the model spent its entire output budget on reasoning and never "
            f"answered — raise AGENT_MAX_TOKENS above {resolved.max_tokens}"
            if completion.spent_budget_thinking
            else f"the model returned nothing (stop reason: {completion.stop_reason or 'unknown'})"
        )
        yield Event("error", {"error": detail, "hint": ""})
        return _failed_turn(message, thread, resolved, llm, detail, started, completion)

    result = gate.evaluate(_draft_from(draft_text), triggered)

    if not triggered:
        decision = "nothing-to-enforce"
        reason = trigger_reason
    elif result.passed:
        decision = "pass"
        reason = f"{len(triggered)} skill(s) checked, no blocking violation"
    else:
        decision = "block"
        reason = result.reason()

    blocking = tuple(str(v) for v in result.blocking)
    observed = tuple(str(v) for v in result.observed)

    yield Event(
        "gate",
        {
            "decision": decision,
            "reason": reason,
            "blocking": list(blocking),
            "observed": list(observed),
        },
    )

    refused = bool(result.blocking)
    reply = _refusal(result) if refused else draft_text

    turn = Turn(
        message=message,
        reply=reply,
        model=llm.name,
        provider=resolved.provider,
        draft=draft_text,
        refused=refused,
        gate_decision=decision,
        gate_reason=reason,
        blocking=blocking,
        observed=observed,
        skills_triggered=tuple(skill.name for skill in triggered),
        trigger_reason=trigger_reason,
        input_tokens=completion.usage.input_tokens,
        output_tokens=completion.usage.output_tokens,
        latency_ms=completion.usage.latency_ms or int((time.monotonic() - started) * 1000),
        reasoning_chars=len(completion.reasoning),
        at=datetime.now(UTC).isoformat(timespec="seconds"),
    )
    thread.turns.append(turn)

    payload = turn.as_dict()
    payload["kind_note"] = "refused" if refused else "delivered"
    yield Event("done", payload)
    return turn


def _refusal(result: gate.GateResult) -> str:
    """What the user sees when the gate blocks.

    Says which obligation failed and what would satisfy it. A bare "I can't help
    with that" trains people to rephrase at random; naming the obligation is both
    more useful and auditable.
    """
    lines = [
        "**Withheld by the obligation gate.** The model produced an answer, but it "
        "did not satisfy the obligations attached to the skill that applies here, "
        "so it was not delivered.",
        "",
    ]
    lines.extend(f"- {violation}" for violation in result.blocking)
    lines.append("")
    lines.append(
        "This is the gate working as designed. The obligations require tools that "
        "are not yet implemented, so a compliant answer is not currently possible "
        "for this kind of question."
    )
    return "\n".join(lines)


def _failed_turn(
    message: str,
    thread: Session,
    config: Config,
    llm: ChatModel,
    error: str,
    started: float,
    completion: Any = None,
) -> Turn:
    """Record a failure as a turn.

    Appended to history like any other, so the conversation does not silently
    lose an exchange — but with an empty `reply`, so `Session.messages` never
    feeds an error back to the model as if it had been said.
    """
    turn = Turn(
        message=message,
        reply="",
        model=llm.name,
        provider=config.provider,
        draft="",
        refused=True,
        gate_decision="not-reached",
        gate_reason=error,
        input_tokens=getattr(getattr(completion, "usage", None), "input_tokens", 0),
        output_tokens=getattr(getattr(completion, "usage", None), "output_tokens", 0),
        latency_ms=int((time.monotonic() - started) * 1000),
        at=datetime.now(UTC).isoformat(timespec="seconds"),
    )
    thread.turns.append(turn)
    return turn


def run(
    message: str,
    session: Session | None = None,
    config: Config | None = None,
    model: ChatModel | None = None,
    judge: ChatModel | None = None,
) -> Turn:
    """`respond` without streaming, for a caller that only wants the answer.

    Drains the generator and returns its value. Written once here so no caller
    has to hand-roll the StopIteration dance.
    """
    stream = respond(message, session, config, model, judge)
    while True:
        try:
            next(stream)
        except StopIteration as stop:
            return stop.value  # type: ignore[no-any-return]
