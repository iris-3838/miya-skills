---
name: ars-kanban
description: ARS (Academic Research System) phase workers that run via Hermes Kanban. Implements Phase 1-6 pipeline with Socratic dialogue mode and Wording-Pattern Advisory.
version: 0.1.0
metadata:
  hermes:
    tags: [academic, research, kanban, phase-worker, socratic]
    category: academic
---

# ARS Kanban — Hermes Port of Claude Code ARS

Implements the ARS (Academic Research System) 6-phase pipeline as Hermes
Kanban tasks. Ported from the Claude Code ARS deep-research skill
(see `references/hermes-porting-glossary.md` in `deep-research`).

## What's Here

| File | Role |
|------|------|
| `scripts/phase_worker.py` | Single-phase dispatcher (phase 1-6). Reads body JSON, calls mentor, writes `phase_result.json`, upgrades passport, syncs KB. |
| `scripts/init_board.py` | Bootstrap: spawn the 6 ARS phase tasks onto a Kanban board. Supports `--mode socratic` for Phase 1. |
| `scripts/passport_layer.py` | Material-passport validation/upgrade (Phase 5 enforcement). |
| `scripts/kb_sync.py` | Persist phase result into the llm-kb wiki (best-effort). |
| `scripts/socratic_phase.py` | Socratic dialogue mode for Phase 1. Block/unblock pattern for multi-turn user interaction. Persists state to `socratic_state.json`. |
| `scripts/wording_patterns.py` | Wording-Pattern Advisory (Kong #257). Detects AI-typical research-question shells; suppressed by domain-native vocabulary. |
| `tests/` | 99 unittest cases across 6 test modules. |

## Phase 1 Modes

- `mode: "full"` — single delegate_task, no user interaction
- `mode: "socratic"` — multi-turn Socratic dialogue with the user via Kanban block/unblock

### Socratic Mode Flow

```
init_board --mode socratic "topic"
  ↓
Phase 1 task (mode=socratic) created on board
  ↓
phase_worker.run_phase_task detects mode=socratic
  ↓
run_socratic_phase() executes one turn
  ├─ state.awaiting_user == True
  │   └─ read user comment → run Wording-Pattern Advisory → mentor delegate
  ├─ mentor returns question → save state, comment, block
  └─ user unblocks + replies → next invocation resumes from state.json
  ↓
convergence signals S1-S4 met (3+) OR max turns (40) reached
  ↓
write phase_result.json + complete Kanban task
```

### Wording-Pattern Advisory

Runs on every user response during Socratic mode. Detects 20 surface
phrasing patterns (WP01-WP20) such as "the impact of X on Y", "factors
affecting Y", "the role of technology in enhancing Y". Suppressed when
the user's RQ contains domain-native vocabulary (LIS terms, theorist
names, methodology signals).

When triggered, posts a kanban comment with the original ARS advisory
template. One advisory per pattern per session.

## Phase Routing

| Phase | Name | Default Agents |
|-------|------|----------------|
| 1 | Scoping | research_question, research_architect, devils_advocate |
| 2 | Investigation | bibliography, source_verification |
| 3 | Analysis | synthesis, devils_advocate |
| 4 | Composition | report_compiler |
| 5 | Review | editor_in_chief, ethics_review, devils_advocate |
| 6 | Revision | report_compiler |

## Running

```bash
# Bootstrap a board for a topic
python scripts/init_board.py "Bates vs Hjørland information concepts" --mode socratic

# (Alternative) Socratic mode
python scripts/init_board.py "Topic" --mode socratic

# Run a single phase task
python scripts/phase_worker.py <task_id>
python scripts/phase_worker.py <task_id> --dry-run
```

## Tests

```bash
cd tests && python -m unittest discover -v
# 99 tests, all green
```

## Differences from Upstream Claude Code ARS

| Aspect | Claude Code ARS | Hermes Kanban ARS |
|--------|------------------|-------------------|
| Cross-session Socratic | No (single session) | Yes (state.json + block/unblock) |
| Delegation | PreToolUse hook | `delegate_task` from phase_worker |
| Layer enforcement | Tool hook | Per-turn state validation |
| Stagnation detection | Mentor LLM | Not yet (planned) |
| Intent (exploratory/goal) | Mentor LLM | Not yet (planned) |
| Wording-Pattern Advisory | Mentor LLM | Python pre-processor (wording_patterns.py) |
| Performance per turn | 1 LLM call | 1 LLM call + ~500ms overhead |

See `references/hermes-porting-glossary.md` in the deep-research skill
for the full porting analysis.

## Versioning

This port targets upstream ARS v3.11.0 (sync commit `0024947`).
