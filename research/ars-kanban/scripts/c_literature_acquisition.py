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

PREVIEW_RECORDS_FILE = "literature_records.json"
ZOTERO_EXPORT_FILE = "zotero_export.json"


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


# =========================================================================
# Preview/selection workflow (review-then-export, no auto-register)
# =========================================================================


def format_records_for_preview(records: list[Dict[str, Any]]) -> str:
    """Build a numbered markdown preview for kanban comment.

    Each entry shows: [N] Author(s) (year). Title. Venue. OA badge.
    """
    lines = ["The following records were found. **Reply with numbers to export** "
             "(e.g., `1,3,5-8,10` or `all`), then unblock this task.\n"]
    for i, rec in enumerate(records, start=1):
        authors = ", ".join(rec.get("authors") or [])[:80]
        title = (rec.get("title") or "Untitled")[:120]
        venue = (rec.get("venue") or "")[:60]
        year = rec.get("year") or "?"
        doi = rec.get("doi") or "-"
        oa_badge = "🟢 OA" if rec.get("is_oa") else "🔒 non-OA"
        abstract = rec.get("abstract") or "(no abstract)"
        abstract_snippet = abstract[:150]
        lines.append(
            f"  **[{i}]** {authors} ({year}). *{title}*. "
            f"*{venue}* — {oa_badge}\n"
            f"      DOI: {doi}\n"
            f"      > {abstract_snippet}"
        )
    lines.append(
        f"\n---\n{len(records)} records total. "
        "Select which ones to add to Zotero. "
        "Paywalled PDFs will not be downloaded — add them to Zotero manually."
    )
    return "\n".join(lines)


def parse_selection(text: str, max_count: int) -> list[int]:
    """Parse user selection (e.g. '1,3,5-8,10') into 0-based index list.

    Supports commas, ranges, spaces, and the literal 'all'.
    Indices outside [1, max_count] are silently dropped.
    Returns deduplicated, sorted list.
    """
    stripped = text.strip().lower()
    if not stripped:
        return []
    if stripped == "all":
        return list(range(max_count))

    # Replace newlines with commas, split on comma/space
    tokens = re.split(r"[\s,]+", stripped)
    seen: set[int] = set()
    result: list[int] = []
    for token in tokens:
        token = token.strip()
        if not token:
            continue
        # Range: "5-8"
        range_match = re.match(r"^(\d+)\s*-\s*(\d+)$", token)
        if range_match:
            lo, hi = int(range_match.group(1)), int(range_match.group(2))
            for num in range(lo, hi + 1):
                idx = num - 1
                if 0 <= idx < max_count and idx not in seen:
                    seen.add(idx)
                    result.append(idx)
            continue
        # Single number
        try:
            num = int(token)
        except ValueError:
            continue
        idx = num - 1
        if 0 <= idx < max_count and idx not in seen:
            seen.add(idx)
            result.append(idx)
    result.sort()
    return result


# collect_records_for_preview — see the multi-source version defined below


def export_selected_to_zotero(
    workspace_path: str,
    selection: list[int],
    *,
    zotero: Optional[Any] = None,
    collection_path: str = "deep-research/selected",
) -> Dict[str, Any]:
    """Load saved records from workspace, filter by selection, register to Zotero.

    If selection is empty or no records file exists, returns a skip result.
    """
    workspace = Path(workspace_path) if workspace_path else Path.cwd()
    records_path = workspace / PREVIEW_RECORDS_FILE
    if not records_path.exists():
        return {
            "status": "skipped",
            "reason": f"records file not found at {records_path}",
            "collection_path": collection_path,
            "selected": 0,
            "total": 0,
        }

    all_records = json.loads(records_path.read_text(encoding="utf-8"))
    if not selection:
        # Zotero collection creation is still useful: creates empty folder
        if zotero:
            ensure_collection_path(zotero, collection_path)
        return {
            "status": "skipped",
            "reason": "no records selected for export",
            "collection_path": collection_path,
            "selected": 0,
            "total": len(all_records),
        }

    selected_records = [all_records[i] for i in selection if 0 <= i < len(all_records)]
    zotero = zotero or load_zotero_client()
    zotero_result = register_records_to_zotero(selected_records, zotero, collection_path)

    result = {
        "status": "completed",
        "collection_path": collection_path,
        "collection_key": zotero_result["collection_key"],
        "selected": len(selected_records),
        "total": len(all_records),
        "attempted": zotero_result["attempted"],
        "created": zotero_result["created"],
    }

    export_path = workspace / ZOTERO_EXPORT_FILE
    export_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


# =========================================================================
# J-STAGE collector (scraping per-journal pubmode=listview)
# =========================================================================

# Japanese Diamond OA LIS journals on J-STAGE
JSTAGE_LIS_JOURNALS: dict[str, dict[str, Any]] = {
    "jslis": {"name": "日本図書館情報学会誌", "url": "https://www.jstage.jst.go.jp/browse/jslis"},
    "jsik": {"name": "情報知識学会誌", "url": "https://www.jstage.jst.go.jp/browse/jsik"},
}
DEFAULT_JSTAGE_JOURNALS = list(JSTAGE_LIS_JOURNALS.keys())


