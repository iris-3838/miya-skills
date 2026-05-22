---
name: llm-kb-wiki
description: "Karpathy's LLM Wiki: build/query interlinked markdown KB."
version: 1.2
author: Hermes Agent
---

# LLM Wiki (llm-kb-wiki)

Knowledge base built on Karpathy's [llm-wiki](https://github.com/karpathy/llm-wiki) concept. Fork at `llm-kb.example.com`.

## Usage

The wiki uses a local markdown-based knowledge base with bidirectional linking.

### Wiki Location
```
/workspace/llm-kb.example.com/
```

### Sources
/workspace/llm-kb.example.com/
```

## Design: Human Zone / Agent Zone

Karpathy の llm-wiki 設計思想に基づき、KB は以下の2ゾーンに分かれる：

| Zone | ディレクトリ | 管理者 | 役割 |
|------|-------------|--------|------|
| **Agent Zone** | concepts/, comparisons/, entities/, queries/, index.md, log.md | Agent（このAI） | 知識の構造化・編集・整理 |
| **Human Zone** | raw/ 以下（articles/, papers/, transcripts/, assets/） | 人間（owner） | 生データの配置 |

Agent は KB の `raw/` を除く全ファイルを直接作成・編集できる。権限設定:
```bash
sudo chmod -R o+w /workspace/llm-kb.example.com
```

### Common Tasks

**Sync with GitHub:**
```bash
cd /workspace/llm-kb.example.com
GIT_CONFIG_NOSYSTEM=1 HOME=/tmp git pull origin main
GIT_CONFIG_NOSYSTEM=1 HOME=/tmp git push origin main
```

## Content Ingestion

### Adding a New Entry

1. Create a Markdown file under the appropriate subdirectory (e.g., `concepts/`, `papers/`, `notes/`)
2. Include YAML frontmatter with: `title`, `created`, `type`, `tags`, `sources`
3. Use `[[]]` wiki-style links to interlink with existing entries
4. Verify by rebuilding or checking index.md

### PDF → Markdown Conversion

#### Step 0: PDF Type Detection（必須の事前判定）

変換方法を選ぶ前に、PDFがテキストベースか画像ベースかを判定する:

```bash
# 方法A: markitdown で抽出を試みる（最速）
result=$(python3 -m markitdown "$PDF" 2>/dev/null | head -100 | wc -c)
echo "markitdown output: ${result} bytes"
# 100 bytes 未満 → 画像ベースの可能性大

# 方法B: ページごとにテキスト有無を確認
python3 -c "
import fitz
doc = fitz.open('$PDF')
text_pages = sum(1 for i in range(len(doc)) if doc[i].get_text().strip())
print(f'Pages with extractable text: {text_pages}/{len(doc)}')
for i in range(min(3, len(doc))):
    t = doc[i].get_text().strip()
    print(f'  Page {i+1}: {\"HAS TEXT\" if t else \"(empty/image)\"} ({len(t)} chars)')
"
```

| 判定結果 | 採用する方法 |
|----------|------------|
| 全ページテキストあり | → **markitdown** で直接変換 |
| 一部ページのみテキスト | → **markitdown + 画像ページは個別対応** |
| 全ページテキストなし | → **画像ベース処理**（下記参照）|

#### Step 1: テキストベースPDF → markitdown

```bash
python3 -m pip install --break-system-packages --user "markitdown[pdf]"
python3 -m markitdown "$PDF" > /tmp/output.md
```

#### Step 2: 画像ベースPDF — フォールバックチェーン

画像ベースのPDF（Google Slides エクスポート、PowerPoint 画像埋め込み、スキャン資料）は、**下記の優先順位でフォールバック**する:

```
① vision_analyze（最も簡単）→ ② 画像抽出＋vision_analyze → ③ OCR（tesseract）
                                                ↕
                                   ④ 画像抽出＋ユーザーハンドオフ
```

---

**① vision_analyze（モデルが vision 対応の場合）**

```bash
# 最初の数ページを試す
python3 -c "
import fitz
doc = fitz.open('$PDF')
for i in range(min(3, len(doc))):
    page = doc[i]
    pix = page.get_pixmap(dpi=150)
    pix.save(f'/tmp/pdf_page_{i+1:02d}.png')
    print(f'/tmp/pdf_page_{i+1:02d}.png')
"
# → vision_analyze(image_url='/tmp/pdf_page_01.png') で各ページ読み取り
```

**② 画像抽出 → vision_analyze（モデルが vision 対応だが pages が大量の場合）**

```bash
python3 -c "
import fitz
doc = fitz.open('$PDF')
for i in range(len(doc)):
    page = doc[i]
    pix = page.get_pixmap(dpi=150)
    pix.save(f'/tmp/pdf_page_{i+1:02d}.png')
