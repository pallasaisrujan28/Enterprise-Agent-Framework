"""The memory ontology — what Graphiti should extract, and how to label it.

Without this, every node was the generic `Entity` and extraction minted facts
about whatever was in the text: "The Assistant greets the User", "The Eiffel
Tower is taller than Big Ben", "Amazon sells ESSEX GLAM shoes". Graphiti's own
guidance (help.getzep.com/graphiti/core-concepts/custom-entity-and-edge-types):
define entity and edge types as Pydantic models whose DOCSTRINGS are the
descriptions the extractor reads, keep attributes optional and atomic, and keep
an ("Entity", "Entity") fallback so an unmapped pair still gets an edge.

Field names must not collide with EntityNode's own (uuid, name, group_id,
labels, created_at, summary, attributes, name_embedding) — Graphiti rejects them.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# ── entity types ──────────────────────────────────────────────────────────────


class Person(BaseModel):
    """A specific human: the user, or someone in their life or work (a colleague,
    recruiter, manager, friend, family member). Not the AI assistant."""

    role: str | None = Field(None, description="Job title or relationship to the user")
    email: str | None = Field(None, description="Email address, if stated")


class Organization(BaseModel):
    """A company, employer, university, government body, or other institution."""

    sector: str | None = Field(None, description="Industry or kind of organization")


class Project(BaseModel):
    """A named piece of work, product, or initiative the user is involved in."""

    status: str | None = Field(None, description="e.g. active, paused, shipped")


class Opportunity(BaseModel):
    """A job offer, application, visa or immigration case, or similar process the
    user is going through."""

    stage: str | None = Field(None, description="e.g. applied, offered, accepted, approved")


class Preference(BaseModel):
    """A stated like, dislike, habit, or standing instruction of the user."""

    category: str | None = Field(None, description="e.g. food, travel, work style, tooling")


class Place(BaseModel):
    """A city, country, address, or venue relevant to the user."""


ENTITY_TYPES: dict[str, type[BaseModel]] = {
    "Person": Person,
    "Organization": Organization,
    "Project": Project,
    "Opportunity": Opportunity,
    "Preference": Preference,
    "Place": Place,
}

# ── edge types ────────────────────────────────────────────────────────────────


class WorksAt(BaseModel):
    """A person is employed by, joining, or contracting for an organization."""

    title: str | None = Field(None, description="Job title")


class CommunicatesWith(BaseModel):
    """A person is in correspondence with another person (email, meetings, calls)."""

    topic: str | None = Field(None, description="What the correspondence is about")


class InvolvedIn(BaseModel):
    """A person or organization takes part in a project or opportunity."""

    capacity: str | None = Field(None, description="e.g. candidate, recruiter, sponsor")


class Prefers(BaseModel):
    """The user holds a preference, habit, or standing instruction."""


class LocatedIn(BaseModel):
    """A person or organization is based in, or moving to, a place."""


EDGE_TYPES: dict[str, type[BaseModel]] = {
    "WorksAt": WorksAt,
    "CommunicatesWith": CommunicatesWith,
    "InvolvedIn": InvolvedIn,
    "Prefers": Prefers,
    "LocatedIn": LocatedIn,
}

# Which edge types may connect which entity types. ("Entity", "Entity") is the
# documented fallback: an unmapped pair still gets a generic RELATES_TO fact.
EDGE_TYPE_MAP: dict[tuple[str, str], list[str]] = {
    ("Person", "Organization"): ["WorksAt", "InvolvedIn"],
    ("Person", "Person"): ["CommunicatesWith"],
    ("Person", "Project"): ["InvolvedIn"],
    ("Person", "Opportunity"): ["InvolvedIn"],
    ("Organization", "Opportunity"): ["InvolvedIn"],
    ("Person", "Preference"): ["Prefers"],
    ("Person", "Place"): ["LocatedIn"],
    ("Organization", "Place"): ["LocatedIn"],
    ("Entity", "Entity"): [],
}

# Read by BOTH Graphiti's node and edge extraction prompts.
EXTRACTION_INSTRUCTIONS = (
    "This is a conversation between the USER and their AI assistant. Extract only "
    "durable facts worth remembering in a month about the user and the people, "
    "organizations, projects, opportunities, preferences and places in their life. "
    "Do NOT extract: the assistant itself or its actions, tools, errors or "
    "capabilities; greetings or small talk; general world knowledge or trivia; "
    "product listings or search results the user merely browsed. Refer to the "
    "user as 'User' unless their name is stated. When writing an edge, use entity "
    "names EXACTLY as they appear in the extracted entity list."
)
