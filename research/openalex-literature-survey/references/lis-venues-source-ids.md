# LIS Venues — OpenAlex Source IDs & Reference Data

Discovered during a LIS literature survey.
Use with `openalex-literature-survey` skill.
→ **For publisher TDM/full-text access policies, see `publisher-tdm-policy-details.md` in this directory.**

## Core LIS Journals

| Venue | OpenAlex ID | ISSN | Publisher | Total Works | OA Rate | Type |
|-------|------------|------|-----------|-------------|---------|------|
| Journal of Documentation | `S10082577` | 0022-0418 | Emerald (GB) | 3,006 | 16.3% | hybrid |
| JASIST | `S4210197613` | 2330-1635 | Wiley / ASIS&T (US) | 2,288 | 41.1% | hybrid |
| Knowledge Organization | `S97705534` | 0943-7444 | Nomos / ISKO (DE) | 2,061 | 35.5% | hybrid |
| Library Trends | `S9186059` | 0024-2594 | Johns Hopkins UP (US) | 1,040 | 58.8% | hybrid |
| Proceedings of ASIS&T | `S4393918545` | — | Wiley / ASIS&T | 2,210 | — | proceedings |
| Information Processing & Management | `S18526058` | 0306-4573 | Elsevier (NL) | 3,859 | 41.0% | hybrid |
| Journal of Information Science | `S18662109` | 0165-5515 | SAGE (GB) | 1,975 | 31.7% | hybrid |
| Scientometrics | `S16384774` | 0138-9130 | Springer (NL) | 6,083 | 35.5% | hybrid |
| Library & Information Science Research | `S19672850` | 0740-8188 | Elsevier (US) | 1,171 | 25.9% | hybrid |\n\n## Japanese & Diamond-OA LIS Journals\n\n| Venue | Platform | ISSN | OA Type | Details |\n|-------|---------|------|---------|---------|\n| **JSLIS** (日本図書館情報学会誌) | J-Stage | 1340-3713 | **Diamond OA** | No APC. 4 issues/year. Japanese language. Publishes empirical LIS research on Japanese libraries. J-Stage has all issues with full PDFs. Use `pubmode=listview` to scrape article data. |\n| **Information Research** | publicera.kb.se (new) / informationr.net (archived) | 1368-1613 | **Diamond OA** | No APC. International LIS journal. 2025 special issue on AI & information science (14 papers). Indexed in Scopus, LISA. IF ~1.5. No author or reader fees. Old site (informationr.net) has SSL cert issues — use publicera.kb.se for new content. |\n| **College & Research Libraries** | ACRL | 0010-0870 | **Diamond OA** | Published by ACRL (ALA division). Focuses on academic library research. Full OA for all issues. |\n| **情報知識学会誌** | J-Stage | — | **Diamond OA** | Japanese language. Cross-disciplinary LIS. |\n| **情報の科学と技術** | J-Stage | — | **Diamond OA** | Published by 情報科学技術協会 (INFOSTA). Japanese language. Practical focus. |\n\n## Publisher Scraping Behavior\n\n| Publisher | Direct Scraping | Notes |\n|-----------|----------------|-------|\n| **Elsevier (ScienceDirect)** | ✅ Allowed | Journal homepages, OA info, and abstracts accessible |\n| **Springer** | ✅ Allowed | Homepage and volume/issue metadata accessible |\n| **J-Stage** | ✅ Allowed | Use `pubmode=listview` for article data; main page needs JS |\n| **Wiley** | ❌ Blocks (403) | Use OpenAlex or Unpaywall instead |\n| **SAGE** | ❌ Blocks (403) | Use OpenAlex or Unpaywall instead |\n| **Emerald** | ❌ Blocks (403) | Use OpenAlex or Unpaywall instead |\n\n## Research Methodology Distribution (JSLIS sample, 2024-2026)\n\nFrom a hands-on survey of JSLIS Vol.70–72 (25 research papers):\n- Questionnaire/Web survey: 20%\n- Bibliometric/document analysis: 20%\n- Secondary data analysis (SSP survey etc.): 12%\n- Interview/Focus group: 12%\n- Literature review: 12%\n- Experiment (eye tracking etc.): 4%\n- Scale development: 4%\n- Historical analysis: 4%\n- Other: 12%\n\n→ Japanese LIS journals lean toward **questionnaire surveys and bibliometric analyses** as dominant methods.

## LIS Thematic Profile (by journal)

- **JDoc**: LIS theory, documentation theory, information concepts, public libraries, information culture, digital inclusion, grounded theory in LIS
- **JASIST**: Bibliometrics, information behavior, misinformation, topic modeling, text mining, scientific communication  
- **KO**: Classification, ontologies, knowledge graphs, semantic enrichment, automatic classification, AI×KO
- **Library Trends**: Themed special issues (currently: data literacy, community data, computational pedagogy)

## Conference Series

| Conference | OpenAlex Coverage | Notes |
|-----------|-------------------|-------|
| iConference | Individual proceedings per year (168–178 works) | No umbrella source ID |
| CoLIS | Not well-indexed as a source | Search by event name + year range |
| ISKO Conferences | Papers published in KO journal or "Advances in Knowledge Organization" series | No standalone source in OA |
| ASIS&T Annual Meeting | `S4393918545` (Proceedings of ASIS&T) | 2,210 works, hybrid access |
| ICADL | Not well-indexed individually | Proceedings in Springer LNCS series |

## Top Topics per Journal (from OpenAlex topics, 2026-05)

| Journal | Top Topics |
|---------|-----------|
| JDoc | Info Retrieval & Search Behavior (367), Library Science & Admin (353), Library Info Literacy (263), Semantic Web & Ontologies (237), Scientometrics & Bibliometrics (220) |
| JASIST | Information retrieval, natural language processing, misinformation, topic modeling, bibliometrics |
| KO | Semantic Web & Ontologies, Economic Policy, Public Administration, Political Science, Sociology |
| Library Trends | Library Science & Admin, Library Info Literacy, Digital Archives, Web & Library Services, Collection Development |

## OA Retrieval Strategy

- **OpenAlex** (`open_access.is_oa + open_access.oa_url`): Best for checking per-paper OA status
- **Unpaywall API**: Also available on DOIs from OpenAlex (use DOI to check via Unpaywall)
- **Semantic Scholar** (`isOpenAccess`, `openAccessPdf`): Alternative OA check, slower rate (1 req/sec)
- **CrossRef**: Check via `https://api.crossref.org/works/{DOI}` for OA info

**Best OA journals for full-text mining:**
1. Library Trends (58.8% OA) — past issues freely available
2. JASIST (41.1% OA) — hybrid model, ASIS&T members get access
3. Knowledge Organization (35.5% OA) — ISKO members get access
4. Journal of Documentation (16.3% OA) — mostly subscription, Emerald paywall
