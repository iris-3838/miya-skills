---
name: zotero
description: "Manage Zotero library — collections (CRUD + hierarchy restructuring), items, notes, attachments, search, and BibTeX export — via pyzotero and Zotero Web API v3."
---

# Zotero Library Manager (pyzotero)

Manage your Zotero library through the Web API using Python scripts. Handles collection hierarchy restructuring, item CRUD, search, and export.

## Authentication

Credentials are stored in `/workspace/.private/zotero_credentials.json` (outside the git-tracked skills dir):

```json
{"user_id": "123456", "api_key": "P9NiFoyLeZu2bZNvvuQPDWsd"}
```

**Setup first run:**
```bash
python3 /workspace/skills/research/zotero/scripts/setup_credentials.py
```

The script verifies the API key against the `/keys/current` endpoint and saves the file with `chmod 600` (owner-only read).

## Quick Commands

All operations via `zotero_client.py`:

| Task | Command |
|---|---|
| Setup credentials | `python3 scripts/setup_credentials.py` |
| Show structure (tree) | `python3 scripts/zotero_client.py structure` |
| List collections (flat) | `python3 scripts/zotero_client.py collections --flat` |
| Create collection | `python3 scripts/zotero_client.py collection-create "Name" [--parent KEY]` |
| Rename collection | `python3 scripts/zotero_client.py collection-rename KEY "New Name"` |
| Move/reparent collection | `python3 scripts/zotero_client.py collection-move KEY --to PARENT_KEY` |
| Move to top-level | `python3 scripts/zotero_client.py collection-move KEY --to root` |
| Delete collection | `python3 scripts/zotero_client.py collection-delete KEY` |
| List items | `python3 scripts/zotero_client.py items [--collection KEY] [--limit 30]` |
| Search items | `python3 scripts/zotero_client.py items --q "search term"` |
| Get item (JSON) | `python3 scripts/zotero_client.py item-get KEY` |
| Show children | `python3 scripts/zotero_client.py item-children KEY` |
| Delete item | `python3 scripts/zotero_client.py item-delete KEY` |
| Export BibTeX | `python3 scripts/zotero_client.py export --collection KEY [--format bibtex]` |
| Library stats | `python3 scripts/zotero_client.py info` |
| List tags | `python3 scripts/zotero_client.py tags` |

(All paths relative to `/workspace/skills/research/zotero/scripts/`)

## Collection Hierarchy Management

Zotero supports nested collections via the `parentCollection` field. The skill supports full restructuring:

### Moving collections between folders
```bash
# Move collection to another parent
python3 /workspace/skills/research/zotero/scripts/zotero_client.py collection-move ABCDEF --to XYZ123

# Promote to top-level (remove parent)
python3 /workspace/skills/research/zotero/scripts/zotero_client.py collection-move ABCDEF --to root
```

### Reorganizing folder structure
1. View current structure: `structure` command shows tree with item counts
2. Plan reorganization: identify target parent keys
3. Execute moves: `collection-move` for each collection
4. Verify: `structure` again to confirm

## Item Workflows

### Programmatic item creation
For complex item creation (e.g., from literature search results), use pyzotero directly in a script:

```python
from pyzotero.zotero import Zotero
import json

creds = json.loads(open("/workspace/.private/zotero_credentials.json").read())
z = Zotero(creds["user_id"], "user", creds["api_key"])

template = z.item_template("journalArticle")
template["title"] = "Paper Title"
template["creators"] = [{"creatorType": "author", "lastName": "Smith", "firstName": "John"}]
result = z.create_items([template])
print(result)
```

### Moving items between collections
```python
z.addto_collection("TARGET_KEY", {"key": "ITEM_KEY"})
z.deletefrom_collection("SOURCE_KEY", {"key": "ITEM_KEY"})
```

## KB Sync (Zotero → LLM-KB)

Mirror Zotero's collection hierarchy into `raw/papers/zotero/` as Markdown files for agentic knowledge retrieval.

