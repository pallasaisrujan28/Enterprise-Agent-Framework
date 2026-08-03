---
title: Vault Assets
type: reference
---

# Vault Assets

Hand-placed binary assets — diagrams, screenshots, reference images — referenced by vault notes.

**Generators never touch this directory.** The rest of `docs/vault/` is generated from the spec design document and the source tree (see `.kiro/steering/obsidian-vault.md`), so anything hand-placed there would be clobbered on regeneration. This directory is the exception, and it is the only one.

## Conventions

- Kebab-case filenames matching the note that references them: `agent-tuning-loop.png` is referenced by `architecture/agent-tuning-loop.md`.
- Prefer a **mermaid reproduction in the note** over an image where the diagram is structural. Mermaid diffs, images do not — a reviewer can see what changed in a mermaid edit and cannot in a re-exported PNG. Keep the original image alongside as provenance.
- No PII, no credentials, and no tenant data in any image. A screenshot of a real session is a compliance incident.
