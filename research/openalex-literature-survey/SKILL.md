---
name: openalex-literature-survey
description: Survey academic venues (journals, conferences) via OpenAlex API — source metadata, topic distribution, OA status, recent papers, and periodic cron-based collection.
category: research
trigger: |
  User asks to survey a journal or conference's publication themes.
  User asks about OA status or topic distribution for a venue.
  User wants periodic collection of new papers from specific venues.
  User asks about literature trends in a specific field.
  User name-drops a specific academic journal or conference series as a potential publication target.
  User says "バックナンバー" or "back-issue" or "chronological survey" regarding journals.
  User says "全件" or "all papers" or "全部内容まで見て" — wants exhaustive coverage, not keywords.
  User says "文献に忠実な記述" or "faithful description" — output preference signal.
---

# OpenAlex Literature Survey

Use the **OpenAlex API** (`api.openalex.org`) to survey academic journal and conference venues. OpenAlex is free, needs no API key, and allows ~10 req/sec — far more generous than Semantic Scholar or Dimensions.

## Core Workflow

### 1. Find a journal/conference source ID

OpenAlex indexes academic sources (journals, conference proceedings, repositories). Find one by name:

```
GET https://api.openalex.org/sources?search=Journal+of+Documentation&per_page=5&select=id,display_name,works_count,type,is_oa
```

Returns: `id` (e.g. `S10082577`), `display_name`, `works_count`, `type` (journal/conference/repository), `is_oa`.

**Don't stop at the first hit** — verify `works_count` and `type` to distinguish the journal from individual issues or years.

### 2. Get source metadata + topics

```
GET https://api.openalex.org/sources/{SOURCE_ID}?select=display_name,works_count,cited_by_count,oa_works_count,is_oa,is_in_doaj,apc_usd,homepage_url,issn_l,counts_by_year,topics
```

Key fields:
- `oa_works_count / works_count` → OA percentage
- `apc_usd` → article processing charge (if hybrid)
- `topics` → list of `{display_name, count}` sorted by paper count
- `counts_by_year` → yearly publication volume
- `is_oa` → is the entire journal open access?
- `is_in_doaj` → registered in Directory of Open Access Journals

### 3. Query recent papers

```
GET https://api.openalex.org/works
  ?filter=primary_location.source.id:{SOURCE_ID},publication_year:2024|2025|2026
  &sort=publication_date:desc
  &per_page=25
  &select=id,title,authorships,publication_date,publication_year,open_access,primary_location,cited_by_count,type,doi,abstract_inverted_index
```

**Filter patterns:**
- Single year: `publication_year:2025`
- Multiple: `publication_year:2024|2025|2026`
- Date range: `from_publication_date:2025-01-01`
- OA only: add `,is_oa:true`
- By type: `,type:article` or `,type:review`

**Select fields:**
- `open_access` → `{is_oa, oa_status, oa_url}` for OA info
- `abstract_inverted_index` → reconstruct with Python (see pitfalls)
- `authorships` → `[{author: {display_name}, institutions: [...]}]`
- `primary_location.source` → venue display name
- `cited_by_count` → citation count (good proxy for impact)

### 4. Reconstruct abstracts from inverted index

OpenAlex stores abstracts as an **inverted index** (word→position list), not plain text. Reconstruct in Python:

```python
def reconstruct_abstract(inverted_index):
    if not inverted_index:
        return ""
    word_positions = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort()
    return " ".join(word for _, word in word_positions)
```

### 5. When OpenAlex data is incomplete — scrape OA journal sites directly

When OpenAlex's OA rate or metadata seems stale, or you need per-issue content (page numbers, full author lists, issue-level themes), scrape OA journal sites directly.

**J-Stage (Japanese OA platform)** — hosts JSLIS, 情報知識学会誌, 情報の科学と技術, and many others:
```
Use urllib.request with ?pubmode=listview parameter:
  https://www.jstage.jst.go.jp/browse/jslis/{VOL}/{ISSUE}/_contents/-char/ja?pubmode=listview
```
This returns full article titles, authors, DOIs, and abstracts in the HTML (no JS needed despite the main page requiring JavaScript). `lang=en` sometimes returns different metadata than `lang=ja` — check both.

**Publisher behavior (for checking OA status via direct scraping):**
- ✅ **Elsevier (ScienceDirect)**, **Springer** — allow scraping of journal homepages (OA info, scope)
- ✅ **J-Stage**, **publicera.kb.se** — allow scraping of OA article content
- ❌ **Wiley**, **SAGE**, **Emerald** — return HTTP 403 on direct scraping (use OpenAlex or Unpaywall instead)

