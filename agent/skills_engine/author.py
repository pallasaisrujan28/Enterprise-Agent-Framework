"""create_skill — let the agent author a reusable SKILL.md at runtime.

Procedural learning, waku-style. When the user teaches a repeatable workflow
("here's how I want you to do a weekly review…"), the agent writes it as a new
skill file under the skills directory. Next time the harness is built,
SkillsMiddleware discloses it in the catalogue and the agent reads it on demand
(progressive disclosure) — so a taught workflow persists instead of being
forgotten when the thread ends.

The file is the unit of persistence: skills/<slug>/SKILL.md, with frontmatter the
Agent Skills spec requires (name must match the directory, lowercase-hyphen). We
refuse to overwrite an existing skill and refuse invalid names, so authoring can
never clobber a shipped skill.

CLUSTER NOTE: like SOUL, this writes a repo-relative file, which persists locally
but not across ephemeral pods. Point AGENT_SKILLS_DIR at a mounted volume (or a
workspace path) for durable authoring in a deploy.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from langchain_core.tools import tool

# Agent Skills spec: 1-64 chars, lowercase alphanumeric + single hyphens, no
# leading/trailing/double hyphen. Must match the parent directory name.
_SLUG = re.compile(r"^[a-z0-9](?:[a-z0-9]|-(?!-)){0,62}[a-z0-9]$")


def skills_dir() -> Path:
    return Path(os.getenv("AGENT_SKILLS_DIR") or (Path(__file__).parents[1] / "skills"))


def _slugify(name: str) -> str:
    s = name.strip().lower().replace("_", "-").replace(" ", "-")
    s = re.sub(r"-+", "-", s)  # collapse runs of hyphens
    return s.strip("-")


def write_skill(name: str, description: str, body: str) -> str:
    """Create skills/<slug>/SKILL.md. Returns a status the tool relays."""
    slug = _slugify(name)
    if not _SLUG.match(slug):
        return "Skill name must be a short slug like 'weekly-review' (lowercase letters, digits, single hyphens)."
    if not description.strip():
        return "A skill needs a one-line description (what it does and when to use it)."
    if not body.strip():
        return "A skill needs a body — the step-by-step instructions."

    dest = skills_dir() / slug / "SKILL.md"
    if dest.exists():
        return f"A skill named '{slug}' already exists — pick another name."

    text = f"---\nname: {slug}\ndescription: {description.strip()}\n---\n\n{body.strip()}\n"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    return (
        f"Created skill '{slug}'. It will be available (disclosed in the skills "
        f"catalogue) from the next turn, and will trigger on: {description.strip()}"
    )


@tool
def create_skill(name: str, description: str, body: str) -> str:
    """Save a reusable skill (a workflow the user taught you) so you can repeat it.

    Only call this after the user agrees to save the workflow. `name` is a short
    slug (e.g. "weekly-review"); `description` is one line covering what it does
    AND when to use it (include trigger words); `body` is the step-by-step
    instructions in markdown. The skill persists as a file and is disclosed to you
    in future turns.
    """
    return write_skill(name, description, body)