```bash
# Dry-run (show structure, no writes)
python3 /workspace/skills/research/zotero/scripts/zotero_kb_sync.py --dry-run

# Execute sync (creates directory tree + item .md files + index.md per collection)
python3 /workspace/skills/research/zotero/scripts/zotero_kb_sync.py

# Sync a single collection only
python3 /workspace/skills/research/zotero/scripts/zotero_kb_sync.py --collection COLLECTION_KEY

# Sync a group library (read-only)
python3 /workspace/skills/research/zotero/scripts/zotero_kb_sync.py --group GROUP_ID
```

**What it produces:**
```
raw/papers/zotero/
├── CollectionA/
│   ├── index.md            ← collection-level index
│   ├── Paper Title.md      ← item metadata + abstract
│   └── SubCollection/
│       ├── index.md
│       └── Another Paper.md
└── index.md                ← global index
```

**Cron setup for periodic sync:**
```bash
python3 /workspace/skills/research/zotero/scripts/zotero_kb_sync.py
# Schedule via: hermes cron create --schedule "0 6 * * 1" --prompt "Run zotero_kb_sync.py"
```

### Group Library Access

Zotero group libraries use a different library type parameter:
```python
from pyzotero.zotero import Zotero
import json

creds = json.loads(open("/workspace/.private/zotero_credentials.json").read())

# User library
z_user = Zotero(creds["user_id"], "user", creds["api_key"])

# Group library (read-only if API key lacks group write)
z_group = Zotero(GROUP_ID, "group", creds["api_key"])
items = z_group.items(limit=10)
```

CLI equivalent: `python3 scripts/zotero_kb_sync.py --group 5643674`

## Credential Management

API credentials are stored in `/workspace/.private/` (outside git-tracked dirs), not in SKILL.md:
- **Format**: JSON (`zotero_credentials.json`)
- **Permissions**: `chmod 600` (owner-only)
- **Setup**: `python3 scripts/setup_credentials.py` (interactive, auto-verifies key)

## Attachment Health Check

Zotero attachments can be in several states — some reports "have files" but the files are actually inaccessible.

### Check attachment types and availability

```bash
python3 /workspace/skills/research/zotero/scripts/check_attachments.py
```

This reports:
- Total items with enclosure links
- Count of downloadable vs broken PDFs  
- Non-PDF attachments

For a detailed breakdown by link mode:

```bash
python3 /workspace/skills/research/zotero/scripts/check_attachments_detail.py
```

This separates attachments into:

| Link Mode | Meaning | Likely state |
|-----------|---------|-------------|
| `imported_file` / `imported_url` | Stored on Zotero cloud | ✅ Accessible via API |
| `embedded_image` | Image in notes | ✅ Zotero-internal |
| `linked_file` | Points to local path | 🔴 **Broken if path no longer exists** |
| `linked_url` | URL bookmark | Varies — test individually |

### Common pattern: broken linked files

The most common attachment failure is `linked_file` items pointing to an old Windows or OneDrive path that no longer exists on the current machine. In the API, these items report having attachments (media-type metadata exists), but the actual file download returns nothing because the path is stale.

Fix: either re-add the file as an `imported_file` attachment, or update the `path` field if the file was moved.

### Understanding "リンク切れ"

When the user says "リンクが切れている" about Zotero, they mean **attachment files that can't actually be downloaded** — not metadata references, collection memberships, or URL relations. Always check actual file download availability via the API, not just the enclosure-link presence.

### Detecting broken linked_file attachments at scale

Scanning children of 800+ parent items via individual `GET /items/{key}/children` calls is **too slow** (times out). Instead, scan ALL items via the paginated `/items` endpoint and filter for `linkMode=linked_file` client-side, then cross-reference with parent collection membership. See `references/broken-attachment-detection.md` for full workflow.

**Typical broken pattern:** `C:\Users\tetka\OneDrive - 筑波大学\...` — Windows OneDrive path from an old setup, inaccessible on Linux.

**Fix workflow:** Create a "fix" subcollection under the parent collection (e.g., Archive → fix), then move broken items there via PATCH (preserving existing collection memberships).

