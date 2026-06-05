---
name: ziten
description: 統一RAGシステム — 辞書（lisdict）・百科事典（ieko）・教科書（d2l）を横断する
  共通索引・検索ライブラリ。FAISS + BM25 ハイブリッド検索 + 知識グラフ。
version: 4.0.0
tags: [rag, search, knowledge-graph, hybrid-search, lis, dictionary, encyclopedia, textbook, faiss, bm25]
metadata:
  hermes:
    tags: [rag, search, knowledge-graph, hybrid-search, lis, dictionary, encyclopedia, textbook, faiss, bm25]
    category: research
    supersedes: [dictionary-knowledge-graph-rag, d2l-rag]
---

# ziten — 統一RAGシステム

`/opt/data/workspace/ziten/` にある共通ライブラリを軸に、**3つのデータセット（lisdict / ieko / d2l）** を統一的な形式で索引・検索するシステム。

## 起動条件（このスキルを使うとき）

- LIS専門用語の質問（RDA, FRBR, AACR2, NDC, 目録規則 etc.）
- 「○○って何？」「××と△△の関係は？」といった辞書的問い合わせ
- 概念定義の引用（論文向け）
- ドメインサーベイ／複数概念の比較
- IEKO百科事典・D2L教科書の内容検索

## 全体構成

```
/opt/data/workspace/
├── lisdict/                  # 図書館情報学辞典 ✅ ziten化済
│   ├── build.py              #   ziten使用
│   ├── query.py              #   CLI検索（388行, ziten.search使用）
│   ├── entries/*.md          #   1,796語
│   ├── data/                 #   dict.json, graph.json, term_to_file.json
│   └── index/                #   index.faiss, bm25.pkl, meta.pkl, embedder.pkl
├── ieko/                     # ISKO Encyclopedia (127記事) ✅ ziten化完了
│   ├── build.py              #   ziten使用（カスタムグラフ：通読セクション＋著者＋相互参照＋ inside-text）
│   ├── query.py              #   CLI検索（ziten.search使用, 3391 edges リッチグラフ）
│   ├── entries/*.md          #   127記事（entry_type=article）
│   ├── data/                 #   dict.json, graph.json (133 nodes), term_to_file.json
│   └── index/                #   index.faiss, bm25.pkl, meta.pkl, embedder.pkl
├── d2l/                      # Dive into Deep Learning ✅ ziten化済
│   ├── build.py              #   ziten使用
│   ├── query.py              #   CLI検索
│   ├── entries/*.md          #   27章（470チャンクから集約）
│   ├── data/                 #   dict.json, graph.json, term_to_file.json
│   └── index/                #   index.faiss, bm25.pkl, meta.pkl, embedder.pkl
└── rag/                      # 統一CLI ✅ 実装済
    └── query.py              #   ~/.local/bin/rag にsymlink
```

## エントリタイプ

zitenは3種類のエントリタイプをサポート:

| type | 形式 | グラフ戦略 | コーパス |
|---|---|---|---|
| `simple` | term + description | related 参照項目エッジ | lisdict (1,796語) |
| `article` | title + sections[] | belongs_to + same_section + same_author + cross_reference + see_also_ref エッジ | ieko (127記事, 3391 edges) |
| `chapters` | chapter + heading + text | chapter→heading 階層エッジ | d2l (27章) |

## 統一CLI: `rag`

インストール先: `~/.local/bin/rag` → `/opt/data/workspace/rag/query.py`（詳細は `references/unified-cli.md`）

```bash
rag "RDA"                              # lisdict（default）
rag -c ieko "faceted classification"   # IEKO百科事典
rag -c d2l "attention"                 # Dive into Deep Learning
rag -c both "FRBR"                     # lisdict + ieko 同時
rag -c all "semantic"                    # 全3corpus同時
rag "RDA" -e                           # 完全一致
rag "RDA" -a                           # エージェンティック検索
rag --stats                            # lisdict統計
rag "RDA" -n 3                         # 3件表示
```

