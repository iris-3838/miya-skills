#!/usr/bin/env python3
"""Save current Zotero collection structure as backup."""
from pyzotero.zotero import Zotero
import json
from pathlib import Path

creds = json.loads(Path("/workspace/.private/zotero_credentials.json").read_text())
z = Zotero(creds["user_id"], "user", creds["api_key"])

# Get all collections with pagination
all_coll = []
start = 0
while True:
    batch = z.collections(limit=100, start=start)
    if not batch: break
    all_coll.extend(batch)
    if len(batch) < 100: break
    start += 100

# Build map
coll_map = {}
for c in all_coll:
    d = c["data"]
    m = c.get("meta", {})
    coll_map[d["key"]] = {
        "name": d["name"],
        "parent": d.get("parentCollection", False),
        "version": d.get("version", 0),
        "numItems": m.get("numItems", 0),
    }

# Recursive tree
def build_tree(parent_key=False, indent=0):
    lines = []
    items = sorted(coll_map.items(), key=lambda x: x[1].get("name", ""))
    for k, v in items:
        pk = v.get("parent", False)
        if pk == parent_key:
            n = v.get("numItems", "?")
            lines.append(f"{'  '*indent}📁 {v['name']}  [{k}] ({n} items)")
            lines.extend(build_tree(k, indent+1))
    return lines

lines = ["# Zotero Collection Structure (backup)", "", f"Saved: 2026-05-23", "", "```"]
lines.extend(build_tree(False))
lines.append("```")
lines.append("")
lines.append(f"Total: {len(all_coll)} collections")
result = "\n".join(lines)

# Save
out_dir = Path("/workspace/llm-kb.miya-lis.net/raw/papers/zotero/_bak")
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "collection_structure.md").write_text(result)

# JSON
json_data = []
for key, v in sorted(coll_map.items()):
    json_data.append({
        "key": key,
        "name": v["name"],
        "parent": v.get("parent", False),
        "version": v.get("version", 0),
        "numItems": v.get("numItems", 0),
    })
(out_dir / "collections.json").write_text(
    json.dumps(json_data, ensure_ascii=False, indent=2)
)

print(result)
print(f"\n--- Backup saved to {out_dir}/ ---")