**Key OA-only LIS journals to check directly (no subscription needed):**
- **Information Research** (InformationR.net / publicera.kb.se) — Diamond OA, no APC
- **JSLIS** (J-Stage) — Diamond OA, no APC
- **College & Research Libraries** (ACRL) — Diamond OA, no APC
- **Library Trends** (Project Muse) — 58.8% OA, past issues freely available

### 6. Present papers neutrally

After collecting papers, present them with **faithful, literal description** based on their abstracts. Do NOT:
- Categorize papers into themes or compute percentages
- Interpret or evaluate papers ("notable", "breakthrough")
- Connect papers to each other or to broader field trends
- Write qualitative trend analysis

Instead, for each paper state: what it investigates, what method it uses, and what it finds — as written in the abstract. Neutral, paper-by-paper, letting the content speak for itself.

Some users may prefer thematic analysis — ask if unsure. But the default should be neutral description.

For quantitative summary, a simple table of papers-per-journal is sufficient:

## 7. Full-Text Access & Publisher Policy Compliance

Before attempting automated full-text retrieval, verify what each publisher's terms allow. Violating license terms can result in IP bans, university-wide access revocation, or legal liability.

### Publisher TDM Policy Landscape

| Target | Source Type | Automated Book-Level | Full-Text PDF | Notes |
|--------|-------------|:---:|:---:|-------|
| **OpenAlex** | Bibliographic API | ✅ | — | Book-level + abstracts always OK. 10 req/s. |
| **Unpaywall** | OA resolution API | ✅ | ✅ OA only | OA links only; use email param. |
| **CrossRef** | DOI registry API | ✅ | — | Book-level metadata, OA links. |
| **EBSCO (LISA)** — via Web UI | Aggregator DB | ❌ | ❌ | License prohibits systematic downloading AND AI/ML use explicitly. **Do not use the web interface for automated collection.** |
| **EBSCOhost API (EDS API)** — *separate product* | Programmatic API | ⚠️ | ❌ | Separate subscription from the web interface. Designed for search, not bulk harvesting. Full text depends on publisher permissions. **Check with institution on API availability.** |
| **ProQuest LISA / ProQuest Library Science** | Aggregator DB | ⚠️ | ⚠️ (Library Science has ~150 full-text LIS journals) | LISA is sometimes provided via ProQuest instead of EBSCO. ProQuest "Library Science" DB adds full text. API via Clarivate/Ex Libris — requires separate license. |
| **Emerald (JDoc)** | Publisher site | ❌ | ❌ | Behind Cloudflare. HTTP 403 on `robots.txt`, 403 on all automated requests. Effectively blocked. |
| **Wiley (JASIST, ASIS&T Proc)** | Publisher site | ⚠️ | ❌ | `robots.txt` blocks `/doi/am-pdf/` (PDF path). Book-level HTML may be accessible case-by-case. |
| **Project MUSE (Library Trends)** | Publisher platform | ⚠️ | ❌ | General T&C prohibit copying/derivative works for "information retrieval systems." Institutional license per-institution. |
| **Nomos (KO)** | Publisher site | ⚠️ | ⚠️ | Most permissive `robots.txt` of the group. Case-by-case due to being a smaller German publisher. |

### Confirmed License Restrictions

**EBSCO (Critical — applies to LISA):**
> *"Downloading all or parts of the Databases or Services in a systematic or regular manner so as to create a collection of materials comprising all or part of the Databases or Services is strictly prohibited."*
> *"Licensee and Authorized Users may not use artificial intelligence tools or machine learning technologies with any of the content included in the Databases or Services for any purpose."*

→ EBSCO-based collection is **contractually prohibited**. LISA-indexed papers must be accessed via alternative routes (publisher-direct or OpenAlex).

**Project MUSE (Library Trends):**
> *"You may not modify, translate, create derivative works of, copy, distribute, market, display, remove or alter any proprietary notices or labels from, lease, sell, sublicense, transfer, decompile, reverse engineer, or incorporate into any information retrieval system, this website, any website content, or any portion thereof."*

→ Automated bulk extraction of MUSE content for local storage/pipeline is likely a violation. Book-level manual download is the safe route.

### 🇯🇵 Japan's Copyright Law Context

