"""Memory hygiene: find junk already in the graph and, only when asked, remove it.

The consolidation quality gate and the ontology stop NEW junk. This cleans what
got in before them: facts about the assistant ("The Assistant greets the User"),
world trivia ("The Eiffel Tower is taller than Big Ben"), browsed listings
("Amazon sells …"), and episodes that recorded a failure ("Gmail isn't
configured") and now feed Graphiti's extraction context (it reads the last 10
episodes as background for every new one).

DRY RUN BY DEFAULT. `agent memory clean` only reports; `--apply` deletes. A
deletion from the graph can't be undone, so the review step isn't optional.

Facts are judged by the main model in ONE batched call against the same
criteria extraction uses (ontology.EXTRACTION_INSTRUCTIONS), so "junk" means
the same thing on both sides. If its reply can't be parsed, nothing is flagged.
Episodes are flagged by the same error/apology rule as the consolidation gate.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from agent.memory import ontology, semantic


@dataclass
class Flagged:
    kind: str  # "fact" | "episode"
    uuid: str
    text: str
    why: str


_JUDGE = """You are cleaning an assistant's long-term memory about its user.
The rules for what belongs in memory:
{rules}

Below are stored facts, numbered. List the ones that do NOT belong.
Reply with JSON only: {{"drop": [{{"i": <number>, "why": "<5 words>"}}]}}
If all belong, reply {{"drop": []}}.

{facts}"""


def _parse_drop(text: str, n: int) -> list[tuple[int, str]]:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("judge returned no JSON — nothing flagged")
    data = json.loads(match.group(0))
    out: list[tuple[int, str]] = []
    for item in data.get("drop", []):
        i = int(item.get("i", -1))
        if 0 <= i < n:
            out.append((i, str(item.get("why", ""))))
    return out


def _episode_is_junk(content: str) -> str:
    """Why an episode should go, or "" if it should stay."""
    from agent.middleware.memory import _ERROR_ANSWER, _TRIVIAL_ANSWER

    assistant = " ".join(
        line.split(":", 1)[1] for line in content.splitlines() if line.startswith("Assistant:")
    ).strip()
    if not assistant:
        return ""
    if _ERROR_ANSWER.search(assistant):
        return "recorded a failure/apology"
    if _TRIVIAL_ANSWER.match(assistant):
        return "trivial exchange"
    return ""


def find_junk(model: Any, group_id: str = semantic.DEFAULT_GROUP) -> list[Flagged]:
    rt = semantic._GraphitiRuntime.get()

    async def _load() -> tuple[list[Any], list[Any]]:
        d = rt._graphiti.driver
        facts = await d.execute_query(
            "MATCH (:Entity)-[e:RELATES_TO]->(:Entity) WHERE e.group_id = $g "
            "AND e.invalid_at IS NULL AND e.expired_at IS NULL "
            "RETURN e.uuid AS uuid, e.fact AS fact ORDER BY e.created_at",
            g=group_id,
        )
        eps = await d.execute_query(
            "MATCH (ep:Episodic) WHERE ep.group_id = $g "
            "RETURN ep.uuid AS uuid, ep.content AS content ORDER BY ep.created_at",
            g=group_id,
        )
        return list(facts.records), list(eps.records)

    facts, episodes = rt._run(_load())
    flagged: list[Flagged] = []

    if facts:
        listing = "\n".join(f"{i}. {r['fact']}" for i, r in enumerate(facts))
        reply = model.invoke(_JUDGE.format(rules=ontology.EXTRACTION_INSTRUCTIONS, facts=listing))
        text = reply.text if hasattr(reply, "text") else str(reply.content)
        for i, why in _parse_drop(text, len(facts)):
            flagged.append(Flagged("fact", facts[i]["uuid"], facts[i]["fact"], why))

    for r in episodes:
        why = _episode_is_junk(r["content"] or "")
        if why:
            flagged.append(Flagged("episode", r["uuid"], (r["content"] or "")[:160], why))
    return flagged


def apply(flagged: list[Flagged]) -> tuple[int, int]:
    """Delete flagged items. Returns (facts_removed, episodes_removed)."""
    rt = semantic._GraphitiRuntime.get()
    facts = sum(1 for f in flagged if f.kind == "fact" and semantic.forget_fact(f.uuid))
    episodes = 0
    for f in flagged:
        if f.kind == "episode":
            # Graphiti's own removal: drops the episode plus edges/nodes that only
            # it introduced — so a failure episode takes its derived junk with it.
            rt._run(rt._graphiti.remove_episode(f.uuid))
            episodes += 1
    return facts, episodes
