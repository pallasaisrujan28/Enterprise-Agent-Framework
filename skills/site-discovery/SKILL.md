---
name: site-discovery
description: Getting data from a website or online service you have no tool or saved site recipe for (property portals, job boards, price or availability pages, any site's search results), learning how it serves that data, and saving a reusable recipe. Use when the user wants listings, prices or results from a named or described site, wants them tracked over time, or when a saved site recipe stopped working.
---

## When this applies

The user wants data that lives on a website, and none of your tools return it
directly. Examples: "find 2-bed flats in Hackney under £2,000", "watch this
shop's price", "what jobs does this company list". Not for a one-off fact
that web search answers in its snippets.

## Procedure

1. **Pin the request.** Write down the user's filters and the fields they
   want (for property: area, price, beds, type, and link). Ask only for a
   filter you cannot proceed without.

2. **Reuse before you rediscover.** List `/skills/` and look for a recipe
   named `site-<domain>` (for example `site-quotes-toscrape-com`). If one
   exists, read it and follow it. If following it fails (no rows, a changed
   shape, an error), treat it as stale and go to step 3.

3. **Delegate discovery, one site per task.** Call the `site-discovery`
   subagent with `task()`. Give it the site (or a description of the kind of
   site, if the user did not name one), the filters, and the fields. For
   several sites, start one task per site in parallel with the interpreter.
   If no `site-discovery` subagent exists, discovery is switched off
   (`AGENT_REA`). Use the `research` subagent and `fetch_url` instead, and
   tell the user that API discovery is not available.

4. **Read the SiteRecipe it returns.**
   - `ready`: the recipe was verified by direct reuse. Use its sample to
     answer.
   - `partial`: say what is unverified (its `unknowns`). Do not schedule it.
   - `blocked`: automated access is not permitted or not possible. Tell the
     user the reason and offer the `alternative`. For portals set to
     `email-alert`, that means: the user creates a saved search with email
     alerts on the site, and you read those alert emails with the Gmail tools.

5. **Check the result against the request** before you answer: every row
   meets every filter, and every row has a link. Remove rows that do not,
   and say how many you removed.

6. **Offer to save the recipe.** Only with the user's agreement, unlock
   `create_skill` with `find_tools` and save it as `site-<domain>` (dots
   become hyphens). Use the body template below. A saved recipe lets future
   requests and scheduled runs skip discovery.

7. **Recurring tracking needs a yes.** Never set up repeated checks without
   the user's explicit agreement, and only for a recipe with status `ready`
   and policy verdict `allow`.

## Recipe body template

```markdown
## Source
<origin> — access: <access_method> — policy: <verdict> (<reason>), checked <date>

## Request
<endpoint_template>
Parameters: <name> = <meaning> (e.g. <example>), one per line
Pagination: <how to page and when to stop>

## Response
Shape: <response_shape>
Map to fields: <user field> <- <path>, one per line

## Verify each run
- Call check_source_policy on the endpoint first; stop if not allow.
- Expect at least one row; every row has a link.
- If the shape differs from the one above, stop and rediscover with site-discovery.

## Known unknowns
<unknowns>
```

## What must be in the answer

- The source of every row (its link), and which site it came from.
- What was verified and what was not.
- When a site was blocked, the reason and the alternative, stated plainly.
  Never work around a block, a CAPTCHA or a login wall.
