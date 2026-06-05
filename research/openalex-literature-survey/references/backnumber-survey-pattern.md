# Backnumber Survey Pattern — Implementation Reference (v3)

## Overview

Chronological LIS journal survey system built on OpenAlex API. Complements the weekly "recent papers" collection by systematically working through each year's full output.

**Architecture:** One run = **one journal × one year**. 5 journals × 5 days (Tue–Sat) = 5 years covered per week in parallel.

**Output style:** Faithful, literal description of each paper based on its abstract. No thematic categorisation, no interpretation.

## Setup

### State File (`/opt/data/research_data/backissues/survey_state.json`)

Each journal tracks its own `current_year` independently:

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

Each cron job reads its journal's `current_year`, runs the year, then increments. When `current_year > year_end`, status becomes `"complete"`.

### Script

`/opt/data/scripts/collect_lis_backissues.py`

Key flags:
- `--journal {jdoc|jasist|ko|library_trends|asist_proc}` — required
- `--year-start N --year-end N` — single year: use same value for both
- `--all-papers` — fetch ALL works (omit keyword query). **Required for backnumber surveys.**
- `--json` — also save structured data
- `--query "..."` — only use for targeted searches; NOT for backnumber surveys

Full command:
```bash
python3 /opt/data/scripts/collect_lis_backissues.py \
  --journal jdoc \
  --year-start 2000 --year-end 2000 \
  --all-papers --json
```

Outputs:
- `~/research_data/backissues/backissue_{journal}_{year}-{year}_{YYYYMMDD}.md` — report
- `~/research_data/backissues/backissue_{journal}_{year}-{year}_{YYYYMMDD}.json` — data
- Automatically also saves to llm-kb at `concepts/lis-journal-surveys/{journal}-{year}.md`

### Cron Jobs (5 separate, LLM-driven)

Each job runs Tuesday through Saturday at 00:00 UTC (09:00 JST):

| Day | Job Name | Journal | Cron |
|-----|----------|---------|------|
| Tue | LIS Back-Issue: JDoc | Journal of Documentation | `0 0 * * 2` |
| Wed | LIS Back-Issue: JASIST | JASIST | `0 0 * * 3` |
| Thu | LIS Back-Issue: KO | Knowledge Organization | `0 0 * * 4` |
| Fri | LIS Back-Issue: Library Trends | Library Trends | `0 0 * * 5` |
| Sat | LIS Back-Issue: ASIS&T Proc. | ASIS&T Proceedings | `0 0 * * 6` |

Each job loads the `llm-kb-wiki` skill and uses toolsets `terminal, file, search`.

### Workflow per Run

1. **Read state** → `journals.{key}.current_year`
2. **Run script** → collects all works for that journal + year (no keyword filter)
3. **Read output** → open the generated MD report, go through EVERY abstract
4. **Describe neutrally** → for each paper, write a 2–3 sentence factual summary based strictly on the abstract. What it investigates, method, findings. No interpretation, no theme-fitting.
5. **Save to llm-kb** → `concepts/lis-journal-surveys/{journal}-{year}.md`. Update `index.md` and `log.md`.
6. **Update state** → increment `current_year`. If done, set `status: "complete"`.

## Output Style (Mandatory — from user correction)

The user explicitly corrected this approach during the session:

> 「文献に忠実な記述を心がけて」
> — "Aim for descriptions faithful to the literature"

> 「検索テーマとの関係よりも、より文献に忠実な記述」
> — "More faithful to the papers than to search themes"

> 「解釈やテーマへの当てはめは最小限に」
> — "Minimize interpretation and theme-fitting"

**Do NOT do:**
- ✗ Classify papers into categories (情報概念 / 情報哲学 / AI)
- ✗ Calculate percentages or theme distributions
- ✗ Write "注目すべき論文" sections
- ✗ Add qualitative trend analysis
- ✗ Connect papers to each other or to broader themes
- ✗ Include any section header with thematic labels

**Do:**
- ✓ Present each paper with its title, authors, date, DOI
- ✓ Write a factual 2–3 sentence summary of what the paper investigates
- ✓ Let the content speak for itself — no framing, no evaluation
- ✓ If a year has 0 papers: simply state "該当期間の論文はありません"

## Paper Entry Template

```markdown
#### N. Title
- **著者**: Author(s)
- **日付**: Date | **被引用**: N
- **DOI**: link
- **内容**: [Factual description based strictly on abstract. What does this paper investigate? What method does it use? What does it find or argue? No more than 3 sentences.]
```

## Coverage

| Journal | Est. papers/year | Total (2000–2026) |
|---------|-----------------|-------------------|
| JDoc | ~110 | ~3,000 |
| JASIST | ~85 | ~2,300 |
| KO | ~76 | ~2,100 |
| Library Trends | ~39 | ~1,000 |
| ASIS&T Proc. | ~82 | ~2,200 |

Pace: 1 journal per day → 5 years of progress per week. All 5 journals complete 2000–2026 in ~27 weeks.

## Journals (5)

| Key | OpenAlex ID | Name | ISSN | Notes |
|-----|-------------|------|------|-------|
| `jdoc` | S10082577 | Journal of Documentation | 0022-0418 | |
| `jasist` | S4210197613 | JASIST | 2330-1635 | Pre-2001 called JASIS — separate ID needed |
| `ko` | S97705534 | Knowledge Organization | 0943-7444 | Pre-1993 "International Classification" |
| `library_trends` | S9186059 | Library Trends | 0024-2594 | |
| `asist_proc` | S4393918545 | ASIS&T Proceedings | 2373-9231 | Pre-2001 "Proceedings of ASIS" |

## Historical Name Changes — OpenAlex Gaps

- **JASIST (pre-2001):** Returns 0 papers for years before 2001. The older JASIS entity needs a separate source lookup.
- **ASIS&T Proc. (pre-2000s):** Same issue. Older ASIS proceedings may be under a different ID.
- **KO (pre-1993):** "International Classification" had a different ISSN.
- **Library Trends:** Some years show 0 papers despite quarterly publication. Verify via `counts_by_year`.

## Weekly Collection Companion

The Monday job `LIS Venues Weekly Collection` collects the most recent 2 weeks' papers from all 5 journals. It uses `/opt/data/scripts/collect_lis_papers.py` (the original script). Output goes to `/opt/data/lis_weekly_*.md` and is also saved to llm-kb under `concepts/lis-journal-surveys/weekly-{YYYYMMDD}.md`.

**Key difference:** The weekly collection should also use neutral/factual description, not thematic analysis (same user preference applies).

## llm-kb Location

```
/opt/data/workspace/llm-kb.miya-lis.net/concepts/lis-journal-surveys/
  ├── weekly-20260525.md                   # Monday weekly collection
  ├── jdoc-2000.md                         # Tuesday backnumber
  ├── jasist-2000.md                       # Wednesday backnumber
  ├── ko-2000.md                           # Thursday backnumber
  ├── library-trends-2000.md               # Friday backnumber
  ├── asist-proc-2000.md                   # Saturday backnumber
  └── ...
```
