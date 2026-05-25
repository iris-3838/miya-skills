#!/usr/bin/env python3
"""Zotero link checker: find broken references, URLs, and orphans."""
from pyzotero.zotero import Zotero
import json
import httpx
from pathlib import Path

creds = json.loads(Path("/workspace/.private/zotero_credentials.json").read_text())
z = Zotero(creds["user_id"], "user", creds["api_key"])
headers = {"Zotero-API-Key": creds["api_key"], "Zotero-API-Version": "3"}

# 1. Fetch ALL collections (full list to check membership)
print("=== Checking collection integrity ===")
all_coll = []
start = 0
while True:
    batch = z.collections(limit=100, start=start)
    if not batch: break
    all_coll.extend(batch)
    if len(batch) < 100: break
    start += 100
coll_keys = set()
coll_name = {}
for c in all_coll:
    d = c["data"]
    coll_keys.add(d["key"])
    coll_name[d["key"]] = d["name"]

# Check for orphaned subcollections
for c in all_coll:
    d = c["data"]
    parent = d.get("parentCollection", False)
    if parent and parent not in coll_keys:
        print(f"  ⚠ Orphaned collection: {d['name']} [{d['key']}] → missing parent {parent}")

# 2. Check items
print("\n=== Fetching all items (this may take a moment) ===")
all_items = []
start = 0
while True:
    batch = z.items(limit=100, start=start, itemType="-note")
    if not batch: break
    all_items.extend(batch)
    if len(batch) < 100: break
    start += 100
print(f"  {len(all_items)} top-level items loaded")

# Also get all children (notes, attachments) for parent reference check
# pyzotero doesn't support comma-separated itemType, so we filter in client
all_children = []
for item in all_items:
    if item["data"].get("itemType") in ("attachment", "note"):
        all_children.append(item)
# Also fetch remaining items that might be notes
start = 0
while True:
    batch = z.items(limit=100, start=start)
    if not batch: break
    for item in batch:
        if item["data"].get("itemType") in ("attachment", "note") and item not in all_children:
            all_children.append(item)
    if len(batch) < 100: break
    start += 100
print(f"  {len(all_children)} child items (attachments/notes) identified")

parent_keys = set(i["data"]["key"] for i in all_items)
child_parent_keys = set()

broken_collections = []
broken_urls = []
broken_relations = []
broken_parents = []
missing_children_ref = []

for item in all_items:
    data = item["data"]
    key = data["key"]
    title = data.get("title", "(no title)")[:60]

    # Check collection membership
    for ck in data.get("collections", []):
        if ck not in coll_keys:
            broken_collections.append((key, title, ck))

    # Check relations
    for rel_type, rel_target in data.get("relations", {}).items():
        if rel_target and "zotero.org" in rel_target:
            # Check if referenced item exists in our loaded set
            ref_key = rel_target.split("/")[-1]
            if ref_key and len(ref_key) == 8:
                if ref_key not in parent_keys and ref_key not in {c["data"]["key"] for c in all_children}:
                    broken_relations.append((key, title, rel_type, rel_target))

    # Check URL (basic check)
    url = data.get("url", "")
    if url and not url.startswith("http"):
        broken_urls.append((key, title, f"Invalid URL: {url}"))

# Check children for parent reference
for item in all_children:
    data = item["data"]
    key = data["key"]
    parent_item = data.get("parentItem")
    child_parent_keys.add(parent_item)
    if parent_item and parent_item not in parent_keys:
        title = data.get("title", "(no title)")[:60]
        broken_parents.append((key, title, parent_item))

# Summary
print("\n=== Results ===")

if broken_collections:
    print(f"\n⚠ Items referencing non-existent collections ({len(broken_collections)}):")
    for key, title, ck in broken_collections[:20]:
        print(f"  [{key}] {title} → missing collection {ck}")
    if len(broken_collections) > 20:
        print(f"  ... and {len(broken_collections)-20} more")

if broken_relations:
    print(f"\n⚠ Items with broken relations ({len(broken_relations)}):")
    for key, title, rtype, target in broken_relations[:20]:
        print(f"  [{key}] {title}")
        print(f"    {rtype}: {target}")
    if len(broken_relations) > 20:
        print(f"  ... and {len(broken_relations)-20} more")

if broken_parents:
    print(f"\n⚠ Child items with missing parent ({len(broken_parents)}):")
    for key, title, parent in broken_parents[:20]:
        print(f"  [{key}] {title} → missing parent {parent}")
    if len(broken_parents) > 20:
        print(f"  ... and {len(broken_parents)-20} more")

if broken_urls:
    print(f"\n⚠ Items with invalid URLs ({len(broken_urls)}):")
    for key, title, url in broken_urls[:10]:
        print(f"  [{key}] {title}: {url}")
    if len(broken_urls) > 10:
        print(f"  ... and {len(broken_urls)-10} more")

# Attachment link modes
print("\n=== Attachment type analysis ===")
link_modes = {}
for item in all_children:
    data = item["data"]
    mode = data.get("linkMode", "unknown")
    if mode not in link_modes:
        link_modes[mode] = 0
    link_modes[mode] += 1
for mode, count in sorted(link_modes.items(), key=lambda x: -x[1]):
    print(f"  {mode}: {count}")

# Check linked attachments for dead targets
linked_attachments = []
for item in all_children:
    data = item["data"]
    if data.get("linkMode") in ("linked_url", "linked_file"):
        url = data.get("url", "") or data.get("path", "")
        ttl = data.get("title", "(no title)")[:50]
        parent = data.get("parentItem", "?")
        linked_attachments.append((data["key"], ttl, url, parent))

if linked_attachments:
    print(f"\n⚠ Linked attachments (target may be broken):")
    print(f"  (Testing first 20 with HTTP HEAD...)")
    tested = 0
    for key, ttl, url, parent in linked_attachments[:20]:
        if url.startswith("http"):
            try:
                resp = httpx.head(url, timeout=10, follow_redirects=True)
                if resp.status_code >= 400:
                    print(f"  🔴 [{key}] {ttl} → HTTP {resp.status_code}: {url[:80]}")
                else:
                    print(f"  🟢 [{key}] {ttl} → {resp.status_code}")
            except Exception as e:
                print(f"  ⚠ [{key}] {ttl} → Error: {str(e)[:60]}")
            tested += 1
    if len(linked_attachments) > 20:
        print(f"  ... and {len(linked_attachments)-20} more untested")

if not any([broken_collections, broken_relations, broken_parents, broken_urls]):
    print("  ✅ No broken links found!")

print("\n=== Done ===")
