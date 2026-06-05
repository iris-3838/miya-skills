#!/usr/bin/env python3
"""
Zotero → LLM-KB Sync Tool

Zoteroのコレクション構造をそのままraw/papers/zotero/以下にミラーし、
各アイテムをMarkdownファイルとして同期する。

Usage:
  python3 zotero_kb_sync.py                    # 全ライブラリ同期
  python3 zotero_kb_sync.py --collection KEY   # 特定コレクションのみ
  python3 zotero_kb_sync.py --dry-run          # 同期せずに構造のみ表示
  python3 zotero_kb_sync.py --group GROUP_ID   # グループライブラリを同期
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# ── Credentials ──────────────────────────────────────────────
from pyzotero.zotero import Zotero

CRED_FILE = Path("/opt/data/workspace/.skills/zotero_credentials.json")
KB_ROOT = Path("/opt/data/workspace/llm-kb.miya-lis.net")
ZOTERO_DIR = KB_ROOT / "raw" / "papers" / "zotero"
INDEX_FILE = ZOTERO_DIR / "index.md"

# ── Credentials loader ──────────────────────────────────────


def load_creds() -> dict[str, str]:
    if not CRED_FILE.exists():
        print(f"Credentials not found at {CRED_FILE}", file=sys.stderr)
        sys.exit(1)
    return json.loads(CRED_FILE.read_text())


def get_client(library_type: str = "user", library_id: str | None = None) -> Zotero:
    creds = load_creds()
    lid = library_id or creds["user_id"]
    return Zotero(lid, library_type, creds["api_key"])


# ── Item data fetching ──────────────────────────────────────


def fetch_all_items(z: Zotero, collection_key: str | None = None) -> list[dict]:
    """Fetch all items from a library or collection, handling pagination."""
    all_items: list[dict] = []
    start = 0
    limit = 100
    while True:
        kwargs: dict[str, Any] = {"limit": limit, "start": start}
        if collection_key:
            batch = z.collection_items(collection_key, **kwargs)
        else:
            kwargs["itemType"] = "-note"  # exclude standalone notes
            batch = z.items(**kwargs)
        if not batch:
            break
        all_items.extend(batch)
        if len(batch) < limit:
            break
        start += limit
    return all_items


def safe_filename(title: str, max_len: int = 60) -> str:
    """Convert a paper title to a safe filename."""
    # Remove or replace problematic characters
    name = re.sub(r'[<>:"/\\|?*]', "", title)
    name = re.sub(r"\s+", " ", name).strip()
    if len(name) > max_len:
        name = name[:max_len].rsplit(" ", 1)[0] if " " in name[:max_len] else name[:max_len]
    return name or "untitled"


def collection_path(base: Path, z: Zotero, collection_key: str, depth: int = 0) -> Path:
    """Build filesystem path matching Zotero collection hierarchy."""
    coll = z.collection(collection_key)
    if not coll:
        return base
    data = coll.get("data", {})
    name = safe_filename(data.get("name", "unknown"), 40)
    parent = data.get("parentCollection", False)
    if parent and depth < 10:
        parent_path = collection_path(base, z, parent, depth + 1)
        return parent_path / name
    else:
        return base / name


def build_item_md(item: dict) -> str:
    """Generate Markdown for a Zotero item."""
    data = item.get("data", {})
    key = data.get("key", "")
    item_type = data.get("itemType", "")
    title = data.get("title", "Untitled") or "Untitled"
    creators = data.get("creators", [])
    date = data.get("date", "")
    doi = data.get("DOI", "") or ""
    url = data.get("url", "") or ""
    abstract = data.get("abstractNote", "") or ""
    tags = [t.get("tag", "") for t in data.get("tags", [])]
    extra = data.get("extra", "") or ""
    collections = data.get("collections", [])
    publication = data.get("publicationTitle", "") or data.get("bookTitle", "") or data.get("proceedingsTitle", "") or ""
    publisher = data.get("publisher", "") or ""
    place = data.get("place", "") or ""
    volume = data.get("volume", "") or ""
    issue = data.get("issue", "") or ""
    pages = data.get("pages", "") or ""
    isbn = data.get("ISBN", "") or ""
    issn = data.get("ISSN", "") or ""

    # Build creator string
    creator_strs = []
    for c in creators:
        if "name" in c:
            creator_strs.append(c["name"])
        elif "lastName" in c:
            fn = c.get("firstName", "")
            creator_strs.append(f"{c['lastName']}, {fn}")
    creators_text = "; ".join(creator_strs)

    # Build frontmatter
    frontmatter_lines = ["---"]
    frontmatter_lines.append(f'title: "{title}"')
    frontmatter_lines.append(f"type: {item_type}")
    frontmatter_lines.append(f"zotero_key: {key}")
    if creators_text:
        frontmatter_lines.append(f"creators: '{creators_text}'")
    if date:
        frontmatter_lines.append(f"date: {date}")
    if doi:
        frontmatter_lines.append(f"doi: {doi}")
    if url:
        frontmatter_lines.append(f"url: {url}")
    if publication:
        frontmatter_lines.append(f"publication: '{publication}'")
    if publisher:
        frontmatter_lines.append(f"publisher: '{publisher}'")
    if isbn:
        frontmatter_lines.append(f"isbn: {isbn}")
    if issn:
        frontmatter_lines.append(f"issn: {issn}")
    if volume:
        frontmatter_lines.append(f"volume: {volume}")
    if issue:
        frontmatter_lines.append(f"issue: {issue}")
    if pages:
        frontmatter_lines.append(f"pages: {pages}")
    if tags:
        frontmatter_lines.append(f"tags: [{', '.join(tags)}]")
    frontmatter_lines.append(f"synced: {datetime.now().strftime('%Y-%m-%d')}")

    # Zotero API link
    zotero_url = f"https://api.zotero.org/users/{load_creds()['user_id']}/items/{key}"
    if collections:
        col_str = ", ".join(collections)
        frontmatter_lines.append(f"collections: [{col_str}]")
    frontmatter_lines.append("---")

    lines = []
    lines.append(f"\n# {title}\n")

    if creators_text:
        lines.append(f"**著者:** {creators_text}  ")
    if date:
        lines.append(f"**日付:** {date}  ")
    if publication:
        lines.append(f"**掲載誌:** {publication}  ")
    if publisher:
        lines.append(f"**出版社:** {publisher}  ")
    if doi:
        lines.append(f"**DOI:** [{doi}](https://doi.org/{doi})  ")
    if url:
        lines.append(f"**URL:** [{url}]({url})  ")
    if volume or issue or pages:
        vol_iss = f"Vol. {volume}" if volume else ""
        if issue:
            vol_iss += f", No. {issue}" if vol_iss else f"No. {issue}"
        if pages:
            vol_iss += f", pp. {pages}" if vol_iss else f"pp. {pages}"
        if vol_iss:
            lines.append(f"**詳細:** {vol_iss}  ")

    lines.append(f"\n**Zotero Key:** `{key}`  ")
    lines.append(f"**Item Type:** `{item_type}`  ")

    if tags:
        lines.append(f"\n**Tags:** {', '.join(f'`{t}`' for t in tags)}  ")

    if abstract:
        lines.append(f"\n## Abstract\n\n{abstract}\n")

    if extra:
        lines.append(f"\n## Extra Notes\n\n```\n{extra}\n```\n")

    lines.append(f"\n---\n_Synced from Zotero on {datetime.now().strftime('%Y-%m-%d %H:%M')}_")

    result = "\n".join(frontmatter_lines) + "\n" + "\n".join(lines)
    return result


def build_collection_index(z: Zotero, collection_key: str, items: list[dict]) -> str:
    """Generate an index.md for a collection directory."""
    coll = z.collection(collection_key)
    name = coll.get("data", {}).get("name", "Collection") if coll else "Collection"
    now = datetime.now().strftime("%Y-%m-%d")

    lines = ["---", f'title: "{name}"', f"type: collection-index", f"synced: {now}", "---", ""]
    lines.append(f"# {name}\n")
    lines.append(f"_{len(items)} items_  \n")

    # Get subcollections
    subs = z.collections_sub(collection_key)
    if subs:
        lines.append(f"\n## Subcollections\n")
        for s in subs:
            sd = s.get("data", {})
            sk = sd.get("key", "")
            sn = sd.get("name", "")
            sc = sd.get("numCollections", 0)
            si = sd.get("numItems", 0)
            lines.append(f"- [[{sn}/index.md|{sn}]] ({si} items)")
        lines.append("")

    lines.append(f"\n## Items\n")
    for item in items:
        data = item.get("data", {})
        title = data.get("title", "Untitled")
        creators = data.get("creators", [])
        date = data.get("date", "")
        creator_strs = []
        for c in creators[:3]:
            if "name" in c:
                creator_strs.append(c["name"])
            elif "lastName" in c:
                creator_strs.append(c["lastName"])
        author_str = ", ".join(creator_strs)
        key = data.get("key", "")

        safe_name = safe_filename(title)
        link = f"[{title}]({safe_name}.md)"
        parts = [link]
        if author_str:
            parts.append(f"_{author_str}_")
        if date:
            parts.append(f"({date})")
        lines.append(f"- {' '.join(parts)}")

    return "\n".join(lines)


def build_global_index(tree: list[tuple[Path, list[dict]]]) -> str:
    """Generate a top-level index of all synced collections."""
    now = datetime.now().strftime("%Y-%m-%d")
    lines = ["---", 'title: "Zotero Library - Synced Collections"', "type: index", f"synced: {now}", "---", ""]
    lines.append("# Zotero Library Sync\n")
    lines.append(f"_Last synced: {now}_  \n")

    lines.append("## Collection Tree\n")
    for path, items in sorted(tree, key=lambda x: x[0]):
        rel = path.relative_to(ZOTERO_DIR)
        indent = "  " * (len(rel.parts) - 1)
        lines.append(f"{indent}- [{rel.name}]({rel}/index.md) ({len(items)} items)")
    lines.append("")

    total = sum(len(items) for _, items in tree)
    lines.append(f"\n**Total: {total} items across {len(tree)} collections**")
    return "\n".join(lines)


# ── Main sync logic ─────────────────────────────────────────


def sync_collection(
    z: Zotero,
    collection_key: str,
    dry_run: bool = False,
    force: bool = False,
) -> tuple[Path, list[dict]]:
    """Sync a single collection: create directory structure + item files."""
    coll = z.collection(collection_key)
    if not coll:
        print(f"  ✗ Collection {collection_key} not found, skipping")
        return (Path(), [])

    data = coll.get("data", {})
    name = safe_filename(data.get("name", "unknown"), 40)
    print(f"\n📁 {name} [{collection_key}]")

    # Build directory path matching hierarchy
    coll_dir = collection_path(ZOTERO_DIR, z, collection_key)
    if dry_run:
        print(f"   → {coll_dir.relative_to(KB_ROOT) if coll_dir else '?'}")

    # Fetch items
    items = fetch_all_items(z, collection_key)
    if not items:
        print(f"   (no items)")
        if not dry_run:
            coll_dir.mkdir(parents=True, exist_ok=True)
        return (coll_dir, [])

    print(f"   → {len(items)} items")

    if dry_run:
        return (coll_dir, items)

    # Create directory
    coll_dir.mkdir(parents=True, exist_ok=True)

    # Write item files
    written = 0
    for item in items:
        data = item.get("data", {})
        title = data.get("title", "Untitled") or "Untitled"
        safe_name = safe_filename(title)
        item_path = coll_dir / f"{safe_name}.md"

        if item_path.exists() and not force:
            continue  # skip if already synced

        content = build_item_md(item)
        item_path.write_text(content, encoding="utf-8")
        written += 1

    if written:
        print(f"   ✍ {written} files written")

    # Generate collection index
    index_content = build_collection_index(z, collection_key, items)
    (coll_dir / "index.md").write_text(index_content, encoding="utf-8")

    return (coll_dir, items)


def sync_all_top_level(z: Zotero, dry_run: bool = False, force: bool = False) -> list[tuple[Path, list[dict]]]:
    """Sync ALL collections recursively, including subcollections."""
    # Fetch ALL collections with pagination
    all_coll: list[dict] = []
    start = 0
    limit = 100
    while True:
        batch = z.collections(limit=limit, start=start)
        if not batch:
            break
        all_coll.extend(batch)
        if len(batch) < limit:
            break
        start += limit

    if not all_coll:
        print("No collections found.")
        return []

    # Build mapping: key → data
    coll_map: dict[str, dict] = {}
    for c in all_coll:
        d = c.get("data", {})
        coll_map[d["key"]] = d

    # Find roots (top-level = parentCollection=False)
    roots = [k for k, d in coll_map.items() if d.get("parentCollection", False) is False]

    results: list[tuple[Path, list[dict]]] = []

    def process(key: str) -> None:
        path, items = sync_collection(z, key, dry_run, force)
        if path and path != Path():
            results.append((path, items))
        # Process subcollections
        subs = [k for k, d in coll_map.items() if d.get("parentCollection") == key]
        for sk in sorted(subs, key=lambda k: coll_map[k].get("name", "")):
            process(sk)

    for root_key in sorted(roots, key=lambda k: coll_map[k].get("name", "")):
        process(root_key)

    return results


def sync_zotero_to_kb(
    dry_run: bool = False,
    force: bool = False,
    collection_key: str | None = None,
    library_type: str = "user",
    library_id: str | None = None,
) -> None:
    """Main sync entry point."""
    print("=" * 60)
    print(f"Zotero → LLM-KB Sync")
    print(f"  Target: {ZOTERO_DIR}")
    print(f"  Mode: {'DRY RUN' if dry_run else 'SYNC'}")
    print("=" * 60)

    z = get_client(library_type, library_id)

    if collection_key:
        # Single collection sync
        path, items = sync_collection(z, collection_key, dry_run, force)
        tree = [(path, items)] if path else []
    else:
        # Full library sync
        tree = sync_all_top_level(z, dry_run, force)

    if dry_run:
        print("\n(Dry run - no files written)")
        return

    # Write global index
    tree = [(p, items) for p, items in tree if p and p != Path()]
    if tree:
        ZOTERO_DIR.mkdir(parents=True, exist_ok=True)
        INDEX_FILE.write_text(build_global_index(tree), encoding="utf-8")

    total = sum(len(items) for _, items in tree)
    print(f"\n{'='*60}")
    print(f"Sync complete: {len(tree)} collections, {total} items")
    print(f"  KB Path: {ZOTERO_DIR}")


# ── CLI ─────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="Zotero → LLM-KB Sync Tool")
    parser.add_argument("--dry-run", action="store_true", help="Show structure without writing")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    parser.add_argument("--collection", help="Sync a specific collection key only")
    parser.add_argument("--group", help="Group ID for group library sync")
    args = parser.parse_args()

    lib_type = "group" if args.group else "user"
    lib_id = args.group if args.group else None

    sync_zotero_to_kb(
        dry_run=args.dry_run,
        force=args.force,
        collection_key=args.collection,
        library_type=lib_type,
        library_id=lib_id,
    )
    return 0


if __name__ == "__main__":
    main()
