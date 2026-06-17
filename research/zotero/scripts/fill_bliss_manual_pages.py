#!/usr/bin/env python3
"""Manual fallback for Bliss 1935 pages that make BabelDOC/pdf2zh stall.

Uses OpenCode OpenAI-compatible deepseek-v4-flash to translate extracted page text,
then creates page-level mono/dual PDFs compatible with run_bliss_deepseek_pagewise.py.
"""
from __future__ import annotations

import json
import os
import textwrap
import time
from pathlib import Path

from openai import OpenAI
import pymupdf

ENV_FILE = Path("/opt/data/.env")
ROOT = Path("/opt/data/workspace/llm-kb.miya-lis.net/raw/papers/zotero_pdf2zh_deepseek_v4_flash_pagewise/The System of the Sciences and the Organization of Knowledge__AT3VBXHL")
SRC = ROOT / "source" / "Bliss - 1935 - The System of the Sciences and the Organization of Knowledge.pdf"
PARTS = ROOT / "parts"
FONT = Path("/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf")
BASE_NAME = "Bliss - 1935 - The System of the Sciences and the Organization of Knowledge"
MODEL = "deepseek-v4-flash"
BASE_URL = "https://opencode.ai/zen/go/v1"
PAGES = [15, 19]


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def call_deepseek(page_no: int, source_text: str) -> str:
    key = os.environ.get("OPENCODE_GO_API_KEY")
    if not key:
        raise RuntimeError("OPENCODE_GO_API_KEY is not set")
    prompt = f"""あなたは学術文献PDFの翻訳者です。以下は Henry Evelyn Bliss (1935) の論文PDFの {page_no} ページ目から抽出した英語/図版ラベル/OCRテキストです。\n\n目的: 日本語PDFの1ページに収めるため、忠実だが簡潔な日本語訳を作ってください。\n制約:\n- 原文にない解説を足さない。\n- OCRノイズや崩れた文字は、文脈から明らかな場合だけ自然に補正する。\n- 図版ページでは、表題・ラベル・キャプションを箇条書きで整理する。\n- JSTOR利用条件行は「JSTOR利用条件」程度に短く処理してよい。\n- 出力は日本語訳のみ。前置き不要。\n\n--- SOURCE TEXT ---\n{source_text}\n"""
    client = OpenAI(api_key=key, base_url=BASE_URL, timeout=180)
    last_err = None
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                temperature=0.1,
                max_tokens=20000,
                messages=[
                    {"role": "system", "content": "Translate academic English/OCR text into concise, faithful Japanese."},
                    {"role": "user", "content": prompt},
                ],
            )
            content = (resp.choices[0].message.content or "").strip()
            if content:
                return content
            last_err = RuntimeError(f"empty content; finish_reason={resp.choices[0].finish_reason}; usage={resp.usage}")
        except Exception as e:  # OpenAI client raises typed exceptions; keep this one-off robust.
            last_err = e
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"deepseek translation failed for page {page_no}: {last_err}")


def wrap_text(text: str, width: int = 33) -> str:
    # PyMuPDF textbox wrapping with Japanese can be conservative depending on font metrics;
    # manual wrapping keeps the text inside the narrow JSTOR page size.
    lines = []
    for para in text.splitlines():
        para = para.rstrip()
        if not para:
            lines.append("")
            continue
        if len(para) <= width:
            lines.append(para)
        else:
            # Break Japanese continuously, but keep indented bullets readable.
            indent = "  " if para.startswith(("-", "・", "—")) else ""
            chunks = textwrap.wrap(para, width=width, break_long_words=True, break_on_hyphens=False)
            for i, ch in enumerate(chunks):
                lines.append((indent if i else "") + ch)
    return "\n".join(lines)


def make_translation_pdf(src_doc: pymupdf.Document, page_no: int, ja_text: str, out_mono: Path, out_dual: Path) -> None:
    src_page = src_doc[page_no - 1]
    rect = src_page.rect
    mono_doc = pymupdf.open()
    page = mono_doc.new_page(width=rect.width, height=rect.height)
    # Header.
    header = f"Bliss (1935) p.{page_no} — 日本語訳（deepseek-v4-flash / manual fallback）"
    page.insert_textbox(
        pymupdf.Rect(24, 18, rect.width - 24, 48),
        header,
        fontsize=8,
        fontname="ipagp",
        fontfile=str(FONT),
        color=(0.10, 0.10, 0.10),
    )
    # Body. Page is small, so use compact Japanese font size.
    body = wrap_text(ja_text, width=35 if page_no == 19 else 30)
    fontsize = 7.1 if page_no == 19 else 6.5
    page.insert_textbox(
        pymupdf.Rect(24, 52, rect.width - 24, rect.height - 34),
        body,
        fontsize=fontsize,
        fontname="ipagp",
        fontfile=str(FONT),
        lineheight=1.12,
        color=(0, 0, 0),
    )
    page.insert_textbox(
        pymupdf.Rect(24, rect.height - 28, rect.width - 24, rect.height - 12),
        "注: このページはBabelDOCがレイアウト解析で停止したため、抽出テキストをLLMで翻訳して別ページ化。",
        fontsize=5.5,
        fontname="ipagp",
        fontfile=str(FONT),
        color=(0.35, 0.35, 0.35),
    )
    out_mono.parent.mkdir(parents=True, exist_ok=True)
    if out_mono.exists():
        out_mono.unlink()
    mono_doc.save(str(out_mono), garbage=4, deflate=True)

    dual_doc = pymupdf.open()
    dual_doc.insert_pdf(src_doc, from_page=page_no - 1, to_page=page_no - 1)
    dual_doc.insert_pdf(mono_doc)
    if out_dual.exists():
        out_dual.unlink()
    dual_doc.save(str(out_dual), garbage=4, deflate=True)
    mono_doc.close()
    dual_doc.close()


def main() -> None:
    load_dotenv(ENV_FILE)
    if not FONT.exists():
        raise RuntimeError(f"Japanese font not found: {FONT}")
    doc = pymupdf.open(str(SRC))
    for page_no in PAGES:
        page_dir = PARTS / f"page_{page_no:02d}"
        out_dir = page_dir / "translated"
        out_dir.mkdir(parents=True, exist_ok=True)
        mono = out_dir / f"{BASE_NAME}.ja.mono.pdf"
        dual = out_dir / f"{BASE_NAME}.ja.dual.pdf"
        # Regenerate manual fallback to ensure contents match this script.
        source_text = doc[page_no - 1].get_text("text").strip()
        translation_path = page_dir / "manual_translation_ja.txt"
        if translation_path.exists() and translation_path.read_text(encoding="utf-8").strip():
            ja = translation_path.read_text(encoding="utf-8").strip()
        else:
            ja = call_deepseek(page_no, source_text)
            translation_path.write_text(ja + "\n", encoding="utf-8")
        make_translation_pdf(doc, page_no, ja, mono, dual)
        print(f"page {page_no}: wrote {mono} ({mono.stat().st_size} bytes)")
        print(f"page {page_no}: wrote {dual} ({dual.stat().st_size} bytes)")
    doc.close()


if __name__ == "__main__":
    main()
