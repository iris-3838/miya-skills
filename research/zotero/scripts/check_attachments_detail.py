#!/usr/bin/env python3
"""Check attachment items' link modes and accessibility."""
import httpx, json
from pathlib import Path

creds = json.loads(Path("/opt/data/workspace/.skills/zotero_credentials.json").read_text())
headers = {"Zotero-API-Key": creds["api_key"], "Zotero-API-Version": "3"}

# Fetch ALL items to find attachment-type items
print("Fetching all items...")
all_items = []
start = 0
while True:
    resp = httpx.get(
        "https://api.zotero.org/users/14272705/items",
        headers=headers,
        params={"limit": 100, "start": start},
        timeout=30,
    )
    batch = resp.json()
    if not batch: break
    all_items.extend(batch)
    if len(batch) < 100: break
    start += 100

print(f"Total items: {len(all_items)}")

# Separate attachment items
attachments = [i for i in all_items if i.get("data", {}).get("itemType") == "attachment"]
print(f"Attachment items: {len(attachments)}")

# Analyze by link mode
modes = {}
for att in attachments:
    mode = att["data"].get("linkMode", "(none)")
    modes[mode] = modes.get(mode, 0) + 1

print("\n=== Link Modes ===")
for mode, count in sorted(modes.items(), key=lambda x: -x[1]):
    print(f"  {mode}: {count}")

# Check linked files (these point to local paths)
linked_file = [a for a in attachments if a["data"].get("linkMode") == "linked_file"]
if linked_file:
    print(f"\n=== Linked Files (local paths, likely broken) ===")
    for att in linked_file[:20]:
        d = att["data"]
        path = d.get("path", "(no path)")
        title = d.get("title", "(no title)")[:40]
        parent = d.get("parentItem", "?")
        # Check if path exists
        exists = Path(path).exists() if path else False
        status = "✅ EXISTS" if exists else "🔴 BROKEN"
        print(f"  [{d['key']}] {title}")
        print(f"    Path: {path[:80]}")
        print(f"    Parent: {parent}")
        print(f"    Status: {status}")
    if len(linked_file) > 20:
        print(f"  ... and {len(linked_file)-20} more")

# Check linked URLs
linked_url = [a for a in attachments if a["data"].get("linkMode") == "linked_url"]
if linked_url:
    print(f"\n=== Linked URLs (test with HEAD) ===")
    tested = 0
    for att in linked_url[:30]:
        d = att["data"]
        url = d.get("url", "")
        title = d.get("title", "(no title)")[:40]
        if url.startswith("http"):
            try:
                resp = httpx.head(url, timeout=10, follow_redirects=True)
                status = f"HTTP {resp.status_code} {'✅' if resp.status_code < 400 else '🔴'}"
            except Exception as e:
                status = f"🔴 ERROR: {str(e)[:40]}"
            print(f"  [{d['key']}] {title}")
            print(f"    URL: {url[:80]}")
            print(f"    Status: {status}")
            tested += 1
    if len(linked_url) > 30:
        print(f"  ... and {len(linked_url)-30} more")

# Check imported files (should be accessible but test some)
imported = [a for a in attachments if a["data"].get("linkMode") == "imported_file" or a["data"].get("linkMode") == "imported_url"]
if imported:
    print(f"\n=== Imported Files (test sample) ===")
    for att in imported[:10]:
        d = att["data"]
        key = d["key"]
        title = d.get("title", "(no title)")[:40]
        # Try to get file
        try:
            resp = httpx.get(
                f"https://api.zotero.org/users/14272705/items/{key}/file",
                headers=headers,
                timeout=15,
                follow_redirects=True,
            )
            if resp.status_code == 200:
                print(f"  ✅ [{key}] {title} — {len(resp.content)/1024:.0f}KB")
            elif resp.status_code == 403:
                print(f"  🔴 [{key}] {title} — 403 Forbidden")
            else:
                print(f"  ⚠ [{key}] {title} — HTTP {resp.status_code}")
        except Exception as e:
            print(f"  ✗ [{key}] {title} — {str(e)[:60]}")

# Check attachments with NO linkMode (storage type?)
no_mode = [a for a in attachments if not a["data"].get("linkMode") and a["data"].get("contentType")]
if no_mode:
    print(f"\n=== Attachments without linkMode but with content type ===")
    for att in no_mode[:5]:
        d = att["data"]
        title = d.get("title", "(no title)")[:40]
        ct = d.get("contentType", "?")
        parent = d.get("parentItem", "?")
        print(f"  [{d['key']}] {title} (type: {ct}, parent: {parent})")

print(f"\n=== Summary ===")
print(f"Total attachment items: {len(attachments)}")
print(f"  imported_file/url:    {len(imported)}")
print(f"  linked_file:          {len(linked_file)}")
print(f"  linked_url:           {len(linked_url)}")
print(f"  no linkMode:          {len(no_mode)}")
print(f"  other:                {len(attachments) - len(imported) - len(linked_file) - len(linked_url) - len(no_mode)}")
