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

from agent.tools.browser_mcp import browser_enabled, build_browser_tools
from agent.tools.fetch import fetch_url
from agent.tools.searxng_mcp import build_search_tools

# The browsing/action agent's operating contract. The single most important rule
# is CONFIRM-BEFORE-COMMIT: this subagent may do everything up to the point of an
# irreversible action, but it must STOP and hand back to the user before crossing
# it. That is how the "everything happens in the chat, the agent acts, the human
# authorises" model is enforced without per-click interrupt machinery — the
# subagent returns, the user confirms in chat, and a fresh task performs the
# commit.
BROWSING_PROMPT = """You are the browsing/action subagent. You drive a real web \
browser to carry out tasks a person would otherwise do by hand — shopping, \
booking (flights, movies, concerts, any buy/order/book site), and filling out \
forms such as visa applications. You work on ANY website that renders in a \
browser; there are no per-site shortcuts.

HOW TO ACT
- Call browser_snapshot to SEE the page. It returns an accessibility tree with a \
`ref` for each element. Act on elements by their ref (browser_click, \
browser_type, browser_fill_form, browser_select_option, browser_press_key).
- Re-snapshot after anything that changes the page. Never assume the layout; read it.
- Use browser_navigate to go to a URL, browser_file_upload for document/photo \
uploads, browser_wait_for when content loads asynchronously.
- Use web search + fetch_url to FIND the right site or compare options before you \
start driving the browser. Prefer plain keyword queries and use `site:` filters \
sparingly — not every engine supports them, so an over-constrained query can come \
back empty. If a search returns nothing, rephrase more simply or navigate to the \
site and search WITHIN it; an empty result is not a dead end.

THE WORKFLOWS
- Shopping: search → filter (price, rating, brand, specs — re-rank as the user \
adds constraints) → compare → select → add to cart → STOP for confirmation → \
(only after confirmation) checkout and pay.
- Booking: search → filter (date, time, price, seat/section, stops, airline/venue) \
→ select → enter passenger/attendee details → STOP for confirmation → pay. Holds \
expire fast, so move promptly once the user has confirmed.
- Forms / visa: open the official site → find the correct form → fill fields from \
the user's data → review every value → STOP for confirmation → submit. A visa/\
application submission is legally significant; never submit without an explicit go.

CONFIRM BEFORE COMMIT — THE RULE YOU MUST NOT BREAK
Never click a final PAY, PLACE ORDER, BOOK, CONFIRM, or SUBMIT button on your own. \
When you reach that point, stop and RETURN to the caller a precise summary of what \
is about to happen — item(s), total price, recipient/passenger, key form values, \
and the exact button you would press — and ask the user to confirm. Only perform \
the irreversible action when you are dispatched again with the user's explicit \
confirmation. Adding to a cart or filling a draft is fine; committing is not.

SECRETS AND LOGINS
If a login or payment step needs a value you were not given (username, password, \
card number, OTP), do NOT invent one and do NOT guess. Stop and ask the user for \
exactly that value; they will provide it in chat and you continue.

CAPTCHAS AND BOT WALLS
Do not try to defeat a CAPTCHA, "prove you're human" challenge, or block page. \
The browser is visible — stop and ask the user to solve the challenge in the \
window, then continue once they say it is done.

ALWAYS report which site and pages you acted on, and end by stating clearly \
whether the task is complete, waiting on the user, or blocked.

RETURN YOUR TRAIL. Your parent cannot see the pages you browsed or the products \
you looked at — only the result you hand back. So when you recommend or select \
something, end with a short 'Considered:' list of the other candidates you saw \
(name + price + why not picked), plus the key steps/pages you went through. This \
lets the user ask "what else did you consider?" and lets the parent answer without \
re-browsing."""


def build_subagents() -> list[SubAgent]:
    """The sub-agents the interpreter dispatches dynamically via `task()`.

    `research` gets exactly the retrieval tools and nothing else. It deliberately
    does NOT get memory or filesystem-writing tools: its job is to look things up
    and hand back a summary, not to mutate durable state.

    `browsing` is added only when AGENT_BROWSER is on (it needs Node + Playwright
    and a running Chromium). It shares the same browser session as the parent via
    the memoised MCP runtime, and its prompt enforces confirm-before-commit so a
    purchase or submission is never made without the user's explicit go.

    No `model` override — the sub-agents inherit the parent's model, so a model
    switch in the dashboard applies end to end.
    """
    roster = [
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
                "sources support; if the evidence is thin, say so. Prefer plain "
                "keyword queries; use `site:` filters sparingly (not every engine "
                "supports them). If a search comes back empty, rephrase more "
                "simply or fetch a likely source directly — do not treat one "
                "empty result as a dead end.\n\n"
                "RETURN YOUR TRAIL. Your parent cannot see the searches you ran or "
                "the sources you rejected — only the result you hand back. So end "
                "your answer with a short 'Considered:' list of the main options / "
                "sources you looked at (including the ones you did NOT pick and "
                "why), so the parent and the user can ask about alternatives later."
            ),
            tools=[*build_search_tools(), fetch_url],
        )
    ]

    if browser_enabled():
        roster.append(
            SubAgent(
                name="browsing",
                description=(
                    "Delegate tasks that require DRIVING A BROWSER and taking "
                    "actions on a website: shopping, booking flights/movies/"
                    "concerts/tickets, and filling out forms like visa "
                    "applications. It navigates, reads pages, fills fields, and "
                    "acts — but STOPS and asks the user before any payment, order, "
                    "or submission. Use it whenever the goal is to DO something on "
                    "a site, not just read it."
                ),
                system_prompt=BROWSING_PROMPT,
                tools=[*build_browser_tools(), *build_search_tools(), fetch_url],
            )
        )

    return roster
