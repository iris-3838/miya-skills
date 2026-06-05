#!/usr/bin/env python3
"""
Zotero → LLM-KB Sync Tool

Reads Zotero library via Web API and creates a collection-structure mirror
under /opt/data/workspace/llm-kb.miya-lis.net/raw/zotero/ for LLM knowledge base use.

Usage:
  python3 zotero_sync_kb.py                  # Full sync
  python3 zotero_sync_kb.py --dry-run        # Preview only, no changes
  python3 zotero_sync_kb.py --since          # Incremental (only changed since last sync)
  python3 zotero_sync_kb.py --stats          # Show stats only

Features:
  - Mirrors Zotero collection hierarchy as directory tree
  - Downloads PDF attachments via Web API
  - Items in multiple collections → symlink in secondary locations
  - Incremental sync via Last-Modified-Version tracking
  - Generates .zotero_index.json with full metadata
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CRED_FILE = Path("/opt/data/workspace/.skills/zotero_credentials.json")
KB_BASE = Path("/opt/data/workspace/llm-kb.miya-lis.net")
OUTPUT_DIR = KB_BASE / "raw" / "zotero"
STATE_FILE = OUTPUT_DIR / ".sync_state.json"
INDEX_FILE = OUTPUT_DIR / ".zotero_index.json"
USER_AGENT = "HermesAgent-ZoteroSync/1.0"

MIME_EXT = {
    "application/pdf": ".pdf",
    "text/html": ".html",
    "text/plain": ".txt",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "application/epub+zip": ".epub",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-powerpoint": ".ppt",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sanitize_filename(name: str, max_len: int = 120) -> str:
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    name = re.sub(r'\s+', " ", name).strip()
    name = name.rstrip(". ")
    if len(name) > max_len:
        name = name[:max_len].rsplit(" ", 1)[0] if " " in name[:max_len] else name[:max_len]
    return name or "untitled"


def get_ext(mime: str) -> str:
    return MIME_EXT.get(mime, "")


def load_credentials() -> dict[str, str]:
    if not CRED_FILE.exists():
        print(f"ERROR: Credentials not found at {CRED_FILE}", file=sys.stderr)
        sys.exit(2)
    return json.loads(CRED_FILE.read_text())


def get_headers() -> dict[str, str]:
    creds = load_credentials()
    return {
        "Zotero-API-Key": creds["api_key"],
        "Zotero-API-Version": "3",
        "User-Agent": USER_AGENT,
    }


def fmt_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


# ---------------------------------------------------------------------------
# Zotero API Client
# ---------------------------------------------------------------------------

def fetch_batch(url: str, headers: dict, **kwargs) -> list[dict]:
    """Fetch ALL items with pagination."""
    all_items = []
    start = 0
    limit = 100

    while True:
        params = {"limit": limit, "start": start, **kwargs}
        resp = httpx.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        all_items.extend(batch)
        if len(batch) < limit:
            break
        start += limit
        print(f"  ... fetched {len(all_items)} items", file=sys.stderr, end="\r")

    print(file=sys.stderr)
    return all_items


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def build_collection_tree(headers: dict) -> dict[str, dict]:
    """Fetch all collections and return a flat dict with hierarchy."""
    raw = fetch_batch(
        "https://api.zotero.org/users/14272705/collections",
        headers,
    )
    coll_map: dict[str, dict] = {}
    for c in raw:
        d = c["data"]
        coll_map[d["key"]] = {
            "key": d["key"],
            "name": d["name"],
            "parent": d.get("parentCollection", False) or None,
            "version": d.get("version", 0),
            "children": [],
        }
    for key, c in coll_map.items():
        if c["parent"] and c["parent"] in coll_map:
            coll_map[c["parent"]]["children"].append(key)
    return coll_map


def get_collection_path(coll_key: str, coll_tree: dict[str, dict]) -> list[str]:
    """Walk up the tree to get the full path segments."""
    parts = []
    node = coll_tree.get(coll_key)
    while node:
        parts.insert(0, sanitize_filename(node["name"]))
        parent_key = node["parent"]
        node = coll_tree.get(parent_key) if parent_key else None
    return parts


def run_sync(
    headers: dict,
    coll_tree: dict[str, dict],
    output_dir: Path,
    dry_run: bool = False,
    since: int | None = None,
) -> dict:
    """Main sync logic."""
    stats = {
        "items_examined": 0,
        "files_found": 0,
        "files_downloaded": 0,
        "files_skipped": 0,
        "symlinks_created": 0,
        "errors": 0,
        "bytes_downloaded": 0,
    }
    index_entries = []

    url = "https://api.zotero.org/users/14272705/items/top"
    params: dict[str, Any] = {"itemType": "-note"}
    if since:
        params["since"] = since

    print(f"Fetching items from Zotero API...")
    items = fetch_batch(url, headers, **params)
    stats["items_examined"] = len(items)

    print(f"Processing {len(items)} items...")

    for item in items:
        data = item.get("data", {})
        links = item.get("links", {})
        enclosure = links.get("enclosure", {})
        item_key = data.get("key")

        if not enclosure or not enclosure.get("href"):
            continue

        # Determine file extension
        file_url = enclosure["href"]
        mime = enclosure.get("type", "")
        ext = get_ext(mime) or ""
        if not ext:
            url_lower = file_url.lower()
            if ".pdf" in url_lower:
                ext = ".pdf"
            elif url_lower.endswith(".html") or url_lower.endswith(".htm"):
                ext = ".html"
            else:
                ext = ".bin"

        # Determine filename
        title_raw = data.get("title", "").strip() or item_key
        safe_title = sanitize_filename(title_raw)
        if safe_title.lower().endswith(ext):
            safe_title = safe_title[:-len(ext)]
        safe_title = safe_title.strip() or item_key
        filename = f"{safe_title}{ext}"
        collections = data.get("collections", [])

        if not collections:
            collections = ["__uncategorized__"]

        stats["files_found"] += 1

        primary_coll = collections[0]
        if primary_coll == "__uncategorized__":
            primary_path = ["uncategorized"]
        else:
            primary_path = get_collection_path(primary_coll, coll_tree)
        primary_dir = output_dir.joinpath(*primary_path)
        filepath = primary_dir / filename

        if not dry_run:
            primary_dir.mkdir(parents=True, exist_ok=True)

            if filepath.exists():
                stats["files_skipped"] += 1
            else:
                try:
                    file_resp = httpx.get(
                        file_url, headers=headers, timeout=120, follow_redirects=True
                    )
                    file_resp.raise_for_status()
                    filepath.write_bytes(file_resp.content)
                    stats["files_downloaded"] += 1
                    stats["bytes_downloaded"] += len(file_resp.content)
                    print(f"  ↓ {filepath.name}")
                except Exception as e:
                    print(f"  ✗ Failed to download {item_key}: {e}", file=sys.stderr)
                    stats["errors"] += 1
                    continue

            # Handle secondary collections → symlinks
            for extra_coll in collections[1:]:
                if extra_coll == "__uncategorized__":
                    extra_path = ["uncategorized"]
                else:
                    extra_path = get_collection_path(extra_coll, coll_tree)
                extra_dir = output_dir.joinpath(*extra_path)
                extra_dir.mkdir(parents=True, exist_ok=True)
                link_path = extra_dir / filename
                if not link_path.exists():
                    try:
                        rel_target = os.path.relpath(filepath, start=extra_dir)
                        os.symlink(rel_target, link_path)
                        stats["symlinks_created"] += 1
                    except Exception as e:
                        print(f"  ✗ Symlink error: {e}", file=sys.stderr)

            # Build index entry
            main_coll_name = coll_tree.get(primary_coll, {}).get("name", "uncategorized") if primary_coll != "__uncategorized__" else "uncategorized"
            index_entries.append({
                "zotero_key": item_key,
                "title": title_raw,
                "filename": filename,
                "path": str(filepath.relative_to(output_dir)),
                "primary_collection": main_coll_name,
                "mime_type": mime,
                "file_size": filepath.stat().st_size if filepath.exists() else 0,
                "date": data.get("date", ""),
                "item_type": data.get("itemType", ""),
                "creators": data.get("creators", []),
                "extra": data.get("extra", ""),
                "doi": data.get("DOI", ""),
                "url": data.get("url", ""),
                "tags": [t["tag"] for t in data.get("tags", [])],
                "collections": [coll_tree.get(k, {}).get("name", k) if k in coll_tree else k for k in collections],
                "synced_at": datetime.now(timezone.utc).isoformat(),
            })
        else:
            path_str = "/".join(primary_path)
            print(f"  [dry-run] {title_raw[:50]} → {path_str}/{filename}")

    # Write index
    if not dry_run and index_entries:
        existing = {}
        if INDEX_FILE.exists():
            try:
                existing_list = json.loads(INDEX_FILE.read_text())
                for e in existing_list:
                    existing[e["zotero_key"]] = e
            except (json.JSONDecodeError, KeyError):
                pass
        for e in index_entries:
            existing[e["zotero_key"]] = e
        INDEX_FILE.write_text(
            json.dumps(list(existing.values()), ensure_ascii=False, indent=2)
        )

    return stats


def get_last_version(output_dir: Path) -> int:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text()).get("last_version", 0)
        except (json.JSONDecodeError, KeyError):
            pass
    return 0


def save_last_version(output_dir: Path, version: int):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({
        "last_version": version,
        "synced_at": datetime.now(timezone.utc).isoformat(),
    }, indent=2))


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Zotero → LLM-KB Sync")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    parser.add_argument("--since", action="store_true", help="Incremental sync")
    parser.add_argument("--stats", action="store_true", help="Show stats only")
    parser.add_argument("--version", type=int, default=None, help="Sync since version")
    args = parser.parse_args()

    headers = get_headers()
    output_dir = OUTPUT_DIR

    if args.stats:
        print(f"Output: {output_dir}")
        print(f"Last synced version: {get_last_version(output_dir)}")
        if INDEX_FILE.exists():
            index = json.loads(INDEX_FILE.read_text())
            print(f"Index entries: {len(index)}")
        return

    dry_run = args.dry_run
    since = args.version
    if args.since:
        since = get_last_version(output_dir)
        print(f"Incremental sync since version: {since}")

    if dry_run:
        print("🔍 DRY RUN — no changes will be made")

    print(f"Building collection tree...")
    coll_tree = build_collection_tree(headers)
    print(f"Found {len(coll_tree)} collections")

    if not coll_tree:
        print("No collections found.")
        return

    stats = run_sync(headers, coll_tree, output_dir, dry_run=dry_run, since=since)

    print(f"\n=== Sync Results ===")
    print(f"Items examined:  {stats['items_examined']}")
    print(f"Files found:     {stats['files_found']}")
    if not dry_run:
        print(f"Downloaded:      {stats['files_downloaded']}")
        print(f"Skipped (exist): {stats['files_skipped']}")
        print(f"Symlinks:        {stats['symlinks_created']}")
        print(f"Errors:          {stats['errors']}")
        print(f"Data:            {fmt_bytes(stats['bytes_downloaded'])}")

        if stats['files_downloaded'] > 0 or stats['symlinks_created'] > 0:
            resp = httpx.get(
                "https://api.zotero.org/users/14272705/collections?limit=1",
                headers=headers,
                timeout=15,
            )
            last_v = int(resp.headers.get("Last-Modified-Version", 0))
            save_last_version(output_dir, last_v)
            print(f"Saved sync state (version: {last_v})")
    else:
        print(f"Would download:  {stats['files_found']}")


if __name__ == "__main__":
    main()
