# deepagents subagents — what they are, and how they work in code

A study note, written against **deepagents 0.7.15** (the version pinned in this
repo) rather than only the docs, so every claim here is something you can import
and run. Where the website describes something our install cannot do yet, that is
called out as a **gap**, not glossed over.

Read top to bottom once; after that the section headers are the index.

---

## 0. The one-sentence version

A subagent is **another agent the main agent can hand a task to**, and the reason
to bother is **context quarantine**: the subagent does the noisy multi-step work
(ten web searches, twenty file reads) on *its own* context, and the main agent
gets back only the answer — not the twenty tool calls that produced it.

Delegation is a first-class feature, not an add-on. But note the mechanics below:
in our current build it is switched **off**, because deepagents only wires it up
when at least one subagent exists and we pass none.

---

## 1. The `task` tool — how delegation actually reaches the model

The model never "calls a subagent" directly. deepagents gives the model an
ordinary tool called **`task`**, and delegation is just a tool call:

```
task(description="research the JEV model", subagent_type="general-purpose")
```

Mechanically, in `create_deep_agent`:

- If **at least one synchronous subagent exists** (either the built-in
  general-purpose one, or one you passed), deepagents attaches
  `SubAgentMiddleware`, which registers the `task` tool and routes each `task(...)`
  call to the right subagent's graph.
- If **no synchronous subagent exists**, `SubAgentMiddleware` is **not attached**,
  there is **no `task` tool**, and the agent simply cannot delegate.

> **Our current state (verified).** `agent/brain.py` calls `create_deep_agent`
> with no `subagents=` argument, and the compiled graph's nodes are:
> `model, tools, SkillsMiddleware, PatchToolCallsMiddleware, TodoListMiddleware,
> ObligationGateMiddleware` — **no `SubAgentMiddleware`, no `task` tool.** So today
> the harness does everything inline (which is why the JEV research was one agent
> doing search+fetch+summarise in its own context). Turning delegation on is a
> matter of enabling the general-purpose subagent or passing one.

---

## 2. The general-purpose subagent — delegation without a subagent per task

This is the part that answers "I don't want to hand-build a subagent for every
task."

deepagents ships a **general-purpose subagent**. It:

- uses the **same model** as the main agent (unless overridden),
- has access to **all the same tools**,
- **inherits the main agent's skills**, and
- exists purely for **context isolation** — it has no specialised prompt.

The main agent delegates any messy multi-step job to it and gets a clean result
back. You define **nothing**. So "one subagent per task" is not the only model —
the general-purpose subagent is the catch-all worker, and for a lot of work it is
all you need.

Code-wise it is controlled on the **harness profile**, not per-call:

```python
from deepagents import GeneralPurposeSubagentProfile  # present in 0.7.15

# rename / re-prompt the built-in one:
GeneralPurposeSubagentProfile(...)
# turn it off entirely:
GeneralPurposeSubagentProfile(enabled=False)
```

> **Gap / nuance.** The docs say the general-purpose subagent is auto-added "by
> default". In our built agent it is **not currently active** (no `task` tool in
> the graph, confirmed above) — the active harness profile in our stack does not
> enable it. So to get delegation we either enable it on the profile or pass a
> subagent explicitly. This is worth knowing before assuming "it's already there".

---

## 3. Two ways to define a custom subagent

You reach for a *custom* subagent when you want a **specialised** worker — its own
prompt, a narrower tool set, a different model. Two forms, both real types in
0.7.15.

### 3a. `SubAgent` — the dictionary form (the common case)

`SubAgent` is a `TypedDict`. Verified fields in 0.7.15:

| field | required? | what it does |
|---|---|---|
| `name` | **yes** | the id the model passes to `task(subagent_type=...)`; also tags streaming/traces |
| `description` | **yes** | how the main agent decides *when* to delegate here — be specific |
| `system_prompt` | required for `isolated` | the subagent's instructions; does **not** inherit the parent's |
| `tools` | optional | overrides inherited tools **entirely** when set; keep minimal |
| `model` | optional | `"provider:model"` string or a chat-model object; omit to inherit |
| `middleware` | optional | extra middleware for this subagent only |
| `skills` | optional | skill source dirs; a custom subagent does **not** inherit skills unless you set this |
| `interrupt_on` | optional | per-tool human-in-the-loop (needs a checkpointer) |
| `permissions` | optional | filesystem permission rules |
| `response_format` | optional | structured output — parent gets JSON instead of prose |
| `mode` | optional | `"isolated"` (default) or `"fork"` — see §5 |