Japan's **Copyright Act Article 47-7** (2019 amendment) creates a broad exception for **information analysis** (text/data mining), permitting reproduction without the copyright holder's permission for computational analysis purposes. **However:**

- **Contract terms override the statutory exception.** EBSCO's license explicitly bans AI/ML use, which nullifies the 47-7 exception for EBSCO-hosted content.
- The exception covers "information analysis" — not archival/repository building. Systematic downloading to create a local collection may fall outside the safe harbor.
- University subscription agreements often include **prohibitions on "mass downloading / excessive access"** (大量ダウンロード・過剰アクセス).

### Practical Access Strategy

Use a layered approach that respects each publisher's boundaries:

```
Layer 1: OpenAlex API
        → Bibliographic metadata + abstracts — ALWAYS OK
        → Run weekly via cron (no policy issues)

Layer 2: Unpaywall API
        → OA full-text links for papers where available
        → Always legal (OA articles are free to download)

Layer 3: EZproxy / direct links (for subscribed content)
        → Generate links for MANUAL download only
        → Attach as "🔒 subscription required — download from: {URL}"
        → Do NOT automate PDF fetching through EZproxy

Layer 4: Diamond OA journals (J-Stage, Information Research, C&RL)
        → Full text fully accessible — safe for automated collection
        → Use direct scraping with pubmode=listview for J-Stage
```

### EZproxy Considerations

University proxy services track download volume:
- Short bursts of many PDF fetches trigger automatic suspension
- Publishers send "excessive usage" reports to the university library
- Result: IP ban or institution-wide access revocation
- → **Never route automated batch PDF downloads through EZproxy**

### Recommended Workflow for a Literature Collection Project

1. **Survey** venues via OpenAlex (book-level + abstracts) — unrestricted
2. **Store** OA full-text via Unpaywall links — always legal
3. **Flag** subscribed papers with direct links — user downloads manually
4. **Exclude** EBSCO/LISA from any automated pipeline
5. **Collect** Diamond OA journals separately (no subscription barrier)
6. **Monitor** policy changes annually (publisher terms evolve)
7. **Document** which policy each source falls under in reference files

## Script for Periodic Collection

For repeatable data collection (cron jobs), create a Python script that:

1. Takes `--weeks N` (lookback window), `--output DIR`, `--json` (save JSON), `--oa-only` flags
2. Iterates over a dict of `{key: {id, name, publisher}}` source definitions
3. For each source: fetches source metadata, recent papers, and topics
4. Generates a markdown report (titles, authors, OA badges, abstract previews, DOI links)
5. Optionally saves JSON with structured paper data

Key patterns for the script:
- Use `urllib.request` (stdlib, no pip needed) with `User-Agent` header
- Add `RATE_LIMIT_DELAY = 0.2` between calls (OpenAlex allows 10/sec)
- Handle `counts_by_year` from source endpoint to compute per-year OA ratios
- Save JSON alongside markdown for downstream analysis

**For back-issue/chronic surveys** (year-by-year, one journal per run), use the companion script at `/opt/data/scripts/collect_lis_backissues.py`. It supports `--all-papers` mode (no keyword filter), single-journal selection, and automatic llm-kb saves. See `references/backnumber-survey-pattern.md` for full workflow.

**Cron job architecture options:**
- **(a) Script-only (`no_agent=True`):** Fetches + saves data verbatim. Zero LLM cost. Deliver to the user as a file notification.
- **(b) LLM-driven (`no_agent=False`, default):** Script runs first (terminal), then the agent analyzes the output qualitatively and writes a narrative summary. Higher value but costs tokens. Use when the user asked for "定性的・定量的両面".

## Pattern: Chronological Back-Issue Survey (Journal-Per-Day)

For systematically surveying a journal's **entire archive** year-by-year. Each run covers **one journal × one year**. With 5 journals assigned across Tue–Sat, all advance by 1 year per week in parallel.

**User preference (output style):** When presenting results, provide **faithful, literal description** of each paper based on its abstract. Do NOT:
- Force-fit papers into predefined theme categories (情報概念, 情報哲学, AI 等)
- Write thematic interpretations or emerging-topic analyses
- Label papers as "注目すべき" or assign qualitative judgments
- Add speculative connections between papers

Instead, for each paper state: what it investigates, its method, and its findings — as written in the abstract. Neutral, paper-by-paper.

### When to use

