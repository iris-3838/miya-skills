---
name: ars-kanban
description: ARS (Academic Research System) phase workers that run via Hermes Kanban. Implements a 10-stage pipeline (1, 2, 2.5, 3, 3', 4, 4.5, 5, 5.5, 6) with mandatory integrity gates, two-stage review, Socratic dialogue, C mode deep-research acquisition loop, and Wording-Pattern Advisory.
version: 0.4.0
metadata:
  hermes:
    tags: [academic, research, kanban, phase-worker, socratic, zotero, integrity-gate, traceability]
    category: academic
---

# ARS Kanban — Hermes Port of Claude Code ARS

Implements the ARS (Academic Research System) pipeline as Hermes Kanban tasks.
The standard pipeline is now **10 stages**: 1 (Scoping), 2 (Investigation),
2.5 (Integrity), 3 (Analysis), 3' (Re-Review), 4 (Composition), 4.5 (Final
Integrity), 5 (Review), 5.5 (Process Summary), 6 (Revision). C mode expands
Stage 2 into `2-1` (Literature Acquisition) and `2-2` (Zotero Corpus
Investigation), inserting the integrity gate at `2.5` after `2-2`.

Ported from the Claude Code ARS deep-research skill (see
`references/hermes-porting-glossary.md` in `deep-research`). Current upstream
target: **ARS v3.15.0**.

## What's Here