## Collection Structure Backup

Before any reorganization, save the current structure:

```bash
python3 /workspace/skills/research/zotero/scripts/backup_structure.py
```

This writes to `/workspace/llm-kb.miya-lis.net/raw/papers/zotero/_bak/`:
- `collection_structure.md` — tree view of all 213+ collections
- `collections.json` — JSON dump of all collections with keys, names, parent refs

## Adding Items to Collections — Correct API

**❌ WRONG:** `POST /collections/{key}/items` — this endpoint **does not exist** in Zotero API v3. Calling it returns 400 `Item '["KEY"]' not found in library`.

**✅ CORRECT:** `PATCH /items/{key}` with the `collections` field:

```python
import json, requests

# Add item to a collection (replaces all collection membership)
requests.patch(
    f'{base}/items/{item_key}',
    headers={'If-Unmodified-Since-Version': str(version)},
    json={'collections': [target_collection_key]}
)
```

When moving items from trash + adding to a collection, do it in a single PATCH:
```python
requests.patch(f'{base}/items/{key}',
    headers={'If-Unmodified-Since-Version': str(version)},
    json={'deleted': False, 'collections': [archive_key]})
```

## Bulk Restoring Trashed Items

See `references/bulk-restore-from-trash.md` for the complete workflow to restore 700+ trashed items to a target collection.

## Pagination Pitfall (pyzotero)

**`z.collections()` defaults to 100 results.** In libraries with 400+ collections, this silently truncates the data — collections beyond page 1 are invisible. This caused a real bug: `_bak` (which existed at root level) appeared "missing" because it lived on page 2+.

**Always paginate through ALL pages when the library might be large:**

```python
import json, requests

with open("/workspace/.private/zotero_credentials.json") as f:
    creds = json.load(f)

headers = {"Zotero-API-Version": "3", "Zotero-API-Key": creds["api_key"]}
base = f"https://api.zotero.org/users/{creds['user_id']}"

all_collections = {}
start = 0
while True:
    r = requests.get(f"{base}/collections", headers=headers,
                     params={"limit": 100, "start": start})
    data = r.json()
    if not data:
        break
    for c in data:
        d = c["data"]
        all_collections[d["key"]] = {
            "name": d["name"],
            "parent": d.get("parentCollection") or None
        }
    start += 100
```

**To include trashed collections**, add `"includeTrashed": 1` to params. Without this flag, trashed collections are invisible. In large libraries the trash may hold hundreds of items.

**Using pyzotero with custom pagination:**
```python
from pyzotero.zotero import Zotero
import json

creds = json.load(open("/workspace/.private/zotero_credentials.json"))
z = Zotero(creds["user_id"], "user", creds["api_key"])
z.add_parameters(limit=100)

# Fetch a specific page
page_3 = z.collections(start=200)
```

When you only need the first page (common for small libraries), pyzotero's default works fine. When in doubt, paginate.

## Collection-Item API Pitfall

**`POST /collections/{key}/items` は存在しない。** このエンドポイントにPOSTを送ると `400 Item not found` エラーになる。

アイテムをコレクションに追加する正しい方法は、**アイテム自体をPATCH** して `collections` フィールドを更新すること:

```python
# ✅ 正しい: PATCH /items/{itemKey}
requests.patch(
    f"{base}/items/{item_key}",
    headers={"Content-Type": "application/json",
             "If-Unmodified-Since-Version": str(version)},
    json={"collections": [target_collection_key]}
)

# ✅ pyzotero を使う場合（これも内部的にはPATCH）
z.addto_collection("TARGET_KEY", {"key": "ITEM_KEY", "version": 123, "data": {"collections": []}})

# ❌ 間違い: POST /collections/{key}/items ← このエンドポイントは存在しない
requests.post(f"{base}/collections/{key}/items", json=["item_key"])  # 400エラー
```