print(f'Extracted {len(doc)} pages to /tmp/pdf_page_*.png')
"
```

**③ OCR（tesseract）— sudo が使える環境のみ**

```bash
sudo apt install tesseract-ocr tesseract-ocr-jpn poppler-utils
pip install pytesseract Pillow
```

```python
import fitz, pytesseract
from PIL import Image
import io

doc = fitz.open("slides.pdf")
for i in range(len(doc)):
    pix = doc[i].get_pixmap(dpi=200)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    text = pytesseract.image_to_string(img, lang="jpn+eng")
    print(f"=== Page {i+1} ===\n{text}\n")
```

**④ 画像抽出＋ユーザーハンドオフ（全ツール使えない場合の最終手段）**

現在のモデルが vision 未対応、かつ sudo/OCR も使えない場合:
1. pymupdf で全ページを PNG 出力
2. `/workspace/` などユーザーがアクセス可能な場所に保存
3. その旨をユーザーに伝え、vision-capable なモデルで画像を読み取ってもらうよう依頼

```bash
OUTDIR="/workspace/$(basename $PDF .pdf)_pages"
mkdir -p "$OUTDIR"
python3 -c "
import fitz, sys, os
doc = fitz.open(sys.argv[1])
outdir = sys.argv[2]
for i in range(len(doc)):
    pix = doc[i].get_pixmap(dpi=150)
    pix.save(os.path.join(outdir, f'page_{i+1:02d}.png'))
print(f'Saved {len(doc)} pages to {outdir}')
" "$PDF" "$OUTDIR"
```

#### 判断フローまとめ

```
PDF到着
  │
  ├─ Type Detection（markitdown先打ち + per-page check）
  │
  ├─ テキストベース → markitdown で一括変換 ✅
  │
  └─ 画像ベース
       │
       ├─ モデルが vision 対応？
       │   ├─ YES → 画像抽出 + vision_analyze ✅
       │   └─ NO
       │
       ├─ sudo / tesseract 利用可能？
       │   ├─ YES → OCR ✅
       │   └─ NO
       │
       └─ 画像抽出 → ユーザーハンドオフ（vision-capable model を案内）
```

👉 参考実例: `references/pdf-ingestion-workflow.md` の「Harness and Agent」ケーススタディ

## KB Management Workflow — 5-Phase Lifecycle

KB全体の管理は以下の5フェーズで構成される。PDF取り込みはフェーズ1〜3の一部にすぎない。

### Phase 1: 収集 (Ingestion)

**ソース種別と選択順序（常に上位から試す）:**

1. **URLあり** → `web_extract(urls=[...])`（最優先）
2. **テキストベースPDF** → `markitdown`（上記PDF変換フロー参照）
3. **日本語スキャンPDF** → `ndlocr-lite`（ocr-and-documents skill参照）
4. **会話トランスクリプト** → セッションログからの抽出、`raw/transcripts/` に保存
5. **手動ノート** → 直接Markdownとして作成

### Phase 2: 構造化 (Structuring)

取り込んだ内容を **SCHEMA慣習**（後述）に従って整形する：

- YAML frontmatter 付与（title, created, type, tags, sources, confidence）
- `[[wikilinks]]` で既存ページと相互リンク（最低2件）
- Provenance markers で変換元を追跡（`^[raw/articles/source.md]`）
- raw/ ファイルには sha256 + source_url frontmatter

### Phase 3: 保存 (Storage)

適切なディレクトリに配置：

| ディレクトリ | 内容 | 作成条件 |
|-------------|------|---------|
| `concepts/` | 概念・分析結果・ワークフロー文書 | 独立した知識単位 |
| `comparisons/` | 比較分析（論文間・ツール間） | 2+ エンティティの比較 |
| `entities/` | 人・組織のプロファイル | 特定の実体の記述 |
| `queries/` | 保存検索・分析クエリ | 再利用可能な手順 |
| `raw/articles/` | ウェブ記事原文 | 加工前の状態を保存 |
| `raw/papers/` | 論文PDF + sha256 | sha256 とともに保存 |
| `raw/transcripts/` | 会話・動画トランスクリプト | 長文の原文 |

### Phase 4: インデックス更新 (Indexing)

新しいページ作成後、必ず以下を更新：

```bash
# index.md にエントリ追加（該当セクションに1行）
# log.md に変更記録（日付・種別・概要）
# SCHEMA.md の updated 日付（必要な場合）
```

**index.md** 更新例：
```markdown
## Concepts

