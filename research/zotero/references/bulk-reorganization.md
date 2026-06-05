# Bulk Reorganization Reference

Working pattern for restructuring large Zotero libraries (200+ collections).

## Scenario

438 collections, 861 items scattered across 5+ root-level folders. Goal: consolidate into 3 form-based root folders (図書館情報学, 講義資料, MISC) + preserve _bak as read-only backup.

## Strategy

1. **Move parent collections, not children.** Moving a root-level collection brings its entire subtree.
2. **Batch via PATCH with version headers.** The API requires `If-Unmodified-Since-Version` on writes.
3. **Delete empty duplicates** after verifying they have 0 items and 0 child collections.
4. **Verify** by dumping all collections (paginated) to confirm no orphans remain.

## Complete Workflow

```python
import json, requests

with open("/opt/data/workspace/.skills/zotero_credentials.json") as f:
    creds = json.load(f)

headers = {
    "Zotero-API-Version": "3",
    "Zotero-API-Key": creds["api_key"],
    "Content-Type": "application/json"
}
base = f"https://api.zotero.org/users/{creds['user_id']}"

# 1. Dump all collections (paginated)
all_cols = {}
start = 0
while True:
    r = requests.get(f"{base}/collections", headers=headers,
                     params={"limit": 100, "start": start})
    data = r.json()
    if not data: break
    for c in data:
        d = c["data"]
        all_cols[d["key"]] = {
            "name": d["name"],
            "parent": d.get("parentCollection") or None,
            "version": d["version"]
        }
    start += 100

# 2. Helper: check if a collection is under another in the tree
def is_under(key, target, visited=None):
    if visited is None: visited = set()
    if key in visited or not key: return False
    visited.add(key)
    if key == target: return True
    v = all_cols.get(key)
    if not v or not v["parent"]: return False
    return is_under(v["parent"], target, visited)

# 3. Move collection
def move_col(key, new_parent):
    v = all_cols.get(key)
    if not v or is_under(key, new_parent) or key == new_parent:
        return
    r = requests.patch(
        f"{base}/collections/{key}",
        headers={**headers, "If-Unmodified-Since-Version": str(v["version"])},
        data=json.dumps({"parentCollection": new_parent})
    )
    if r.status_code in (200, 204):
        all_cols[key]["parent"] = new_parent
        all_cols[key]["version"] += 1
        print(f"  ✅ {v['name']}")
    else:
        print(f"  ❌ {v['name']}: HTTP {r.status_code}")

# 4. Delete empty collection
def delete_col(key):
    v = all_cols.get(key)
    if not v: return
    r = requests.delete(f"{base}/collections/{key}",
        headers={**headers, "If-Unmodified-Since-Version": str(v["version"])})
    return r.status_code in (200, 204)

# 5. Check item count
def item_count(key):
    r = requests.get(f"{base}/collections/{key}/items/top",
                     headers=headers, params={"limit": 0})
    return int(r.headers.get("Total-Results", 0))

# 6. Check if has child collections
def has_children(key):
    return any(v["parent"] == key for v in all_cols.values())
```

## Pitfalls

- **pyzotero's `z.collections()` only returns page 1** (100 items). For 438 collections you need the raw paginated API.
- **`includeTrashed=1` is required** to see trashed collections. Without it, 300+ items may be invisible.
- **Deleting a parent collection orphans its children** in Zotero. The children still exist in the API but become invisible in the tree view.
- **Empty collections may still have children.** Check `has_children()` before deleting.
- **Version numbers increment on write.** Always use the latest version from the `all_cols` dict (which you increment optimistically after a successful PATCH).
- **Duplicate names at root level** (e.g. 図書館情報学×3) are common after reorganization — merge or delete empties after moving items.

## Item Count Caveat

`/collections/{key}/items/top` returns only top-level items (not items in sub-collections). For total count across the tree, sum recursively.
