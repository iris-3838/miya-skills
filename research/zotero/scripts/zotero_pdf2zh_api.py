#!/usr/bin/env python3
"""Prototype: Zotero PDF -> pdf2zh-next via Python API (do_translate_async_stream).

This mirrors zotero_pdf2zh.py but uses the native async Python API instead of
subprocess invocation. Goals:
  - progress events for long LLM translations
  - capture auto-extracted glossary CSV
  - deterministic output paths for llm-kb ingestion
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from pdf2zh_next.config.model import (
    BasicSettings,
    GUISettings,
    PDFSettings,
    SettingsModel,
    TranslationSettings,
)
from pdf2zh_next.config.translate_engine_model import BingSettings, OpenAICompatibleSettings
from pdf2zh_next.high_level import do_translate_async_stream

CRED_FILE = Path("/opt/data/workspace/.skills/zotero_credentials.json")
DEFAULT_OUT = Path("/opt/data/workspace/llm-kb.miya-lis.net/raw/papers/zotero_pdf2zh_api")
USER_AGENT = "HermesAgent-ZoteroPdf2zhAPI/0.1"


def sanitize(name: str, max_len: int = 110) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    name = re.sub(r"\s+", " ", name).strip().rstrip(". ")
    if len(name) > max_len:
        name = name[:max_len].rsplit(" ", 1)[0] if " " in name[:max_len] else name[:max_len]
    return name or "untitled"


def load_credentials() -> dict[str, str]:
    if not CRED_FILE.exists():
        raise SystemExit(f"Credentials not found: {CRED_FILE}")
    return json.loads(CRED_FILE.read_text())


def api_base(creds: dict[str, str], group: str | None = None) -> str:
    if group:
        return f"https://api.zotero.org/groups/{group}"
    return f"https://api.zotero.org/users/{creds['user_id']}"


def headers(creds: dict[str, str]) -> dict[str, str]:
    return {
        "Zotero-API-Key": creds["api_key"],
        "Zotero-API-Version": "3",
        "User-Agent": USER_AGENT,
    }


def get_json(client: httpx.Client, url: str, **params: Any) -> list[dict] | dict:
    r = client.get(url, params=params)
    r.raise_for_status()
    return r.json()


def find_item(client: httpx.Client, base: str, item_key: str | None, query: str | None) -> dict:
    if item_key:
        obj = get_json(client, f"{base}/items/{item_key}")
        assert isinstance(obj, dict)
        return obj
    if not query:
        raise SystemExit("Specify --item KEY or --query TEXT")
    res = get_json(client, f"{base}/items/top", q=query, limit=10, itemType="-note")
    assert isinstance(res, list)
    if not res:
        raise SystemExit(f"No Zotero item found for query: {query}")
    if len(res) > 1:
        print("Multiple matches; using the first. Candidates:", file=sys.stderr)
        for item in res[:10]:
            d = item.get("data", {})
            print(f"  {d.get('key')}  {d.get('title', '')[:100]}", file=sys.stderr)
    return res[0]


def choose_pdf_attachment(client: httpx.Client, base: str, item_key: str, attachment_key: str | None) -> dict:
    children = get_json(client, f"{base}/items/{item_key}/children")
    assert isinstance(children, list)
    pdfs = []
    for child in children:
        d = child.get("data", {})
        if d.get("itemType") != "attachment":
            continue
        content_type = (d.get("contentType") or "").lower()
        title = (d.get("title") or "").lower()
        links = child.get("links", {})
        enclosure = links.get("enclosure", {})
        href = enclosure.get("href")
        if content_type == "application/pdf" or title.endswith(".pdf") or (href and ".pdf" in href.lower()):
            pdfs.append(child)

    if attachment_key:
        for p in pdfs:
            if p.get("data", {}).get("key") == attachment_key:
                return p
        raise SystemExit(f"Attachment {attachment_key} is not a downloadable PDF child of {item_key}")
    if not pdfs:
        raise SystemExit(f"No PDF attachment children found for item {item_key}")

    def score(p: dict) -> tuple[int, str]:
        d = p.get("data", {})
        title = (d.get("title") or d.get("filename") or "").lower()
        penalty = 0
        if any(x in title for x in ("mono", "dual", "compare", "openailiked", "translated", "pdf2zh")):
            penalty += 10
        if title in ("pdf", "full text pdf"):
            penalty -= 5
        if d.get("linkMode") == "imported_file":
            penalty -= 1
        return (penalty, title)

    pdfs = sorted(pdfs, key=score)
    if len(pdfs) > 1:
        print("Multiple PDF attachments; using the best-scored candidate. Candidates:", file=sys.stderr)
        for p in pdfs:
            d = p.get("data", {})
            print(f"  {d.get('key')}  {d.get('title')}  linkMode={d.get('linkMode')} score={score(p)[0]}", file=sys.stderr)
    return pdfs[0]


def download_attachment(client: httpx.Client, attachment: dict, dest: Path, dry_run: bool) -> Path:
    d = attachment.get("data", {})
    enclosure = attachment.get("links", {}).get("enclosure", {})
    href = enclosure.get("href")
    if not href:
        mode = d.get("linkMode")
        path = d.get("path")
        raise SystemExit(f"PDF attachment has no downloadable enclosure; linkMode={mode}, path={path}")
    filename = sanitize(d.get("filename") or d.get("title") or d.get("key") or "attachment")
    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"
    dest.mkdir(parents=True, exist_ok=True)
    pdf_path = dest / filename
    if dry_run:
        print(f"[dry-run] would download {href} -> {pdf_path}")
        return pdf_path
    if pdf_path.exists() and pdf_path.stat().st_size > 0:
        print(f"✓ PDF already exists: {pdf_path}")
        return pdf_path
    with client.stream("GET", href, follow_redirects=True, timeout=180) as resp:
        resp.raise_for_status()
        with pdf_path.open("wb") as f:
            for chunk in resp.iter_bytes():
                f.write(chunk)
    print(f"✓ Downloaded: {pdf_path} ({pdf_path.stat().st_size:,} bytes)")
    return pdf_path


def make_settings(args: argparse.Namespace) -> SettingsModel:
    basic = BasicSettings()
    pdf = PDFSettings(
        pages=args.pages,
        no_dual=args.no_dual,
        no_mono=args.no_mono,
        skip_scanned_detection=args.skip_scanned_detection,
        ocr_workaround=args.ocr_workaround,
        auto_enable_ocr_workaround=args.auto_enable_ocr_workaround,
        use_alternating_pages_dual=args.use_alternating_pages_dual,
        only_include_translated_page=args.only_include_translated_page,
        enhance_compatibility=args.enhance_compatibility,
        split_short_lines=args.split_short_lines,
        primary_font_family=args.primary_font_family,
    )
    translation = TranslationSettings(
        lang_in=args.lang_in,
        lang_out=args.lang_out,
        output=args.output,
        qps=args.qps,
        no_auto_extract_glossary=args.no_auto_extract_glossary,
        save_auto_extracted_glossary=not args.no_auto_extract_glossary,
        term_qps=args.term_qps,
    )

    engine_type = args.engine.lower()
    if engine_type == "bing":
        engine_settings = BingSettings()
    elif engine_type == "openaicompatible":
        key = os.environ.get(args.openai_compatible_api_key_env or "")
        if not key:
            raise SystemExit(f"Environment variable not set: {args.openai_compatible_api_key_env}")
        engine_settings = OpenAICompatibleSettings(
            openai_compatible_model=args.openai_compatible_model,
            openai_compatible_base_url=args.openai_compatible_base_url,
            openai_compatible_api_key=key,
            openai_compatible_timeout=str(args.openai_compatible_timeout),
        )
    else:
        raise SystemExit(f"Engine '{engine_type}' not yet implemented in API prototype")

    return SettingsModel(
        basic=basic,
        pdf=pdf,
        translation=translation,
        gui_settings=GUISettings(),
        translate_engine_settings=engine_settings,
    )


async def run_translate(settings: SettingsModel, pdf_path: Path, progress_log: Path | None = None) -> dict:
    print(f"Starting translation: {pdf_path}")
    result_obj = None
    log_lines: list[str] = []

    def emit(msg: str) -> None:
        print(msg)
        log_lines.append(msg)
        if progress_log:
            with progress_log.open("a", encoding="utf-8") as f:
                f.write(msg + "\n")
                f.flush()

    async for event in do_translate_async_stream(settings, pdf_path):
        etype = event.get("type")
        if etype in ("progress_start", "progress_update", "progress_end"):
            stage = event.get("stage", "?")
            overall = event.get("overall_progress")
            stage_prog = event.get("stage_progress")
            emit(f"[{etype}] {stage} | stage {stage_prog:.1f}% | overall {overall:.1f}%")
        elif etype == "error":
            emit(f"[error] {event.get('error')} ({event.get('error_type')})")
        elif etype == "finish":
            result_obj = event.get("translate_result")
            break
    if result_obj is None:
        raise SystemExit("Translation finished without result object")
    result = {
        "original_pdf_path": getattr(result_obj, "original_pdf_path", None),
        "mono_pdf_path": getattr(result_obj, "mono_pdf_path", None),
        "dual_pdf_path": getattr(result_obj, "dual_pdf_path", None),
        "no_watermark_mono_pdf_path": getattr(result_obj, "no_watermark_mono_pdf_path", None),
        "no_watermark_dual_pdf_path": getattr(result_obj, "no_watermark_dual_pdf_path", None),
        "auto_extracted_glossary_path": getattr(result_obj, "auto_extracted_glossary_path", None),
        "total_seconds": getattr(result_obj, "total_seconds", None),
        "peak_memory_usage": getattr(result_obj, "peak_memory_usage", None),
    }
    emit("Translation result:")
    for line in json.dumps(result, ensure_ascii=False, indent=2, default=str).splitlines():
        emit(line)
    return result


def main() -> None:
    p = argparse.ArgumentParser(description="Zotero PDF attachment -> pdf2zh-next Python API")
    p.add_argument("--item", help="Zotero parent item key")
    p.add_argument("--query", help="Search Zotero top-level items and use the first match")
    p.add_argument("--attachment", help="Specific child PDF attachment key")
    p.add_argument("--group", help="Group library ID (read/write only if API key permits it)")
    p.add_argument("--out", default=str(DEFAULT_OUT), help="Output root directory")
    p.add_argument("--engine", default="bing", choices=["bing", "openaicompatible"])
    p.add_argument("--openai-compatible-model", default="deepseek-v4-flash")
    p.add_argument("--openai-compatible-base-url", default="https://opencode.ai/zen/go/v1")
    p.add_argument("--openai-compatible-api-key-env", default="OPENCODE_GO_API_KEY")
    p.add_argument("--lang-in", default="en")
    p.add_argument("--lang-out", default="ja")
    p.add_argument("--pages", help="Page range, e.g. 1-10")
    p.add_argument("--qps", type=int, default=1)
    p.add_argument("--term-qps", type=int, default=1, help="QPS for automatic term extraction")
    p.add_argument("--openai-compatible-timeout", type=int, default=120, help="Timeout seconds for OpenAI-compatible API")
    p.add_argument("--skip-scanned-detection", action="store_true", default=True)
    p.add_argument("--ocr-workaround", action="store_true")
    p.add_argument("--auto-enable-ocr-workaround", action="store_true")
    p.add_argument("--use-alternating-pages-dual", action="store_true")
    p.add_argument("--only-include-translated-page", action="store_true")
    p.add_argument("--enhance-compatibility", action="store_true")
    p.add_argument("--split-short-lines", action="store_true")
    p.add_argument("--no-auto-extract-glossary", action="store_true")
    p.add_argument("--primary-font-family", choices=["serif", "sans-serif", "script"])
    p.add_argument("--no-mono", action="store_true")
    p.add_argument("--no-dual", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    # output is per-item directory; we pass the parent so pdf2zh creates its own subdir.
    item_dir = Path(args.out)  # caller builds title__key below
    item_dir.mkdir(parents=True, exist_ok=True)
    args.output = str(item_dir / "translated")

    creds = load_credentials()
    base = api_base(creds, args.group)
    with httpx.Client(headers=headers(creds), timeout=60) as client:
        item = find_item(client, base, args.item, args.query)
        item_data = item.get("data", {})
        item_key = item_data["key"]
        title = item_data.get("title") or item_key
        print(f"Zotero item: {item_key} — {title}")
        attachment = choose_pdf_attachment(client, base, item_key, args.attachment)
        att_data = attachment.get("data", {})
        print(f"PDF attachment: {att_data.get('key')} — {att_data.get('title')} linkMode={att_data.get('linkMode')}")

        item_dir = Path(args.out) / f"{sanitize(title)}__{item_key}"
        src_dir = item_dir / "source"
        out_dir = item_dir / "translated"
        pdf_path = download_attachment(client, attachment, src_dir, args.dry_run)
        out_dir.mkdir(parents=True, exist_ok=True)
        args.output = str(out_dir)
        progress_log = out_dir / "translation.log"
        if progress_log.exists():
            progress_log.unlink()

        if args.dry_run:
            print(f"[dry-run] would translate {pdf_path} -> {out_dir}")
            return

        settings = make_settings(args)
        result = asyncio.run(run_translate(settings, pdf_path, progress_log))
        print(f"Output directory: {out_dir}")
        result_file = out_dir / "translation_result.json"
        result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print(f"Result written to: {result_file}")

if __name__ == "__main__":
    main()