def parse_jstage_listview(html: str, *, journal_key: str = "") -> list[Dict[str, Any]]:
    """Parse J-STAGE pubmode=listview HTML into normalized records.

    Reads the full article title from the ``title`` attribute of the blue-link
    element. Extracts authors, DOIs, and OA PDF URLs where available.
    """
    import html as html_mod

    records: list[Dict[str, Any]] = []
    article_links = re.findall(
        r'<a\s[^>]*href="(https?://www\.jstage\.jst\.go\.jp/article/[^"]+)"[^>]*'
        r'class="bluelink-style customTooltip"[^>]*title="([^"]*)"[^>]*>',
        html,
    )
    if not article_links:
        return records

    author_blocks = re.findall(r'class="listview-article__author"[^>]*>(.*?)</p>', html, re.DOTALL)
    doi_links = re.findall(r'href="https?://doi\.org/([^"]+)"', html)
    pdf_links = re.findall(r'href="(https?://www\.jstage\.jst\.go\.jp/article/[^"]+_pdf/[^"]*)"', html)

    for i, (link_url, full_title) in enumerate(article_links):
        doi = doi_links[i] if i < len(doi_links) else ""
        pdf_url = pdf_links[i] if i < len(pdf_links) else ""
        authors_raw = author_blocks[i] if i < len(author_blocks) else ""
        authors = [a.strip() for a in re.split(r"[,、]", authors_raw) if a.strip()]

        record: Dict[str, Any] = {
            "source": "jstage",
            "title": html_mod.unescape(full_title).strip(),
            "doi": normalize_doi(doi) if doi else "",
            "authors": authors,
            "year": None,
            "venue": journal_key.upper() if journal_key else "J-STAGE",
            "abstract": "",
            "is_oa": True,
            "oa_status": "diamond",
            "oa_url": pdf_url,
            "cited_by_count": 0,
        }
        records.append(record)
    return records


def search_jstage_recent(
    journal_key: str,
    max_volumes: int = 2,
    *,
    fetcher: Any = None,
) -> list[Dict[str, Any]]:
    """Scrape recent volumes of a J-STAGE journal via pubmode=listview.

    Fetches the browse page for each volume and parses article metadata.
    """
    import urllib.request

    fetch = fetcher or (lambda url: urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    ).read().decode("utf-8"))

    info = JSTAGE_LIS_JOURNALS.get(journal_key)
    if not info:
        return []

    all_records: list[Dict[str, Any]] = []
    base_url = info["url"]
    for vol in range(1, max_volumes + 1):
        url = f"{base_url}/{vol}/_contents/-char/ja?pubmode=listview"
        try:
            html_text = fetch(url)
        except Exception:
            continue
        records = parse_jstage_listview(html_text, journal_key=journal_key)
        for rec in records:
            rec["year"] = 2026 - (vol - 1)  # heuristic
        all_records.extend(records)
    return all_records


# =========================================================================
# CiNii Research collector (OpenSearch JSON API)
# =========================================================================

CINII_OPENSEARCH_URL = "https://cir.nii.ac.jp/opensearch/articles"


def parse_cinii_opensearch(data: Dict[str, Any]) -> list[Dict[str, Any]]:
    """Parse CiNii Research OpenSearch JSON response into normalized records."""
    items = data.get("items") or []
    records: list[Dict[str, Any]] = []

    for item in items:
        title = str(item.get("title") or "")
        creators = item.get("dc:creator") or []
        if isinstance(creators, str):
            creators = [creators]
        authors = [str(a) for a in creators if a]
        doi = item.get("prism:doi") or ""
        if not doi:
            for ident in item.get("dc:identifier") or []:
                if isinstance(ident, dict) and ident.get("@type") in ("cir:DOI", "DOI"):
                    doi = str(ident.get("@value") or "")
                    break
        pub_date = item.get("prism:publicationDate") or ""
        year = None
        if pub_date:
            ym = re.match(r"(\d{4})", str(pub_date))
            if ym:
                year = int(ym.group(1))
        abstract_raw = item.get("description") or ""
        abstract = strip_markup(abstract_raw) if abstract_raw else ""
        record: Dict[str, Any] = {
            "source": "cinii",
            "title": title,
            "doi": normalize_doi(doi) if doi else "",
            "authors": authors,
            "year": year,
            "venue": str(item.get("prism:publicationName") or ""),
            "abstract": abstract,
            "is_oa": False,
            "oa_status": "unknown",
            "oa_url": str(item.get("link") or ""),
            "cited_by_count": 0,
        }
        records.append(record)
    return records


# =========================================================================
# Updated collect_records_for_preview (multi-source)
# =========================================================================


def collect_records_for_preview(
    body: Dict[str, Any],
    *,
    workspace_path: Optional[str] = None,
    fetcher=fetch_json,
    per_page: int = 25,
) -> list[Dict[str, Any]]:
    """Multi-source collection: OpenAlex + J-STAGE + CiNii Research.

    Returns deduplicated records saved to workspace_path.
    """
    topic = str(body.get("topic") or "")
    records = search_openalex(topic, per_page=per_page, fetcher=fetcher) if topic else []
    records = enrich_missing_abstracts_with_crossref(records, fetcher=fetcher)
    for jkey in DEFAULT_JSTAGE_JOURNALS:
        try:
            records.extend(search_jstage_recent(jkey, max_volumes=2))
        except Exception:
            pass
    if topic:
        try:
            cinii_data = fetcher(f"{CINII_OPENSEARCH_URL}?q={urllib.parse.quote(topic)}&format=json")
            if cinii_data:
                records.extend(parse_cinii_opensearch(cinii_data)[:20])
        except Exception:
            pass
    records = dedupe_records(records)
    if workspace_path:
        records_path = Path(workspace_path) / PREVIEW_RECORDS_FILE
        records_path.parent.mkdir(parents=True, exist_ok=True)
        records_path.write_text(json.dumps(records, ensure_ascii=False) + "\n", encoding="utf-8")
    return records


# =========================================================================
# Backward-compatible one-shot acquisition (for CLI use)
# =========================================================================


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
