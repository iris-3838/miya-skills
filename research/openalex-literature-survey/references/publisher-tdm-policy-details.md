# Publisher TDM Policy Details

Discovered during full-text access feasibility investigation.
Complements `openalex-literature-survey` skill section 7.

## EBSCO License (EBSCOhost Web Interface — LISA, LISTA, etc.)

Confirmed via EBSCO's Master License Agreement (applicable to the standard EBSCOhost web interface for all databases including LISA):

```
Downloading all or parts of the Databases or Services in a systematic or
regular manner so as to create a collection of materials comprising all or
part of the Databases or Services is strictly prohibited.

Licensee and Authorized Users may not use artificial intelligence tools or
machine learning technologies with any of the content included in the
Databases or Services for any purpose.
```

**Verdict:** ❌ Cannot use the EBSCOhost **web interface** for automated collection. This applies to LISA, LISTA (Library, Information Science & Technology Abstracts), and all EBSCO-hosted indices accessed through the standard web browser interface.

### ⚠️ Important: EBSCOhost API (EDS API) is a Separate Product

EBSCO offers a **REST API** (EBSCO Discovery Service API / EBSCOhost API) which is a **separate product** governed by a **separate license agreement**. 

- URL (EBSCO Connect): `https://connect.ebsco.com/s/article/EBSCOhost-API`
- Developer portal: `https://developer.ebsco.com/` (hosted on ReadMe: `ebsco-group.readme.io`)
- Requires a **separate API subscription** from the institution — does NOT automatically come with an EBSCOhost database subscription
- Designed for programmatic search and retrieval of bibliographic metadata
- Full text retrieval is **subject to individual publisher restrictions** — some publishers block full text via API even if the institution subscribes
- The API is NOT exempt from systematic downloading prohibitions — it's meant for real-time search, not bulk harvesting
- Terms require per-institution verification (not publicly viewable — requires EBSCO developer account and active API key)

**Practical implication:** If an institution has an EBSCOhost API subscription, users can search LISA (and other EBSCO databases) programmatically. BUT:
- LISA is an abstracting DB — full text is NOT included
- The API still prohibits creating a local repository of all records
- Rate limits apply (varies by subscription tier)
- Need to check with the university library: "Does our EBSCO subscription include API access?"

### ProQuest Alternative for LISA

In one checked institution, LISA was accessed via **ProQuest** (not EBSCOhost). The database listing showed:
- `https://search.proquest.com/lisa` — LISA via ProQuest platform
- `https://search.proquest.com/lisashell`? — alternative LISA access

Additionally, ProQuest offers **"Library Science"** — a separate full-text database with ~150 LIS journals in full text. This is a distinct subscription from LISA and provides actual article content, not just abstracts.

ProQuest has its own API (via Ex Libris/Clarivate), accessible through:
- `https://developer.proquest.com/` (redirects to Ex Libris developer portal)
- Requires separate licensing from the standard database subscription
  
**Library check needed:** Contact the university library to ask:
1. Whether ProQuest API access is available (or can be added)
2. Whether the "Library Science" full-text database is part of the current subscription
3. Whether the ProQuest TDM policy allows programmatic non-commercial research use

## Emerald Insight (Journal of Documentation)

- `https://www.emerald.com/insight/` — behind **Cloudflare** challenge (JS required)
- `https://www.emerald.com/robots.txt` — returns **HTTP 403** (effectively blocks all crawlers)
- `https://www.emeraldgrouppublishing.com/robots.txt` — standard robots.txt, but the publishing platform itself blocks automation
- All policy pages return Cloudflare challenges, making automated TDM essentially impossible via their native platform
- OpenAlex or Unpaywall remain the only practical way to get Emerald metadata/OA links

**Verdict:** ❌ Direct automated access effectively blocked at Cloudflare level.

## Wiley Online Library (JASIST, Proceedings of ASIS&T)

`robots.txt` (Wiley Online Library) key disallowed paths:

```
Disallow: /doi/am-pdf/      # blocks automated PDF download
Disallow: /doi/pdf/         # blocks PDF delivery endpoint
Disallow: /doi/epdf/        # blocks PDF viewer
Allow: /doi/                # allows DOI landing pages (book-level HTML)
```

- Landing pages (HTML abstracts) are generally accessible
- PDF download paths are explicitly blocked for bots
- Terms of Service at `wiley.com/en-us/terms-conditions` returns 404 — older version referenced the standard Wiley subscription T&Cs
- Wiley has a formal **Text and Data Mining** program for subscribed content, but it requires registration and uses the CrossRef TDM API or a dedicated Wiley API

**Verdict:** ⚠️ Book-level HTML and abstracts accessible. PDF download blocked by robots.txt. For bulk TDM, Wiley's official program requires registration.

## Project MUSE (Library Trends)