**複数コレクションに所属させる場合:**
```python
# 現在の所属を取得してから新しいコレクションを追加
r = requests.get(f"{base}/items/{item_key}", headers=headers)
d = r.json()["data"]
current = d.get("collections", [])
new_colls = list(set(current + [target_key]))

requests.patch(
    f"{base}/items/{item_key}",
    headers={"If-Unmodified-Since-Version": str(d["version"])},
    json={"collections": new_colls}
)
```

**複数アイテムを一括で同じコレクションに追加する場合:**
レスポンスが返るたびにバージョンが更新されるので、各アイテムを個別にPATCHする。
pyzoteroの `addto_collection` も内部的には1アイテムずつPATCHしている。

## Structure Diagnosis

### Finding orphaned collections (parent deleted)

`structure` only shows root-level and nested collections. If a parent collection was deleted without reparenting its children, those sub-collections become **invisible in the tree view** but still exist in the API — they are "orphans."

**Detection method:**
```bash
# 1. List flat to see all collections with parent refs
python3 /workspace/skills/research/zotero/scripts/zotero_client.py collections --flat

# 2. Look for [parent=KEY] where KEY does not appear as its own line
#    Those are orphans — the parent no longer exists.
```

**Programmatic orphan check with item counts:**
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

all_keys = set(by_key.keys())
for k, v in sorted(by_key.items()):
    if v["parent"] and v["parent"] not in all_keys:
        r = z.collection_items(k)
        total = r.get("totalResults", 0) if isinstance(r, dict) else len(r)
        print(f"⚠️ Orphan: {v['name']} ({total} items) [{k}] → missing parent [{v['parent']}]")
```

**Fixing orphans:**
```bash
# Promote to root level (removes parent reference)
python3 /workspace/skills/research/zotero/scripts/zotero_client.py collection-move KEY --to root

# Or reparent to a specific parent
python3 /workspace/skills/research/zotero/scripts/zotero_client.py collection-move KEY --to PARENT_KEY
```

**Caveat:** The backup script (`backup_structure.py`) captures all collections including orphans, so review a fresh backup before any restructuring to understand the full picture.

## Bulk Restructuring (100+ Collections)

For large-scale reorganization (hundreds of collections), `zotero_client.py collection-move` is too slow one-at-a-time. Use raw API calls with `requests.patch` and version headers:

```python
import json, requests

with open("/workspace/.private/zotero_credentials.json") as f:
    creds = json.load(f)

headers = {
    "Zotero-API-Version": "3",
    "Zotero-API-Key": creds["api_key"],
    "Content-Type": "application/json"
}
base = f"https://api.zotero.org/users/{creds['user_id']}"

# Build key→collection map with versions (paginated)
cols = {}
start = 0
while True:
    r = requests.get(f"{base}/collections", headers=headers,
                     params={"limit": 100, "start": start})
    data = r.json()
    if not data: break
    for c in data:
        d = c["data"]
        cols[d["key"]] = {"name": d["name"], "version": d["version"]}
    start += 100

def move_collection(key, new_parent_key):
    """Reparent a single collection. Returns True on success."""
    v = cols.get(key)
    if not v:
        return False
    r = requests.patch(
        f"{base}/collections/{key}",
        headers={**headers, "If-Unmodified-Since-Version": str(v["version"])},
        data=json.dumps({"parentCollection": new_parent_key})
    )
    if r.status_code in (200, 204):
        v["version"] += 1  # optimistic: version incremented server-side
        return True
    return False

# Batch reparenting: move root-level collections that belong under new parents
for k, v in cols.items():
    if v["parent"] is None and v["name"] in ("学術", "学術分野別"):
        move_collection(k, NEW_ROOT_KEY)