- User asks to "survey back-issues" (バックナンバー) of journals
- User says "時期でフィルタして、できるだけ全部内容まで見て" — filter by time period, read ALL content
- User says "クエリというよりは" — don't keyword-query; browse chronologically
- User says "文献に忠実な記述を心がけて" — faithful/literal description
- User emphasizes reading ALL abstracts ("論文全件のアブストに目を通してほしい")

### Architecture

Each run = **one journal × one year**. No keyword filter — fetch ALL papers for that journal+year.

**State file** (`survey_state.json`):
```json
{
  "version": 2,
  "day_assignment": {
    "tuesday": "jdoc",
    "wednesday": "jasist",
    "thursday": "ko",
    "friday": "library_trends",
    "saturday": "asist_proc"
  },
  "year_end": 2026,
  "journals": {
    "jdoc": {"current_year": 2000, "status": "active"},
    "jasist": {"current_year": 2000, "status": "active"},
    "ko": {"current_year": 2000, "status": "active"},
    "library_trends": {"current_year": 2000, "status": "active"},
    "asist_proc": {"current_year": 2000, "status": "active"}
  }
}
```

**Cron schedule:** 5 separate jobs (one per journal), Tue–Sat at 00:00 UTC (09:00 JST):
```
Tue 0 0 * * 2 → jdoc
Wed 0 0 * * 3 → jasist
Thu 0 0 * * 4 → ko
Fri 0 0 * * 5 → library_trends
Sat 0 0 * * 6 → asist_proc
```

Each job is LLM-driven (not `no_agent`) with `llm-kb-wiki` skill loaded. The agent reads the state file, runs the script, reads ALL abstracts, writes a neutral report, saves to llm-kb, and updates state.

### Workflow

1. **Read state:** Load `survey_state.json`, read `journals.{key}.current_year`
2. **Collect:** Run the collection script with `--all-papers` (no keyword filter):
   ```
   python3 collect_lis_backissues.py --journal {journal_key} \
     --year-start {year} --year-end {year} --all-papers --json
   ```
3. **Read & describe:** Read the generated report file. For every paper, extract what it does from the abstract and write a **neutral, factual summary** in Japanese. No thematic categorisation, no interpretation.
4. **Save to llm-kb:** `/opt/data/workspace/llm-kb.miya-lis.net/concepts/lis-journal-surveys/{journal}-{year}.md`.
   Update `index.md` and `log.md`.
5. **Update state:** Increment `current_year`. If `> 2026`, set `status: "complete"`.

### Script Design (collect_lis_backissues.py)

Key features:
- `--all-papers` flag: omits the `?search=` query parameter, fetching ALL works for the source+year
- `--journal {key}`: single-journal mode (one of 5 predefined sources)
- `--year-start N --year-end N`: exact year(s); use same value for single-year
- `--json`: saves structured data alongside the markdown report
- Pagination up to 500 results with 100/page
- Abstract reconstruction from OpenAlex inverted index
- Saves to both `~/research_data/backissues/` and llm-kb

The script's automatic theme classification (情報概念/情報哲学/AI) is for the **machine-generated tag column only**. The agent's written analysis must **not** use these categories.

### Output Style (Mandatory)

Each paper entry:
```
#### N. Title
- **著者**: Authors
- **日付**: Date | **被引用**: N
- **DOI**: link
- **内容**: [2–3 sentence factual summary based strictly on the abstract.
   What does this paper investigate, using what method, finding what?
   No interpretation, no praise, no theme-fitting.]
```

No sections like "Theme Distribution" or "注目すべき論文". No percentage breakdowns. No qualitative trend analysis. Just the papers, presented factually.

### Coverage Timeline

27 years per journal (2000–2026). With 5 journals in parallel:
- **Per week:** 5 years total (one year per journal)
- **Completion:** ~27 weeks (all 5 journals reach 2026 simultaneously)
- **Average load per run:** 30–120 abstracts to read

### Known Limitations

- **JASIST (pre-2001):** Was "Journal of the American Society for Information Science (JASIS)". OpenAlex source S4210197613 may not include pre-2001 works. Check `counts_by_year`.
- **ASIS&T Proc. (pre-2000s):** Earlier title "Proceedings of ASIS". Same issue.
- **KO (pre-1993):** Was "International Classification". Coverage gaps.
- **Some journals publish sporadically:** KO publishes ~5 papers/year; Library Trends publishes themed issues with ~8–12 papers per issue, 4 issues/year. Empty years are normal — report "該当期間の論文はありません" without further comment.

## Publisher TDM & Institutional Access Checks

Before relying on full-text retrieval, verify each publisher's policy:

