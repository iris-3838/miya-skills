# ARC Reflection

evidence scopeを区別した分析・経路評価・研究計画への還元を行う。

## 事前条件

- `state.current_phase` が `curate`（取得待ちなし）または `acquisition_pending`（全取得待ち解決済み）
- HG③ が承認済み。acquisition manifest が `resolved`
- candidate ledger、acquisition manifest、source run manifest が存在

## 入力

- `artifacts/curate/candidate-ledger.jsonl`
- `artifacts/curate/acquisition-manifest.yaml`
- `artifacts/curate/source-runs/*.json`
- `artifacts/curate/prisma-flow.md`
- `artifacts/design/rq-brief.md`
- `artifacts/plan/search-strategy.yaml`

## 手順

### 1. Evidence-Scoped Analysis

候補を evidence scope 別に分析する。

#### fulltext_ready 文献

以下の構造で分析する。

```yaml
- candidate_id: "<uuid>"
  bibliography:        # 完全な書誌
  source_type:         # journal_article | monograph | book_chapter | dissertation | report
  theoretical_role:    # primary_text | interpretation | critique | application
  main_claim:          # 著者の中心的主張
  concepts:            # 使用される中核概念と定義
  argument_structure:  # 論証の構造
  evidence_basis:      # 論証の基盤
  relation_to_rq:      # RQへの直接的関連
  relation_to_other:   # 他の候補文献との関係
  limitations:         # 著者自身の限定・または分析上の制約
  new_search_clues:    # 発見された新しい探索手がかり
  confidence: "high"   # fulltextに基づくためhigh
```

#### abstract_only 文献

抄録で確認できる範囲に限定する。

```yaml
- candidate_id: "<uuid>"
  bibliography:
  source_type:
  abstract_summary:    # 抄録の要約（著者の主張として）
  relation_to_rq:      # 抄録から判断できる範囲で
  new_search_clues:    # 抄録から得られる手がかり
  access_limitation:   # 本文未取得のため未確認の項目を明示
  confidence: "medium" | "low"
```

#### metadata_only / unavailable 文献

内容分析は行わない。

```yaml
- candidate_id: "<uuid>"
  bibliography:
  evidence_scope: "metadata_only" | "unavailable"
  reason_unavailable:  # 取得不能理由
  potential_relevance: # 書誌から推測される潜在的関連性（推測であることを明記）
  confidence: "low"
```

### 2. Route Effectiveness 評価

source run manifest と candidate ledger から、各経路の効果を評価する。

```yaml
route_effectiveness:
  route_id: "A1-crossref"
  hits: 15
  adopted: 3
  noise_ratio: 0.8
  novel_concepts: 2
  novel_relations: 1
  assessment: "continue" | "depleted" | "critical_new" | "refine"
```

### 3. Coverage & Saturation Diagnosis

以下の診断指標を計算し、自動停止はせず人間に提示する。

```yaml
saturation_indicators:
  vocabulary_novelty:       # 新中核語の出現状況
  conceptual_novelty:       # 新概念の出現状況
  controversy_coverage:     # 論争関係の探査深度
  route_coverage:           # 経路別の採用率・枯渇状況
  known_item_recall:        # 既知文献の再発見率
  language_and_genre_gaps:  # 未カバーの言語・資料種別
  provider_failures:        # APIエラーの影響
  access_limited_candidates: # 未取得文献の割合と重要度
```

### 4. Reflection Report

以下の要素を含む `artifacts/reflection/reflection-report.md` を作成する。

```markdown
## 今回分かったこと
## まだ不明なこと
## 見つかった新しい語・著者・引用経路
## 現在の盲点
## 本文入手が必要な文献
## 経路効果サマリー
## 推奨する次の経路
```

### 5. Human Gate ④

reflection report + saturation indicatorsを提示し、ユーザーに以下を確認する。

```text
継続 (continue)    — 同じRQで次のepisodeへ
修正 (revise)      — RQ・計画を修正して再探索
拡張 (expand)      — 新しい経路・sliceを追加
取得 (acquire)     — 未取得文献の入手を優先
停止 (stop)        — 探索を終了し、llm-kbへのpromoteを検討
```

ユーザーが選択するまで次の探索を開始しない。ユーザーの判断は manifest の decision event として記録する。

## 出力

| artifact | 形式 | 説明 |
|---|---|---|
| `artifacts/reflection/evidence-analysis.jsonl` | JSONL | scope別の分析結果 |
| `artifacts/reflection/route-effectiveness.yaml` | YAML | 経路効果評価 |
| `artifacts/reflection/saturation-diagnosis.yaml` | YAML | 飽和診断指標 |
| `artifacts/reflection/reflection-report.md` | Markdown | 総合報告 |
| `research-manifest.yaml` 更新 | YAML | `state.current_phase: reflection`、decision event を追記 |

## Evidence Scope 制約（最重要）

- `fulltext_ready` 文献のみ、主張・論証・方法・概念の確定的分析が可能
- `abstract_only` 文献は、抄録に明示された範囲内でのみ報告する。本文の論証・方法・概念使用を断定しない
- `metadata_only` / `unavailable` 文献の内容を断定しない。書誌とアクセス不能理由だけを記録する
- confidence は evidence scope に応じて付与し、`abstract_only` で `high` を付けない

## Failure Paths

| 状況 | 対応 |
|---|---|
| 全候補が abstract_only で内容分析不能 | その旨を明記し、acquisition priorityを人間に提案 |
| 経路が枯渇し新規発見がない | 別経路・別sliceへの拡張を提案 |
| DA的な反証文献が見つかっていない | 反証経路（A5, B5, B6）の未着手を指摘 |
| 採用候補が少なすぎる | episode設計の見直し。planへ差し戻し |
| 候補が多すぎて分析しきれない | episode分割またはfocus narrowedを提案 |
| llm-kbへのpromote判断 | agentが自動promoteしない。人間が明示的に指示 |
