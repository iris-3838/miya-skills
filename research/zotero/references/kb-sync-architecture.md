# Zotero → LLM-KB Sync Architecture

## Purpose

Mirror Zotero's collection hierarchy into `/opt/data/workspace/llm-kb.miya-lis.net/raw/papers/zotero/` so an agent can navigate Zotero's folder structure directly for knowledge retrieval (agentic search).

## Data Flow

```
Zotero Web API                    raw/papers/zotero/
┌──────────────┐                 ┌──────────────────────┐
│ Collections  │ ──sync──►       │ CollectionA/         │
│   ├─ FolderA │                 │   ├── index.md       │
│   │  ├─ Item1│                 │   ├── Paper Title.md │
│   │  └─ Item2│                 │   └── SubCollection/ │
│   └─ FolderB │                 │       ├── index.md   │
│              │                 │       └── Paper.md   │
└──────────────┘                 └──────────────────────┘
```

## Sync Tool

`scripts/zotero_kb_sync.py` — the canonical sync tool.

**What it does per collection:**
1. Creates a directory matching the Zotero collection name (parent-child hierarchy preserved)
2. Fetches all items in the collection (paginated, 100 at a time)
3. For each item, writes a Markdown file with:
   - YAML frontmatter (title, creators, date, DOI, tags, zotero_key, item type)
   - Body with abstract, publication metadata, extra notes
4. Generates `index.md` per collection with subcollection links and item list
5. Generates top-level `index.md` with the full collection tree

**Sync modes:**
- Full sync (default): processes all top-level collections and their children recursively
- Single collection: `--collection KEY`
- Incremental: not yet implemented (all-fetches each run)

**Caveats:**
- No pagination of child items within a collection beyond the first 100
- Items in multiple collections get their own copy in each collection directory
- Non-file metadata only (no PDF attachment download in the KB sync)