```python
researcher = {
    "name": "researcher",
    "description": "Searches the web and returns a cited summary. Use for any "
                   "question needing current facts.",
    "system_prompt": "You research. Search, open the top sources, cross-check, "
                     "and return a short summary with a URL for every claim.",
    "tools": [web_search, fetch_and_store, search_memory],   # narrowed on purpose
    "model": "amazon.nova-lite-v1:0",                        # cheaper for this job
}

agent = create_deep_agent(model=get_model(), subagents=[researcher], ...)
```

### 3b. `CompiledSubAgent` — wrap a whole LangGraph graph

When the subagent is itself a full graph (built with `create_agent` or the raw
graph API), wrap it. Verified fields: `name`, `description`, `runnable` (a
**compiled** graph, `.compile()` first), and optional `mode`.

```python
from deepagents import CompiledSubAgent

reviewer = CompiledSubAgent(name="reviewer", description="...", runnable=my_graph)
```

The one hard requirement: the graph's state must have a `messages` key.

---

## 4. `response_format` — get JSON back, not prose

Any subagent can set `response_format` (a Pydantic model or schema). When it
finishes, its result is **JSON-serialised and returned as the tool result** to the
parent, instead of free-form text. Use this when the parent needs to *process* the
result — feed it to another tool, score it, store it — rather than read it. This
is the clean way to make a subagent a reliable step in a pipeline.

---

## 5. Isolated vs forked — how much context the subagent starts with

`mode` on a `SubAgent` (or `CompiledSubAgent`) picks one of two:

| | `isolated` (default) | `fork` |
|---|---|---|
| what it sees | **only** the task description you pass | the parent's **full conversation + system prompt** |
| system prompt | you set it | inherited; setting one appends (and breaks prompt cache) |
| skills | you set them | not settable |
| can it call `task`? | yes | **no** — it must finish the work itself |
| best for | fresh focused work | *continuing* work the parent already started |

**How fork works, mechanically:** the fork does not get a new task description. It
gets the parent's own message history, with the delegating call removed and
replaced by a short "this is a continuation" preamble. Its answer comes back as a
normal tool result and the parent resumes. Because it reuses the parent's exact
prefix, it can reuse the parent's **prompt cache** — cheaper than starting cold.

Rule of thumb: **isolated** for "go find out X", **fork** for "you diagnosed the
bug, now go fix it".

---

## 6. Dynamic subagents — the real answer to "not one subagent per task"

This is the concept that matters most for your concern about manageability.

**Normal (static) delegation:** the model chooses *one* `task(...)` call at a
time. To review 40 files it must decide, 40 times, to call the reviewer.

**Dynamic subagents:** with an **interpreter** attached, the model instead writes
**JavaScript** that calls a built-in `task()` global in a loop — fanning the same
subagent across many items and combining the results in code:

```javascript
// what the MODEL writes and runs in the interpreter — not something you hand-wire
const files = await tools.glob("src/**/*.py");
const findings = await Promise.all(
  files.map(f => task({ description: `review ${f} for SQL injection`,
                        subagentType: "reviewer" }))
);
// then dedupe / synthesize in JS
```

So you configure **one** `reviewer` subagent, and the *agent* decides to run it 40
times. You are not writing a subagent per task, and you are not even writing the
fan-out — the model writes it, from the shape of the request. The docs list the
patterns this enables: classify-and-act, fan-out-and-synthesize, adversarial
verification (two subagents check each other), generate-and-filter, tournament,
loop-until-done.

`task()` takes `description`, `subagentType`, and optional `responseSchema` (when
set, you get a typed JS object back).

> **Gap (important).** Dynamic subagents need the **QuickJS interpreter
> middleware**, which is a separate package. In our install it is **not present** —
> `langchain_quickjs` is missing and there is no `code_interpreter` middleware
> module. So dynamic subagents are a **deliberate add-on we have not installed**,
> not something available today. Turning them on is: install the QuickJS package,
> add `CodeInterpreterMiddleware`, and have at least one subagent.

