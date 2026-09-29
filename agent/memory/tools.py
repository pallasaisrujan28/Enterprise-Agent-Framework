"""Memory agency tools — let the agent explicitly save, correct, and forget.

These are the waku-style CRUD over durable memory, built on our Graphiti store:

  save_note      — write a durable fact on request ("remember that …")
  manage_memory  — search / update / forget facts (the correction path)

WHY, ON TOP OF CONSOLIDATION. Consolidation (agent/middleware/memory.py) grows
memory automatically every N turns. But two things need explicit agency:
  - the user says "remember X" and expects it saved NOW, not eventually;
  - the user says "that's wrong, forget it" — and a graph that can only grow is
    a graph that stays wrong.
These tools cover both. "Forget" is a real delete of the fact edge; "update"
rewrites the fact text in place (Graphiti's temporal supersession handles the
implicit corrections; this is the explicit one).

OFF WITHOUT MEMORY. Every tool returns a clear message when AGENT_MEMORY is off,
rather than erroring — so a memory-less deploy still exposes the tool surface
consistently without touching Neo4j.
"""

from __future__ import annotations

from langchain_core.tools import tool

from agent.memory import semantic


@tool
def save_note(subject: str, content: str) -> str:
    """Save a durable fact to long-term memory on the user's behalf.

    Use when the user tells you something worth remembering about themselves, a
    person, a project, or a standing preference — especially if they say
    "remember". `subject` is who/what it is about (e.g. "alex", "acme-project");
    `content` is the fact in one sentence.
    """
    if not semantic.memory_enabled():
        return "Long-term memory is off in this deployment, so I can't save that."
    if not subject.strip() or not content.strip():
        return "I need both a subject and the fact to save."
    try:
        semantic.save_fact(subject.strip(), content.strip())
        return f"Saved to memory under '{subject.strip()}': {content.strip()}"
    except Exception as exc:  # noqa: BLE001 — surface a readable failure, never crash the turn
        return f"Could not save that to memory ({type(exc).__name__}: {exc})."


@tool
def manage_memory(action: str, query: str = "", id: str = "", content: str = "") -> str:
    """Search, correct, or forget the user's long-term memory facts.

    ALWAYS search first to get a fact's id, then update or forget by that id.
    - action="search", query="keywords"      -> lists matching facts with ids
    - action="update", id="<id>", content="new text"  -> rewrites that fact
    - action="forget", id="<id>"             -> deletes that fact

    Use when the user says something you remember is wrong or should be forgotten.
    """
    if not semantic.memory_enabled():
        return "Long-term memory is off in this deployment, so there is nothing to manage."

    act = (action or "").strip().lower()
    try:
        if act == "search":
            if not query.strip():
                return "Provide a search query."
            hits = semantic.search_facts(query.strip())
            if not hits:
                return "No matching facts."
            return "\n".join(f"#{uuid} {fact}" for uuid, fact in hits if uuid)
        if act == "update":
            if not id.strip() or not content.strip():
                return "Update needs both id (from a search) and the new content."
            ok = semantic.update_fact(id.strip(), content.strip())
            return f"Updated fact #{id}." if ok else f"No fact found with id {id}."
        if act in ("forget", "delete"):
            if not id.strip():
                return "Forget needs the id of the fact (from a search)."
            ok = semantic.forget_fact(id.strip())
            return f"Forgotten fact #{id}." if ok else f"No fact found with id {id}."
        return "action must be one of: search, update, forget"
    except Exception as exc:  # noqa: BLE001 — readable failure, never crash the turn
        return f"Memory operation failed ({type(exc).__name__}: {exc})."
