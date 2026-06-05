# Bulk Restore Trashed Items to a Collection

Restore all top-level trashed items (journal articles, books, etc.) to a target collection (e.g., "Archive") while clearing old collection associations.

## Workflow

### 1. Get collection map and target key

```python
import json, requests

creds = json.load(open('/opt/data/workspace/.skills/zotero_credentials.json'))
headers = {'Zotero-API-Version': '3', 'Zotero-API-Key': creds['api_key']}
base = f'https://api.zotero.org/users/{creds["user_id"]}'

# Find target collection
r = requests.get(f'{base}/collections', headers=headers, params={'limit': 100})
archive_key = None
for c in r.json():
    if c['data']['name'] == 'Archive':
        archive_key = c['data']['key']
        break
```

### 2. Get all top-level trashed items (paginated)

```python
all_items = []
start = 0
while True:
    r = requests.get(f'{base}/items/trash', headers=headers,
                     params={'limit': 100, 'start': start})
    data = r.json()
    if not data: break
    for item in data:
        d = item['data']
        if d.get('itemType') in ('attachment', 'note'): continue  # skip children
        all_items.append({
            'key': d['key'],
            'version': d['version'],
            'title': d.get('title', '?')[:50],
            'collections': d.get('collections', []),  # old associations to clear
        })
    start += 100
    if len(data) < 100: break
```

### 3. Restore + add to Archive in one PATCH

**⚠️ ALWAYS preserve existing collection links** (グループライブラリ紐付け). Never blindly overwrite `collections` — the user explicitly requires this.

```python
import time

success = 0
fail = 0
for item in all_items:
    # Read current item to get fresh version + preserve existing collection links
    r_get = requests.get(f'{base}/items/{item["key"]}', headers=headers)
    if r_get.status_code != 200:
        fail += 1
        continue
    current = r_get.json()['data']
    existing_colls = current.get('collections', [])

    # PRESERVE existing collections, add Archive
    new_colls = list(set(existing_colls + [archive_key]))

    r = requests.patch(
        f'{base}/items/{item["key"]}',
        headers={**headers, 'If-Unmodified-Since-Version': str(current['version']),
                 'Content-Type': 'application/json'},
        json={'deleted': False, 'collections': new_colls}
    )
    if r.status_code in (200, 204):
        success += 1
    else:
        fail += 1
    time.sleep(0.15)  # rate limiting — 0.15s is safe for 800+ items
```

## Pitfalls

### POST /collections/{key}/items does NOT exist
- Results in 400: `Item '["KEY"]' not found in library`
- Use **PATCH /items/{key}** with `collections` field instead

### Trashed items retain collection associations — PRESERVE them
- `data.collections[]` on trashed items may contain links to still-existing collections (including group library collections)
- **DO NOT** use `{'collections': [archive_key]}` — this OVERWRITES and loses group library associations
- Always re-fetch the item first to get current collections, then merge: `list(set(existing + [archive_key]))`
- If collections[] contains orphan keys (collections that no longer exist), Zotero ignores them silently — safe to keep

### Version headers required
- Every PATCH needs `If-Unmodified-Since-Version` matching the item's current `version`
- The version increments after each successful PATCH — if you PATCH twice, the second call needs the NEW version

### Trash count discrepancy
- `GET /items/trash` with default `limit=100` only returns first page
- Total count from `Total-Results` header includes ALL trashed items (attachments, notes)
- Top-level count requires client-side filtering by `itemType`

### Rate limiting
- ~50ms delay between PATCH calls is sufficient for 700+ items
- Total time at 50ms delay: ~35 seconds for 700 items
- Use `time.sleep(0.02)` for safety

## Related
- `web-api-v3.md` — Full API reference
- `api.md` — pyzotero method reference
