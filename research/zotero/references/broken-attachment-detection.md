# Detecting Broken Attachments in Zotero

## Attachment Link Modes

Zotero attachments have a `linkMode` field that determines where the file lives:

| linkMode | Meaning | Accessibility |
|---|---|---|
| `imported_file` / `imported_url` | Stored on Zotero cloud | ✅ Accessible via API download |
| `embedded_image` | Image stored in a note | ✅ Inline in note data |
| `linked_file` | Points to a local filesystem path | 🔴 **Broken if path no longer exists** |
| `linked_url` | URL bookmark | Varies — test individually |

## The "Broken linked_file" Pattern

The most common broken attachment is `linked_file` pointing to a Windows path that doesn't exist on the current machine:

```
C:\Users\tetka\OneDrive - 筑波大学\ドキュメント\Zotero\Hjørland_2005_Empiricism.pdf
```

These paths come from an old Windows + OneDrive setup. On Linux (or any other machine), the file can't be downloaded — the API reports an attachment exists (media-type metadata), but the file content returns nothing.

## Detection Approaches

### Approach A: Scan all items for linked_file (faster, recommended)

Scan the ENTIRE library for linked_file attachments, then cross-reference with Archive/collection membership. This avoids checking children of each parent individually.

```python
import json, requests, os

creds = json.load(open('/workspace/.private/zotero_credentials.json'))
headers = {'Zotero-API-Version': '3', 'Zotero-API-Key': creds['api_key']}
base = f'https://api.zotero.org/users/{creds["user_id"]}'

# Get parent collection membership (e.g., Archive keys)
archive_keys = {}
start = 0
while True:
    r = requests.get(f'{base}/collections/{archive_key}/items/top', headers=headers,
                     params={'limit': 100, 'start': start})
    data = r.json()
    if not data: break
    for item in data:
        archive_keys[item['data']['key']] = item['data'].get('title', '?')[:100]
    start += 100
    if len(data) < 100: break

# Scan ALL items for linked_file attachments
broken = []
start = 0
page = 0
while page < 20:  # covers up to 2000 items
    r = requests.get(f'{base}/items', headers=headers,
                     params={'limit': 100, 'start': start})
    data = r.json()
    if not data: break
    
    for item in data:
        d = item['data']
        if d.get('itemType') != 'attachment' or d.get('linkMode') != 'linked_file':
            continue
        
        parent = d.get('parentItem', '')
        path = d.get('path', '') or ''
        if not path or os.path.exists(path):
            continue
        
        # Check if parent is in our target collection
        if parent in archive_keys:
            broken.append((parent, archive_keys[parent], path, 'child'))
        elif not parent and d['key'] in archive_keys:
            broken.append((d['key'], archive_keys[d['key']], path, 'standalone'))
    
    page += 1
    start += 100
    if len(data) < 100: break

print(f'Broken linked_file attachments: {len(broken)}')
for pk, pt, path, typ in broken:
    print(f'  [{pk}] ({typ}) {pt[:50]}')
    print(f'    → {path[:90]}')
```

### Approach B: Check children individually (slow for 800+ items)

Checking children of each parent item one-by-one using `GET /items/{key}/children` is **too slow** for large libraries. At ~0.1-0.3s per call, scanning 800+ items takes 80-240 seconds — exceeding typical CLI timeout limits.

Use Approach A instead.

### Approach C: Check standalone attachments directly

Some PDFs are top-level items themselves (not children of a reference). These can be checked by examining the item's own data:

```python
# Check if a top-level item is itself a broken linked_file attachment
for pk, pt in archive_keys.items():
    r = requests.get(f'{base}/items/{pk}', headers=headers)
    if r.status_code == 200:
        d = r.json()['data']
        if d.get('itemType') == 'attachment' and d.get('linkMode') == 'linked_file':
            path = d.get('path', '') or ''
            if path and not os.path.exists(path):
                print(f'BROKEN standalone: [{pk}] {pt}')
```

## Fix Strategy

1. Create a "fix" collection as a child of the main collection (e.g., Archive → fix)
2. Move broken items to fix by PATCHing their `collections` field (preserving existing memberships)
3. User can later re-upload files as `imported_file` attachments or delete the items

```python
fix_key = '7CNEHA82'  # key of the fix collection

for pk, pt, path, typ in broken:
    r = requests.get(f'{base}/items/{pk}', headers=headers)
    d = r.json()['data']
    existing = d.get('collections', [])
    new = list(set(existing + [fix_key]))
    
    requests.patch(
        f'{base}/items/{pk}',
        headers={**headers, 'If-Unmodified-Since-Version': str(d['version']),
                 'Content-Type': 'application/json'},
        json={'collections': new}
    )
```

## Pitfalls

- **Don't use `POST /collections/{key}/items`** — this endpoint does not exist and returns 400.
- **Always re-fetch item version before PATCH** – the version from the trash listing or cached data may be stale.
- **Preserve existing collection links** – don't overwrite `collections` if the item might be in a group library.
- **linked_file without a path** exists but is irrelevant (no file to check). Skip.
- **attachments in trash** can still be PATCHed to restore them, but check their `collections[]` first for stale links.
