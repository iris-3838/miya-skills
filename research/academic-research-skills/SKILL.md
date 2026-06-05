---
name: academic-research-skills
description: Academic Research Skills for Hermes. Routes research, paper writing, peer review, and full research-to-publication workflows.
version: 3.10.1
metadata:
  hermes:
    tags: [academic, research, writing, review, pipeline]
    category: academic
---

# Academic Research Skills for Hermes

This folder is a standalone Hermes skill package. Install by moving or copying
this directory only:

```text
~/.hermes/skills/academic-research-skills/
```

No symlinks, alias skill folders, Claude Code plugin files, GitHub workflow files,
or test code are required for Hermes registration.

## Read Order

1. `SKILL.md` — this Hermes entry point.
2. `MODE_REGISTRY.md` — canonical mode list.
3. The selected source skill:
   `deep-research/SKILL.md`, `academic-paper/SKILL.md`,
   `academic-paper-reviewer/SKILL.md`, or `academic-pipeline/SKILL.md`.
4. Any `agents/`, `references/`, `templates/`, or `shared/` files referenced by
   that selected source skill.

## Routing

- Full research-to-publication workflow: `academic-pipeline/SKILL.md`.
- Research, literature review, systematic review, fact-checking: `deep-research/SKILL.md`.
- Paper planning, drafting, revision, formatting, citation checks, disclosure: `academic-paper/SKILL.md`.
- Peer review, methodology review, re-review, calibration: `academic-paper-reviewer/SKILL.md`.

When materials span multiple phases and the target workflow is unclear, ask the
user which workflow they want before dispatching.