```

**Strategy for bulk reorganization:**
1. Create new root folders first (POST)
2. Move **parent collections** — their subtree follows automatically
3. Delete empty duplicate shells after confirming they have no items or children
4. Verify with a paginated collection dump

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `401 Unauthorized` | Invalid/expired API key | Re-run `setup_credentials.py` |
| `412 Precondition Failed` | Version conflict | Re-fetch item before update |
| `409 Conflict` | Library locked | Wait and retry |
| `404 Not Found` | Wrong key or endpoint | Verify collection/item key |
| pyzotero import error | Wrong Python path | Use `python3 -m pip install pyzotero --break-system-packages` |
| Attachment won't download | Linked file with stale path | Check `check_attachments_detail.py` → re-import file |
| `400` adding item to collection | Using wrong endpoint (`POST /collections/{key}/items`) | Use `PATCH /items/{key}` with `collections` field instead |

## ゴミ箱アイテムの復元

ゴミ箱のアイテムを復元し、コレクションに追加する正しい手順:

```python
# 1. ゴミ箱から復元 + コレクション紐づけクリア + 新しいコレクションに追加（一括PATCH）
requests.patch(
    f"{base}/items/{item_key}",
    headers={"If-Unmodified-Since-Version": str(version)},
    json={
        "deleted": False,        # ゴミ箱から復元
        "collections": [target]  # 旧コレクションをクリアして新しいコレクションに追加
    }
)
```

**注意:**
- `deleted: False` でゴミ箱から復元
- `collections` フィールドは**全置換**される。空配列 `[]` で全クリア
- ゴミ箱アイテムを復元せずにコレクションに追加することはできない
- ゴミ箱の添付ファイル（child items）は残しても問題ない

## ライブラリスコープの分離（重要）

Zotero API では以下のスコープが完全に分離されている:

| スコープ | エンドポイント | 対象 |
|---------|---------------|------|
| 個人ライブラリ | `/users/{id}/items` | My Libraryのアイテム |
| グループライブラリ | `/groups/{id}/items` | グループのアイテム |

**個人ライブラリのアイテムはグループライブラリのコレクションに属せず、その逆も不可。**
操作時はターゲットのスコープを明示すること。特に「全アイテム」の一括操作では、意図しないスコープのアイテムを変更しないよう注意。
| Trashed item still in old collection | Item was trashed but `collections[]` field retains stale membership | Before restoring, PATCH `{"deleted": False, "collections": []}` in a single call — or clear collections PATCH first, then restore. Items in trash CAN still be modified via PATCH with version header. |

## Prerequisites
- Zotero account with API key (Settings → Feeds/API Keys)
- pyzotero installed (`python3 -m pip install pyzotero --break-system-packages`)
- Network access to `https://api.zotero.org`

## Related Skills

- `zotero-integration` — Architectural decisions, credential management policy, and future direction for Zotero integration. Load alongside `zotero` for full context.

## Survey Library Structure (after reorganization)

After significant restructuring (moves, renames, delete/backup), verify the result with a structured survey:

```bash
# 1. Quick overview — item counts, library version
python3 scripts/zotero_client.py info

# 2. Tree view — confirm hierarchy matches intent
python3 scripts/zotero_client.py structure

# 3. Flat list — check for orphaned/duplicate collections
python3 scripts/zotero_client.py collections --flat

# 4. Compare with backup (if available)
#    backup_structure.py saves to LLM-KB raw/papers/zotero/_bak/
#    Compare current `structure` output with the backed-up tree
```

**Watch for:**
- Empty collections (`numItems: 0`) that should have items
- Duplicate-named collections at the same level (e.g., 図書館情報学×3)
- Collections at unexpected hierarchy positions
- The `_bak/` collection persist after restructuring is verified

## Tag-Based Status Management (seimiya's workflow)

seimiya manages items using three status tags instead of manual collection placement. This is the objective approach: tags describe the item's state, collections are derived views.

| Status | Tag | Meaning |
|---|---|---|
| 未読 | `Archive` | Not yet read |
| 読書中 | `In-progress` | Currently reading |
| 読了 | `Collection` | Finished reading |

### Workflow

1. **New items** arrive → tag `Archive`, add to the `Archive` collection.
2. **Start reading** → change tag from `Archive` to `In-progress`, move item from Archive → In-progress collection (or keep in place with tag as the source of truth).
3. **Finished** → change tag from `In-progress` to `Collection`, move to Collection collection.

### Pitfalls

