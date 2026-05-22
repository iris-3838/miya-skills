# Institutional Access & Publisher Policy Research

## Workflow for checking if institutional API access is possible

### Step 1: Find target journals' publishers
- JDoc → Emerald
- JASIST → Wiley (ASIS&T)
- Knowledge Organization → Nomos
- Library Trends → Project MUSE (Johns Hopkins UP)
- ASIS&T Proceedings → Wiley

### Step 2: Check institutional database subscriptions
- Visit the university library's database list (e.g. `library.example.ac.jp/database/`)
- Look for abstract DBs (cover more titles, metadata only) vs full-text DBs (fewer titles but full articles)
- Note which platform hosts each DB (ProQuest, EBSCOhost, Gale, etc.)

### Step 3: Check publisher TDM policies
Four signals to check (in order of reliability):
1. **robots.txt** — confirms automated access stance
2. **Terms of Use / License Agreement** — the definitive legal document
3. **Publisher TDM page** — some have formal TDM programs (STM Association, Wiley TDM framework)
4. **API documentation** — if a REST API exists, programmatic access is intended

### Step 4: Determine the viable data pipeline

```
Target journals
    ↓
Publisher websites (full-text)
    ├── OpenAlex API → metadata + abstracts (✅ always)
    ├── Unpaywall → OA full-text (✅ if OA exists)
    └── Institutional API → full-text (❓ if contracted)
        ├── ProQuest Platform API (requires add-on)
        └── EBSCOhost EDS API (requires add-on)
```

### Example: University access + LIS journals

| Resource | Platform | Full-text? | API available? |
|---|---|---|---|
| LISA | ProQuest | ❌ (abstracts only) | ⚠️ add-on needed |
| Library Science | ProQuest | ✅ ~150 journals | ⚠️ add-on needed |
| JDoc | Emerald Insight | ✅ | ❌ Cloudflare |
| JASIST | Wiley Online Library | ✅ | ⚠️ TDM framework |
| Knowledge Organization | Nomos | ✅ | ✅ robots.txt permissive |
| Library Trends | Project MUSE | ✅ | ⚠️ license terms apply |

### Key legal notes
- Japan's Copyright Act Art. 47-7 allows TDM for information analysis, but **contract terms override** this exception
- University library agreements typically prohibit "systematic/mass downloading" and "excessive access"
- EZproxy has automated detection of bulk downloads and can trigger IP bans
- Always check the specific DB license (not just the general terms of use)
