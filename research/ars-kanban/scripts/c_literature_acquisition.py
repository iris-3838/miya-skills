#!/usr/bin/env python3
"""ARS C mode Phase 2-1 literature acquisition engine.

This module implements the safe, API-first part of C mode:
- OpenAlex metadata/OA discovery
- CrossRef DOI fallback parsing
- Zotero deep-research collection creation and item mapping

It deliberately does NOT automate paywalled full-text retrieval. Paywalled
records are registered as metadata-only items for human full-text handoff.
"""

from __future__ import annotations

import html
import json
import os
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

USER_AGENT = "HermesAgent/ars-kanban-c-mode/0.1 (mailto:rseimiya+iris@miya-lis.net)"
OPENALEX_WORKS_URL = "https://api.openalex.org/works"
CROSSREF_WORKS_URL = "https://api.crossref.org/works"


def reconstruct_openalex_abstract(inverted_index: Optional[Dict[str, Sequence[int]]]) -> str:
    """Reconstruct OpenAlex abstract from abstract_inverted_index."""
    if not inverted_index:
        return ""
    positioned: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        for pos in positions:
            positioned.append((int(pos), str(word)))
    positioned.sort(key=lambda pair: pair[0])
    return " ".join(word for _, word in positioned)


def normalize_doi(doi: Optional[str]) -> str:
    """Normalize DOI values from OpenAlex/CrossRef to bare lowercase DOI."""
    if not doi:
        return ""
    value = doi.strip()
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value, flags=re.I)
    value = re.sub(r"^doi:\s*", "", value, flags=re.I)
    return value.strip().lower()


def strip_markup(text: str) -> str:
    """Strip lightweight JATS/HTML markup from CrossRef abstracts."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _authors_from_openalex(authorships: Iterable[Dict[str, Any]]) -> list[str]:
    authors = []
    for authorship in authorships or []:
        name = (authorship.get("author") or {}).get("display_name")
        if name:
            authors.append(str(name))
    return authors


def openalex_work_to_record(work: Dict[str, Any]) -> Dict[str, Any]:
    """Convert an OpenAlex work object into a normalized acquisition record."""
    primary = work.get("primary_location") or {}
    source = primary.get("source") or {}
    oa = work.get("open_access") or {}
    return {
        "source": "openalex",
        "openalex_id": work.get("id") or "",
        "title": work.get("title") or "",
        "doi": normalize_doi(work.get("doi")),
        "authors": _authors_from_openalex(work.get("authorships") or []),
        "year": work.get("publication_year"),
        "publication_date": work.get("publication_date"),
        "venue": source.get("display_name") or "",
        "abstract": reconstruct_openalex_abstract(work.get("abstract_inverted_index")),
        "is_oa": bool(oa.get("is_oa")),
        "oa_status": oa.get("oa_status") or "",
        "oa_url": oa.get("oa_url") or "",
        "cited_by_count": work.get("cited_by_count") or 0,
        "raw": work,
    }


def _first(value: Any, default: str = "") -> Any:
    if isinstance(value, list):
        return value[0] if value else default
    return value if value is not None else default


def _year_from_crossref(message: Dict[str, Any]) -> Optional[int]:
    for key in ("published-print", "published-online", "issued"):
        parts = ((message.get(key) or {}).get("date-parts") or [])
        if parts and parts[0]:
            try:
                return int(parts[0][0])
            except (TypeError, ValueError):
                return None
    return None


def crossref_message_to_record(message: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a CrossRef message object into a normalized acquisition record."""
    authors = []
    for author in message.get("author") or []:
        given = author.get("given") or ""
        family = author.get("family") or ""
        name = " ".join(part for part in (given, family) if part).strip()
        if name:
            authors.append(name)
    return {
        "source": "crossref",
        "title": _first(message.get("title"), ""),
        "doi": normalize_doi(message.get("DOI")),
        "authors": authors,
        "year": _year_from_crossref(message),
        "venue": _first(message.get("container-title"), ""),
        "abstract": strip_markup(message.get("abstract") or ""),
        "is_oa": False,
        "oa_status": "unknown",
        "oa_url": "",
        "raw": message,
    }


def split_author_name(name: str) -> Dict[str, str]:
    """Map a display name to Zotero creator fields."""
    name = name.strip()
    if not name:
        return {"creatorType": "author", "lastName": "", "firstName": ""}
    parts = name.split()
    if len(parts) == 1:
        return {"creatorType": "author", "lastName": parts[0], "firstName": ""}
    return {"creatorType": "author", "lastName": parts[-1], "firstName": " ".join(parts[:-1])}


