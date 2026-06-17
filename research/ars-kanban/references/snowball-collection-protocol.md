# Snowball / Saturation Collection Protocol

## When to Use This Mode

- The user explicitly requests "芋づる式" (potato-vine pulling) exhaustive collection.
- The research topic has a well-bounded seed corpus (e.g., 2–6 special issues, a conference proceedings, a known set of canonical works).
- Keyword-driven OpenAlex searches are likely to miss key theoretical works (common in philosophy, meta-theory, and interdisciplinary debates).
- The Phase 1 deliverable specifies this mode in `c_mode.collection_mode: "snowball"`.

## Phase 1 Prerequisites

Before the Phase 2-1 worker starts, Phase 1 must have defined:

1. **Seed corpus**: exact list of papers (DOIs or stable identifiers) that form Layer 0.
2. **Relevance domain keywords**: terms that define what counts as "in-scope" for Layer 2 filtering (e.g., "philosophy of information", "social epistemology", "library and information science theory", "domain analysis").
3. **Estimated corpus size**: rough count of expected Layer 1 records (for feasibility check).

These MUST be written to the Phase 1 artifact (e.g., `phase1_deliverables.md`) so
the Phase 2-1 worker can read them.

## Execution Steps

### Step 1: Identify Seed Papers (Layer 0)

For each paper in the seed corpus, collect:
- DOI (preferred) or stable URL
- Title, authors, year, journal/venue
- PDF or HTML full text (for reference-list extraction)

When the seed papers are from 1–5 special issues, use OpenAlex
`works?filter=primary_location.source.id:<venue-id>,publication_year:<year>`
to batch-retrieve all papers in the issue, then manually verify completeness
against the issue's table of contents.

**Pitfall**: OpenAlex indexing of special issues is sometimes incomplete.
Older special issues (pre-2010) may have poor coverage. Verify against the
publisher's TOC and supplement manually.

### Step 2: Extract Reference Lists (Layer 0 → Layer 1)

For each seed paper, extract its list of cited references. Sources:
- **OpenAlex `works/{id}/references`** — returns DOIs of referenced works when available.
- **CrossRef** — `works/{doi}/references` endpoint for DOI-based ref lists.
- **Semantic Scholar** — `paper/{id}/references` with richer metadata (if API key available).
- **Manual extraction** — when the paper lacks structured reference data, the full-text PDF may need reference-list extraction. This is labour-intensive; batch by seed corpus size.

**Pitfall**: Reference coverage varies across APIs. OpenAlex's `references` field
is populated only when the source work has a DOI and the references also have
DOIs. CrossRef coverage is broader but still incomplete. Semantic Scholar has
the best reference coverage but requires an API key for bulk usage. **Cross-verify
between at least two sources** for the most important seed papers.

### Step 3: Resolve Layer 1 Records

For each unique reference from Step 2:

1. **Primary**: OpenAlex `works?filter=doi:<doi>` — retrieves full metadata,
   abstract, OA status, OA URLs.
2. **Fallback**: CrossRef `works/{doi}` — metadata and abstract when OpenAlex
   is missing them.
3. **Secondary enrichment**: Semantic Scholar `paper/{id}` — citation count,
   influential citation count, TLDR (if available).

Store each resolved record with:
```json
{
  "doi": "10.xxxx/xxxxx",
  "title": "...",
  "authors": ["..."],
  "year": 2020,
  "abstract": "...",
  "oa_status": "gold/hybrid/bronze/green/closed",
  "oa_url": "https://...",
  "layer": 1,
  "source_seed": ["<seed_paper_doi>"],
  "relevance_score": null,
  "zotero_key": null
}
```

**Deduplication**: Many references will be cited by multiple seed papers.
Deduplicate on DOI before resolution to avoid redundant API calls.

### Step 4: Relevance Filtering and Layer 2 Expansion

**Layer 2 expansion is OPTIONAL and MUST be filtered.** Do not expand every
Layer 1 record. Use a tiered approach:

| Tier | Condition | Action |
|:----:|-----------|--------|
| A | Layer 1 record is about the core topic (score 8–10) | Expand to Layer 2 (extract its references) |
| B | Layer 1 record is related (score 6–7) | Expand selectively — only if it cites or is cited by Tier A works |
| C | Layer 1 record is peripheral (score 1–5) | Do NOT expand |

Apply the relevance domain keywords from Phase 1 as an automated pre-filter,
then manually verify Tier B decisions if time permits.

### Step 5: Score and Classify for Zotero

**Use a 0–100 relevance scale with 10-step buckets.** A narrow 1–10 scale causes
bucket collapse: a single tier can absorb 50%+ of the corpus (e.g. 929 of 1,752
records all landing in `31-40`). The 0–100 scale gives enough granularity to
create meaningful review-priority ranges.

