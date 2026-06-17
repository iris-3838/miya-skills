#!/usr/bin/env python3
"""Download a Zotero PDF attachment and translate it with pdf2zh-next.

Default behavior is conservative: download an imported PDF attachment from the
user library and write translated PDFs to the local workspace. It does not modify
Zotero unless --add-note is passed.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

CRED_FILE = Path("/opt/data/workspace/.skills/zotero_credentials.json")
PDF2ZH_ENV = Path("/opt/data/workspace/pdf2zh-env")
PDF2ZH = PDF2ZH_ENV / ".venv/bin/pdf2zh"
DEFAULT_OUT = Path("/opt/data/workspace/llm-kb.miya-lis.net/raw/papers/zotero_pdf2zh")
USER_AGENT = "HermesAgent-ZoteroPdf2zh/1.0"


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
        # Prefer original/imported Zotero PDFs over already-translated outputs.
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


def run_pdf2zh(pdf_path: Path, out_dir: Path, args: argparse.Namespace) -> None:
    if not PDF2ZH.exists():
        raise SystemExit(f"pdf2zh not found: {PDF2ZH}. Set up /opt/data/workspace/pdf2zh-env first.")
    cmd = [
        str(PDF2ZH), str(pdf_path),
        f"--{args.engine}",
        "--lang-in", args.lang_in,
        "--lang-out", args.lang_out,
        "--output", str(out_dir),
        "--qps", str(args.qps),
    ]
    env = os.environ.copy()
    if args.engine == "openaicompatible":
        if args.openai_compatible_model:
            cmd += ["--openai-compatible-model", args.openai_compatible_model]
            env["OPENAI_COMPATIBLE_MODEL"] = args.openai_compatible_model
        if args.openai_compatible_base_url:
            cmd += ["--openai-compatible-base-url", args.openai_compatible_base_url]
            env["OPENAI_COMPATIBLE_BASE_URL"] = args.openai_compatible_base_url
        if args.openai_compatible_api_key_env:
            key = env.get(args.openai_compatible_api_key_env)
            if not key:
                raise SystemExit(f"Environment variable not set: {args.openai_compatible_api_key_env}")
            env["OPENAI_COMPATIBLE_API_KEY"] = key
            cmd += ["--openai-compatible-api-key", key]
    if args.pages:
        cmd += ["--pages", args.pages]
    if args.skip_scanned_detection:
        cmd.append("--skip-scanned-detection")
    if args.ocr_workaround:
        cmd.append("--ocr-workaround")
    if args.auto_enable_ocr_workaround:
        cmd.append("--auto-enable-ocr-workaround")
    if args.use_alternating_pages_dual:
        cmd.append("--use-alternating-pages-dual")
    if args.only_include_translated_page:
        cmd.append("--only-include-translated-page")
    if args.enhance_compatibility:
        cmd.append("--enhance-compatibility")
    if args.split_short_lines:
        cmd.append("--split-short-lines")
    if args.no_auto_extract_glossary:
        cmd.append("--no-auto-extract-glossary")
    if args.primary_font_family:
        cmd += ["--primary-font-family", args.primary_font_family]
    if args.no_mono:
        cmd.append("--no-mono")
    if args.no_dual:
        cmd.append("--no-dual")
    display_cmd = []
    redact_next = False
    for part in cmd:
        if redact_next:
            display_cmd.append("<redacted>")
            redact_next = False
            continue
        display_cmd.append(part)
        if part == "--openai-compatible-api-key":
            redact_next = True
    print("$ " + " ".join(map(str, display_cmd)))
    if args.dry_run:
        return
    try:
        subprocess.run(cmd, cwd=str(PDF2ZH_ENV), env=env, check=True)
    except subprocess.CalledProcessError as e:
        raise SystemExit(f"pdf2zh failed with exit code {e.returncode}") from None


def translated_pdfs(out_dir: Path) -> list[Path]:
    return sorted(p for p in out_dir.glob("*.pdf") if p.is_file())


def add_note(client: httpx.Client, base: str, parent_key: str, out_dir: Path) -> None:
    pdfs = [str(p) for p in translated_pdfs(out_dir)]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    note_html = (
        f"<p>pdf2zh-next translation completed at {now}</p>"
        + "<ul>"
        + "".join(f"<li><code>{p}</code></li>" for p in pdfs)
        + "</ul>"
    )
    payload = [{"itemType": "note", "parentItem": parent_key, "note": note_html}]
    r = client.post(f"{base}/items", json=payload)
    r.raise_for_status()
    print(f"✓ Added Zotero child note for {parent_key}")


def attach_outputs_to_zotero(
    parent_key: str,
    out_dir: Path,
    creds: dict[str, str],
    group: str | None = None,
    title_prefix: str = "pdf2zh",
) -> None:
    # Keep this isolated so normal local-only translations do not require pyzotero.
    from pyzotero.zotero import Zotero

    pdfs = translated_pdfs(out_dir)
    if not pdfs:
        raise SystemExit(f"No translated PDFs found in {out_dir}; cannot attach to Zotero")
    library_id = group or creds["user_id"]
    library_type = "group" if group else "user"
    z = Zotero(library_id, library_type, creds["api_key"])
    files = [(f"{title_prefix} {p.name}", str(p)) for p in pdfs]
    result = z.attachment_both(files, parentid=parent_key)
    print(f"✓ Attached {len(files)} translated PDF(s) to Zotero item {parent_key}")
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


def main() -> None:
    p = argparse.ArgumentParser(description="Zotero PDF attachment -> pdf2zh-next")
    p.add_argument("--item", help="Zotero parent item key")
    p.add_argument("--query", help="Search Zotero top-level items and use the first match")
    p.add_argument("--attachment", help="Specific child PDF attachment key")
    p.add_argument("--group", help="Group library ID (read/write only if API key permits it)")
    p.add_argument("--out", default=str(DEFAULT_OUT), help="Output root directory")
    p.add_argument("--engine", default="bing", choices=["bing", "openai", "deepl", "google", "deepseek", "ollama", "gemini", "groq", "openaicompatible", "siliconflowfree"])
    p.add_argument("--openai-compatible-model", help="Model for --engine openaicompatible, e.g. deepseek-v4-flash")
    p.add_argument("--openai-compatible-base-url", help="Base URL for --engine openaicompatible")
    p.add_argument("--openai-compatible-api-key-env", help="Env var containing the OpenAI-compatible API key; value is passed only via subprocess env")
    p.add_argument("--lang-in", default="en")
    p.add_argument("--lang-out", default="ja")
    p.add_argument("--pages", help="Page range passed to pdf2zh, e.g. 1-10")
    p.add_argument("--qps", default="1")
    p.add_argument("--skip-scanned-detection", action="store_true", default=True)
    p.add_argument("--ocr-workaround", action="store_true", help="Use white text background to avoid overlay on scanned/original text")
    p.add_argument("--auto-enable-ocr-workaround", action="store_true")
    p.add_argument("--use-alternating-pages-dual", action="store_true", help="Use alternating original/translated pages for dual PDF to avoid line overlap")
    p.add_argument("--only-include-translated-page", action="store_true", help="Only include selected translated pages when --pages is used")
    p.add_argument("--enhance-compatibility", action="store_true")
    p.add_argument("--split-short-lines", action="store_true")
    p.add_argument("--no-auto-extract-glossary", action="store_true", help="Disable LLM glossary extraction; useful for long PDFs or API timeouts")
    p.add_argument("--primary-font-family", choices=["serif", "sans-serif", "script"])
    p.add_argument("--no-mono", action="store_true")
    p.add_argument("--no-dual", action="store_true")
    p.add_argument("--add-note", action="store_true", help="Add a Zotero child note with local output paths")
    p.add_argument("--attach-output", action="store_true", help="Upload translated mono/dual PDFs back to the Zotero parent item")
    p.add_argument("--attachment-title-prefix", default="pdf2zh", help="Title prefix for uploaded Zotero attachments")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

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
        run_pdf2zh(pdf_path, out_dir, args)
        if args.add_note and not args.dry_run:
            add_note(client, base, item_key, out_dir)
        if args.attach_output:
            if args.dry_run:
                print(f"[dry-run] would attach translated PDFs from {out_dir} to Zotero item {item_key}")
            else:
                attach_outputs_to_zotero(
                    item_key,
                    out_dir,
                    creds,
                    group=args.group,
                    title_prefix=args.attachment_title_prefix,
                )
        print(f"Output directory: {out_dir}")


if __name__ == "__main__":
    main()