---

## 7. Async subagents — background work the supervisor doesn't block on

Everything above is **synchronous**: the main agent calls `task(...)` and *waits*.
Async subagents are the opposite — launch and keep going.

`AsyncSubAgent` verified fields: `name`, `description`, `graph_id` (required),
`url`, `headers` (optional). Note the shape: an async subagent is **not** a prompt
+ tools like `SubAgent` — it is a **pointer to a deployed graph** (an Agent
Protocol server), addressed by `graph_id`.

When async subagents are configured, `AsyncSubAgentMiddleware` gives the
supervisor **five tools**:

| tool | purpose |
|---|---|
| `start_async_task` | launch a background task, returns a task id immediately |
| `check_async_task` | status + result if done |
| `update_async_task` | send new instructions to a running task (interrupts + restarts it) |
| `cancel_async_task` | stop it |
| `list_async_tasks` | all tracked tasks with live status |

Two design details worth remembering:

- **Task ids live in their own state channel** (`async_tasks`), separate from the
  message history — deliberately, because deep agents compact message history when
  context fills, and ids in tool messages would be lost. The dedicated channel
  survives compaction.
- **Transport** is chosen by the `url` field: omit it for in-process (ASGI)
  co-deployment; set it for a remote HTTP Agent Protocol server (independent
  scaling, different team).

**Sync vs async in one line:** sync = "wait for the answer before continuing";
async = "kick it off, keep talking to the user, check back later".

> **Gap.** Async subagents require the subagents to be **deployed as Agent Protocol
> graphs** (registered in a `langgraph.json`, reachable in-process or over HTTP).
> We have no such deployment, so async is a future capability, documented here so
> the shape is understood, not something wired today.

---

## 8. Streaming and tracing — telling subagents apart

- **Streaming:** `stream.subagents` gives a handle per delegated task, each with
  `.name`, `.messages`, `.tool_calls`, `.output`, so a UI can show each subagent's
  progress separately. (Our dashboard streams the *main* agent via
  `stream_mode="messages"`; per-subagent streaming would build on this.)
- **Tracing:** every run a subagent produces is tagged with `lc_agent_name` in its
  metadata (e.g. `{'lc_agent_name': 'researcher'}`). In LangSmith you filter on
  that key to isolate one subagent's runs. The same value is how you tell, inside a
  shared tool, which agent called it.

---

## 9. How this maps onto our repo

| concept | our status |
|---|---|
| `task` tool / delegation | **off** — no subagent passed, so `SubAgentMiddleware` isn't attached |
| general-purpose subagent | present in the library, **not active** in our profile |
| custom `SubAgent` | available; none defined (only the `legislation_advice` *skill* exists, which is a different thing) |
| forked subagents | available (`mode: "fork"`); unused |
| dynamic subagents | **not installed** — needs the QuickJS interpreter package |
| async subagents | available in the library; needs an Agent Protocol deployment we don't have |
| streaming per subagent | our dashboard streams the main agent only |

**Skill vs subagent — do not confuse them.** A *skill* (`skills/*.md`, via
`SkillsMiddleware`) is instructions injected into *one* agent's prompt. A
*subagent* is a *separate* agent with its *own* context. The obligation gate
governs skills; it currently runs `after_agent` on the **main** agent, so if we
add subagents we will need to decide whether their answers pass back through the
gate too.

---

## 10. What this means for the "equip research properly" question

Two coherent ways to make research a real, managed capability, both avoiding
"a subagent per task":

1. **General-purpose subagent + a `web_research` skill.** Enable the built-in
   general-purpose subagent for context isolation, and put the research
   *procedure* (search, cross-check, cite) in a skill the main agent follows.
   Smallest step; no new subagent types.
2. **One `researcher` subagent + dynamic dispatch.** Define a single specialised
   `researcher` (narrow tools, research prompt, `response_format` for cited
   findings), and — once the QuickJS interpreter is installed — let the agent
   fan it out across many sources/questions from code. This is the scalable
   answer to "many independent units without hand-wiring each".

Either way the manageability worry is handled: you maintain **one** worker
definition (or none, with general-purpose), and delegation scales through the
`task` tool and dynamic dispatch rather than through a growing pile of
task-specific subagents.
