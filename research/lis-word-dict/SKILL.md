---
name: lis-word-dict
description: "図書館情報学辞典 — RAG検索＋知識グラフ展開。〜/ziten/ 上の FAISS/BM25 ハイブリッド検索 + 参照項目グラフ探索。"
version: 1.0.0
author: user
license: MIT
metadata:
  hermes:
    tags: [lis, dictionary, knowledge-graph, rag, search, japanese]
    category: research
    related_skills: []
---

# lis-word-dict — 図書館情報学辞典検索

`~/ziten/` に構築された図書館情報学辞典（1,796語）の RAG 検索＋知識グラフ探索を提供する。

## 実行環境

```bash
PYTHON=~/ziten/venv/bin/python
QUERY=~/ziten/query.py
```

## When This Skill Activates

- ユーザーが図書館情報学の用語について質問したとき（RDA, AACR2, FRBR, ISBD, NDC, 目録規則, 情報検索 etc.）
- 「○○って何？」「××と△△の関係は？」といった辞書的な問い合わせ
- 学術論文の文脈でLIS用語の定義確認が必要なとき

**判断基準**: 質問に LIS 専門用語が含まれているか。カタカナ用語（RDA, FRBR...）、日本語専門用語（目録規則, 書誌調整, 索引作業...）が対象。一般語や日常的な質問には使わない。

## 検索モード一覧

### Mode 1: 完全一致検索（用語名で引く）

用語名が明確な場合、最も高速で正確。

```bash
$PYTHON $QUERY --exact "RDA"
```

グラフ展開も同時に:

```bash
$PYTHON $QUERY --exact "RDA" --expand
```

### Mode 2: ハイブリッド検索（概念的な質問）

用語名が不明瞭な場合や概念的な質問。BM25 + FAISS embedding の RRF 融合。

```bash
$PYTHON $QUERY "目録規則の変遷" -n 5
```

### Mode 3: グラフ展開（参照項目を辿る）

検索結果から参照項目リンクを指定hop数展開（default: 2）。

```bash
$PYTHON $QUERY "FRBR" --expand           # default 2hop
$PYTHON $QUERY "FRBR" --expand --depth 1  # 1hopのみ
$PYTHON $QUERY "FRBR" --expand --depth 3  # 3hopまで
```

最初の結果の用語を起点にグラフを辿る。出力例:

```
RDA → 英米目録規則, FRBR, 目録規則
  ├─ 英米目録規則 → RDA, 目録規則
  └─ FRBR → IFLA LRM, 概念モデル, 著作
```

### Mode 6: ドメインサーベイ／知識グラフ構築（複数検索の連鎖）

単一の用語から参照を辿るのではなく、**あるドメイン全体をカバーする知識グラフを構築**するための連鎖検索パターン。複数のクエリを系統的に実行し、結果を統合する。

**手順**:

1. **起点**: ドメイン名でハイブリッド検索 `$PYTHON $QUERY "知識の組織化" -n 5`
2. **サブ領域の特定**: 結果から当該ドメインの主要サブ領域（分類、件名標目、書誌記述、メタデータ etc.）を特定
3. **サブ領域ごとに検索**: 各サブ領域をハイブリッド検索 `$PYTHON $QUERY "分類法 分類表 十進" -n 5`
4. **具体用語を完全一致で取得**: サブ領域の結果に現れた参照項目を `--exact` で取得
5. **反復**: カバレッジが十分になるまで (3)-(4) を繰り返す
6. **統合**: 取得した全エントリの定義と参照関係から、ドメイン全体の知識グラフを構造化

```bash
# 例: 知識・情報の組織化ドメイン
$PYTHON $QUERY "知識の組織化" -n 5
# ↓ サブ領域を特定して検索
$PYTHON $QUERY "分類法 分類表 十進" -n 5
$PYTHON $QUERY "件名標目 シソーラス 主題分析" -n 5
$PYTHON $QUERY "目録 書誌記述 FRBR RDA" -n 5
$PYTHON $QUERY "メタデータ オントロジー セマンティックウェブ" -n 5
# ↓ 参照項目に出てきた具体用語を完全一致で取得
$PYTHON $QUERY --exact "オントロジー"
$PYTHON $QUERY --exact "日本十進分類法"
$PYTHON $QUERY --exact "件名標目"
$PYTHON $QUERY --exact "記述目録法"
```

**単一展開(Mode 3)との違い**:

