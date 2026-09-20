"""EAF middleware — empty on purpose.

deepagents supplies the middleware this platform needs, and per
`.kiro/steering/coding-standards.md` a component is written here only when
deepagents has none. Right now it has all of them:

    SkillsMiddleware          skills in the prompt, progressive disclosure
    FilesystemMiddleware      file tools
    SubAgentMiddleware        delegation
    MemoryMiddleware          long-term memory
    SummarizationMiddleware   context compaction AND tool-result offload
    RubricMiddleware          scored evaluation
    PatchToolCallsMiddleware  dangling tool calls

WHAT WAS HERE, AND WHY IT IS GONE. `ContentOverflowMiddleware` offloaded large
tool results to /workspace. It failed twice over:

  It was not a middleware. A plain class, not an `AgentMiddleware` subclass, so it
  had no `name` and its `wrap_tool_call(tool_name, result)` did not match the
  hook signature. `create_deep_agent` rejected it with AttributeError, which means
  the whole harness raised on every build and no turn had ever run through it.

  It was redundant. `SummarizationMiddleware` already offloads conversation
  history to the backend and clips oversized tool messages on the overflow path.

The ideas listed here as "future middleware" have upstream homes too, and should
be checked for before anything is written: a token budget belongs with
`SummarizationMiddleware`'s trigger, and injecting retrieved context belongs with
`MemoryMiddleware`.

BEFORE ADDING A MODULE HERE, answer in the PR: which upstream component did you
look for, and what specifically does it not do? The obligation gate
(`agent/gate.py`) is the standing example of a good answer — nothing in deepagents
enforces obligations outside the model.
"""
