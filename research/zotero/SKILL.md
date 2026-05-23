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

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `401 Unauthorized` | Invalid/expired API key | Re-run `setup_credentials.py` |
| `412 Precondition Failed` | Version conflict | Re-fetch item before update |
| `409 Conflict` | Library locked | Wait and retry |
| `404 Not Found` | Wrong key or endpoint | Verify collection/item key |
| pyzotero import error | Wrong Python path | Use `python3 -m pip install pyzotero --break-system-packages` |

## Prerequisites
- Zotero account with API key (Settings → Feeds/API Keys)
- pyzotero installed (`python3 -m pip install pyzotero --break-system-packages`)
- Network access to `https://api.zotero.org`

## References
- `references/web-api-v3.md` — API endpoint reference
- `references/api.md` — pyzotero method reference & folder restructuring guide
- Zotero Web API v3: https://www.zotero.org/support/dev/web_api/v3
- pyzotero: https://github.com/urschrei/pyzotero
