# PDF Ingestion Workflow — 実例集

## ツール

- **markitdown** (Microsoft): テキストベースPDF→Markdown変換。`pip install "markitdown[pdf]"`
- **pdfplumber**: markitdown の内部依存。テキスト抽出に使用。
- **PyMuPDF (fitz)**: 画像ベースPDFのページ→PNG変換、メタデータ取得、テキスト有無スキャン。

---

## 実例: テキストベースPDFの変換

```bash
# 単純変換
python3 -m markitdown paper.pdf > paper.md

# ヘッダーだけ確認
python3 -m markitdown paper.pdf | head -50
```

## 実例: 画像ベースPDF（スライド）の扱い

画像ベースのPDF（Google Slides のエクスポート、PowerPointの画像埋め込みなど）は markitdown / pdfplumber ではテキスト抽出不可。

### メタデータだけでも抽出する

```python
import fitz
doc = fitz.open("slides.pdf")
meta = doc.metadata
print(f"Title: {meta.get('title', 'N/A')}")
print(f"Creator: {meta.get('creator', 'N/A')}")
print(f"Producer: {meta.get('producer', 'N/A')}")
print(f"Pages: {len(doc)}")
```

### スライドを画像として保存する（vision分析用）

```python
import fitz
doc = fitz.open("slides.pdf")
for i in range(len(doc)):
    page = doc[i]
    pix = page.get_pixmap(dpi=150)
    pix.save(f"/tmp/slide_{i+1:02d}.png")
```

その後、`vision_analyze` で画像からテキストを読み取る（要 vision-capable model）。

### 参考文献ページだけでもテキスト抽出する

選択可能テキストが一部だけ含まれている場合がある（最終ページやフッターなど）。

```python
import fitz
doc = fitz.open("slides.pdf")
for i in range(len(doc)):
    text = doc[i].get_text().strip()
    if text:
        print(f"=== Page {i+1} ===")
        print(text)
```

---

## 実例: 「Harness and Agent」PDF — 全フォールバックを経験したケース

**元ファイル**: SpeakerDeck 「Harness and Agent」(Harness Engineering) - Google Slides エクスポート、全20ページ中19ページが画像のみ

**遭遇した障害の連鎖:**

| ステップ | 試した方法 | 結果 | 原因 |
|----------|-----------|------|------|
| ① | `markitdown` | ❌ 空出力（ほぼ0バイト） | 画像ベースPDF → テキスト抽出不可 |
| ② | PyMuPDF `get_text()` | ❌ 1/20ページのみテキスト抽出 | Google Slides export = 各ページが背景画像 |
| ③ | BrowserでPDFを開く | ❌ 不可 | agent-browser が使えない環境 |
| ④ | `vision_analyze` | ❌ エラー | モデル（DeepSeek V4 Flash）がvision未対応 |
| ⑤ | OCR (tesseract) | ❌ スキップ | コンテナ環境で sudo 不可 |

**最終手段（未実行）**: pymupdf で全ページ PNG 出力 → ユーザーにハンドオフ（vision-capable modelで読み取り依頼）

### 教訓

1. **PDFタイプ判定を最初に行う** → 変換方法を選ぶ基準になる
2. **vision_analyze を使う前に、モデルが vision 対応か事前確認する**
   - `vision_analyze` がエラーになったら諦めるのではなく、**画像抽出→ユーザーハンドオフ**に切り替える
3. **「全ツール使えない」シナリオの備えを持つ**
   - pymupdf があれば画像抽出は可能 → `/opt/data/workspace/` に出力してユーザーへ
4. **SpeakerDeck PDFの確認ポイント**
   - SpeakerDeck の直接PDF URLが存在するか確認（`https://files.speakerdeck.com/presentations/<ID>/<filename>.pdf`）
   - 元ページ削除済みでもPDFが残っていることがある

---

## 実例: SpeakerDeck からのPDFダウンロード

SpeakerDeckの公開URLから直接PDFをダウンロード可能な場合がある。

URLパターン:
```
https://files.speakerdeck.com/presentations/<ID>/<filename>.pdf
```

```bash
curl -sLO "https://files.speakerdeck.com/presentations/<ID>/<filename>.pdf"
```

注: 元ページ（`https://speakerdeck.com/<path>`）が削除済みでも、PDFファイルが直接残っていることがある。

---

## 判断フロー（簡易版）

1. `python3 -m markitdown input.pdf | wc -c` → 出力が空に近い場合は画像ベース
2. `python3 -c "import fitz; doc=fitz.open('input.pdf'); print([doc[i].get_text().strip() for i in range(len(doc))])"` → 全ページ空なら画像ベース確定
3. 画像ベースの場合：
   - モデルがvision対応 → PNG保存 + `vision_analyze`
   - vision未対応 + sudo可 → tesseract OCR
   - vision未対応 + sudo不可 → PNG保存 + ユーザーハンドオフ
4. テキストベースの場合 → markitdown で直接変換