**Scoring strategy** (base tier + modifiers):

| Base tier | Condition | Base score |
|-----------|-----------|------------|
| T1 | Direct Floridi PI-LIS foundation engagement | 85 |
| T2 | Substantive PI-LIS engagement | 72 |
| T3 | Competing LIS theoretical foundations (SE/DA/philosophy of science) | 62 |
| T4 | LIS theory-methodology / paradigm relation | 52 |
| T5 | Broader LIS theory / metatheory | 42 |
| T6 | PI/Floridi general context (not necessarily LIS-specific) | 38 |
| T7 | PI/information concept context | 28 |
| T8 | LIS background (library, information science, etc.) | 14–24 |
| T9 | Peripheral / general reference | 10 |

**Modifiers** (add to base):
- Seed paper bonus: +5
- Methodology bridge present: +3
- Citation impact: +1 (5+ cites) to +5 (200+ cites)
- Has abstract: +2, has DOI: +1, is OA: +1
- Penalties: non-LIS −5, missing abstract −2

**Caps and floors**: min 1, max 100. Seed floor: 50. Filter for Zotero: score ≥ 20.

**Zotero bucket mapping** (`relevance:NN` tag + subcollection):

| Bucket | Score range | Reading priority |
|---|---|---|
| `91-100` | 91–100 | Definitive core / seed anchors |
| `81-90` | 81–90 | Core foundation papers |
| `71-80` | 71–80 | Strong engagement |
| `61-70` | 61–70 | Direct debate / competing frameworks |
| `51-60` | 51–60 | LIS theoretical foundations |
| `41-50` | 41–50 | Theory-methodology / metatheory |
| `31-40` | 31–40 | Broader theory / information concept context |
| `21-30` | 21–30 | LIS background / PI context |
| `11-20` | 11–20 | Peripheral / borderline |
| `01-10` | 1–10 | Very peripheral (filtered out unless seed) |

**Zotero actions per record**:
1. Create item (if not already in Zotero)
2. Set tag `relevance:NN`
3. Set field `issue` (Japanese UI: 「番号」) to the numeric score string **only when**
   the item type supports `issue` (e.g. `journalArticle`). For `book` and other types,
   the score lives in tags only — patching `issue` on unsupported types returns 400.
4. Remove direct membership in the project parent collection
5. Add to the correct relevance-range child collection

**Historical pitfall (narrow 1–10 scoring):** Earlier runs used a 1–10 scale where
most records clustered at score 4, causing 929 items to collapse into `31-40`.
Always use 0–100 for snowball corpus work.

### Step 6: Report and Block

Write the following artifacts to the phase workspace:

| File | Contents |
|------|----------|
| `literature_records.json` | Full record list with scores, deduplicated |
| `literature_stats.json` | Counts by layer, source, OA status, score range |
| `snowball_report.md` | Narrative: coverage gaps, notable omissions, expansion decisions |
| `zotero_export.json` | Zotero item mapping (DOI → Zotero key) |

Then block the Phase 2-1 kanban task with `review-required` reason:
"Snowball collection complete — N records in Zotero. Please add paywalled
full-text PDFs to the project collection, then unblock to promote Phase 2-2."

## Common Pitfalls

| Pitfall | Impact | Prevention |
|---------|--------|------------|
| Narrow 1–10 relevance scale | 50%+ corpus collapses into one bucket; no reading priority granularity | Use 0–100 base-tier + modifier scoring with explicit 10-step bucket mapping |
| Unfiltered Layer 2 expansion | 10×–40× record explosion | Mandatory relevance domain filter; score records before deciding to expand |
| Seed paper reference lists incomplete | Layer 1 gaps | Cross-verify seed paper refs from multiple APIs; note missing refs in report |
| OpenAlex index gaps for old seed papers | Layer 0 incomplete | Manually verify against publisher TOC; supplement with publisher website |
| Dedup failure on variant DOIs | Duplicate Zotero items | Normalise DOIs to lowercase; use Zotero's own dedup after export |
| Semantic Scholar rate limit (429) during Layer 2 | Partial expansion | Batch in small groups; track which seed→Layer1→Layer2 chains are complete |
| Relevance scoring inconsistency | Misplaced Zotero classification | Apply scoring rubric BEFORE looking at citation counts (halo effect) |

## Examples

### Floridi LIS Theory-Practice Relation

Seed corpus: 5 special issues (Library Trends 2004/2015/2024,
Journal of Documentation 2005/2018) — ~60–80 papers.
Layer 1: ~1,000–2,000 unique references.
Layer 2 (after relevance filtering): ~300–600 additional records.
Relevance domain keywords: "philosophy of information", "LIS theory",
"social epistemology", "domain analysis", "information concept",
"Floridi", "Hjørland", "Bates".
