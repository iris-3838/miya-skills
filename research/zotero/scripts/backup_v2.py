#!/usr/bin/env python3
"""Corrected backup of Zotero collection structure."""
from pyzotero.zotero import Zotero
from pathlib import Path
from collections import Counter
import json

creds = json.loads(Path("/opt/data/workspace/.skills/zotero_credentials.json").read_text())
z = Zotero(creds["user_id"], "user", creds["api_key"])

# Fetch ALL collections with pagination
all_coll = []
start = 0
while True:
    batch = z.collections(limit=100, start=start)
    if not batch:
        break
    all_coll.extend(batch)
    if len(batch) < 100:
        break
    start += 100

print(f"Total collections: {len(all_coll)}")

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
    for k, v in sorted(coll_map.items(), key=lambda x: x[1].get("name", "")):
        pk = v.get("parent", False)
        if pk == parent_key:
            n = v.get("numItems", "?")
            lines.append(f"{'  ' * indent}📁 {v['name']}  [{k}] ({n} items)")
            lines.extend(build_tree(k, indent + 1))
    return lines

lines = ["# Zotero Collection Structure (corrected)", "", "```"]
lines.extend(build_tree(False))
lines.append("```")
lines.append("")
lines.append(f"Total: {len(all_coll)} collections")

out_dir = Path("/opt/data/workspace/llm-kb.miya-lis.net/raw/papers/zotero/_bak")
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "structure_corrected.md").write_text("\n".join(lines))

# Save JSON
json_data = []
for key, v in sorted(coll_map.items()):
    json_data.append({
        "key": key,
        "name": v["name"],
        "parent": v["parent"] if v["parent"] else False,
        "version": v["version"],
        "numItems": v["numItems"],
    })
(out_dir / "collections_corrected.json").write_text(
    json.dumps(json_data, ensure_ascii=False, indent=2)
)

print(f"Saved to {out_dir}/")

# Check duplicates
name_counts = Counter(v["name"] for v in coll_map.values())
dups = {n: c for n, c in name_counts.items() if c > 1}
if dups:
    print(f"\nDuplicate names ({len(dups)} found):")
    for n, cnt in sorted(dups.items(), key=lambda x: -x[1])[:10]:
        keys = [(k, v.get("parent", "-")) for k, v in coll_map.items() if v["name"] == n]
        print(f"  「{n}」×{cnt}: {keys}")

# Check orphans
all_keys = set(coll_map.keys())
orphans = [v for v in coll_map.values() if v["parent"] and v["parent"] not in all_keys]
if not orphans:
    print("\nOrphaned collections: 0 ✅")
else:
    print(f"\nOrphaned collections ({len(orphans)}):")
    for v in orphans:
        print(f"  {v['name']} → missing parent: {v['parent']}")
