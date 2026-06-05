# Standalone Hermes Package

This package intentionally contains only Hermes-relevant ARS material:

- `SKILL.md`: Hermes registration entry point.
- `MODE_REGISTRY.md`: ARS mode registry.
- `deep-research/`: research source skill.
- `academic-paper/`: paper writing source skill.
- `academic-paper-reviewer/`: peer-review source skill.
- `academic-pipeline/`: full workflow source skill.
- `shared/`: shared referenced materials.
- Per-skill `agents/`, `references/`, and `templates/` directories inside each
  source skill.

It intentionally excludes Claude Code packaging, alias skills, symlinks, GitHub
workflow files, repository tests, and development tooling.
