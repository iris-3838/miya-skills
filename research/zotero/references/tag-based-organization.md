# Tag-Based Status Organization (seimiya's workflow)

## Motivation

Replace subjective manual collection placement with objective tag-based status tracking. Instead of deciding "which folder does this paper go in?", each item receives a status tag describing its reading state. Collections become derived views filtered by tag.

## Status Tags

| Tag | Meaning | Color suggestion |
|---|---|---|
| `Archive` | 未読 — not yet read | Grey |
| `In-progress` | 読書中 — currently reading | Yellow |
| `Collection` | 読了 — finished reading | Green |

## Collection Structure

```
📁 Archive          (items tagged Archive)
📁 In-progress      (items tagged In-progress)
📁 Collection       (items tagged Collection)
```

Items are added to these collections programmatically based on their tag. Manual placement into these collections is not needed — the tag is the source of truth.

## When to Use

- After bulk-importing items from a literature search
- During weekly review: move items between statuses as reading progresses
- After cleaning up the trash (restoring items to Archive with stale collection associations cleared)

## Workflow Steps

### 1. Audit trashed items for stale collection associations

Before restoring trashed items, always check if any still have old collection links:

```python
import json, requests

creds = json.load(open("/workspace/.private/zotero_credentials.json"))
headers = {"Zotero-API-Version": "3", "Zotero-API-Key": creds["api_key"]}
base = f"https://api.zotero.org/users/{creds['user_id']}"

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

start = 0
while True:
    r = requests.get(f"{base}/items/trash", headers=headers, params={"limit": 100, "start": start})
    data = r.json()
    if not data: break
    for item in data:
        d = item["data"]
        if d.get("itemType") in ("attachment", "note"):
            continue
        colls = d.get("collections", [])
        if colls:
            print(f"⚠️ [{d['key']}] {d.get('title','?')[:60]}")
            for c in colls:
                print(f"   still in → {all_cols.get(c, f'UNKNOWN:{c[:8]}')}")
    start += 100
    if len(data) < 100: break
```

### 2. Create status collections (if missing)

```python
import json, requests
creds = json.load(open("/workspace/.private/zotero_credentials.json"))
headers = {"Zotero-API-Version": "3", "Zotero-API-Key": creds["api_key"]}
base = f"https://api.zotero.org/users/{creds['user_id']}"

existing = {c["data"]["name"]: c["data"]["key"]
            for c in requests.get(f"{base}/collections", headers=headers).json()}

for name in ("Archive", "In-progress", "Collection"):
    if name not in existing:
        r = requests.post(f"{base}/collections", headers=headers,
                          data=json.dumps([{"name": name, "parentCollection": False}]))
        print(f"Created {name}: {r.json()}")
```

### 3. Restore trashed items to Archive

See the bulk restore script in the main zotero skill SKILL.md.

### 4. Tag items

After items are in Archive, assign additional tags beyond the status tag — subject area, methodology, project name, etc. The status tag is just the first axis.

### 5. Move items between statuses

```python
# Change tag and move collection membership
import json, requests

creds = json.load(open("/workspace/.private/zotero_credentials.json"))
headers = {"Zotero-API-Version": "3", "Zotero-API-Key": creds["api_key"]}
base = f"https://api.zotero.org/users/{creds['user_id']}"

def move_to_status(item_key, new_status):
    """Move an item to a new status collection and update its tag."""
    # Get current item — use FRESH version for PATCH header
    r = requests.get(f"{base}/items/{item_key}", headers=headers)
    item = r.json()["data"]
    version = item["version"]  # MUST be from the GET, not cached

    # Update tags: replace status tag, keep all others
    old_tags = [t for t in item.get("tags", [])
                if t.get("tag") not in ("Archive", "In-progress", "Collection")]
    old_tags.append({"tag": new_status})

    # Find target collection key
    collections = {c["data"]["name"]: c["data"]["key"]
                   for c in requests.get(f"{base}/collections", headers=headers).json()}
    target = collections.get(new_status)

    # PRESERVE existing collection links + add target
    existing_colls = item.get("collections", [])
    new_colls = list(set(existing_colls + [target]))

    requests.patch(f"{base}/items/{item_key}",
        headers={**headers, "If-Unmodified-Since-Version": str(version)},
        data=json.dumps({"tags": old_tags, "collections": new_colls}))

# Usage: move_to_status("ABCDEF", "In-progress")
```

## API Notes

- **Re-fetch version before PATCH.** When you need to read an item's current state (e.g., to preserve collections), use the `version` from that GET response as your `If-Unmodified-Since-Version`, not a cached/stale value — the version may have changed since the last listing.
- Trashed items can be PATCHed — they are not immutable.
- Setting `"collections": []` in a PATCH clears all collection memberships.
- Setting `"collections": [target_key]` simultaneously clears old and sets new — **do NOT do this** if the item may be in group library collections. Always preserve: `new_colls = list(set(existing_colls + [target_key]))`.
- Restore and add to Archive in ONE PATCH: `{"deleted": False, "collections": [archive_key]}`.
- There is NO `POST /collections/{key}/items` endpoint — use PATCH /items/{key} with the `collections` field.
- Zotero API requires `If-Unmodified-Since-Version` header on all writes.
- Always paginate: the API returns at most 100 results per page.
