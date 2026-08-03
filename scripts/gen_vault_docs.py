#!/usr/bin/env python3
"""Generate the Obsidian architecture vault from the spec design document.

The vault under ``docs/vault/architecture`` is a DERIVED artifact. This script is
the only thing that writes it. See ``.kiro/steering/obsidian-vault.md`` for why:
a hand-maintained parallel vault drifts from the design document within a few
features, and the drift is silent.

Usage
-----
    python3 scripts/gen_vault_docs.py            # regenerate in place
    python3 scripts/gen_vault_docs.py --check    # exit 1 if anything would change (CI gate)

Idempotency
-----------
The ``generated`` frontmatter timestamp is only advanced when a note's body
actually changes. A generator that rewrites timestamps on every run makes the
``--check`` gate useless, because every run produces a diff.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
import sys
from pathlib import Path
from typing import NamedTuple

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE = REPO_ROOT / ".kiro/specs/enterprise-agent-framework/design.md"
VAULT = REPO_ROOT / "docs/vault"
ARCH = VAULT / "architecture"

# Directories this script owns outright: pruned and rewritten on every run.
OWNED_DIRS = (
    ARCH / "adr",
    ARCH / "sections",
    ARCH / "properties",
    ARCH / "phases",
    ARCH / "principles",
    ARCH / "topics",
)

# Hand-authored notes the generator must never touch. This is a deliberate,
# enumerated exception to the "vault is generated" rule: this note analyses an
# externally-provided reference artifact (an image), which has no representation
# in the design document to generate from.
HAND_AUTHORED = (ARCH / "agent-tuning-loop.md",)

# docs/vault/assets is never touched under any circumstance.

FENCE = re.compile(r"^\s*```")

RE_H2 = re.compile(r"^## (.+?)\s*$")
RE_H3 = re.compile(r"^### (.+?)\s*$")

RE_ADR = re.compile(r"^ADR-(\d+[a-z]?): (.+)$")
RE_PROPERTY = re.compile(r"^Property (\d+): (.+)$")
RE_PHASE = re.compile(r"^Phase (\d+) [—-] (.+)$")
RE_SECTION = re.compile(r"^(\d+)\.(\d+) (.+)$")
RE_NUMBERED_H2 = re.compile(r"^(\d+)\. (.+)$")
RE_PRINCIPLE = re.compile(r"^- \*\*(P\d+) [—-] (.+?)\*\*\s*(.*)$")

# Small keyword -> tag table. Tags are what make the Obsidian graph filterable
# instead of a hairball, so they are derived rather than left empty.
TAG_KEYWORDS = (
    ("skill", "skills"),
    ("cache", "kv-cache"),
    ("prefix", "kv-cache"),
    ("compact", "compaction"),
    ("context", "context-engineering"),
    ("pii", "pii"),
    ("guardrail", "guardrails"),
    ("tenan", "multi-tenancy"),
    ("tool", "tools"),
    ("graph", "graph"),
    ("retriev", "retrieval"),
    ("rag", "retrieval"),
    ("retry", "failure-handling"),
    ("failure", "failure-handling"),
    ("kubernetes", "deployment"),
    ("deploy", "deployment"),
    ("local", "local-first"),
    ("docker", "local-first"),
    ("terraform", "infrastructure"),
    ("storage", "storage"),
    ("session", "session-state"),
    ("model", "model-routing"),
    ("eval", "evals"),
    ("improvement", "improvement-layer"),
    ("polic", "authz"),
    ("access", "authz"),
    ("classif", "classification"),
    ("scal", "scaling"),
    ("observab", "observability"),
    ("silent", "compaction"),
)


class Block(NamedTuple):
    level: int  # 2 or 3
    heading: str
    body: list[str]
    parent: str | None  # heading text of the enclosing H2, for H3 blocks


class Note(NamedTuple):
    path: Path
    title: str
    kind: str
    tags: list[str]
    body: list[str]
    # Short stable name(s) the note can be linked by. Filenames embed the title,
    # so a title edit would break every hand-written link that used the stem;
    # aliases are what make `[[ADR-008]]` survive a rename.
    aliases: list[str] = []


def slugify(text: str, max_len: int = 64) -> str:
    text = re.sub(r"[`*_\[\]()]", "", text)
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    if len(text) <= max_len:
        return text
    cut = text[:max_len]
    return cut.rsplit("-", 1)[0] if "-" in cut else cut


def derive_tags(kind: str, title: str) -> list[str]:
    haystack = title.lower()
    tags = [kind]
    for keyword, tag in TAG_KEYWORDS:
        if keyword in haystack and tag not in tags:
            tags.append(tag)
    return tags


def parse_blocks(lines: list[str]) -> list[Block]:
    """Split the document into H2 and H3 blocks, ignoring headings inside fences.

    Fence tracking is not optional: the design document embeds Python and
    pseudocode fences whose comment lines begin with ``#``, and a naive split
    would treat them as headings.
    """
    blocks: list[Block] = []
    in_fence = False
    current: Block | None = None
    parent_h2: str | None = None

    for line in lines:
        if FENCE.match(line):
            in_fence = not in_fence
            if current:
                current.body.append(line)
            continue

        if not in_fence:
            m2 = RE_H2.match(line)
            if m2:
                current = Block(2, m2.group(1), [], None)
                blocks.append(current)
                parent_h2 = m2.group(1)
                continue
            m3 = RE_H3.match(line)
            if m3:
                current = Block(3, m3.group(1), [], parent_h2)
                blocks.append(current)
                continue

        if current:
            current.body.append(line)

    return blocks


def parse_principles(blocks: list[Block]) -> list[tuple[str, str, str]]:
    """Extract (id, summary, detail) for each P-numbered invariant."""
    out: list[tuple[str, str, str]] = []
    for block in blocks:
        if not block.heading.startswith("Guiding Principles"):
            continue
        in_fence = False
        for line in block.body:
            if FENCE.match(line):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            m = RE_PRINCIPLE.match(line)
            if m:
                out.append((m.group(1), m.group(2).strip(), m.group(3).strip()))
    return out


def classify(block: Block) -> tuple[str, str, str | None]:
    """Return (kind, note_stem, key) for a H3 block."""
    h = block.heading
    m = RE_ADR.match(h)
    if m:
        return "adr", f"ADR-{m.group(1)}-{slugify(m.group(2))}", "ADR-" + m.group(1)
    m = RE_PROPERTY.match(h)
    if m:
        return "property", f"property-{m.group(1)}", m.group(1)
    m = RE_PHASE.match(h)
    if m:
        return "phase", f"phase-{m.group(1)}", m.group(1)
    m = RE_SECTION.match(h)
    if m:
        stem = f"{m.group(1)}-{m.group(2)}-{slugify(m.group(3))}"
        return "section", stem, f"{m.group(1)}.{m.group(2)}"
    return "topic", slugify(h), None


class Linker:
    """Rewrites cross-references into Obsidian wikilinks.

    One combined pattern and one pass, so a substitution can never be
    re-processed by a later rule.
    """

    def __init__(self) -> None:
        self.adr: dict[str, str] = {}
        self.prop: dict[str, str] = {}
        self.phase: dict[str, str] = {}
        self.section: dict[str, str] = {}
        self.toplevel: dict[str, str] = {}
        self.principle: dict[str, str] = {}
        self.pattern = re.compile(
            r"(?P<adr>\bADR-\d+[a-z]?\b)"
            r"|(?P<section>§\d+\.\d+)"
            r"|(?P<top>§\d+\b)"
            r"|(?P<prop>\bProperty \d+\b)"
            r"|(?P<phase>\bPhase \d+\b)"
            r"|(?P<principle>(?<![A-Za-z0-9])P\d{1,2}(?![0-9A-Za-z]))"
        )

    def _link(self, target: str, label: str, current: str) -> str:
        if target == current or target == label == current:
            return label
        if target == label:
            return f"[[{target}]]"
        return f"[[{target}|{label}]]"

    def apply(self, text: str, current_stem: str) -> str:
        def repl(m: re.Match[str]) -> str:
            token = m.group(0)
            if m.group("adr"):
                target = self.adr.get(token)
            elif m.group("section"):
                target = self.section.get(token[1:])
            elif m.group("top"):
                target = self.toplevel.get(token[1:])
            elif m.group("prop"):
                target = self.prop.get(token.split()[1])
            elif m.group("phase"):
                target = self.phase.get(token.split()[1])
            else:
                target = self.principle.get(token)
            if not target:
                return token
            return self._link(target, token, current_stem)

        return self.pattern.sub(repl, text)

    def apply_lines(self, lines: list[str], current_stem: str) -> list[str]:
        out: list[str] = []
        in_fence = False
        for line in lines:
            if FENCE.match(line):
                in_fence = not in_fence
                out.append(line)
                continue
            out.append(line if in_fence else self.apply(line, current_stem))
        return out


def trim(lines: list[str]) -> list[str]:
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def body_before_subsections(block: Block, blocks: list[Block]) -> list[str]:
    """An H2 note keeps only its own intro; its H3 children become their own notes."""
    return trim(list(block.body))


def build_notes(lines: list[str]) -> list[Note]:
    blocks = parse_blocks(lines)
    h3_blocks = [b for b in blocks if b.level == 3]
    h2_blocks = [b for b in blocks if b.level == 2]

    linker = Linker()
    staged: list[tuple[Block, str, str, Path, str]] = []

    for block in h3_blocks:
        kind, stem, key = classify(block)
        subdir = {
            "adr": "adr",
            "property": "properties",
            "phase": "phases",
            "section": "sections",
            "topic": "topics",
        }[kind]
        alias = ""
        if kind == "adr" and key:
            alias = key  # ADR-008
            linker.adr[key] = alias
        elif kind == "property" and key:
            alias = f"Property {key}"
            linker.prop[key] = alias
        elif kind == "phase" and key:
            alias = f"Phase {key}"
            linker.phase[key] = alias
        elif kind == "section" and key:
            alias = f"§{key}"  # §2.10
            linker.section[key] = alias
        staged.append((block, kind, stem, ARCH / subdir / (stem + ".md"), alias))

    # A top-level §N resolves to whichever H2 contains the N.x subsections, so the
    # unnumbered "## Architecture" heading still answers to §2 without special-casing.
    h2_stems: dict[str, str] = {}
    h2_alias: dict[str, str] = {}
    for block in h2_blocks:
        h2_stems[block.heading] = slugify(block.heading)
    for block in h2_blocks:
        m = RE_NUMBERED_H2.match(block.heading)
        if m:
            linker.toplevel[m.group(1)] = f"§{m.group(1)}"
            h2_alias[block.heading] = f"§{m.group(1)}"
    for block in h3_blocks:
        m = RE_SECTION.match(block.heading)
        if m and block.parent and m.group(1) not in linker.toplevel:
            linker.toplevel[m.group(1)] = f"§{m.group(1)}"
            h2_alias[block.parent] = f"§{m.group(1)}"

    principles = parse_principles(blocks)
    for pid, _summary, _detail in principles:
        linker.principle[pid] = pid

    notes: list[Note] = []

    for block, kind, stem, path, alias in staged:
        current = alias or stem
        body = linker.apply_lines(trim(list(block.body)), current)
        header = [f"# {linker.apply(block.heading, current)}", ""]
        if block.parent:
            header += [f"Part of [[{h2_stems[block.parent]}|{block.parent}]].", ""]
        notes.append(
            Note(
                path,
                block.heading,
                kind,
                derive_tags(kind, block.heading),
                header + body,
                [alias] if alias else [],
            )
        )

    for block in h2_blocks:
        stem = h2_stems[block.heading]
        alias = h2_alias.get(block.heading, "")
        children = [(b.heading, s) for b, _k, s, _p, _a in staged if b.parent == block.heading]
        body = linker.apply_lines(body_before_subsections(block, blocks), alias or stem)
        listing: list[str] = []
        if children:
            listing = ["", "## In this section", ""]
            listing += [f"- [[{s}|{h}]]" for h, s in children]
        notes.append(
            Note(
                ARCH / (stem + ".md"),
                block.heading,
                "hub",
                derive_tags("hub", block.heading),
                [f"# {block.heading}", ""] + body + listing,
                [alias] if alias else [],
            )
        )

    for pid, summary, detail in principles:
        body = [f"# {pid} — {summary}", ""]
        principles_hub = slugify("Guiding Principles (Invariants)")
        body += ["Part of [[{}|Guiding Principles]].".format(principles_hub), ""]
        if detail:
            body += linker.apply_lines([detail], pid)
        notes.append(
            Note(
                ARCH / "principles" / (pid + ".md"),
                f"{pid} — {summary}",
                "principle",
                derive_tags("principle", summary + " " + detail),
                body,
                [pid],
            )
        )

    notes.append(build_index(notes))
    return notes


def build_index(notes: list[Note]) -> Note:
    def group(kind: str) -> list[Note]:
        return sorted((n for n in notes if n.kind == kind), key=lambda n: n.path.name)

    body = [
        "# Enterprise Agent Framework — Architecture Vault",
        "",
        "Generated from the spec design document. **Do not edit anything under "
        "`architecture/` by hand** — edit the design document and regenerate "
        "(`python3 scripts/gen_vault_docs.py`).",
        "",
        "**Start here:** [[the-anatomy-of-an-agent-read-this-before-2-1|The Anatomy of an Agent]] "
        "lays out agent, skills, loading, execution, and tools in one pass.",
        "",
    ]
    sections = (
        ("Guiding principles (invariants)", "principle"),
        ("Architecture decisions", "adr"),
        ("Sections", "section"),
        ("Topics", "topic"),
        ("Delivery phases", "phase"),
        ("Correctness properties", "property"),
        ("Document hubs", "hub"),
    )
    for label, kind in sections:
        items = group(kind)
        if not items:
            continue
        body += [f"## {label}", ""]
        body += [f"- [[{n.path.stem}|{n.title}]]" for n in items]
        body += [""]
    body += [
        "## Not generated here",
        "",
        "- [[agent-tuning-loop]] — hand-authored; analyses an externally provided "
        "reference image, which has no source in the design document.",
        "- `assets/` — binary source material. Never touched by any generator.",
        "- A code map (`code/`) arrives with `scripts/gen_vault_code.py` once there "
        "is a source tree to map. There is no application code yet.",
        "",
    ]
    return Note(VAULT / "index.md", "Architecture Vault", "index", ["index"], body)


def render(note: Note, generated: str) -> str:
    tags = ", ".join(note.tags)
    front = [
        "---",
        'title: "{}"'.format(note.title.replace('"', "'")),
        f"type: {note.kind}",
        f"tags: [{tags}]",
    ]
    if note.aliases:
        # Obsidian resolves [[ADR-008]] through this, which is why generated links
        # use the short alias instead of the long title-derived filename.
        front.append("aliases: [{}]".format(", ".join(f'"{a}"' for a in note.aliases)))
    front += [
        "source: .kiro/specs/enterprise-agent-framework/design.md",
        f"generated: {generated}",
        "---",
        "",
    ]
    return "\n".join(front + note.body).rstrip() + "\n"


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    meta: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ": " in line:
            k, v = line.split(": ", 1)
            meta[k.strip()] = v.strip()
    return meta, text[end + 5 :]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="do not write; exit 1 if regenerating would change anything",
    )
    args = parser.parse_args()

    if not SOURCE.exists():
        print(f"source design document not found: {SOURCE}", file=sys.stderr)
        return 2

    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    notes = build_notes(lines)

    # dt.timezone.utc, not dt.UTC — this script runs under the system python,
    # which may be older than 3.11.
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()  # noqa: UP017
    planned: dict[Path, str] = {}

    for note in notes:
        existing = note.path.read_text(encoding="utf-8") if note.path.exists() else None
        stamp = now
        if existing is not None:
            old_meta, old_body = split_frontmatter(existing)
            _, new_body = split_frontmatter(render(note, now))
            if old_body == new_body and "generated" in old_meta:
                # Body unchanged: keep the old timestamp so --check stays meaningful.
                stamp = old_meta["generated"]
        planned[note.path] = render(note, stamp)

    stale: list[Path] = []
    for owned in OWNED_DIRS:
        if owned.exists():
            for path in owned.rglob("*.md"):
                if path not in planned:
                    stale.append(path)
    for path in ARCH.glob("*.md"):
        if path not in planned and path not in HAND_AUTHORED:
            stale.append(path)

    changed = [
        p for p, text in planned.items() if not p.exists() or p.read_text(encoding="utf-8") != text
    ]

    if args.check:
        if changed or stale:
            print("vault is out of date; run: python3 scripts/gen_vault_docs.py", file=sys.stderr)
            for path in sorted(changed):
                print(f"  would write  {path.relative_to(REPO_ROOT)}", file=sys.stderr)
            for path in sorted(stale):
                print(f"  would delete {path.relative_to(REPO_ROOT)}", file=sys.stderr)
            return 1
        print("vault is up to date (%d notes)" % len(planned))
        return 0

    for path in stale:
        path.unlink()
    for owned in OWNED_DIRS:
        if owned.exists() and not any(owned.rglob("*")):
            shutil.rmtree(owned)
    for path, text in planned.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            path.write_text(text, encoding="utf-8")

    print(
        "wrote %d notes (%d changed, %d removed) to %s"
        % (len(planned), len(changed), len(stale), VAULT.relative_to(REPO_ROOT))
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
