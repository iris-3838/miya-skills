# ARC Curate

確認済み探索計画に基づき、boundedな書誌収集・候補整理・取得queue作成を行う。

## 事前条件

- `state.current_phase` が `plan` で、HG②が承認済み
- `artifacts/plan/search-strategy.yaml` が存在
- API adapterが利用可能であること（`unavailable` の場合は最初に報告）

## 入力

- `artifacts/plan/search-strategy.yaml`（first episodeのroute spec）
- `arc-context.md` のAPI adapter設定、Zotero collection prefix
- BWS経由のAPI credential（環境変数のみ）

## 手順

### 1. Provider Run

episodeの各routeについて、指定されたsourceにクエリを発行する。

```yaml
# source_run manifest（sourceごとに生成）
run_id: "<uuid>"
source: "crossref"
query: "information concept Bates"
provider_status: "success" | "zero_hits" | "unavailable" | "transient_error" | "rate_limited"
num_records: 15
error_detail: null  # エラー時のみ
retry_count: 0
coverage_effect: "full" | "partial" | "missing"
```

並列実行は `delegate_task` でsourceごとに分ける。episode全体のprovider status summaryを必ず人間に提示する。

### 2. Candidate Ledger

全source runの結果を正規化し、候補ledgerを作成する。

```yaml
# candidate（候補ごと）
candidate_id: "<uuid>"
title: "..."
authors: ["..."]
year: 2020
doi: "10.xxxx/xxxxx"
source: "crossref"
evidence_scope: "metadata_only" | "abstract_only" | "fulltext_ready"
relevance: "HIGH" | "MEDIUM" | "LOW"
relevance_reason: "..."
duplicate_of: null  # 重複候補のID
excluded: false
exclusion_reason: null
```

fulltext_ready は人間が本文を取得・開封確認した場合のみ。metadata_only と abstract_only を混同しない。

### 3. Acquisition Queue

evidence_scope が `metadata_only` または `abstract_only` で、かつ relevance が `HIGH` または `MEDIUM` の候補について、acquisition queueを作成する。

```yaml
# acquisition_manifest.yaml エントリ（正本スキーマ）
- candidate_id: "<uuid>"
  doi: "10.xxxx/xxxxx"
  title: "..."
  current_scope: "abstract_only"
  target_scope: "fulltext"
  acquisition_status: "not_attempted"
  access:
    route: "OA" | "DOI resolver" | "機関リポジトリ" | "ILL" | "著者プレプリント"
    note: ""
  zotero_key: null
```

### 4. PRISMA Flow（full / lit-review モード）

収集・選別・除外の流れを記録する。

```markdown
## PRISMA Flow

- 検索式: ...
- DB: ...
- 検索日: YYYY-MM-DD
- 総ヒット数: N
- 重複除去後: N
- 抄録スクリーニング後: N
- 本文確認対象: N
- 本文取得済み: N
- 採用候補: N
```

quick-scanモードでは簡易版（件数のみ）でよい。

### 5. Human Gate ③

候補ledger + acquisition queue + provider status summaryを提示し、ユーザーに以下を確認する。

- 採用する候補（analysis対象）
- 除外する候補（理由付き）
- 本文取得が必要な候補（acquisition queueへ）
- 取得不能で残す候補（`unavailable`、理由付き）

ユーザーが判断するまでreflectionへ進まない。取得待ちがある場合は `acquisition_pending` に遷移する。

## 出力

| artifact | 形式 | 説明 |
|---|---|---|
| `artifacts/curate/candidate-ledger.jsonl` | JSONL | 正規化候補一覧 |
| `artifacts/curate/acquisition-manifest.yaml` | YAML | 取得queue（正本スキーマ） |
| `artifacts/curate/source-runs/*.json` | JSON | source run manifest群 |
| `artifacts/curate/prisma-flow.md` | Markdown | PRISMAフローチャート |
| `research-manifest.yaml` 更新 | YAML | `state.current_phase: curate` または `acquisition_pending` |

## Evidence Scope 制約

- metadata_only / abstract_only の候補は、書誌情報と抄録内容の範囲内でのみ記述する
- 抄録から本文の論証を推測して candidate ledger の `relevance_reason` に書かない
- `fulltext_ready` でない文献を、内容分析の対象候補として確定しない

## Provider Failure Handling

| provider_status | 処理 |
|---|---|
| `success` + `zero_hits` | coverage情報として記録。拡大・別経路の要否を人間に確認 |
| `unavailable` | credential不足なら人間に通知。API到達不能なら別sourceで代替可能か確認 |
| `transient_error` | 最大2回retry。解決しなければ当該sourceの coverage_effect を `missing` として記録 |
| `rate_limited` | 遅延retry（最低30秒）。予算・割当の問題なら人間に通知 |

いずれの場合も、失敗を `zero_hits` に偽装しない。

## Failure Paths

| 状況 | 対応 |
|---|---|
| 全sourceが `unavailable` | 候補収集不可として人間に報告。手動検索・別DBの提案 |
| 全候補が `LOW` relevance | episode設計の見直しを提案。planへ差し戻し |
| 全候補がpaywallでOAアクセス不可 | acquisition queueに全件登録。acquisition_pendingへ遷移 |
| 重複が極端に多い | 正規化・dedupロジックの確認。既知文献との重複率を報告 |
| 候補数が上限を大幅に超過 | 抄録スクリーニングで絞り込み。またはepisode分割を提案 |
