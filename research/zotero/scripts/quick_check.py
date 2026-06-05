#!/usr/bin/env python3
"""Quick check of current Zotero collection structure (excluding _bak)."""
from pyzotero.zotero import Zotero
from pathlib import Path
import json

creds = json.loads(Path("/opt/data/workspace/.skills/zotero_credentials.json").read_text())
z = Zotero(creds["user_id"], "user", creds["api_key"])

# Fetch ALL collections
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

coll_map = {}
for c in all_coll:
    d = c["data"]
    m = c.get("meta", {})
    coll_map[d["key"]] = {
        "name": d["name"],
        "parent": d.get("parentCollection", False),
        "numItems": m.get("numItems", 0),
    }

# Find roots excluding _bak
roots = []
bak_keys = set()
for k, v in coll_map.items():
    p = v["parent"]
    if not p or p not in coll_map:
        if v["name"] == "_bak":
            bak_keys.add(k)
        else:
            roots.append((k, v))

# Also find all descendants of _bak
def find_descendants(key):
    results = {key}
    for k, v in coll_map.items():
        if v["parent"] == key:
            results.update(find_descendants(k))
    return results

bak_descendants = set()
for bk in bak_keys:
    bak_descendants.update(find_descendants(bk))

# Count what's inside bak
bak_nested = [v for k, v in coll_map.items() if k in bak_descendants and k not in bak_keys]
bak_total_items = sum(v.get("numItems", 0) for v in bak_nested if v["parent"] in bak_descendants)

# Main structure (excluding _bak)
main_keys = set(coll_map.keys()) - bak_descendants
main_map = {k: v for k, v in coll_map.items() if k in main_keys}

print(f"=== Current Zotero Structure ===")
print(f"Total collections:    {len(all_coll)}")
print(f"  Inside _bak:        {len(bak_descendants)} (backup)")
print(f"  Main structure:     {len(main_map)}")
print(f"  Items in _bak:      ~{bak_total_items}")

# List roots in main structure
print(f"\nRoot collections ({len(roots)}):")
for k, v in sorted(roots, key=lambda x: x[1].get("name", "")):
    # Count items recursively
    items = 0
    for k2, v2 in coll_map.items():
        p = v2["parent"]
        while p:
            if p == k:
                items += v2.get("numItems", 0)
                break
            p = coll_map.get(p, {}).get("parent", False)
    print(f"  📁 {v['name']}  [{k}]  (~{v.get('numItems',0)} + children)")