| Mode 3: 単一起点展開 | Mode 6: ドメインサーベイ |
|---|---|
| 1つの用語から参照を辿る | 複数のクエリでドメインをカバー |
| 参照項目リンクのみに依存 | ハイブリッド検索＋完全一致を併用 |
| 木構造（木の深さ） | ネットワーク構造（分野の幅） |
| 見落としの可能性大 | サブ領域を意識的にカバー |
| 5回未満のクエリ | 典型的に10-20回のクエリ |

### Mode 4: LLM 生成（Plamo-2）

検索結果をコンテキストにして Plamo-2 (boogie:3838) で回答生成。

```bash
$PYTHON $QUERY "RDAとAACR2の違いは？" --llm
$PYTHON $QUERY "NDCの大分類" --llm --expand
```

注: Plamo-2 は cold load ~90秒。warm 時は ~5秒で応答。

### Mode 5: 生JSON出力（パイプ連携用）

```bash
$PYTHON $QUERY "情報検索" --raw | jq '.results[0].description'
```

## 典型的なユースケース

### 単語の定義確認（最も頻繁）

ユーザーが「RDAって何？」と聞いてきたら:

1. `$PYTHON $QUERY --exact "RDA"` で完全一致を試す
2. 見つからなければ `$PYTHON $QUERY "RDA" -n 3` でハイブリッド検索
3. 結果をそのまま回答として表示

### 参照関係の探索

「目録規則の系統を調べたい」:

1. `$PYTHON $QUERY "目録規則" --expand` でグラフ展開
2. 展開結果を元に「次は ISBD も見ますか？」などと提案
3. 必要ならさらに掘り下げる

### 複数概念の比較

「RDAとAACR2の違い」:

1. `$PYTHON $QUERY --exact "RDA"` と `$PYTHON $QUERY --exact "AACR2"` を両方取得
2. それぞれの説明文を提示して比較
3. --llm が使える環境なら生成に任せても良い

### 論文の引用用定義

「論文で使うRDAの定義を正確に引用したい」:

1. `$PYTHON $QUERY --exact "RDA"` で原文を表示
2. 辞書の説明文（kotobank からの引用）をそのまま提示
3. URL も併せて表示（出典として利用可能）

### ドメインサーベイ：知識グラフによる俯瞰

「知識・情報の組織化の全体像をまとめてほしい」:

1. Mode 6（ドメインサーベイ）の手順で複数クエリを連鎖
2. 各エントリの定義と参照関係を収集
3. 結果をセクション構造（分類 / 件名標目 / 書誌記述 / 概念モデル / メタデータ / 索引言語）に整理
4. ASCIIツリー図で概念間の関係を可視化
5. 出典を明示し、参照項目リンクを活用してカバレッジを確認

具体例は `references/knowledge-organization-knowledge-graph.md` を参照。

### 可視化（参考: vis.js による知識グラフ描画）

Mode 6 で収集した概念・関係を、**インタラクティブなネットワークグラフ**として可視化する。

**ワークフロー**:
1. Mode 6 で全エントリの定義と参照関係を収集
2. 各概念をグループ（分類理論 / 件名標目 / 目録法 / 概念モデル / メタデータ / 索引言語 / KOS / 人物）に分類
3. エッジ（関係）を定義（is-a / influenced-by / implements / precedes / part-of）
4. vis.js でレンダリングし、スクリーンショット + HTML で配信

**vis.js テクニカルノート**:
- CDN URL: `https://cdnjs.cloudflare.com/ajax/libs/vis-network/10.0.2/standalone/umd/vis-network.min.js`（v9.1.6 以前のパスは404。常に cdnjs API で最新を確認してから使うこと）
- CSS: 同上ディレクトリの `vis-network.min.css`
- **Physics パラメータ（v10.0.2推奨）**:
  - ソルバ: `barnesHut`（forceAtlas2Based より密な配置に向く）
  - `gravitationalConstant: -4000`（強い引力で凝集）
  - `centralGravity: 0.4`（中央への収束を強める）
  - `springLength: 100`（短いバネで密接）
  - `springConstant: 0.08` / `damping: 0.9`
  - `stabilization.iterations: 500`
- 71〜80ノード級のグラフが典型。ノード形式は`box`（shrink 防止のため`margin`指定必須）
- ノード数が多い場合はグループ別色分け必須（凡例を別途表示）
- スクリーンショットは `browser_vision` 経由（DeepSeek は画像非対応のためエラーになるが、`screenshot_path` は取得可能。`terminal` で `cp` して `MEDIA:` で送信）

**補足: D3.js による大規模グラフ可視化**

この LIS 辞書（1,796語）よりさらに大規模な知識グラフ（IEKO百科事典: 127エントリ、5,454エッジ）では、D3.js による force-directed グラフが適している。違い:

