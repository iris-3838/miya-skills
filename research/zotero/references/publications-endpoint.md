# My Publications (Publications Endpoint)

Zotero's **"My Publications"** is NOT a regular collection. It has its own dedicated API endpoint, separate from the standard library collections. Attempting to find it via `GET /collections` will fail silently — the publications collection is invisible to that endpoint.

## Key Facts

| Aspect | Regular Collections | My Publications |
|--------|-------------------|----------------|
| API endpoint | `/users/{id}/collections/{key}/items` | `/users/{id}/publications/items/` |
| Collection type | Standard `collections` resource | Special `publications` resource |
| Searchable by name? | Yes (`collections` → find by `name`) | **No** — not listed in `GET /collections` |
| Attachment download | `/users/{id}/items/{attachment_key}/file` | `/users/{id}/publications/items/{attachment_key}/file` |
| pyzotero support? | Full (`z.collection_items()`, etc.) | **None** — use raw `requests` |

## Trigger

Use this when:
- User says "zotero の私の出版物にあります" / "it's in My Publications"
- User says "My Publications からPDFを取得して"
- You need to download a PDF from a publication item

## Accessing My Publications Items

```python
import json, requests

creds = json.load(open("/opt/data/workspace/.skills/zotero_credentials.json"))
headers = {"Zotero-API-Version": "3", "Zotero-API-Key": creds["api_key"]}
base = f"https://api.zotero.org/users/{creds['user_id']}"

# List all top-level items
r = requests.get(f"{base}/publications/items/top", headers=headers, params={"limit": 100})
for item in r.json():
    d = item["data"]
    print(f"[{d['key']}] {d.get('title','?')[:60]} | {d.get('itemType')}")
```

## Downloading PDF Attachments

Attachments from publication items use a **different download endpoint** than regular items:

```python
# 1. Get children (attachments)
r = requests.get(f"{base}/publications/items/{parent_key}/children", headers=headers)
children = r.json()

# 2. Find PDF attachment and download
for ch in children:
    d = ch["data"]
    if d.get("contentType") == "application/pdf" or d.get("linkMode") == "imported_file":
        furl = f"{base}/publications/items/{d['key']}/file"
        fr = requests.get(furl, headers=headers, allow_redirects=True)
        if fr.status_code == 200 and len(fr.content) > 1000:
            with open("/tmp/publication_download.pdf", "wb") as f:
                f.write(fr.content)
            print(f"Downloaded: {len(fr.content)} bytes")
```

Verification after download: use `file` to confirm it's a real PDF, or check file size.

## Pitfalls

- **"My Publications" does NOT appear in `GET /collections`.** Searching for it by name in the collections list is guaranteed to fail. Always use the dedicated `/publications/items/` endpoint.
- **Attachment download URLs differ.** The regular `/items/{attachment_key}/file` endpoint returns 404 for publication items. You MUST use `/publications/items/{attachment_key}/file`.
- **pyzotero has NO dedicated publications methods.** Do not attempt `z.collection_items(pub_key)` — it will not find it. Use raw `requests` calls with the publications URL path.
- **Standard API semantics still apply:** version headers, pagination (`limit`, `start`, `offset`), and item type filtering work the same as regular items.
- **The parent item's `data.collections[]` is empty** for publication items — they are not members of any visible collection.
