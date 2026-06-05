# Academic Research Skills — Agent Entry Point

This folder is the standalone Hermes package for Academic Research Skills.
Hermes should start here or at `SKILL.md`.

## Read Order

1. `AGENTS.md` — this package entry point.
2. `MODE_REGISTRY.md` — single source of truth for ARS modes.
3. `SKILL.md` — Hermes root skill entry point.
4. The target source skill's `SKILL.md` in one of:
   `deep-research/`, `academic-paper/`, `academic-paper-reviewer/`,
   `academic-pipeline/`.
5. Any referenced `references/`, `templates/`, `agents/`, and `shared/` files.

## Harness Boundaries

- This directory is the Hermes-only package surface.
- Do not add Claude Code packaging, alias skill folders, symlinks, CI files, tests,
  or development tooling to this package.

## Routing Discipline

Use clarification before dispatching ambiguous cross-phase materials. In Hermes,
implement clarification through the `clarify` tool or by asking the user directly.

Routing summary:

- Full research-to-publication workflow: `academic-pipeline`.
- Research, literature review, fact-checking: `deep-research`.
- Paper drafting, planning, revision, formatting, disclosure: `academic-paper`.
- Peer review, methodology review, re-review, calibration: `academic-paper-reviewer`.
- Ambiguous cross-phase materials: ask for clarification before dispatching.
