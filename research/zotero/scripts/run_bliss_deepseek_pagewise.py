#!/usr/bin/env python3
"""One-off: translate Bliss 1935 page-by-page with pdf2zh-next + deepseek-v4-flash.

Why pagewise: full-document OpenAI-compatible translation stalled during automatic
layout/term stages. Single-page runs complete, so this builds final mono/dual PDFs
by translating each page with --only-include-translated-page and merging outputs.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pymupdf
from pyzotero.zotero import Zotero

ITEM_KEY = "AT3VBXHL"
USER_ID = "14272705"
CRED_FILE = Path("/opt/data/workspace/.skills/zotero_credentials.json")
ENV_FILE = Path("/opt/data/.env")
PDF2ZH = Path("/opt/data/workspace/pdf2zh-env/.venv/bin/pdf2zh")
PDF2ZH_ENV = Path("/opt/data/workspace/pdf2zh-env")
SOURCE_CANDIDATES = [
    Path("/opt/data/workspace/llm-kb.miya-lis.net/raw/papers/zotero_pdf2zh/The System of the Sciences and the Organization of Knowledge__AT3VBXHL/source/Bliss - 1935 - The System of the Sciences and the Organization of Knowledge.pdf"),
    Path("/opt/data/workspace/llm-kb.miya-lis.net/raw/papers/zotero_pdf2zh_deepseek_page2_test/The System of the Sciences and the Organization of Knowledge__AT3VBXHL/source/Bliss - 1935 - The System of the Sciences and the Organization of Knowledge.pdf"),
]
ROOT = Path("/opt/data/workspace/llm-kb.miya-lis.net/raw/papers/zotero_pdf2zh_deepseek_v4_flash_pagewise/The System of the Sciences and the Organization of Knowledge__AT3VBXHL")
SOURCE = ROOT / "source" / "Bliss - 1935 - The System of the Sciences and the Organization of Knowledge.pdf"
PARTS = ROOT / "parts"
FINAL = ROOT / "final"
MAX_WORKERS = int(os.environ.get("PDF2ZH_PAGEWISE_WORKERS", "2"))


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)


def prepare_source() -> None:
    SOURCE.parent.mkdir(parents=True, exist_ok=True)
    if SOURCE.exists() and SOURCE.stat().st_size > 0:
        return
    for src in SOURCE_CANDIDATES:
        if src.exists() and src.stat().st_size > 0:
            shutil.copy2(src, SOURCE)
            return
    raise SystemExit("Source PDF not found in known locations")


def run_page(page: int) -> tuple[int, Path, Path]:
    page_dir = PARTS / f"page_{page:02d}"
    out_dir = page_dir / "translated"
    log_path = page_dir / "run.log"
    out_dir.mkdir(parents=True, exist_ok=True)
    mono_existing = list(out_dir.glob("*.ja.mono.pdf"))
    dual_existing = list(out_dir.glob("*.ja.dual.pdf"))
    if mono_existing and dual_existing:
        return page, mono_existing[0], dual_existing[0]

    key = os.environ.get("OPENCODE_GO_API_KEY")
    if not key:
        raise RuntimeError("OPENCODE_GO_API_KEY is not set")

    cmd = [
        str(PDF2ZH), str(SOURCE),
        "--openaicompatible",
        "--lang-in", "en",
        "--lang-out", "ja",
        "--output", str(out_dir),
        "--qps", "1",
        "--openai-compatible-model", "deepseek-v4-flash",
        "--openai-compatible-base-url", "https://opencode.ai/zen/go/v1",
        "--openai-compatible-api-key", key,
        "--openai-compatible-timeout", "300",
        "--pages", str(page),
        "--skip-scanned-detection",
        "--ocr-workaround",
        "--use-alternating-pages-dual",
        "--only-include-translated-page",
        "--no-auto-extract-glossary",
    ]
    redacted = ["<redacted>" if i and cmd[i-1] == "--openai-compatible-api-key" else x for i, x in enumerate(cmd)]
    with log_path.open("w", encoding="utf-8") as log:
        log.write("$ " + " ".join(redacted) + "\n\n")
        log.flush()
        env = os.environ.copy()
        env.setdefault("OMP_NUM_THREADS", "2")
        env.setdefault("ORT_NUM_THREADS", "2")
        proc = subprocess.run(
            cmd,
            cwd=str(PDF2ZH_ENV),
            stdout=log,
            stderr=subprocess.STDOUT,
            env=env,
            timeout=900,
        )
    if proc.returncode != 0:
        raise RuntimeError(f"page {page} failed: exit {proc.returncode}; see {log_path}")
    mono = list(out_dir.glob("*.ja.mono.pdf"))
    dual = list(out_dir.glob("*.ja.dual.pdf"))
    if not mono or not dual:
        raise RuntimeError(f"page {page} produced no mono/dual output; see {log_path}")
    return page, mono[0], dual[0]


def merge_pdfs(items: list[tuple[int, Path, Path]]) -> tuple[Path, Path]:
    FINAL.mkdir(parents=True, exist_ok=True)
    mono_out = FINAL / "Bliss - 1935 - The System of the Sciences and the Organization of Knowledge.deepseek-v4-flash.ocr.ja.mono.pdf"
    dual_out = FINAL / "Bliss - 1935 - The System of the Sciences and the Organization of Knowledge.deepseek-v4-flash.ocr.ja.dual.pdf"
    mono_doc = pymupdf.open()
    dual_doc = pymupdf.open()
    for page, mono, dual in sorted(items):
        with pymupdf.open(str(mono)) as m:
            mono_doc.insert_pdf(m)
        with pymupdf.open(str(dual)) as d:
            dual_doc.insert_pdf(d)
    if mono_out.exists():
        mono_out.unlink()
    if dual_out.exists():
        dual_out.unlink()
    mono_doc.save(str(mono_out), garbage=4, deflate=True)
    dual_doc.save(str(dual_out), garbage=4, deflate=True)
    mono_doc.close(); dual_doc.close()
    return mono_out, dual_out


def upload_outputs(mono: Path, dual: Path) -> dict:
    creds = json.loads(CRED_FILE.read_text())
    z = Zotero(creds["user_id"], "user", creds["api_key"])
    files = [
        ("pdf2zh deepseek-v4-flash OCR pagewise mono " + mono.name, str(mono)),
        ("pdf2zh deepseek-v4-flash OCR pagewise dual " + dual.name, str(dual)),
    ]
    return z.attachment_both(files, parentid=ITEM_KEY)


def main() -> None:
    load_dotenv(ENV_FILE)
    prepare_source()
    doc = pymupdf.open(str(SOURCE))
    page_count = doc.page_count
    doc.close()
    print(f"Source: {SOURCE}")
    print(f"Pages: {page_count}; workers: {MAX_WORKERS}")
    PARTS.mkdir(parents=True, exist_ok=True)
    results: list[tuple[int, Path, Path]] = []
    pages = list(range(1, page_count + 1))
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = {ex.submit(run_page, p): p for p in pages}
        for fut in as_completed(futs):
            p = futs[fut]
            try:
                page, mono, dual = fut.result()
                results.append((page, mono, dual))
                print(f"✓ page {page:02d}: {mono.name} / {dual.name}", flush=True)
            except Exception as e:
                print(f"✗ page {p:02d}: {e}", file=sys.stderr, flush=True)
                raise
    mono, dual = merge_pdfs(results)
    print(f"✓ merged mono: {mono} ({mono.stat().st_size:,} bytes)")
    print(f"✓ merged dual: {dual} ({dual.stat().st_size:,} bytes)")
    upload = upload_outputs(mono, dual)
    print("✓ uploaded to Zotero")
    print(json.dumps(upload, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
