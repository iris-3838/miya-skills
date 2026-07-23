# ARC Search Plan

確認済みRQをもとに探索方針・経路・bounded episodeを設計する。Devil's Advocateチェックポイントを含む。

## 事前条件

- `state.current_phase` が `design` で、HG①が承認済み
- `artifacts/design/rq-brief.md` が存在
- `state.rq.core` がmanifestに記録済み

## 入力

- `artifacts/design/rq-brief.md`（RQ、前提、除外範囲、DA指摘）
- `arc-context.md` のAPI adapter設定、対象分野・DB
- llm-kbの既存知識（既知文献・概念マップ）

## 手順

### 1. Question Slice への分解

RQを探索可能な単位に分割する。

```yaml
question_slices:
  - id: "slice-01"
    focus: "中核概念の定義と用法"
    search_purpose: "Bates, Hjørland, Floridiの情報概念の定義を収集"
  - id: "slice-02"
    focus: "理論間の直接応答・批判"
    search_purpose: "三者間の明示的な批判・応答を特定"
```

### 2. Route Spec の設計

各sliceに対して探索経路を選択する。経路分類は `references/arc-architecture.md` のA系列（語彙）・B系列（関係性）を参照。

```yaml
route_spec:
  slice_id: "slice-01"
  routes:
    - type: "A1"                    # 中核概念語
      queries: ["information concept Bates"]
      sources: [crossref, openalex]
    - type: "B1"                    # 前方引用
      seed_dois: ["10.xxxx/xxxxx"]
      sources: [semanticscholar]
```

### 3. Known Items の明示

既知の重要文献を列挙し、新規探索との重複・欠落を後で評価できるようにする。

```yaml
known_items:
  - title: "Information and Knowledge: An Evolutionary Framework"
    author: "Bates, M.J."
    year: 2005
    role: "primary_text"
```

### 4. Coverage Claim

何をカバーし、何をカバーしないかを明示する。

```yaml
coverage:
  languages: [en, ja]
  years: "1990-2025"
  source_types: [journal_article, monograph, book_chapter]
  intentional_gaps:
    - "会議録（LIS理論では重要性が低いため）"
    - "学部生向け教科書"
```

### 5. Episode Design

最初のbounded episodeを設計する。episodeは1回の探索単位で、上限候補数と停止条件を決める。

```yaml
first_episode:
  question_slice: "slice-01"
  routes: [A1, A2, B1]
  max_candidates: 15
  stop_condition: "15件到達 or 経路枯渇"
  next_human_decision: "候補一覧から採用・除外・要入手を判断"
```

### 6. Devil's Advocate（必須、plan末尾）

探索計画に対して反証チェックを行う。

- この経路選択では捉えられない文献タイプは何か
- 学派・言語・地域バイアスはないか
- 既知文献に依存しすぎて新規発見の余地が狭まっていないか
- RQを反証する文献を積極的に探す経路が含まれているか

### 7. Human Gate ②

計画全体 + DA指摘を提示し、ユーザーに以下を確認する。

- question sliceの分割は適切か
- 経路選択に偏りはないか
- coverage claimは妥当か
- 最初のepisodeの規模・停止条件は適切か

ユーザーが `approve` するまでcurateへ進まない。

## 出力

| artifact | 形式 | 説明 |
|---|---|---|
| `artifacts/plan/search-strategy.yaml` | YAML | slices、routes、known items、coverage、first episode |
| `research-manifest.yaml` 更新 | YAML | `state.current_phase: plan`、`state.route_ledger` 初期化 |

## Evidence Scope 制約

- 既知文献の列挙は人間の知識に基づく
- 探索クエリの設計は行うが、実際のAPI呼び出しはcurateで行う
- DAでの反証経路提案は仮説的なものに留める

## Failure Paths

| 状況 | 対応 |
|---|---|
| sliceが広すぎてepisodeに収まらない | さらに分割する |
| 適切なseed DOIが見つからない | 語彙探索のみで開始し、発見後に引用探索を追加 |
| DAが深刻なcoverage gapを指摘 | 経路または範囲を修正して再提案 |
| 全sourceが`unavailable`の可能性 | coverage claimで明示し、人間の判断を仰ぐ |
