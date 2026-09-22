"""The sub-agent roster — what the agent can delegate to.

DECOUPLED FROM THE HARNESS ON PURPOSE. `brain.py` wires the harness together; it
should not also be the place that decides which specialists exist or what tools
each one gets. That is a delegation concern, so it lives here. `brain.py` just
calls `build_subagents()` and passes the result to `create_deep_agent`.

WHY DELEGATE AT ALL. A sub-agent runs in its OWN context window and returns only
its final result to the parent. Open-ended research fans out many searches and
fetches whose intermediate tool output would otherwise flood — and blow the
budget of — the main thread. The parent gets a synthesised answer back, not the
raw trail.

DYNAMIC, NOT TURN-BY-TURN. With the interpreter middleware attached (see
`agent/delegation/interpreter.py`), the model does not pick one sub-agent call at
a time; it writes an orchestration script that calls `task()` in loops / parallel
batches over these specs. This roster is what `task()` is allowed to dispatch.

THE OBLIGATION GATE STILL GOVERNS. Sub-agent output returns to the parent as a
tool message; the parent composes the final answer, and the gate checks THAT. So
delegation never becomes a way around the gate — the delivered answer is judged
exactly as before, regardless of how many sub-agents produced it.
"""

from __future__ import annotations

from deepagents import SubAgent

from agent.tools.fetch_and_store import fetch_and_store
from agent.tools.searxng_mcp import build_search_tools


def build_subagents() -> list[SubAgent]:
    """The sub-agents the interpreter dispatches dynamically via `task()`.

    `research` gets exactly the retrieval tools and nothing else. It deliberately
    does NOT get memory or filesystem-writing tools: its job is to look things up
    and hand back a summary, not to mutate durable state.

    No `model` override — the sub-agent inherits the parent's model, so a model
    switch in the dashboard applies end to end.
    """
    return [
        SubAgent(
            name="research",
            description=(
                "Delegate open-ended web research to this subagent: searching "
                "multiple sources and fetching/synthesising pages into a cited "
                "summary. Use it for 'find out about X', comparisons, or anything "
                "needing several lookups — it keeps that search/fetch churn out "
                "of the main thread. Not for one-off factual recall."
            ),
            system_prompt=(
                "You are a focused web-research subagent. Given a topic, search "
                "for several relevant sources, fetch the most useful ones, and "
                "return a concise, well-structured summary. Always include the "
                "source URLs you relied on. Do not speculate beyond what the "
                "sources support; if the evidence is thin, say so."
            ),
            tools=[*build_search_tools(), fetch_and_store],
        )
    ]