- [[some-new-analysis]] — 分析の概要（1行）
```

**log.md** 追記例：
```markdown
## [YYYY-MM-DD] create | KB管理ワークフロー文書
- Source: セッション内でのKB管理手順の整理
- Files created:
  - `concepts/kb-management-workflow.md` — ワークフロー定義
  - `index.md` — Concepts にエントリ追加
```

### Phase 5: 同期 (Sync)

```bash
GIT_CONFIG_NOSYSTEM=1 HOME=/tmp git -C /workspace/llm-kb.example.com add -A
GIT_CONFIG_NOSYSTEM=1 HOME=/tmp git -C /workspace/llm-kb.example.com commit -m "feat: <summary>"
GIT_CONFIG_NOSYSTEM=1 HOME=/tmp git -C /workspace/llm-kb.example.com push origin main
```

> コミットメッセージは conventional commits: `feat:` / `fix:` / `docs:` / `refactor:`

## SCHEMA Conventions

### Frontmatter

全ページにYAML frontmatterを付与する：

```yaml
---
title: ページタイトル（日本語・説明的に）
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: entity | concept | comparison | query | summary
tags: [小文字ハイフン、SCHEMA.mdの分類に従う]
sources: [raw/articles/source-name.md]
confidence: high | medium | low
---
```

raw/ エントリは別形式：

```yaml
---
source_url: https://example.com
ingested: YYYY-MM-DD
sha256: <hex digest>
---
```

### Naming Rules

- ファイル名: 小文字ハイフン（`jslis-journal-analysis-2001-2026.md`）
- ディレクトリ名: 複数形（`concepts/`, `raw/papers/`）
- tag: 小文字ハイフン、SCHEMA.mdの分類から選択
- 分割: 200行超えたら分割し、相互リンクで接続

### Wikilinks

- 全ページ間で `[[wikilinks]]` 使用（最低2件のoutbound links）
- 既存ページの参照には必ずwikilinkを使う
- raw/ からの引用には provenance marker: `^[raw/articles/source.md]`

### ページ作成判断基準 (Page Thresholds)

- **作成**: エンティティ/概念が2+ の分析に登場 → ページ化
- **追記**: 新しい分析が既存トピックをカバー → 既存ページに追記
- **スキップ**: 単なる言及（passing mention） → 非作成
- **分割**: 200行超過 → 分割 + 相互リンク

### Update Policy

- 更新時は `updated` 日付を更新
- 矛盾情報が生じた場合: 両方の立場を日付・ソース付きで併記
- frontmatter の `confidence` で信頼性を明示

## Pitfalls

### /workspace/llm-kb.example.com 書き込み不可（解決済み）

**過去の制約**: Docker hermes ユーザー (uid 10000) が KB ディレクトリに直接書き込めなかった。
- `/workspace/` 自体は 777、しかし `llm-kb.example.com/` 以下は `775` (owner=1000のみ書き込み可)
- **解決**: `sudo chmod -R o+w /workspace/llm-kb.example.com` を実行済み
- 現在は agent が Agent Zone 全ファイルに直接書き込み可能

### Git Permission Denied (`~/.gitconfig`)
`~/.gitconfig` へのアクセス権限がないため、git 操作が失敗する（exit 128）。
- **回避策:** `GIT_CONFIG_NOSYSTEM=1 HOME=/tmp` を git コマンドの前に付与する
  ```bash
  # 初回だけ safe.directory 登録が必要
  GIT_CONFIG_NOSYSTEM=1 HOME=/tmp git config --global --add safe.directory /workspace/llm-kb.example.com
  
  # 以降はこのプレフィックスで git 操作
  GIT_CONFIG_NOSYSTEM=1 HOME=/tmp git -C /workspace/llm-kb.example.com status
  GIT_CONFIG_NOSYSTEM=1 HOME=/tmp git -C /workspace/llm-kb.example.com log --oneline -5
  ```

### SpeakerDeck / SlideShare Pages May Be Deleted
発表資料の元ページが削除されている場合がある。PDF 自体のダウンロードは可能でも、元の SpeakerDeck ページは "User Not Found" になることがある。PDF ダウンロードは早めに行い、メタデータは取得しておく。

## Structure
- `*.md` files = knowledge entries
- Interlinked via `[[]]` wiki-style links
- Serves as persistent knowledge base for LIS/AI research
- See `references/pdf-ingestion-workflow.md` for detailed PDF→Markdown ingestion examples
