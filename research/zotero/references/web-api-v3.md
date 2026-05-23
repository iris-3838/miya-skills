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

## Item Types
`book`, `journalArticle`, `bookSection`, `conferencePaper`, `preprint`, `thesis`, `report`, `webpage`, `note`, `attachment`, `patent`, `film`, `artwork`, `letter`, `manuscript`, `interview`, `newspaperArticle`, `bill`, `hearing`, `statute`, `map`, `podcast`, `instantMessage`, `forumPost`, `email`, `document`, `presentation`, `computerProgram`, `dictionaryEntry`, `encyclopediaArticle`, `blogPost`
