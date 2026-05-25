# Zotero Web API v3 — Reference

## Base
- `https://api.zotero.org`
- Required: `Zotero-API-Version: 3` header
- Auth: `Zotero-API-Key: <key>` header (or `Authorization: Bearer <key>`)
- Prefix: `/users/<userID>` or `/groups/<groupID>`

## Collections
| Method | Endpoint | Description |
|---|---|---|
| GET | `<prefix>/collections` | All collections |
| GET | `<prefix>/collections/top` | Top-level only |
| GET | `<prefix>/collections/<key>` | Specific collection |
| GET | `<prefix>/collections/<key>/collections` | Subcollections |
| POST | `<prefix>/collections` | Create collection(s) |
| PATCH | `<prefix>/collections/<key>` | Update collection |
| DELETE | `<prefix>/collections/<key>` | Delete collection |

**Collection data:** `{name, parentCollection, key, version}`

## Items
| Method | Endpoint | Description |
|---|---|---|
| GET | `<prefix>/items` | All items |
| GET | `<prefix>/items/top` | Top-level items |
| GET | `<prefix>/items/trash` | Trashed items |
| GET | `<prefix>/items/<key>` | Specific item |
| GET | `<prefix>/items/<key>/children` | Child items |
| GET | `<prefix>/collections/<key>/items` | Items in collection |
| POST | `<prefix>/items` | Create item(s) |
| PATCH | `<prefix>/items/<key>` | Update item |
| DELETE | `<prefix>/items/<key>` | Delete item |

## Query Parameters
| Param | Description |
|---|---|
| `q` | Quick search |
| `qmode` | `titleCreatorYear` or `everything` |
| `itemType` | Filter by type |
| `tag` | Filter by tag (boolean syntax) |
| `since=<version>` | Incremental sync |
| `format=json\|bib\|citation\|keys\|versions\|bibtex\|ris\|csljson` | Response format |
| `limit` | Max results (default: 100) |
| `start` | Offset for pagination |
| `includeTrashed=1` | Include trashed items |

## Adding Items to Collections

⛔ There is NO `POST /collections/{key}/items` endpoint. The API returns 400.

✅ Use `PATCH /items/{key}` to set the `collections` field directly:

```
PATCH /<prefix>/items/<key>
Content-Type: application/json

{"collections": ["targetCollectionKey1", "targetCollectionKey2"]}
```

The `collections` field is **replaced entirely** — include all desired collection keys.

### Bulk add to a collection
```python
import json, requests
for item in all_items:
    requests.patch(f'{base}/items/{item[\"key\"]}',
        headers={'If-Unmodified-Since-Version': str(item['version'])},
        json={'collections': [target_key]})
```

Also works for restoring from trash + adding at once:
```python
json={'deleted': False, 'collections': [target_key]}
```
`book`, `journalArticle`, `bookSection`, `conferencePaper`, `preprint`, `thesis`, `report`, `webpage`, `note`, `attachment`, `patent`, `film`, `artwork`, `letter`, `manuscript`, `interview`, `newspaperArticle`, `bill`, `hearing`, `statute`, `map`, `podcast`, `instantMessage`, `forumPost`, `email`, `document`, `presentation`, `computerProgram`, `dictionaryEntry`, `encyclopediaArticle`, `blogPost`
