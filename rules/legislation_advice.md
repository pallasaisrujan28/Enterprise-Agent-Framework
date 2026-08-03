---
name: legislation_advice
description: Answering questions about UK statute.
obligations:
  - must_cite: {contains: legislation.gov.uk, version_pinned: true}
  - must_ask_when_missing: {fields: [as_at_date]}
  - must_disclose: {when: unapplied_effects_exist, disclose: unapplied_effects}
---

## When this applies

Any question about what UK legislation says, requires, permits or prohibits.

## Procedure

1. **Establish the date.** Legislation answers are only true as at a date. If
   the user has not given one and there is no default for this tenant, ask.
   Do not assume "today" — a compliance question is often about the law as it
   stood when something happened.

2. **Resolve the item.** Use `leg_resolve_identifier`. If it reports
   `AMBIGUOUS`, ask the user which item they meant. Do not pick the most
   recent one.

3. **Find the provisions before reading them.** Use `leg_get_contents` with a
   text match to learn which provisions are relevant. Never fetch a whole Act
   to find out which three sections matter — some Acts run past 10,000 pages.

4. **Read the provisions at the date**, not the current version.

5. **Check the amendment history.** Use `leg_traverse_amendments`. Report
   whether anything amended the provision, when it came into force, and for
   which territorial extent.

6. **Check for unapplied effects.** An amendment can be in force but not yet
   written into the published text. Where that is true, say so — the text you
   read is not the law as at that date.

## What must be in the answer

- The provision, quoted or closely paraphrased.
- A citation URI that includes the date segment, so the version is unambiguous.
- Any outstanding unapplied effects, stated plainly.
- Where the traversal was incomplete, say that it was incomplete.

## What this rule does not cover

Case law, HMRC or regulator practice, and anything requiring a view on how a
court would decide. Those are a different agent's work — hand back a re-route
rather than answering from general knowledge.
