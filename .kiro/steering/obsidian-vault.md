# Obsidian Documentation Vault

The project is readable as an **Obsidian vault** at `docs/vault/`. Open that folder as a vault and the graph view gives a navigable map of both the architecture and the codebase, instead of a single very long design document.

## Core Rule: The Vault Is Generated, Never Hand-Maintained

Vault notes are **derived artifacts**, produced by generators from two sources of truth:

| Vault content | Generated from | Generator |
| --- | --- | --- |
| Architecture notes — one per ADR, invariant, section, phase, correctness property | The spec design document | `scripts/gen_vault_docs.py` — **written** |
| Code map — one note per module, links mirroring imports | The source tree | `scripts/gen_vault_code.py` — **not written yet; there is no application code to map** |

```bash
python3 scripts/gen_vault_docs.py            # regenerate in place
python3 scripts/gen_vault_docs.py --check     # exit 1 if anything would change
```

**Reading the vault:** Obsidian does not browse the filesystem. Use *Open folder as vault* and select `docs/vault`. The entry point is `index.md`.

**Why generated and not written by hand.** A hand-maintained parallel vault is duplicated documentation, and duplicated documentation drifts. Within a few features the vault and the design document disagree, and neither is trustworthy. Derived artifacts cannot drift, because regenerating is the only way to change them.

Alternatives considered and rejected:
- **Hand-written vault notes** — rejected. Double maintenance, guaranteed drift, and the drift is silent.
- **Vault as the source of truth, design document compiled from it** — rejected. It fights the spec tooling that owns the design document, and it fragments a document that reviewers need to read linearly.
- **Vault generated at read time only, not committed** — rejected. You should be able to open the vault without running a build step.

Never edit a file under `docs/vault/` directly. Edit the design document or the source, then regenerate.

**Two enumerated exceptions, and they are enumerated in the generator itself rather than left to memory:**

| Path | Why it is exempt |
| --- | --- |
| `docs/vault/assets/` | Binary source material. No generator touches it under any circumstance. |
| `docs/vault/architecture/agent-tuning-loop.md` | Hand-authored. It analyses an externally provided reference **image**, which has no representation in the design document to generate from. |

Anything else appearing under a generator-owned directory is deleted on the next run. That is the intended behaviour: it is what makes a removed design section disappear from the vault instead of lingering.

## Structure

```
docs/vault/
  index.md                     # entry point; links to each section hub
  architecture/
    adr/ADR-001-....md         # one note per ADR
    components/....md          # one note per component
    phases/phase-1.md          # one note per delivery phase
    properties/property-01.md  # one note per correctness property
  code/
    <module-path>.md           # one note per module, links follow imports
  features/
    <feature-name>.md          # one note per shipped feature
```

## Conventions

- **Link by alias, never by filename.** Generated filenames embed the section title, so a title edit would silently break every link that used the stem. Each note declares a short stable alias in frontmatter — `ADR-008`, `Property 27`, `§2.10`, `Phase 5`, `§2` — and links target the alias: `[[ADR-008]]`, `[[§2.10]]`. Back-links are most of the value: opening an ADR note shows every section and property that touches it.
- **Frontmatter on every note** — `title`, `type` (`adr` / `principle` / `section` / `topic` / `phase` / `property` / `hub` / `index`, plus `module` once the code map exists), `tags`, `aliases` where the note has one, `source` (the file it was generated from), and `generated` (timestamp). `type` and `tags` are what make the graph view filterable instead of a hairball.
- **Cross-references are linkified automatically, and never inside a code fence.** The generator rewrites `ADR-nnn`, `§N.M`, `§N`, `Property N`, `Phase N`, and `P1`–`P16` into wikilinks in prose only. Mermaid, Python, and pseudocode fences are left byte-identical — rewriting a diagram label into a wikilink would corrupt the diagram.
- **One concept per note.** A note that covers three ADRs is one node in the graph and defeats the purpose.
- **Link density is the point.** An ADR links to the components it constrains, the properties that enforce it, and the phase that delivers it. An isolated note is a note nobody will find.
- **Code notes link along real imports**, so the graph shows actual dependency structure. If the generated graph shows a cycle, that is a real circular import and a defect to fix, not a rendering artifact.

## When the Vault Is Regenerated

- **In CI on every pull request**, via `gen_vault_docs.py --check`. If regenerating produces a diff that is not committed, the build fails. That is what keeps the vault honest.
  > **Not wired up yet.** CI today is deliberately three gates — lint/format and vulnerability scanning — and nothing else. This check is the next entry on the gate-growth table in the design document's §4.4, not a fourth gate added quietly. Run it locally before opening a pull request until it is wired.
- **On every feature**, as part of the same pull request as the feature — consistent with the documentation rule in the git workflow standards.
- Regeneration is idempotent: running it twice with no source change produces no diff. A generator that rewrites timestamps on every run makes the check useless, so `generated` timestamps are only updated when content actually changes.

## What Belongs in the Vault and What Does Not

**Belongs:** architecture, decisions and their rationale, component responsibilities, delivery phases, correctness properties, the code dependency map, and per-feature notes describing what shipped and why.

**Does not belong:** secrets or credentials of any kind, raw tenant data, PII in any form including examples, and anything already better served by the spec documents themselves. The vault is a *reading surface*, not a second system of record.
