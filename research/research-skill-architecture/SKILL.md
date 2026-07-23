---
name: research-skill-architecture
description: "Hermes上のLIS研究スキル群の設計原則・アーキテクチャパターン・命名規約。新規スキル作成時に参照する。"
category: research
trigger: |
  新しいresearchスキルを作成する・既存スキルを再編する。
  ユーザーが「research skillsの設計」「スキルアーキテクチャ」について議論したい。
  ARC-* スキル群の構成や責務分担について確認したい。
---

# Research Skill Architecture

## 基本設計原則

1. **Router + support-file vendoring** — アクティブなroot Routerは1つだけにする。実際のworkflow仕様は`references/`配下（必要ならvendorした`WORKFLOW.md`）に置き、個別に自動登録されるskillへ分解しない。Routerは必要なsupport fileを明示的に読む。

2. **Routerは薄く、契約は外出しする** — Routerにはトリガー、核となる判断基準、routing、不可侵ルールだけを置く。状態遷移、schema、API、失敗パス、詳細手順は`references/`、`templates/`、`scripts/`へ置く。長大化したRouterは、機能追加の根拠ではなくrefactor signalとして扱う。

3. **人間との共創（collaborator）が中心** — 自動化の最大化ではなく、RQ判断・文献選別・方針決定は人間が主導。エージェントは伴走し提案する。`literature-human-in-loop-kanban` の考え方を継承。

4. **フェーズ分離でルーティング可能に** — 責務ごとに独立したworkflowを持ち、Routerがユーザー発話から適切なworkflowを選択できるようにする。「続きから」再開が容易になる。

## ARCの現行契約

`academic-research-collaborator` がARC runtimeの正本である。本skillは、そのRouterを再定義せず、配置・統合・設計上の共通原則を扱う。

```text
academic-research-collaborator（唯一のRouter）
  ├─ research-design   RQ策定・研究内容設計
  ├─ search-plan       探索方針・経路選定
  ├─ curate            書誌収集・候補整理・取得queue
  └─ reflection        証拠範囲を分けた分析・研究計画還元

curate と reflection の間に、人間による Acquisition Gate を置く。
```

この4名称はRouterの機能ラベルであり、個別の自動登録skillではない。各workflowの詳細は`references/`内のsupport fileへ置き、Routerが必要な時点で明示的に読む。

過去の5段階案（`design → strategy → search → select → synthesize`）は設計史であり、現行実装の命名・遷移として再利用しない。再導入にはRouter、schema、artifact、migrationを含む明示的な設計変更が必要である。

## 研究ループの構造

```text
研究設計
  → 承認済み探索計画
  → boundedな書誌収集・候補整理
  → 人間による本文取得・選別
  → evidence scopeを明示したreflection
  → 人間が継続・分岐・拡張・取得・停止を決定
  ↺ 次の設計／計画へ還元
```

研究上のphase・判断・証拠範囲はversioned manifestとartifactに、待機・割当・retryはKanbanに置く。Kanban taskの完了だけで研究phaseを進めず、reconciliationでartifactとmanifest revisionを検証する。

現行契約、設計史との境界、変更時のチェックは [`references/arc-runtime-boundary.md`](references/arc-runtime-boundary.md) を参照する。

## 実装・変更の順序

1. `academic-research-collaborator` を現行runtime契約の唯一の正本として確認し、旧工程図との競合を解消する。
2. canonical source（profile-localかexternal Git管理treeか）を一つに決め、同名skillの二重配置を解消する。
3. workflow support file、template、schema、state controllerの入出力契約を先に作る。
4. path containment、phase transition、evidence scope、atomic write、recoveryをテスト駆動で実装する。
5. bounded delegation、Kanbanのhuman gate、provider adapterをそれぞれの契約に沿って結合する。
6. 既存研究にはread-only shadow modeで適合を確認してからboard bindingやmigrationを行う。
7. skill bundle、controller、Kanban durability、実モデルのbehavioral evaluationを通過してから実行可能と報告する。

## 既存スキルとの連携方針

| 既存スキル | ARCとの関係 |
|-----------|------------|
| literature-agent-epistemics | `reflection`の探索判断・証拠区分・反証・停止理由を補助するreference |
| literature-human-in-loop-kanban | Acquisition Gateとbounded episodeのKanbanパターン。単純に吸収せず、専門skillとして連携する |
| lis-theory-comparison | `research-design`で理論比較の問い・比較軸を作る際のreference |
| kanban-literature-search | `curate`の収集・queue設計のreference |
| author-level-literature-completeness | `search-plan`/`curate`のcoverage確認に利用 |
| lis-journal | データベース・雑誌・収集経路の選定reference |
| research-draft-translation | 執筆フェーズで利用する独立skill |
| research-project-status-audit | manifest/artifactを読む独立の状態監査skill |
| arg-analysis | `reflection`から呼べる論証分析ツール |
| llm-wiki | 人間承認済みの知識をpromoteする独立KB skill |
| arxiv | 必要時に使う低優先度の検索source |

既存skillを統合・削除する前に、Routerからの参照、利用者の既存workflow、artifact contractを確認する。類似するskillを無条件にmergeしない。

## 設計上の注意

- RouterのSKILL.mdはルーティングテーブル＋共通コンテキスト注入のみ。判断ロジックを複雑にしすぎない。
- `WORKFLOW.md` は元のスキルの内容を簡潔に再構成する。コピペではなく、LIS研究向けにパーソナライズする。
- 執筆ワークフロー（ARC-write等）は後日追加。現在の主眼は計画＋探索ループ。
- APIキー・BWS認証はRouterの共通コンテキスト注入で一元管理する。
