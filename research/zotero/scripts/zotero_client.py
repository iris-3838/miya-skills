#!/usr/bin/env python3
"""
Zotero Library Manager — pyzotero wrapper for Hermes Agent skill.

Usage:
  python3 zotero_client.py collections                          # List all collections (tree)
  python3 zotero_client.py collections --flat                   # Flat list with keys
  python3 zotero_client.py collection-create "Name" [--parent KEY]
  python3 zotero_client.py collection-rename KEY "New Name"
  python3 zotero_client.py collection-move KEY --to PARENT_KEY   # Move/reparent collection
  python3 zotero_client.py collection-delete KEY                 # Delete collection (empty)
  python3 zotero_client.py items [--collection KEY] [--limit N]  # List items
  python3 zotero_client.py items --q "search term"               # Search items
  python3 zotero_client.py items-top                             # Top-level items only
  python3 zotero_client.py item-add TYPE --title "T" [--creators ...] [--collection KEY]
  python3 zotero_client.py item-get KEY                          # Get item details
  python3 zotero_client.py item-update KEY --field value         # Update item field
  python3 zotero_client.py item-delete KEY                       # Delete item
  python3 zotero_client.py item-children KEY                     # Show children (notes/attachments)
  python3 zotero_client.py export [--collection KEY|--item KEY] [--format FORMAT]
  python3 zotero_client.py tags                                  # List all tags
  python3 zotero_client.py info                                  # Show library info/stats
  python3 zotero_client.py structure                             # Show folder tree
  python3 zotero_client.py restructure --from KEY --to KEY       # Move items between collections
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from pyzotero.zotero import Zotero

# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------
CRED_FILE = Path("/opt/data/workspace/.skills/zotero_credentials.json")


def load_credentials() -> dict[str, str]:
    if not CRED_FILE.exists():
        print(f"Error: Credentials not found at {CRED_FILE}", file=sys.stderr)
        print("Run: python3 scripts/setup_credentials.py", file=sys.stderr)
        sys.exit(2)
    data = json.loads(CRED_FILE.read_text())
    return {"user_id": data["user_id"], "api_key": data["api_key"]}


def get_client() -> Zotero:
    creds = load_credentials()
    return Zotero(creds["user_id"], "user", creds["api_key"])


# ---------------------------------------------------------------------------
# Date helper
# ---------------------------------------------------------------------------
def fmt_date(ts: str | None) -> str:
    if not ts:
        return ""
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except Exception:
        return ts[:10] if ts else ""


# ---------------------------------------------------------------------------
# Collection commands
# ---------------------------------------------------------------------------
def cmd_collections(args: argparse.Namespace) -> None:
    z = get_client()
    if args.flat:
        all_coll = z.collections()
        for c in all_coll:
            data = c.get("data", {})
            parent = data.get("parentCollection", False)
            parent_str = f" [parent={parent}]" if parent else ""
            print(f"{data['key']}\t{data['name']}{parent_str}")
    else:
        # Build tree
        all_coll = z.collections()
        coll_map: dict[str, dict[str, Any]] = {}
        for c in all_coll:
            d = c.get("data", {})
            coll_map[d["key"]] = d

        def print_tree(parent_key: str | bool, indent: int = 0) -> None:
            for key, d in sorted(coll_map.items(), key=lambda x: x[1].get("name", "")):
                pk = d.get("parentCollection", False)
                if pk == parent_key:
                    item_count = z.num_collectionitems(key)
                    print(f"{'  ' * indent}📁 {d['name']}  [{key}] ({item_count} items)")
                    print_tree(key, indent + 1)

        print_tree(False)
        orphaned = [d for d in coll_map.values() if d.get("parentCollection", False) is not False and d["parentCollection"] not in coll_map]
        if orphaned:
            print("\n⚠ Orphaned collections (parent missing):")
            for d in orphaned:
                print(f"  📁 {d['name']}  [{d['key']}]")


def cmd_collection_create(args: argparse.Namespace) -> None:
    z = get_client()
    payload = [{"name": args.name}]
    if args.parent:
        payload[0]["parentCollection"] = args.parent
    result = z.create_collections(payload)
    print(f"✓ Collection created: {args.name}")
    if result and "success" in result:
        keys = list(result["success"].values())
        if keys:
            print(f"  Key: {keys[0]}")


def cmd_collection_rename(args: argparse.Namespace) -> None:
    z = get_client()
    # Get current version
    col_data = z.collection(args.key)
    if not col_data:
        print(f"✗ Collection {args.key} not found")
        sys.exit(1)
    data = col_data.get("data", {})
    data["name"] = args.name
    result = z.update_collection(data)
    print(f"✓ Collection renamed: {data['name']} → {args.name}")


def cmd_collection_move(args: argparse.Namespace) -> None:
    z = get_client()
    col_data = z.collection(args.key)
    if not col_data:
        print(f"✗ Collection {args.key} not found")
        sys.exit(1)
    data = col_data.get("data", {})
    old_parent = data.get("parentCollection", False)
    if args.to == "root":
        # If hasattr and it's set
        if "parentCollection" in data:
            del data["parentCollection"]
    else:
        data["parentCollection"] = args.to
    z.update_collection(data)
    print(f"✓ Collection moved: {data['name']}")


def cmd_collection_delete(args: argparse.Namespace) -> None:
    z = get_client()
    z.delete_collection([args.key])
    print(f"✓ Collection deleted: {args.key}")


# ---------------------------------------------------------------------------
# Item commands
# ---------------------------------------------------------------------------
def cmd_items(args: argparse.Namespace) -> None:
    z = get_client()
    kwargs: dict[str, Any] = {"limit": args.limit or 50}
    if args.collection:
        items_raw = z.collection_items(args.collection, **kwargs)
    elif args.q:
        kwargs["q"] = args.q
        items_raw = z.items(**kwargs)
    else:
        items_raw = z.items(**kwargs)

    if not items_raw:
        print("(no items)")
        return

    print(f"Total: {len(items_raw)} items")
    print(f"{'Date':<12} {'Type':<18} {'Title':<60} {'Key':<12}")
    print("-" * 102)
    for item in items_raw:
        data = item.get("data", {})
        date = fmt_date(data.get("date", ""))
        print(f"{date:<12} {data.get('itemType',''):<18} {data.get('title','')[:58]:<60} {data.get('key',''):<12}")


def cmd_items_top(args: argparse.Namespace) -> None:
    z = get_client()
    items_raw = z.items(limit=args.limit or 50, itemType="-note")
    if not items_raw:
        print("(no top-level items)")
        return
    print(f"{'Date':<12} {'Type':<18} {'Title':<60} {'Key':<12}")
    print("-" * 102)
    for item in items_raw:
        data = item.get("data", {})
        if data.get("itemType") == "note" or data.get("parentItem"):
            continue
        date = fmt_date(data.get("date", ""))
        print(f"{date:<12} {data.get('itemType',''):<18} {data.get('title','')[:58]:<60} {data.get('key',''):<12}")


def cmd_item_get(args: argparse.Namespace) -> None:
    z = get_client()
    item = z.item(args.key)
    if item:
        print(json.dumps(item, indent=2, ensure_ascii=False))


def cmd_item_children(args: argparse.Namespace) -> None:
    z = get_client()
    item = z.item(args.key)
    if not item:
        print(f"✗ Item {args.key} not found")
        return
    children_url = item.get("links", {}).get("children", {}).get("href", "")
    if children_url:
        import httpx
        creds = load_credentials()
        resp = httpx.get(
            children_url,
            headers={"Zotero-API-Key": creds["api_key"], "Zotero-API-Version": "3"},
        )
        children = resp.json()
        if not children:
            print("(no children)")
            return
        for c in children:
            d = c.get("data", {})
            print(f"  [{d.get('itemType','')}] {d.get('title','')[:60]}  key={d.get('key','')}")
    else:
        print("(no children link available)")


def cmd_item_delete(args: argparse.Namespace) -> None:
    z = get_client()
    z.delete_item([args.key])
    print(f"✓ Item deleted: {args.key}")


# ---------------------------------------------------------------------------
# Structure / reorganization
# ---------------------------------------------------------------------------
def cmd_structure(args: argparse.Namespace) -> None:
    """Show full folder structure with item counts."""
    z = get_client()
    all_coll = z.collections() or []
    coll_map = {}
    for c in all_coll:
        d = c.get("data", {})
        coll_map[d["key"]] = d

    def print_tree(parent_key: str | bool, indent: int = 0):
        for key, d in sorted(coll_map.items(), key=lambda x: x[1].get("name", "")):
            pk = d.get("parentCollection", False)
            if pk == parent_key:
                count = z.num_collectionitems(key)
                print(f"{'  ' * indent}📁 {d['name']}  ({count} items)")
                print_tree(key, indent + 1)

    print("=== Zotero Library Structure ===\n")
    print_tree(False)
    print(f"\nTotal collections: {len(all_coll)}")
    print(f"Total items: {z.num_items()}")


def cmd_info(args: argparse.Namespace) -> None:
    """Show library stats."""
    z = get_client()
    try:
        num_items = z.num_items()
        coll_count = len(z.collections() or [])
        tags = z.tags() or []
        tag_count = len(tags) if isinstance(tags, list) else 0
        print("=== Zotero Library Info ===")
        print(f"  Items:      {num_items}")
        print(f"  Collections: {coll_count}")
        print(f"  Tags:       {tag_count}")
    except Exception as e:
        print(f"✗ Error: {e}")


def cmd_tags(args: argparse.Namespace) -> None:
    z = get_client()
    tags = z.tags() or []
    for t in tags:
        if isinstance(t, dict):
            print(f"  {t.get('tag', str(t))}")
        else:
            print(f"  {t}")


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
def cmd_export(args: argparse.Namespace) -> None:
    """Export items in a given format using the Web API's format parameter."""
    z = get_client()
    fmt = args.format or "bibtex"
    if args.collection:
        url = f"{z.api_base_url}/users/{z.library_id}/collections/{args.collection}/items"
    elif args.item:
        url = f"{z.api_base_url}/users/{z.library_id}/items/{args.item}"
    else:
        # Entire library (NOT recommended for large libs)
        url = f"{z.api_base_url}/users/{z.library_id}/items"

    import httpx
    creds = load_credentials()
    params = {"format": fmt, "limit": args.limit or 50}
    resp = httpx.get(
        url,
        headers={"Zotero-API-Key": creds["api_key"], "Zotero-API-Version": "3"},
        params=params,
    )
    if resp.status_code == 200:
        print(resp.text)
    else:
        print(f"✗ Export failed: HTTP {resp.status_code}")
        print(resp.text[:500], file=sys.stderr)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="Zotero Library Manager (pyzotero)")
    sub = parser.add_subparsers(dest="command")

    # collections
    p = sub.add_parser("collections", help="List collections (tree view)")
    p.add_argument("--flat", action="store_true", help="Flat list with keys")

    sub.add_parser("collections-top", help="Top-level collections only")

    p = sub.add_parser("collection-create", help="Create a new collection")
    p.add_argument("name", help="Collection name")
    p.add_argument("--parent", help="Parent collection key")

    p = sub.add_parser("collection-rename", help="Rename a collection")
    p.add_argument("key", help="Collection key")
    p.add_argument("name", help="New name")

    p = sub.add_parser("collection-move", help="Move/reparent a collection")
    p.add_argument("key", help="Collection key to move")
    p.add_argument("--to", required=True, help="Target parent key (or 'root')")

    p = sub.add_parser("collection-delete", help="Delete a collection")
    p.add_argument("key", help="Collection key to delete")

    # items
    p = sub.add_parser("items", help="List/search items")
    p.add_argument("--collection", help="Filter by collection key")
    p.add_argument("--q", help="Search query")
    p.add_argument("--limit", type=int, default=30, help="Max items (default: 30)")

    p = sub.add_parser("items-top", help="Top-level items")
    p.add_argument("--limit", type=int, default=30)

    p = sub.add_parser("item-get", help="Get item details (JSON)")
    p.add_argument("key", help="Item key")

    p = sub.add_parser("item-children", help="Show child items (notes/attachments)")
    p.add_argument("key", help="Parent item key")

    p = sub.add_parser("item-delete", help="Delete an item")
    p.add_argument("key", help="Item key to delete")

    # structure / info
    sub.add_parser("structure", help="Show collection tree with stats")
    sub.add_parser("info", help="Show library stats")
    sub.add_parser("tags", help="List all tags")

    # export
    p = sub.add_parser("export", help="Export items")
    p.add_argument("--collection", help="Collection key")
    p.add_argument("--item", help="Single item key")
    p.add_argument("--format", default="bibtex", help="Export format (bibtex, biblatex, ris, csljson)")
    p.add_argument("--limit", type=int, default=50)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    cmd_map = {
        "collections": cmd_collections,
        "collections-top": lambda a: cmd_items(a) if False else ...,
        "collection-create": cmd_collection_create,
        "collection-rename": cmd_collection_rename,
        "collection-move": cmd_collection_move,
        "collection-delete": cmd_collection_delete,
        "items": cmd_items,
        "items-top": cmd_items_top,
        "item-get": cmd_item_get,
        "item-children": cmd_item_children,
        "item-delete": cmd_item_delete,
        "structure": cmd_structure,
        "info": cmd_info,
        "tags": cmd_tags,
        "export": cmd_export,
    }
    fn = cmd_map.get(args.command)
    if fn:
        fn(args)
        return 0
    parser.print_help()
    return 1


if __name__ == "__main__":
    main()