**General Terms of Use** (https://muse.jhu.edu/terms_use, updated 2018-05-31):

> *"You may not modify, translate, create derivative works of, copy, distribute, market, display, remove or alter any proprietary notices or labels from, lease, sell, sublicense, transfer, decompile, reverse engineer, or incorporate into any information retrieval system, this website, any website content, or any portion thereof."*

**Institutional License Agreement PDF** (confirmed available at):
`https://about.muse.jhu.edu/media/uploads/downloads/project_muse_journal_collection_institutional_license.pdf`

Key restrictions in the general T&C:
- No incorporation into "information retrieval systems" (prohibits local aggregation pipelines)
- No derivative works
- Non-commercial personal use only

**Verdict:** ⚠️ Automated extraction into a local retrieval system likely violates general T&C. Institutional license may have different terms — per-institution verification required.

## Nomos eLibrary (Knowledge Organization)

`robots.txt` (https://www.nomos-elibrary.de/robots.txt):
- Generally permissive — standard crawl delays
- No specific PDF path blocking
- Sitemaps available for structured access

As a smaller German academic publisher, Nomos has less restrictive automated access policies than the major anglophone publishers. However, institutional subscription terms may still apply.

**Verdict:** ⚠️ Most permissive of the group, but institutional license terms should still be verified before automated PDF collection.

## Example university proxy access (EZproxy)

- Service: OCLC EZproxy
- Login URL: `https://institution.idm.oclc.org/login`
- Access control: Shibboleth-based authentication
- Institutional policy: **Prohibits mass downloading / excessive access** (大量ダウンロード・過剰アクセス)
- Publishers have automated excessive-usage detection — sends alerts to the university library
- Multiple violations can lead to institution-wide access revocation

**Rule of thumb:** EZproxy is for HUMAN use. At most ~dozens of PDFs per day. A script fetching hundreds of PDFs/hour will be detected and blocked.

## Japanese Copyright Act Article 47-7

The 2019 amendment (effective 2021-01-01) introduced Article 47-7, allowing:

- **Reproduction** of copyrighted works for "information analysis" (情報解析) purposes
- **No requirement** for lawful access to the work (controversially — allows even bypassing TPM for TDM)
- **Application** to both non-profit and commercial research

**Critical caveat:**
> Article 47-7 is a statutory exception, but **contractual terms that restrict TDM override the exception**. If a license agreement (like EBSCO's) explicitly prohibits AI/ML or systematic analysis, the contract takes precedence over the copyright law exception.

This is a well-known tension in Japanese copyright law — the TDM exception was intended to promote AI/data innovation, but the contract override provision means publishers can opt out via their terms of service.

## Practical Investigation Methodology

When a user asks about their institution's database access for automated collection, use this methodology:

### 1. Find the University's Database/Resource List

University libraries maintain a database A-Z list. Common URL patterns:
- `lib.example.ac.jp/database/` or `library.example.ac.jp/eresources/`

These pages typically list ALL subscribed databases with links and brief descriptions.

### 2. Extract Key Information from Login URLs

The login URLs reveal the underlying platform and customer IDs:
- `search.ebscohost.com/login.aspx?custid=sXXXXXXX` → EBSCO customer ID (redacted)
- `search.proquest.com/lisa` → ProQuest platform
- `institution.idm.oclc.org` → OCLC EZproxy

Parse the EBSCOhost login URLs for:
- `defaultdb=lii` → database code (LISA = `lii`)
- `profile=ehost` → interface type
- `custid=sXXXXXXX` → institution's customer ID
- `authtype=ip,shib` → authentication method (IP or Shibboleth)

### 3. Distinguish Between Platforms

The same database "LISA" can be available through multiple platforms:
- **EBSCOhost**: `search.ebscohost.com/login.asp?profile=ehost&defaultdb=lii`
- **ProQuest**: `search.proquest.com/lisa`
- The underlying data is similar, but the license terms, API availability, and TDM policies differ by platform

### 4. Check Database Info Pages

University libraries often have detail pages for each database (e.g., `library.example.ac.jp/lib/dbinfo/lisa-ls`) that include:
- Full-text availability status ("一部可", "あり", "なし")
- Concurrent user limits
- Which department/系 manages the subscription
- Platform and coverage dates

### 5. Look for Companion Full-Text Databases

If the target database is abstract-only (like LISA), check if the library also subscribes to full-text companions:
- **Library Science** (ProQuest) — ~150 LIS journals in full text, complementary to LISA
- **LISTA** (EBSCO) — "Library, Information Science & Technology Abstracts" (free version with limited full text)
- These are separate subscriptions and may require separate verification

### 6. Contact the Library

For API availability, the only way to verify is to contact the library directly:
- Ask specifically about **API subscriptions** (EBSCOhost API / ProQuest API / Clarivate Web of Science API)
- Ask about **TDM policies** under the institution's license agreement
- In Japan, ask about the contract's stance on **著作権法47条の7** (whether the contract overrides it)
- The library's **電子リソース担当** (electronic resources librarian) or the department's **図書委員** is the right contact

## Summary Table: Which Automated Routes Are Safe

| Route | Book-level | Full-text PDF | Legal basis |
|-------|:---:|:---:|-----------|
| OpenAlex API | ✅ | — | Public API, no license restriction |
| Unpaywall API | — | ✅ (OA only) | OA articles, no restriction |
| CrossRef API | ✅ | — | Public API, no license restriction |
| EBSCO/LISA | ❌ | ❌ | License explicitly prohibits |
| Emerald direct | ❌ | ❌ | Cloudflare blocks; license uncertain |
| Wiley direct | ⚠️ HTML | ❌ PDF | robots.txt blocks PDF paths |
| Project MUSE direct | ⚠️ | ❌ | T&C prohibit info retrieval systems |
| Nomos direct | ⚠️ | ⚠️ | Permissive robots.txt, check license |
| Diamond OA (J-Stage etc.) | ✅ | ✅ | Open access, no restriction |

## Monthly Monitoring Recommendation

Publisher policies change. Re-verify these sources every 6–12 months:

1. EBSCO Terms of Use → `https://www.ebsco.com/terms-of-use`
2. Project MUSE Terms → `https://muse.jhu.edu/terms_use`
3. Emerald policies → check if Cloudflare protection has been modified
4. Wiley TDM program → check if self-service TDM API has changed
5. Nomos license → verify with institution