def record_to_zotero_item(record: Dict[str, Any], zotero: Any, collection_key: Optional[str] = None) -> Dict[str, Any]:
    """Build a Zotero journalArticle item payload from a normalized record."""
    item = zotero.item_template("journalArticle")
    item["title"] = record.get("title") or "Untitled"
    item["DOI"] = record.get("doi") or ""
    item["publicationTitle"] = record.get("venue") or ""
    if record.get("year"):
        item["date"] = str(record["year"])
    item["abstractNote"] = record.get("abstract") or ""
    if record.get("oa_url"):
        item["url"] = record["oa_url"]
    item["creators"] = [split_author_name(a) for a in record.get("authors") or []]
    tags = [
        {"tag": "deep-research"},
        {"tag": f"source:{record.get('source') or 'unknown'}"},
        {"tag": "access:oa" if record.get("is_oa") else "access:non-oa"},
    ]
    if record.get("oa_status"):
        tags.append({"tag": f"oa:{record['oa_status']}"})
    item["tags"] = tags
    if collection_key:
        item["collections"] = [collection_key]
    return item


def _all_collections(zotero: Any) -> list[Dict[str, Any]]:
    """Fetch all collections with pagination; works with pyzotero-like clients."""
    collections: list[Dict[str, Any]] = []
    start = 0
    while True:
        page = zotero.collections(start=start)
        if isinstance(page, dict):
            page = page.get("data") or []
        if not page:
            break
        collections.extend(page)
        if len(page) < 100:
            break
        start += 100
    return collections


def ensure_collection_path(zotero: Any, path: str) -> str:
    """Ensure a nested Zotero collection path exists and return the leaf key."""
    parts = [p for p in path.split("/") if p]
    if not parts:
        raise ValueError("collection path must not be empty")

    parent_key: Optional[str] = None
    known = _all_collections(zotero)

    def find_child(name: str, parent: Optional[str]) -> Optional[str]:
        for collection in known:
            data = collection.get("data", collection)
            c_parent = data.get("parentCollection") or None
            if data.get("name") == name and c_parent == parent:
                return data.get("key") or collection.get("key")
        return None

    for name in parts:
        existing = find_child(name, parent_key)
        if existing:
            parent_key = existing
            continue
        payload = [{"name": name, "parentCollection": parent_key or False}]
        created = zotero.create_collections(payload)
        key = created.get("success", {}).get("0")
        if not key:
            raise RuntimeError(f"failed to create Zotero collection {name!r}: {created}")
        record = {"key": key, "data": {"key": key, "name": name, "parentCollection": parent_key or False}}
        known.append(record)
        parent_key = key
    assert parent_key is not None
    return parent_key


def fetch_json(url: str, *, params: Optional[Dict[str, Any]] = None, timeout: int = 30) -> Dict[str, Any]:
    """Fetch JSON with a clear User-Agent. Small stdlib wrapper for testability."""
    if params:
        query = urllib.parse.urlencode(params, doseq=True)
        url = f"{url}?{query}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - fixed public APIs only
        return json.loads(resp.read().decode("utf-8"))


def search_openalex(topic: str, *, per_page: int = 25, fetcher=fetch_json) -> list[Dict[str, Any]]:
    """Search OpenAlex works for a topic and return normalized records."""
    params = {
        "search": topic,
        "per_page": per_page,
        "select": ",".join([
            "id", "doi", "title", "publication_year", "publication_date",
            "authorships", "abstract_inverted_index", "open_access",
            "primary_location", "cited_by_count",
        ]),
    }
    data = fetcher(OPENALEX_WORKS_URL, params=params)
    return [openalex_work_to_record(work) for work in data.get("results", [])]


def fetch_crossref_by_doi(doi: str, *, fetcher=fetch_json) -> Optional[Dict[str, Any]]:
    """Fetch CrossRef metadata for a DOI, returning a normalized record."""
    if not doi:
        return None
    url = f"{CROSSREF_WORKS_URL}/{urllib.parse.quote(doi)}"
    data = fetcher(url, params={"mailto": "rseimiya+iris@miya-lis.net"})
    message = data.get("message")
    return crossref_message_to_record(message) if message else None


