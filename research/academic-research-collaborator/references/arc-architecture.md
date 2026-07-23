# ARC Architecture — 詳細設計

2026-07-22 要件定義セッションで決定。Router・テンプレート・共通コンテキストは実装済み。workflow referenceは作成中。
state controller、validatorの純粋Python coreは実装済み。Hermes plugin guard、Kanban reconcile、provider adapterは未実装。詳細なruntime契約は `runtime-contract-and-validation.md` を参照。

## 決定事項

### 4ワークフロー構成

| 機能 | 責務 | Socratic | DA | WHW | PRISMA |
|---|---|---|---|---|---|
| research-design | RQ策定・研究内容設計 | ✅入口 | ✅末尾 | — | — |
| search-plan | 探索方針・経路選定 | — | ✅末尾 | — | — |
| curate | 書誌収集・候補整理・取得queue | — | — | ✅quick時 | ✅ |
| reflection | evidence scopeを分けた分析・研究計画還元 | — | — | — | — |

curate と reflection の間に Acquisition Gate（人間による本文取得）を置く。

### モード別実行

| モード | design | plan | curate | reflection | DA回数 | PRISMA深度 |
|---|---|---|---|---|---|---|
| full | ✅通常 | ✅通常 | ✅全文 | ✅通常 | 2 | 全文 |
| quick-scan | ✅lite | ✅lite | ✅lite | ✅lite | 0 | 簡易 |
| lit-review | ✅通常 | ✅通常 | ✅全文 | ✅通常 | 1 | 全文 |

lit-reviewは既存の確認済みRQがない限りdesignを飛ばさない。

### 3層状態管理

| 層 | ファイル | 内容 | 更新頻度 |
|---|---|---|---|---|
| L1 準不変 | `arc-context.md` | llm-kbパス、対象理論家、引用ルール | 研究枠組変更時のみ |
| L2 状態遷移 | `research-manifest.yaml` | 現在phase、経路履歴、未決decision | phase遷移ごと |
| L3 成果物 | `artifacts/` | 各phaseの出力（次phaseの入力） | phase完了時 |

manifestの正本は `templates/research-manifest.yaml`。実際の状態フィールドと遷移契約は `runtime-contract-and-validation.md` を優先する。

## 探索経路分類

**A. クエリ探索（語彙ベース）**
- A1: 中核概念語
- A2: 翻訳語・異表記
- A3: 学派キーワード
- A4: 隣接概念
- A5: 反対・批判概念
- A6: 時代・地域区切り

**B. 関係性探索（ネットワークベース）**
- B1: 前方引用
- B2: 後方引用
- B3: 共引用
- B4: 著者全著作
- B5: 直接応答（前方引用＋本文確認）
- B6: 第三者批評
- B7: 雑誌特集・資料種別

語彙探索と関係性探索を区別して記録し、それぞれのcoverage gapを明示する。

## ARSマッピング

| ARS要素 | ARCでの位置 |
|---|---|
| deep-research Phase 1 (Scoping) | research-design + search-plan |
| deep-research Phase 2 (Investigation) | curate |
| deep-research Phase 3 (Analysis) | reflection |
| deep-research Phase 4-6 (Composition/Review/Revision) | 後回し |
| socratic_mentor_agent | research-design 入口 |
| devils_advocate_agent | design末尾 + plan末尾 |
| bibliography_agent | curate |
| source_verification_agent | curate 内部 |
| synthesis_agent | reflection |
| PRISMAプロトコル | curate 出力フォーマット |
| IRON RULE / 失敗パス | 全ARC共通（`references/ars-shared/`） |

### 採用したARS要素

1. Socraticモード
2. Devil's Advocate（design + plan の2箇所）
3. WHWスキャン（quick-scan時）
4. ソース品質分類（Tier 1-5 → ARCでは出版形態の固定序列ではなく、`source_type`、`theoretical_role`、`directness_to_rq`を分離）
5. PRISMAフローチャート（full:全文 / quick:簡易）
6. IRON RULE + Anti-Patterns
7. 失敗パス（12シナリオ＋回復戦略）
8. モード選択（full / quick-scan / lit-review）

### 不採用要素

- meta_analysis_agent → 定量的。理論比較に不要
- risk_of_bias_agent → RCT/ROBINS-I。LIS理論に不要
- report_compiler_agent → 執筆フェーズ後回し
- editor_in_chief_agent → 査読フェーズ後回し
- ethics_review_agent → 執筆フェーズ後回し

## Paywall対策

LIS分野は90%以上がペイウォール。機械的取得可能性が極めて低い。
→ 書誌収集（curate）と人力取得（Acquisition Gate）を第1級の分離概念として設計。
→ `templates/acquisition_manifest.yaml` が境界artifact。
→ `fulltext_ready` / `abstract_only` / `acquisition_required` / `unavailable` をreflectionでconfidence付きで区別して扱う。

## ヒューマンゲート一覧

| # | 位置 | 機構 | 判断内容 |
|---|---|---|---|
| HG① | design完了 | `clarify()` またはKanban task | RQ確定/修正 |
| HG② | plan完了 | `clarify()` またはKanban task | 探索計画承認/修正 |
| HG③ | curate完了 | Kanban `needs_input` | 候補から採用/除外/要入手 |
| ACQ | curate→reflection間 | Kanban `needs_input` + acquisition manifest | 人間が本文入手→manifest更新 |
| HG④ | reflection完了 | Kanban task | continue/revise/expand/acquire/stop |

長期gate（ACQ、本文待ち、数日単位の判断）はKanban `block(kind="needs_input")` を使う。`clarify()` は同一対話内の即時確認のみ。

## 飽和診断指標（自動停止規則ではない）

| 指標 | 説明 | 人間判断への提示 |
|---|---|---|
| vocabulary_novelty | 新中核語の出現頻度 | 経路ごとに提示 |
| conceptual_novelty | 新概念の出現頻度 | 経路ごとに提示 |
| controversy_coverage | 論争関係の探査深度 | 未探査routeとともに提示 |
| route_coverage | 経路別の採用率 | 枯渇route・未着手routeを明示 |
| known_item_recall | 既知文献の再発見率 | 重複と新規を分けて提示 |
| language_and_genre_gaps | カバーしていない言語・資料種別 | 意図的除外と未探査を区別 |
| provider_failures | APIエラー・レート制限の影響 | coverage欠損として提示 |
| access_limited_candidates | 未取得文献の割合と重要度 | acquisition priorityとして提示 |

固定件数・固定新規率による自動停止は行わない。指標を人間に提示し、継続・分岐・拡張・取得・停止を決める。

## 既存スキルとの関係

- `literature-human-in-loop-kanban` — エピソード制のhuman-in-loop。curate + reflectionのgateパターンとして参照
- `literature-agent-epistemics` — 探索認識論。reflectionの判断基準として `references/` へ取り込み候補
- `kanban-literature-search` — kanbanベースの文献収集DAG。miya-skills側のpolicy-gated loop版と統合検討中

これらの統合・廃止判断はARC実装後に再検討。

## 実装優先順位

1. ~~Router (SKILL.md) + `arc-context.md` + template~~ ✅
2. workflow reference（`references/workflows/` の4文書）← **現在**
3. `references/ars-shared/`（IRON RULE、失敗パス）
4. `references/runtime-contract-and-validation.md`（詳細契約）
5. state controller + validator（`arc-core`）
6. plugin guard（`pre_tool_call`）
7. adapter配備 + provider fixture
8. Kanban durability test
9. 既存研究へのread-only shadow pilot
