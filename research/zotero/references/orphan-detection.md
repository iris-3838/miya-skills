# Orphan Detection in Zotero

## Background

Zotero allows deleting a parent collection without automatically reparenting or deleting its children. This leaves sub-collections in a state where:
- They still have items and sub-hierarchies
- They are **invisible** in the Zotero UI tree
- They **do not appear** in `zotero_client.py structure`
- They **are only discoverable** via `collections --flat` or programmatic API access

## Detection Workflow

### Step 1: Suspect orphans

Run `structure` — if the total collection count is much higher than what the tree shows (`Total collections: N` vs. visible folders), orphans are likely.

### Step 2: Confirm via flat listing

```bash
python3 /workspace/skills/research/zotero/scripts/zotero_client.py collections --flat
```

Lines with `[parent=KEY]` where KEY doesn't appear as its own entry are orphans.

### Step 3: Programmatic check (comprehensive)

```python
from pyzotero.zotero import Zotero
import json

creds = json.load(open("/workspace/.private/zotero_credentials.json"))
z = Zotero(creds["user_id"], "user", creds["api_key"])

cols = z.collections()
by_key = {}
for c in cols:
    d = c["data"]
    by_key[d["key"]] = {
        "name": d["name"],
        "parent": d.get("parentCollection", False) or None
    }

# Find orphans
all_keys = set(by_key.keys())
orphans = []
for k, v in sorted(by_key.items()):
    if v["parent"] and v["parent"] not in all_keys:
        r = z.collection_items(k)
        total = r.get("totalResults", 0) if isinstance(r, dict) else len(r)
        orphans.append((k, v["name"], v["parent"], total))
        print(f"⚠️ Orphan: {v['name']} ({total} items) [{k}] → missing parent [{v['parent']}]")

print(f"\nTotal orphans: {len(orphans)}")
```

### Step 4: Backup before fixing

```bash
python3 /workspace/skills/research/zotero/scripts/backup_structure.py
```

## Repair

### Option A: Promote orphans to root level

```bash
# One at a time
python3 /workspace/skills/research/zotero/scripts/zotero_client.py collection-move KEY --to root
```

### Option B: Reparent under a new parent

Create a new parent collection first, then move:
```bash
python3 /workspace/skills/research/zotero/scripts/zotero_client.py collection-create "New Parent"
python3 /workspace/skills/research/zotero/scripts/zotero_client.py collection-move ORPHAN_KEY --to NEW_PARENT_KEY
```

### Option C: Bulk reparent (Python)

```python
from pyzotero.zotero import Zotero
import json

creds = json.load(open("/workspace/.private/zotero_credentials.json"))
z = Zotero(creds["user_id"], "user", creds["api_key"])

# Create target parent first in Zotero UI, get its key
TARGET_PARENT_KEY = "XXXXXXXX"

cols = z.collections()
for c in cols:
    d = c["data"]
    parent = d.get("parentCollection", False)
    if parent and parent not in {cc["data"]["key"] for cc in cols}:
        # Found orphan — reparent
        d["parentCollection"] = TARGET_PARENT_KEY
        z.update_collection(c)
        print(f"Moved {d['name']} [{d['key']}] → {TARGET_PARENT_KEY}")
```

## Pitfalls

- **`collection-move --to root`** works for individual collections but doesn't cascade to their existing children — the children keep their current parent (which is now the newly-promoted collection key, so they're no longer orphaned ✅).
- Zotero API has rate limits (~1 req/sec). For 50+ orphan repairs, add `time.sleep(0.5)` between calls.
- After reparenting, the Zotero UI/web may take a few seconds to refresh the tree view.
- The deleted parent's key (e.g., `Q4I2MVWQ`) is gone forever — you cannot recover it. Only the children survive.

## Real-world example (2026-05-23)

The entire library structure collapsed when the top-level parent `Q4I2MVWQ` was deleted:
- 7 direct children became orphaned (大学, 図書館情報学, 情報評価, 情報の哲学入門, 情報について考える, 書誌, 参考文献)
- Only 2 root collections survived (参考文献 with 48 items, 図書館情報学 with 0 items)
- The orphans still contained 800+ items across 90+ sub-collections
- `structure` showed only 2 root folders; the flat list revealed the true extent
