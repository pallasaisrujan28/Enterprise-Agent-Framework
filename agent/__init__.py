"""Enterprise Agent Framework.

A small, boring agent loop wrapped in the two things a personal-assistant agent
does not need and an enterprise one cannot ship without:

  rules        published by the business, in two forms from one file — guidance
               the model reads, and obligations the system enforces.
  boundaries   a user boundary at the edge, and an agent + tool + delegated-user
               boundary at every tool call.

The loop is deliberately commodity. All the leverage is in what reaches the
model's context and what is checked on the way out.
"""

__version__ = "0.0.1"