| | vis.js (LIS辞書向け) | D3.js (大規模グラフ向け) |
|---|---|---|
| ノード数上限 | ~150 | 500+ (canvas併用でさらに) |
| エッジ数 | ~500まで実用的 | 5,000+でも動作 |
| カスタマイズ性 | 設定値のみ | CSS/SVG完全制御 |
| エッジ種別の色分け | 単一色 | 種別ごとに色＋透過度 |

D3.js版の実装詳細は `dictionary-knowledge-graph-rag` スキルの `references/interactive-graph-visualization.md` を参照。

**Discord 配信パターン**: スクリーンショット（`MEDIA:`）＋HTML ファイルの絶対パスを案内

### Mode 7: 統一 `rag` コマンド（IEKOとのクロス検索）

`~/rag/query.py` に設置された統一ラッパー。LIS辞書とIEKO百科事典（ISKO Cyclopedia）の両方を1つのCLIで検索できる。`rag` コマンドとして利用可能（`~/.local/bin/` にインストール済み）。

**アーキテクチャ**: subprocess で各 corpus のネイティブ query.py を呼ぶ軽量ラッパー。依存関係の衝突なし。各 corpus の独立した更新に追従する。

```bash
rag "RDA"                              # LIS辞書（default）
rag -c ieko "faceted classification"   # IEKO百科事典
rag -c both "FRBR"                     # 両方同時検索
rag "RDA" --depth 2                    # LIS＋グラフ展開
rag -c ieko "faceted classification" --depth 2  # IEKOグラフ横断
rag "RDA" -c lis --exact               # LIS完全一致
rag "RDA" -c lis --llm                 # LIS + Plamo-2生成
rag -c ieko "information" --graph      # IEKO単体グラフ関係
rag --stats                            # LIS統計
rag --stats -c ieko                    # IEKO統計
```

| フラグ | 対象 | 機能 |
|--------|------|------|
| `-c lis\|ieko\|both` | 共通 | 検索対象選択（default: lis） |
| `--depth N` | 共通 | グラフ展開hop数 |
| `-n N` | 共通 | 表示件数 |
| `-e`/`--exact` | LIS | 完全一致 |
| `-l`/`--llm` | LIS | Plamo-2回答生成 |
| `-r`/`--raw` | LIS | JSON生出力 |
| `--graph [href]` | IEKO | エントリのグラフ関係 |
| `--stats` | 共通 | 統計表示 |
| `-v` | IEKO | 詳細表示 |

内部的には各 corpus の Python venv で query.py を subprocess 実行するため、これまでと同様の依存関係・モデルキャッシュで動作する。初回の sentence-transformers モデルロードが必要な点は各 corpus ごとに独立。

## 重要な注意点

### 初回起動のレイテンシ

- sentence-transformers モデル (`intfloat/multilingual-e5-small`) のロードに ~2秒
- embedding 生成（全件）に ~1分
- **2回目以降はモデルがキャッシュされるため速い**（~2秒）
- 同一セッション内で複数回検索する場合、モデルはメモリに残る
- 初回起動時は `Warning: You are sending unauthenticated requests to the HF Hub.` が出るが無害（HF_TOKEN 未設定でも動作する）

### トークナイザ

- MeCab がインストールされていない環境では char unigram + 英単語分割の fallback トークナイザを使用
- 検索品質への影響は軽微（BM25 は辞書説明文に対して十分に機能する）
- MeCab を入れる場合は `sudo apt install mecab mecab-ipadic-utf8 && pip install mecab-python3`

### Plamo-2 (--llm) の制約

- boogie:3838 の Ollama 経由。boogie が落ちていると使えない
- cold load ~90秒
- 応答が対訳形式で返ることがある（extract_japanese で処理済み）
- 3000字を超えるコンテキストは送れない（truncate 済み）

### グラフの限界

- 未解決リンク: 91件（辞書内に該当語がない参照先）
- 参照項目リンクは「説明文の中からパース」しているため、すべての関連語をカバーしているわけではない
- グラフ展開は最初の結果のみを起点とする（複数起点は未サポート）

### エラーハンドリング

- `query.py` がエラー終了した場合、端末から直接叩いて動作確認する
- FAISS/B25 索引が存在しない場合は `~/ziten/venv/bin/python ~/ziten/build.py` で再構築

## 辞書データの出典

- 元データ: `tosyokan_dictionary.csv`（図書館情報学用語辞典）
- 各エントリに URL フィールドあり（kotobank.jp へのリンク）
- 約71%のエントリに「参照項目」あり
