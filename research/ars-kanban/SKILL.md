---
name: ars-kanban
description: ARS (Academic Research System) phase workers that run via Hermes Kanban. Implements Phase 1-6 pipeline with Socratic dialogue mode, C mode deep-research acquisition loop, and Wording-Pattern Advisory.
version: 0.3.0
metadata:
  hermes:
    tags: [academic, research, kanban, phase-worker, socratic, zotero]
    category: academic
---

# ARS Kanban — Hermes Port of Claude Code ARS

Implements the ARS (Academic Research System) 6-phase pipeline as Hermes
Kanban tasks. Ported from the Claude Code ARS deep-research skill
(see `references/hermes-porting-glossary.md` in `deep-research`).

## What's Here

| File | Role |
|------|------|
| `scripts/phase_worker.py` | Single-phase dispatcher (phase 1-6, plus C mode `2-1`/`2-2`). Reads body JSON, calls mentor, writes `phase_result.json`, upgrades passport, syncs KB. |
| `scripts/init_board.py` | Bootstrap: spawn ARS phase tasks onto a Kanban board. Supports `--mode socratic` and `--mode c`. |
| `scripts/c_literature_acquisition.py` | C mode Phase 2-1 engine: OpenAlex search, CrossRef abstract fallback, Zotero collection creation/item mapping. Does not bypass paywalls. |
| `scripts/passport_layer.py` | Material-passport validation/upgrade (Phase 5 enforcement). |
| `scripts/kb_sync.py` | Persist phase result into the llm-kb wiki (best-effort). |
| `scripts/socratic_phase.py` | Socratic dialogue mode for Phase 1. Block/unblock pattern for multi-turn user interaction. Persists state to `socratic_state.json`. |
| `scripts/wording_patterns.py` | Wording-Pattern Advisory (Kong #257). Detects AI-typical research-question shells; suppressed by domain-native vocabulary. |
| `tests/` | 125 unittest cases across 8 test modules. |

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
  └─ Phase 2-2: Investigation (Zotero Corpus)
Phase 3: Analysis
Phase 4: Composition
Phase 5: Review
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

## Phase Routing

| Phase | Name | Default Agents |
|-------|------|----------------|
| 1 | Scoping | research_question, research_architect, devils_advocate |
| 2 | Investigation | bibliography, source_verification |
| 2-1 | Literature Acquisition | bibliography, source_verification |
| 2-2 | Investigation (Zotero Corpus) | bibliography, source_verification, synthesis |
| 3 | Analysis | synthesis, devils_advocate |
| 4 | Composition | report_compiler |
| 5 | Review | editor_in_chief, ethics_review, devils_advocate |
| 6 | Revision | report_compiler |

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
# 125 tests, all green
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