### フラグ一覧

| フラグ | 機能 |
|--------|------|
| `-c lis\|ieko\|d2l\|both\|all` | 検索対象（default: lis） |
| `-n N` | 表示件数（default: 5） |
| `-e`/`--exact` | 完全一致 |
| `-a`/`--agentic` | エージェンティック検索 |
| `--stats` | 統計表示 |

## コーパス別操作

### lisdict（図書館情報学辞典）— ✅ ziten化完了

```bash
# 検索
cd /opt/data/workspace/lisdict
python query.py "RDA"                   # ハイブリッド検索
python query.py "RDA" --expand          # グラフ展開付き
python query.py "RDA" --llm             # LLM回答生成
python query.py --exact "RDA"           # 完全一致
python query.py --stats                 # 統計表示
python query.py "RDA" --raw             # JSON出力

# 索引再構築
python build.py --force                 # 全再構築
python build.py --skip-embed            # embedding以外
python build.py --entries-only          # MD→JSON+graphのみ

# データ
ls entries/ | wc -l                     # 1,796
ls data/                                # dict.json graph.json term_to_file.json
ls index/                               # index.faiss bm25.pkl meta.pkl embedder.pkl
```

### d2l（Dive into Deep Learning）— ✅ ziten化完了

```bash
cd /opt/data/workspace/d2l
python query.py "attention mechanism" -n 5
python build.py --force
rag "CNN architecture" -c d2l
```

### ieko（ISKO Encyclopedia）— ✅ ziten化完了

```bash
cd /opt/data/workspace/ieko
python query.py "faceted classification"    # ハイブリッド検索（FAISS+BM25）
python query.py "Classification" --expand   # グラフ展開付き（133 nodes / 3391 edges）
python query.py --graph "Classification"    # 特定エントリのグラフ詳細
python query.py --stats                     # 統計表示
python query.py --agentic "knowledge organization"  # エージェンティック検索
python build.py --force                     # 全再構築

# rag CLI（統一）
rag -c ieko "faceted classification"        # IEKOのみ
rag -c both "classification"                # lisdict + IEKO 同時
```

## ZitenConfig API

各corpusのbuild.py/query.pyで `ZitenConfig` を生成して使用:

```python
from pathlib import Path
from ziten import ZitenConfig

config = ZitenConfig(
    name='corpus_name',          # 内部識別子
    title='表示名',               # 表示用
    entry_type='simple',         # simple | article | chapters
    source_path=None,            # 変換元データ（JSON/JSONL）
    data_dir=Path('data'),       # data/ 出力先
    entries_dir=Path('entries'), # MDファイル格納先
    id_field='term',             # IDフィールド名
    text_field='description',    # 索引対象テキストフィールド
    title_field='term',          # 表示タイトル
    url_field='url',             # URLフィールド
    related_field='related',     # 関連項目フィールド
    ref_pattern=r'',             # 参照項目抽出用正規表現
    embed_model='intfloat/multilingual-e5-small',
)
```

### 自動派生パス

| プロパティ | 値 |
|---|---|
| `data_dir / dict_json` | data/dict.json |
| `data_dir / graph_json` | data/graph.json |
| `data_dir / term_map_json` | data/term_to_file.json |
| `index_dir / faiss_index` | index/index.faiss |
| `index_dir / bm25_pkl` | index/bm25.pkl |
| `index_dir / meta_pkl` | index/meta.pkl |
| `index_dir / embedder_pkl` | index/embedder.pkl |

## ビルドパイプライン

各corpusで共通の3ステップ:

### Step 1: entries/*.md → dict.json + graph.json

```python
from ziten import ZitenConfig
from ziten.convert import md_to_json
from ziten.graph import build_graph

config = ZitenConfig(...)
entries = md_to_json(config)     # → data/dict.json
build_graph(config, entries)     # → data/graph.json
```

