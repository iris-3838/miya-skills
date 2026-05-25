#!/usr/bin/env python3
"""Check Zotero attachments: which files are actually downloadable."""
from pathlib import Path
import json
import httpx

CRED_FILE = Path("/workspace/.private/zotero_credentials.json")
creds = json.loads(CRED_FILE.read_text())
headers = {
    "Zotero-API-Key": creds["api_key"],
    "Zotero-API-Version": "3",
    "User-Agent": "HermesAgent-Check/1.0",
}

BASE = f"https://api.zotero.org/users/{creds['user_id']}"

def check_attachments() -> None:
    """Iterate items + children, check enclosure links."""
    stats = {
        "total_items": 0,
        "with_enclosure": 0,
        "ok_pdf": 0,
        "broken": 0,
        "no_enclosure": 0,
        "non_pdf": 0,
        "children_checked": 0,
        "children_with_file": 0,
    }
    broken_list = []
    ok_list = []
    other_list = []

    def check_file(item_key: str, title: str, enclosure: dict) -> None:
        """Check if a file attachment is accessible."""
        nonlocal stats
        file_url = enclosure["href"]
        mime = enclosure.get("type", "")
        stats["with_enclosure"] += 1

        if mime != "application/pdf":
            stats["non_pdf"] += 1
            other_list.append((item_key, title, mime[:30]))
            return

        try:
            head = httpx.head(
                file_url,
                headers=headers,
                timeout=10,
                follow_redirects=True,
            )
            if head.status_code == 200:
                cl = head.headers.get("Content-Length", "?")
                if cl.isdigit() and int(cl) > 0:
                    stats["ok_pdf"] += 1
                    ok_list.append((item_key, title, cl))
                    return
                # Content-Length=0 might mean broken
                stats["broken"] += 1
                broken_list.append((item_key, title, f"zero-length"))
                return
            # Try GET if HEAD fails
            get_resp = httpx.get(
                file_url, headers=headers, timeout=30, follow_redirects=True
            )
            if get_resp.status_code == 200 and len(get_resp.content) > 0:
                stats["ok_pdf"] += 1
                ok_list.append((item_key, title, str(len(get_resp.content))))
            else:
                stats["broken"] += 1
                broken_list.append((item_key, title, f"GET→{get_resp.status_code}"))
        except Exception as e:
            stats["broken"] += 1
            broken_list.append((item_key, title, f"error: {e}"))

    start = 0
    while True:
        resp = httpx.get(
            f"{BASE}/items/top",
            headers=headers,
            params={"limit": 100, "start": start},
            timeout=15,
        )
        batch = resp.json()
        if not batch:
            break
        stats["total_items"] += len(batch)

        for item in batch:
            data = item.get("data", {})
            item_type = data.get("itemType", "")
            item_key = data.get("key", "")
            title = (data.get("title", "") or "")[:60]

            # Check top-level item's own enclosure
            enclosure = item.get("links", {}).get("enclosure", {})
            if enclosure and enclosure.get("href"):
                check_file(item_key, title, enclosure)

            # Check children if this item might have attachments
            if item_type not in ("note", "attachment"):
                try:
                    children_resp = httpx.get(
                        f"{BASE}/items/{item_key}/children",
                        headers=headers,
                        timeout=10,
                    )
                    if children_resp.status_code == 200:
                        children = children_resp.json()
                        stats["children_checked"] += len(children)
                        for child in children:
                            cd = child.get("data", {})
                            c_key = cd.get("key", "")
                            c_title = (cd.get("title", "") or "")[:60]
                            c_enclosure = child.get("links", {}).get("enclosure", {})
                            if c_enclosure and c_enclosure.get("href"):
                                stats["children_with_file"] += 1
                                check_file(c_key, c_title, c_enclosure)
                except Exception:
                    pass

        if len(batch) < 100:
            break
        start += 100

    # Print results
    print(f"\n{'='*60}")
    print(f"Zotero Attachment Check")
    print(f"{'='*60}")
    print(f"Total items examined:  {stats['total_items']}")
    print(f"With enclosure link:   {stats['with_enclosure']}")
    print(f"  → PDF OK:            {stats['ok_pdf']}")
    print(f"  → PDF BROKEN:        {stats['broken']}")
    print(f"  → Non-PDF:           {stats['non_pdf']}")
    print(f"Without enclosure:     {stats['no_enclosure']}")

    if broken_list:
        print(f"\n{'─'*60}")
        print(f"BROKEN PDFs ({len(broken_list)}):")
        print(f"{'─'*60}")
        for key, title, reason in broken_list:
            coll_info = ""
            print(f"  [{key}] {title}")
            print(f"         Reason: {reason}")

    if ok_list:
        total_size = sum(int(s) for _, _, s in ok_list if s.isdigit())
        print(f"\nOK PDFs: {len(ok_list)} (total ~{total_size // 1024 // 1024} MB)")

    if other_list:
        print(f"\nNon-PDF attachments ({len(other_list)}):")
        for key, title, mime in other_list[:10]:
            print(f"  [{key}] {title} ({mime})")
        if len(other_list) > 10:
            print(f"  ... and {len(other_list)-10} more")

    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY: {stats['ok_pdf']} OK / {stats['broken']} Broken / {stats['non_pdf']} Non-PDF")

check_attachments()