def enrich_missing_abstracts_with_crossref(records: list[Dict[str, Any]], *, fetcher=fetch_json, delay: float = 0.0) -> list[Dict[str, Any]]:
    """Fill missing abstracts via CrossRef when a DOI exists."""
    enriched = []
    for record in records:
        item = dict(record)
        if not item.get("abstract") and item.get("doi"):
            try:
                fallback = fetch_crossref_by_doi(item["doi"], fetcher=fetcher)
            except Exception:
                fallback = None
            if fallback and fallback.get("abstract"):
                item["abstract"] = fallback["abstract"]
                item.setdefault("fallback_sources", []).append("crossref")
            if delay:
                time.sleep(delay)
        enriched.append(item)
    return enriched


def dedupe_records(records: Iterable[Dict[str, Any]]) -> list[Dict[str, Any]]:
    """Dedupe records by DOI, falling back to normalized title."""
    seen: set[str] = set()
    out: list[Dict[str, Any]] = []
    for record in records:
        key = record.get("doi") or re.sub(r"\W+", "", (record.get("title") or "").lower())
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(record)
    return out


def register_records_to_zotero(records: list[Dict[str, Any]], zotero: Any, collection_path: str) -> Dict[str, Any]:
    """Create Zotero collection path and register records as metadata items."""
    collection_key = ensure_collection_path(zotero, collection_path)
    items = [record_to_zotero_item(record, zotero, collection_key=collection_key) for record in records]
    result = zotero.create_items(items) if items else {"success": {}}
    return {
        "collection_key": collection_key,
        "attempted": len(items),
        "created": len(result.get("success", {})) if isinstance(result, dict) else len(items),
        "raw_result": result,
    }


def load_zotero_client() -> Any:
    """Load pyzotero client from the user's credential file."""
    from pyzotero.zotero import Zotero  # type: ignore[import-untyped]

    cred_path = Path("/opt/data/workspace/.skills/zotero_credentials.json")
    creds = json.loads(cred_path.read_text(encoding="utf-8"))
    return Zotero(creds["user_id"], "user", creds["api_key"])


def run_literature_acquisition(
    *,
    body: Dict[str, Any],
    workspace_path: Optional[str] = None,
    zotero: Optional[Any] = None,
    fetcher=fetch_json,
    per_page: int = 25,
    register_zotero: bool = True,
) -> Dict[str, Any]:
    """Run Phase 2-1 acquisition for a task body.

    The current implementation covers OpenAlex + CrossRef fallback + Zotero
    metadata registration. J-STAGE/CiNii/Semantic Scholar hooks are represented
    in the task policy and will be implemented as additional collectors.
    """
    topic = str(body.get("topic") or "")
    c_mode = body.get("c_mode") or {}
    collection_path = c_mode.get("zotero_collection_path") or f"deep-research/{topic or 'research'}"
    records = search_openalex(topic, per_page=per_page, fetcher=fetcher) if topic else []
    records = enrich_missing_abstracts_with_crossref(records, fetcher=fetcher)
    records = dedupe_records(records)

    zotero_result = {"skipped": True, "reason": "register_zotero=false"}
    if register_zotero:
        zotero = zotero or load_zotero_client()
        zotero_result = register_records_to_zotero(records, zotero, collection_path)

    artifacts = {
        "zotero_collection_path": collection_path,
        "record_count": len(records),
        "oa_count": sum(1 for r in records if r.get("is_oa")),
        "non_oa_count": sum(1 for r in records if not r.get("is_oa")),
        "sources_used": ["openalex", "crossref"],
        "records": records,
        "zotero": zotero_result,
        "human_handoff_required": True,
    }
    summary = (
        f"Phase 2-1 Literature Acquisition collected {len(records)} metadata records "
        f"for {topic!r}; OA={artifacts['oa_count']}, non-OA={artifacts['non_oa_count']}. "
        "Paywalled full texts were not downloaded; add them manually to Zotero, then unblock Phase 2-2."
    )
    if workspace_path:
        path = Path(workspace_path) / "literature_acquisition.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(artifacts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"summary": summary, "artifacts": artifacts}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run ARS C mode Phase 2-1 literature acquisition")
    parser.add_argument("topic")
    parser.add_argument("--collection", default=None)
    parser.add_argument("--per-page", type=int, default=25)
    parser.add_argument("--no-zotero", action="store_true")
    args = parser.parse_args()
    body = {
        "topic": args.topic,
        "c_mode": {"zotero_collection_path": args.collection or f"deep-research/{args.topic}"},
    }
    result = run_literature_acquisition(body=body, per_page=args.per_page, register_zotero=not args.no_zotero)
    print(json.dumps(result, ensure_ascii=False, indent=2))