- **Trashed items retain collection associations.** Before restoring a trashed item, always check `data.collections[]` — items can be linked to collections they no longer belong to. Use PATCH with `{"deleted": False, "collections": new_colls}` where `new_colls = list(set(existing_colls + [target_key]))` to preserve group library links.
- **Re-fetch version before PATCH.** When reading an item's current `collections[]` to preserve them, also use the FRESH version returned by that GET — the version from the trash listing may be stale by the time you PATCH.
- **Tag naming convention:** Use English (Archive / In-progress / Collection) for consistency with Zotero's multilingual ecosystem. Avoid mixing Japanese and English status tags.
- **Bulk restore from trash:** Always audit collection associations first — scan all top-level trashed items, report which have stale links, then clear those links during restore.

### Bulk: list trashed items with stale collection associations

```python
import json, requests

creds = json.load(open("/workspace/.private/zotero_credentials.json"))
headers = {"Zotero-API-Version": "3", "Zotero-API-Key": creds["api_key"]}
base = f"https://api.zotero.org/users/{creds['user_id']}"

# Build collection key→name map
all_cols = {}
start = 0
while True:
    r = requests.get(f"{base}/collections", headers=headers, params={"limit": 100, "start": start})
    data = r.json()
    if not data: break
    for c in data:
        all_cols[c["data"]["key"]] = c["data"]["name"]
    start += 100
    if len(data) < 100: break

# Scan top-level trashed items for stale collections
start = 0
while True:
    r = requests.get(f"{base}/items/trash", headers=headers,
                     params={"limit": 100, "start": start})
    data = r.json()
    if not data: break
    for item in data:
        d = item["data"]
        if d.get("itemType") in ("attachment", "note"):
            continue
        colls = d.get("collections", [])
        if colls:
            print(f"[{d['key']}] {d.get('title','?')[:60]}")
            for c in colls:
                print(f"  → {all_cols.get(c, f'UNKNOWN:{c[:8]}')}")
    start += 100
    if len(data) < 100: break
```

### Bulk: restore trashed items to Archive (clearing stale associations)

```python
import json, requests

creds = json.load(open("/workspace/.private/zotero_credentials.json"))
headers = {"Zotero-API-Version": "3", "Zotero-API-Key": creds["api_key"]}
base = f"https://api.zotero.org/users/{creds['user_id']}"

# Find Archive collection key
archive_key = None
for c in requests.get(f"{base}/collections", headers=headers).json():
    if c["data"]["name"] == "Archive":
        archive_key = c["data"]["key"]
        break
if not archive_key:
    r = requests.post(f"{base}/collections", headers=headers,
                      data=json.dumps([{"name": "Archive", "parentCollection": False}]))
    archive_key = r.json()["success"]["0"]

# Restore + clear stale collections + add to Archive in ONE PATCH per item
start = 0
while True:
    r = requests.get(f"{base}/items/trash", headers=headers,
                     params={"limit": 100, "start": start})
    data = r.json()
    if not data: break
    for item in data:
        d = item["data"]
        if d.get("itemType") in ("attachment", "note"):
            continue
        # ⚠️ DO NOT use POST /collections/{key}/items — that endpoint does not exist
        # ✅ Use PATCH /items/{key} with both deleted and collections fields
        requests.patch(f"{base}/items/{d['key']}",
            headers={**headers, "If-Unmodified-Since-Version": str(d["version"])},
            data=json.dumps({"deleted": False, "collections": [archive_key]}))
    start += 100
    if len(data) < 100: break
```

## References
- `references/web-api-v3.md` — API endpoint reference
- `references/api.md` — pyzotero method reference & folder restructuring guide
- `references/bulk-reorganization.md` — complete workflow for restructuring 200+ collections via raw API
- `references/orphan-detection.md` — detecting and fixing orphaned collections
- `references/tag-based-organization.md` — tag-based status management workflow (Archive / In-progress / Collection)
- Zotero Web API v3: https://www.zotero.org/support/dev/web_api/v3
- pyzotero: https://github.com/urschrei/pyzotero