### Policy research checklist
1. **robots.txt** — check if automated PDF download paths are blocked (e.g. Wiley blocks `/doi/am-pdf/`)
2. **Terms of Use** — check for systematic downloading / AI/ML prohibitions (EBSCO explicitly prohibits both)
3. **Institutional DB subscriptions** — check which platform the target DB is on (LISA may be ProQuest, not EBSCOhost, at a given institution)
4. **API availability** — some DBs offer REST APIs separately from web interface (ProQuest Platform API, EBSCOhost EDS API) but require add-on contracts
5. **Abstract vs full-text DBs** — LISA, LISTA, SSCI are abstracting/indexing DBs; "Library Science" (ProQuest) is a full-text database with ~150 journals

### Common patterns by publisher
| Publisher | Content | Automated Access |
|---|---|---|
| EBSCO (LISA web) | Abstracts | ❌ Web TOS prohibits systematic DL + AI/ML. API requires separate subscription. |
| ProQuest (LISA, Library Science) | Abstracts + Full-text (~150 LIS journals) | ⚠️ API available (ProQuest Platform API) but add-on contract needed. TDM program exists separately. |
| Emerald (JDoc) | Full-text | ❌ Cloudflare-protected. robots.txt returns 403. |
| Wiley (JASIST) | Full-text | ⚠️ robots.txt blocks PDF paths. TDM framework available. |
| Project MUSE (Library Trends) | Full-text | ⚠️ Standard institutional license terms apply. |
| Nomos (KO) | Full-text | ✅ Permissive robots.txt. |

### Fallback chain for full-text access
1. **OpenAlex API** → free bibliographic metadata + abstracts (always available, no auth needed)
2. **Unpaywall API** → OA full-text links (where OA version exists)
3. **ProQuest / EBSCO API** → institutional full-text (if API add-on is contracted)
4. **EZproxy links** → handoff for manual download (automated bulk DL prohibited by most licenses)

## Pitfalls

1. **Conference venues are poorly indexed.** OpenAlex often doesn't have individual conferences as standalone sources. Individual proceedings volumes (e.g. "iConference 2014 Proceedings") are listed separately, not under one umbrella. Use general search with venue names and filter by year ranges for conferences.
2. **Search is broad.** `?search=...` matches any paper mentioning the term anywhere — it's NOT restricted by venue. Use `filter=primary_location.source.id:...` for precise venue queries.
3. **Topics field sometimes returns non-LIS topics** (e.g. "Economic Policy" for a KO journal). Verify against the journal's actual scope. The topic data is based on citation patterns, not editorial policy.
4. **`x_concepts` was removed** from the API. Use `topics` field instead (available via `?select=topics` on source endpoint).
5. **`venues` endpoint was removed** from the API. Use `sources` endpoint only (type=journal or type=conference).
6. **`primary_location.source` field returns `null`** for works without a known venue — check before accessing.
7. **Rate limits are generous but not limitless.** If you get HTTP 429 (in practice rare at 10 req/sec without API key), back off with exponential retry.
8. **Semantic Scholar API** (1 req/sec unauthenticated) can complement OpenAlex for citation data and author influences, but is much slower and less reliable for bulk queries.
9. **J-Stage main pages require JavaScript** and return empty HTML without it. Use the `pubmode=listview` parameter on the browse URL to get article data in plain HTML. If that also fails, try `?lang=en` first before switching to browser tools.
10. **Major publisher scraping blocks:** Wiley, SAGE, and Emerald block direct HTTP scraping with HTTP 403. Do not retry these — fall back to OpenAlex or Unpaywall immediately.
11. **Old `informationr.net` SSL certificate** has expired/is mismatched for `www.informationr.net`. Use `https://publicera.kb.se/ir/` (the new platform) for Information Research access, or use `https://informationr.net/ir/` without the `www` prefix.
12. **Historical journal name changes cause OpenAlex gaps.** Journals that changed names (JASIS→JASIST, ASIS→ASIS&T, International Classification→KO) may have incomplete archives under their current OpenAlex source ID. Check `counts_by_year` on the source endpoint to verify coverage before trusting «0 papers» results.

## Related Skills
- `jstage-jslis-daily-summary` — Japanese LIS papers from J-STAGE/CiNii (complementary coverage for East Asian LIS literature)
- `arxiv` — CS/DL/IR preprints on arXiv (for computer science-adjacent surveys)
- `blogwatcher` — RSS feed monitoring for blog/feed-based literature alerts