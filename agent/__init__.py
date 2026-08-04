"""Enterprise Agent Framework.

A small, boring agent loop wrapped in the two things a personal-assistant agent
does not need and an enterprise one cannot ship without:

  skills       published by the business, one file per procedure — guidance the
               model reads, the tools it may use, and obligations the system
               enforces outside the model.
  boundaries   a user boundary at the edge, and an agent + tool + delegated-user
               boundary at every tool call.

The loop is deliberately commodity. All the leverage is in what reaches the
model's context and what is checked on the way out.
"""

__version__ = "0.0.1"