| File | Role |
|------|------|
| `scripts/phase_worker.py` | Single-stage dispatcher (phases 1-6, 2.5, 3', 4.5, 5.5, plus C mode `2-1`/`2-2`). Reads body JSON, calls mentor, runs integrity gates for 2.5/4.5, writes `phase_result.json`, upgrades passport, syncs KB. |
| `scripts/init_board.py` | Bootstrap: spawn ARS stage tasks onto a Kanban board. Supports `--mode socratic` and `--mode c`. |
| `scripts/integrity_check.py` | 7-mode AI failure checklist for mandatory integrity gates (Stage 2.5 + 4.5). M1-M7, Lu 2026. |
| `scripts/traceability_matrix.py` | Schema 11 R&R Traceability Matrix for Stage 3' re-review. Tracks author claims vs reviewer comments. |
| `scripts/c_literature_acquisition.py` | C mode Stage 2-1 engine: OpenAlex search, CrossRef abstract fallback, Zotero collection creation/item mapping. Does not bypass paywalls. |
| `scripts/passport_layer.py` | Material-passport validation/upgrade (Schema 9 v2). Supports claim verification report, trust-chain frontmatter, literature corpus, reset boundary, collaboration depth history. |
| `scripts/kb_sync.py` | Persist phase result into the llm-kb wiki (best-effort). |
| `scripts/socratic_phase.py` | Socratic dialogue mode for Stage 1. Block/unblock pattern for multi-turn user interaction. Persists state to `socratic_state.json`. |
| `scripts/wording_patterns.py` | Wording-Pattern Advisory (Kong #257). Detects AI-typical research-question shells; suppressed by domain-native vocabulary. |
| `tests/` | unittest cases across 9 test modules. |

## 10-Stage Pipeline

The default full pipeline creates ten Kanban tasks:

```text
Stage 1:  Scoping
Stage 2:  Investigation
Stage 2.5: Integrity Gate (mandatory, non-skippable)
Stage 3:  Analysis
Stage 3':  Re-Review
Stage 4:  Composition
Stage 4.5: Final Integrity Gate (mandatory, zero-tolerance)
Stage 5:  Review
Stage 5.5: Process Summary
Stage 6:  Revision
```

### Mandatory Integrity Gates

- **Stage 2.5** (`integrity_check.py`, mode=`pre_review`): runs after Stage 2
  (or after C mode `2-2`). Samples 30% of claims (min 10) and checks the 7
  canonical AI failure modes from Lu 2026 (M1-M7). Fails → block for fixes,
  max 3 rounds.
- **Stage 4.5** (`integrity_check.py`, mode=`final_check`): runs after Stage 4
  revision. Verifies **100%** of claims with zero-tolerance; any `SUSPECTED`
  mode must be cleared or user-overridden before the pipeline advances.

Both gates post a Kanban comment with `integrity_gate_report` metadata and call
`kanban.block()` when failing.

### Two-Stage Review

- **Stage 3** (`academic-paper-reviewer`): first-round review package (EIC +
  R1/R2/R3 + Devil's Advocate) produces an editorial decision and revision
  roadmap.
- **Stage 3'** (`traceability_matrix.py`): re-review after Stage 4 revision.
  Builds a Schema 11 traceability matrix pairing each reviewer comment with the
  author's claim, verification status, and residual issue. Emits a new decision
  (Accept / Minor / Major). The hard revision-loop cap is **max 2 total loops**
  across Stage 4 + Stage 4'.

### Process Summary

**Stage 5.5** emits a process record and AI self-reflection report after the
final review. It runs after Stage 5 and before Stage 6 (final formatting-level
revision if needed).

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

## C Mode: Deep Research Acquisition Loop

`mode: "c"` keeps the existing ARS numbering, but expands Phase 2 into a
hierarchical deep-research loop:

```text
Phase 1: Scoping
Phase 2: Investigation (Deep Research)
  ├─ Phase 2-1: Literature Acquisition
  ├─ Phase 2-2: Investigation (Zotero Corpus)
  └─ Phase 2.5: Integrity Gate (mandatory)
Phase 3: Analysis
Phase 3': Re-Review
Phase 4: Composition
Phase 4.5: Final Integrity Gate (mandatory)
Phase 5: Review
Phase 5.5: Process Summary
Phase 6: Revision
```

### Rationale

The standard B/full mode has strong research and critical-analysis ability, but
cannot access paywalled full texts by principle. C mode therefore splits deep
research into:

1. **AI-automated metadata/OA acquisition** — collect OA papers and metadata.
2. **Human full-text acquisition** — the user manually accesses institutional
   databases (e.g. ProQuest/LISA) and attaches paywalled PDFs to Zotero.
3. **Zotero-corpus investigation** — the agent analyzes the enriched Zotero
   collection and may request another acquisition loop if gaps remain.

### Phase 2-1: Two Collection Modes

Phase 2-1 supports two literature acquisition strategies. The task body
`c_mode.collection_mode` field selects which mode a worker should follow;
if absent, default to **keyword search** (the `collect_records_for_preview()`
engine). The Phase 1 Scoping deliverable should specify which mode is
appropriate for the research question.

#### Keyword-Search Mode (default)

Uses OpenAlex / CrossRef / J-STAGE / CiNii keyword queries driven by the
task body's `topic` string. Best for:
- Broad topical surveys where the literature is defined by subject area
- Topics with well-established keyword vocabularies
- First-pass acquisition to establish a baseline corpus

#### Snowball / Saturation Collection Mode (alternative)

Uses the seed corpus (defined in Phase 1) as the starting point, then
recursively follows their cited-reference lists outward. Best for:
- Well-bounded debates with a known seed corpus (e.g., a set of special issues)
- Topics where keyword search misses key literature (philosophy, theory debates)
- Exhaustive coverage requirements ("芋づる式" / potato-vine pulling, the user's
  instruction to scroll through every referenced work systematically)

When this mode is chosen, **do NOT run `collect_records_for_preview()`**;
execute the snowball protocol instead (see `references/snowball-collection-protocol.md`).

##### Layer Protocol

```
Layer 0 (Seed): The corpus defined in Phase 1 (e.g., 5 special issues)
    ↓ extract all cited references
Layer 1: Resolve every reference via OpenAlex (preferred) or CrossRef (fallback)
         → full metadata + abstract + OA status
         → tag with layer:1, source_seed:<paper_id>
    ↓ for each Layer 1 paper, extract its cited references
Layer 2: Resolve and retrieve — but FILTER by relevance first
         (domain: LIS, PI, epistemology, social epistemology, domain analysis)
         → tag with layer:2
    ↓
Zotero: Assign relevance:N score → classify into subcollections
```

Layer 2 relevance filtering is **mandatory** — unfiltered second-degree
snowball can explode from ~2K to ~40K records. Use the scoring criteria
in `references/snowball-collection-protocol.md` to decide which Layer 1
papers are worth expanding.

##### Relevance Scoring for Zotero Subcollections

| Score | Criteria |
|:-----:|----------|
| 10 | Direct engagement with the core RQ (e.g., Floridi PI as LIS foundation) |
| 8-9 | Substantive engagement with the debate or its key concepts |
| 6-7 | Related theoretical literature (competing frameworks, methodology) |
| 4-5 | Contextual literature (history, adjacent philosophy, meta-theory) |
| 1-3 | Peripheral (cited for background only, not directly relevant) |

Assign each item a `relevance:N` Zotero tag AND the Japanese UI
**「番号」** field (API `issue`) with the same score. Then place it in a
direct child collection by range (`01-10`, `11-20`, ...), removing direct
membership in the project parent (as described in the Zotero Layout section
below).

### Phase 2-1: Literature Acquisition Sources

Implemented engine status:

| Component | Status |
|---|---|
| OpenAlex search | Implemented (`search_openalex`) |
| OpenAlex abstract reconstruction | Implemented |
| CrossRef DOI fallback for missing abstracts | Implemented |
| Zotero `deep-research/<project>` collection creation | Implemented |
| Zotero metadata item creation | Implemented |
| Paywalled full-text download | Explicitly not implemented |
| J-STAGE collector | Implemented (`parse_jstage_listview` + `search_jstage_recent`) |
| CiNii Research collector | Implemented (`parse_cinii_opensearch` via OpenSearch JSON API) |
| Semantic Scholar collector | Planned, optional API key |

Sources are configured in every C mode `2-1` task body under
`c_mode.literature_sources`:

| Source | Role | API key | Use |
|---|---|---:|---|
| OpenAlex | `primary-international` | No | International LIS journals; metadata, abstracts, OA status, OA URLs |
| CrossRef | `doi-metadata-abstract-fallback` | No | DOI metadata and abstract fallback when OpenAlex abstracts are empty |
| J-STAGE | `primary-japanese-diamond-oa` | No | Japanese LIS journals; metadata, abstracts, Diamond OA PDFs |
| CiNii Research | `japanese-supplement` | No | Domestic literature not covered by J-STAGE; metadata and repository links |
| Semantic Scholar | `citation-network-supplement` | Optional (`SEMANTIC_SCHOLAR_API_KEY`) | Citation graph, references/citations, TLDR, author metadata |

Contract-sensitive sources such as LISTA/LISA/ProQuest are **not scraped**.
Instead, Phase 2-1 registers metadata and blocks for human full-text acquisition.

### Zotero Layout

```text
Zotero Library/
  deep-research/
    <project-slug>/
      01-10/
      11-20/
      21-30/
      31-40/
      ...
```

For C-mode/additional literature, assign each item a `relevance:N` tag and the Zotero Japanese UI **「番号」** field (API `issue`) with the same numeric score. Then place the item in exactly one direct child collection by relevance range (`01-10`, `11-20`, `21-30`, ...), removing direct membership in the project parent but preserving unrelated collection memberships. This keeps priority visible for Phase 2-2: higher ranges are higher-priority review candidates.

The project path is stored as:

```json
"c_mode": {
  "zotero_collection_path": "deep-research/<project-slug>",
  "loop_count": 0,
  "max_loops": 3
}
```

### Phase 2-2: Investigation (Zotero Corpus)

Phase 2-2 reads the Zotero project collection, analyzes OA PDFs plus manually
attached full texts, and detects gaps. If important gaps remain, it can request
a loop back to Phase 2-1; otherwise the workflow proceeds to Phase 3.

### C Mode Example Prompt

```text
C modeで「Bates vs Hjørland の情報概念対立」についてdeep researchしたい。

init_board.pyを --mode c で起動して、Phase 2を2-1/2-2に分けてください。
2-1ではOpenAlex, CrossRef, J-STAGE, CiNii Researchで書誌・abstract・OA全文を集め、
Zoteroの deep-research/bates-vs-hjrland に登録してください。
Semantic Scholar keyがあれば引用ネットワーク補完にも使ってください。

ペイウォール本文は迂回せず、書誌だけ登録して人手取得待ちでblockしてください。
私がProQuest等でPDFをZoteroに追加したらunblockするので、2-2でZotero corpusを分析してください。
```

## Stage Routing

| Stage | Name | Default Agents | Notes |
|-------|------|----------------|-------|
| 1 | Scoping | research_question, research_architect, devils_advocate | Socratic/full mode |
| 2 | Investigation | bibliography, source_verification | |
| 2-1 | Literature Acquisition | bibliography, source_verification | C mode only |
| 2-2 | Investigation (Zotero Corpus) | bibliography, source_verification, synthesis | C mode only |
| 2.5 | Integrity | integrity_verification_agent, state_tracker_agent | Mandatory gate |
| 3 | Analysis | synthesis, devils_advocate | |
| 3' | Re-Review | field_analyst_agent, eic_agent, editorial_synthesizer_agent | Traceability matrix |
| 4 | Composition | report_compiler | |
| 4.5 | Final Integrity | integrity_verification_agent, state_tracker_agent | Mandatory gate |
| 5 | Review | editor_in_chief, ethics_review, devils_advocate | |
| 5.5 | Process Summary | state_tracker_agent, pipeline_orchestrator_agent | |
| 6 | Revision | report_compiler | Terminal revision |

## Running

```bash
# Bootstrap a board for a topic
python scripts/init_board.py "Bates vs Hjørland information concepts" --mode socratic

# C mode: Phase 2 becomes 2-1/2-2 deep-research acquisition loop
python scripts/init_board.py "Bates vs Hjørland information concepts" --mode c

# Run a single phase task
python scripts/phase_worker.py <task_id>
python scripts/phase_worker.py <task_id> --dry-run
```

For C-mode bootstrap details, see `references/c-mode-init-board-pitfalls.md`.

### Phase 2-1 Query Pitfall

`c_literature_acquisition.collect_records_for_preview()` currently sends the task body's `topic` string directly to OpenAlex/CiNii. Mixed Japanese+English topics or highly discursive Japanese prompts can return 0 records even when obvious English literature exists. For C mode literature acquisition, use an English search-oriented topic when possible, or manually seed Phase 2-1 with targeted English queries and write the curated results to the phase workspace's `literature_records.json` / `literature_preview.md` before blocking for Zotero selection. Semantic Scholar may be listed in task policy and an API key may exist, but the built-in collector is still planned rather than fully integrated.

### Board Slug Length Pitfall

`init_board.py` derives the Kanban board slug directly from the full `topic`. Hermes Kanban board slugs are limited to 64 characters, so long detailed research questions can fail during board/task creation. Use a short English topic for `init_board.py` (for example, `Bates-Hjorland direct information concept controversy`) and store the detailed research question, inclusion/exclusion criteria, and search strategy in Phase 1 artifacts or Kanban comments. If a long topic run fails with empty/non-JSON task creation output, retry with a shorter topic slug rather than reusing the discursive prompt as the topic.

### Expanded Citation-Corpus Runs

When expanding a Phase 2-1 corpus beyond direct search results (e.g., seed papers + Semantic Scholar citing papers), keep the run artifacts in the phase workspace (`literature_records_expanded.json`, `expanded_collection_summary.md`, `expanded_collection_stats.json`, `zotero_export_expanded.json`) and then complete the Kanban task with those paths in metadata. Use the Zotero skill venv for exports (`/opt/data/workspace/miya-skills/research/zotero/.venv/bin/python`) because system Python may not have `pyzotero`. Semantic Scholar's `/citations` endpoint does **not** accept `citingPaper.tldr`; use citation-safe fields such as `citingPaper.paperId,title,authors,year,venue,abstract,externalIds,isOpenAccess,openAccessPdf,citationCount,referenceCount,influentialCitationCount,url`. API 429s can occur on large citation walks; record partial counts in `expanded_collection_stats.json` and retry only missing offsets to avoid duplicating Zotero items.

## Tests

```bash
cd tests && python -m unittest discover -v
# 160 tests, all green
```

## Differences from Upstream Claude Code ARS

| Aspect | Claude Code ARS | Hermes Kanban ARS |
|--------|------------------|-------------------|
| Pipeline stages | 10 stages with 2 mandatory integrity gates | 10 stages with 2 mandatory integrity gates |
| Two-stage review | Stage 3 + Stage 3' (Schema 11) | Stage 3 + Stage 3' (`traceability_matrix.py`) |
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

This port targets upstream ARS **v3.15.0**.
