#!/usr/bin/env python3
"""Analyze Zotero collections for research vs non-research separation."""
from pyzotero.zotero import Zotero
from collections import Counter
import json
from pathlib import Path

creds = json.loads(Path("/opt/data/workspace/.skills/zotero_credentials.json").read_text())
z = Zotero(creds["user_id"], "user", creds["api_key"])

# Fetch ALL collections with pagination
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

# Get all top-level parents (roots)
roots = []
for k, v in coll_map.items():
    p = v["parent"]
    if not p or p not in coll_map:
        roots.append((k, v))

# Categorize roots
categories = {
    "Research": [],
    "Non-Research": [],
    "Mixed": [],
    "Empty/Undecided": [],
}

# Count items per collection recursively
def count_items_recursive(key, coll_map):
    total = coll_map.get(key, {}).get("numItems", 0)
    for k, v in coll_map.items():
        if v.get("parent") == key:
            total += count_items_recursive(k, coll_map)
    return total

research_keywords = [
    "図書館情報学", "LIS", "学術", "書誌", "情報哲学", "知識組織",
    "Journal of Documentation", "Library Trends", "情報学",
    "哲学", "システム論", "機械学習", "人工知能", "KO", "情報検索",
    "情報探索", "学術コミュニケーション", "ドメイン分析",
    "Floridi", "Hjørland", "Bates", "方法論", "書評",
    "コンピュータサイエンス", "強化学習", "自己組織性",
    "情報について考える", "情報の哲学", "情報評価",
    "論文", "研究"
]

non_research_keywords = [
    "小説", "マンガ", "実用", "Private", "借りてる",
    "講義資料", "専門英語", "卒論", "期末レポート",
    "Docker", "Vim", "Python", "Rust", "Java", "LaTeX",
    "システム数理", "プログラム言語"
]

def classify_collection(key, coll_map, depth=0):
    v = coll_map.get(key, {})
    name = v.get("name", "")
    total = count_items_recursive(key, coll_map)
    
    if total == 0 and depth == 0:
        return "Empty/Undecided"
    
    # Check name keywords
    is_research = any(kw in name for kw in research_keywords)
    is_non_research = any(kw in name for kw in non_research_keywords)
    
    if is_research and not is_non_research:
        return "Research"
    elif is_non_research and not is_research:
        return "Non-Research"
    
    # Check children for mixed collections
    children_classifications = []
    for k, cv in coll_map.items():
        if cv.get("parent") == key:
            children_classifications.append(classify_collection(k, coll_map, depth+1))
    
    if all(c == "Research" for c in children_classifications):
        return "Research"
    elif all(c == "Non-Research" for c in children_classifications):
        return "Non-Research"
    elif any(c == "Research" for c in children_classifications) and any(c == "Non-Research" for c in children_classifications):
        return "Mixed"
    elif "Research" in children_classifications:
        return "Research"  # Default research if some children are research
    elif total == 0:
        return "Empty/Undecided"
    else:
        return "Non-Research"  # Default non-research

# Print tree with classification
def print_tree(parent_key=False, indent=0, prefix=""):
    lines = []
    items = [(k, v) for k, v in sorted(coll_map.items(), key=lambda x: x[1].get("name", "")) if v.get("parent") == parent_key]
    for i, (key, v) in enumerate(items):
        is_last = i == len(items) - 1
        connector = "└── " if is_last else "├── "
        child_prefix = "    " if is_last else "│   "
        n = v.get("numItems", 0)
        cat = classify_collection(key, coll_map)
        cat_mark = {"Research": "📘", "Non-Research": "📗", "Mixed": "📙", "Empty/Undecided": "📦"}
        mark = cat_mark.get(cat, "📄")
        lines.append(f"{prefix}{connector}{mark} {v['name']}  [{key}] ({n} items) — {cat}")
        lines.extend(print_tree(key, indent+1, prefix + child_prefix))
    return lines

print("=== Zotero Collection Analysis: Research vs Non-Research ===\n")
lines = print_tree()
for l in lines:
    print(l)

# Summary
total = len(all_coll)
research_count = sum(1 for k in coll_map if classify_collection(k, coll_map) == "Research")
non_research_count = sum(1 for k in coll_map if classify_collection(k, coll_map) == "Non-Research")
mixed_count = sum(1 for k in coll_map if classify_collection(k, coll_map) == "Mixed")
empty_count = sum(1 for k in coll_map if classify_collection(k, coll_map) == "Empty/Undecided")

# Item counts per research items (top-level key items)
research_items = 0
non_research_items = 0
for k, v in coll_map.items():
    cat = classify_collection(k, coll_map)
    if v.get("parent") and coll_map.get(v["parent"]):
        parent_cat = classify_collection(v["parent"], coll_map)
        # Leaf collections - count items
        if cat == "Research" or parent_cat == "Research":
            research_items += v.get("numItems", 0)
        elif cat == "Non-Research" or parent_cat == "Non-Research":
            non_research_items += v.get("numItems", 0)

print(f"\n{'='*60}")
print(f"Summary:")
print(f"  Research collections:     {research_count}")
print(f"  Non-Research collections: {non_research_count}")
print(f"  Mixed:                   {mixed_count}")
print(f"  Empty/Undecided:         {empty_count}")
print(f"  Total:                   {total}")