### Step 2: FAISS embedding

```python
from ziten.index import build as build_index
build_index(config, force=True)
```

- モデル: `intfloat/multilingual-e5-small` (384-dim)
- 測度: Inner Product (正規化ベクトル)
- 出力: `index/index.faiss`, `index/meta.pkl`, `index/embedder.pkl`

### Step 3: BM25（Step 2に内包）

自動生成: `index/bm25.pkl`

## 検索モード（query.py）

### Mode 1: ハイブリッド検索（default）

BM25 + FAISS embedding の RRF融合（K=60）。

```python
from ziten.search import hybrid_search
results = hybrid_search(config, "RDA", top_k=5)
# → [{id, title, snippet, url, rrf_score, graph_edge_count}]
```

### Mode 2: 完全一致

```python
from ziten.search import exact_search
entry = exact_search(config, "RDA")
# → dict or None
```

### Mode 3: グラフ展開

```python
from ziten.search import expand_graph
graph = expand_graph(config, entry_id, hops=2)
# → {source, nodes: [{depth, id, link_to}], total}
```

### Mode 4: エージェンティック検索

3段階: ディレクトリ俯瞰 → RAG精密検索 → 全文MD読込＋グラフ展開。

```python
from ziten.search import agentic_search
result = agentic_search(config, "目録規則の変遷", top_k=5)
# → {query, results (full_markdown付き), graph, phase1_candidates}
```

## 一般的なユースケース

### 単語の定義確認
```
rag "RDA" -e          → 完全一致
rag "RDA" -n 3        → ハイブリッド（上位3件）
rag "RDAとAACR2" -a   → エージェンティックで比較
```

### 参照関係の探索
```
cd /opt/data/workspace/lisdict && python query.py "目録規則" --expand --depth 2
```

### 論文の引用用定義
```
rag "RDA" -e    → 辞書原文＋URLを出典として提示
```

### ドメインサーベイ
```bash
# 複数クエリで体系的にカバー
rag "知識の組織化" -n 5
rag "分類法 分類表" -n 5
rag "メタデータ オントロジー" -n 5
# 具体用語をexact取得
rag "日本十進分類法" -e
rag "オントロジー" -e
```

## 既存課題・注意点

### 依存関係
```bash
pip install --break-system-packages sentence-transformers faiss-cpu rank-bm25 nltk pyyaml
```
初回起動時はsentence-transformersモデルのダウンロードに数分。
2回目以降はキャッシュ使用で高速。

### BM25の日本語トークナイズ
MeCab無し。nltk word_tokenize フォールバック。
韓国語テキスト（d2l）はchar-level tokenizerを自動検出・切替。

### グラフの限界
- lisdict: 未解決リンク91件（辞書内に該当語なし）
- グラフ展開は最初の結果のみ起点

### KB連携 (LLM-KB wiki)

3 corpus の entry ファイルは KB の `raw/corpora/` から参照可能:

```
raw/corpora/
  ├── lisdict/  →  ../../../lisdict/entries/   (1,796件)
  ├── ieko/     →  ../../../ieko/entries/       (127件)
  └── d2l/      →  ../../../d2l/entries/        (470件)
```

KB内で `raw/corpora/lisdict/FRBR.md` のように直接参照できる。symlinkはgit追跡対象（mode 120000）。clone先では実体が切れる点に注意。

## エラーハンドリング
- query.pyエラー時は直接叩いて確認
- FAISS/BM25欠損: `python build.py --force` で再構築
- 依存不足: `pip install --break-system-packages ...` で追加

## 出典データ

| corpus | type | 件数 | 出典 |
|--------|------|------|------|
| **lisdict** | simple | 1,796語 | 図書館情報学辞典 / kotobank.jp |
| **ieko** | article | 127件 (3391 edges) | ISKO Encyclopedia of KO / isko.org |
| **d2l** | chapters | 27章 (470chunks) | Dive into Deep Learning / d2l.ai |
