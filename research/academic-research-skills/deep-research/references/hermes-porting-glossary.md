# Hermes Porting Glossary

本ドキュメントは、deep-researchスキル（元々Claude Code用に設計されたARSの一部）をHermes Agent上で使用する際の注意点・代替手段をまとめる。

## 1. Claude Code依存の全体像

ARS deep-researchはClaude Codeの以下の機能に依存している。各項目のHermes代替手段を示す。

| # | Claude Code機能 | 依存度 | Hermesでの状態 | 代替手段 |
|---|----------------|:----:|:-------------:|---------|
| 1 | `.claude/CLAUDE.md` ルーティング | HIGH | ❌ 未対応 | `AGENTS.md` + `SKILL.md` + `MODE_REGISTRY.md` で代替済み |
| 2 | `/ars-<mode>` スラッシュコマンド | HIGH | ❌ 未対応 | 自然言語ルーティング（clarifyツール） |
| 3 | `/ars-mark-read` スラッシュコマンド | HIGH | ❌ 未対応 | ユーザープロンプトで代用 |
| 4 | PreToolUse フック | HIGH | ❌ 未対応 | プロンプトレベルの指示のみ（Anthropic API固有） |
| 5 | Mode B（クロスセッション再開） | HIGH | ❌ 未対応 | Kanbanタスクボードで代替（後述） |
| 6 | Codex 監査サイクル参照 | MED | 🟡 不要 | 実行に影響なし。単なる開発サイクルへの言及 |
| 7 | Pythonバリデータースクリプト | MED | 🟡 未移植 | ファイル自体が存在しない（元ARSでも未実装の可能性） |
| 8 | Bucket A/B フェーズ分離 | MED | ⚠️ 注意 | プロンプトレベルのみ。ファイルアクセス制御は未実装 |
| 9 | `docs/design/` 設計文書 | LOW | 📄 不存在 | 実行不要。理解のための参考資料 |
| 10 | 環境変数ゲート | LOW | ✅ 動作 | `ARS_PASSPORT_RESET`, `ARS_SOCRATIC_READING_PROBE` 等そのまま使える |

## 2. Mode A は完全動作

**Mode A（オーケストレータ駆動、単一セッション）はHermes上で問題なく動作する。**

→ 単一の会話内で全6フェーズを実行する従来の使い方には制限がない。
→ trigger keywords（"research [topic]"、"deep research"等）で起動可能。
→ Socratic modeも含む全7モードが利用可能。

## 3. KanbanによるMode B代替

Claude CodeのMode B（複数セッションにまたがる研究パイプライン）は、Hermes Kanbanで代替可能。

**基本戦略：** ARSの各フェーズをkanbanタスクに分解し、依存関係で連結する。Gatewayが自動dispatchする。

```
Phase 1: Scoping ────────────────────────────┐
  [RQ + Methodology Design]                   │
        ↓                                     │
Phase 2: Investigation ───────────────────────┤
  [Literature Search + Verification]          │
        ↓                                     │
Phase 3: Analysis ────────────────────────────┤
  [Synthesis + Gap + DA]                      │
        ↓                                     │
Phase 4: Composition ─────────────────────────┤
  [APA 7.0 Report Draft]                      │
        ↓                                     │
Phase 5: Review (3並列) ─────────────────────┤
  [Editor] [Ethics] [Devil's Advocate]        │
        ↓ (3完了)                              │
Phase 6: Revision ────────────────────────────┘
  [Final Report]
```

**使用するkanbanコマンド：**
- `hermes kanban boards create <slug>` — プロジェクトボード作成
- `hermes kanban create --board <slug> --title <title>` — タスク作成
- `hermes kanban link <parent> <child>` — 依存関係設定
- `hermes kanban claim <id>` — ワーカーがタスクを取得（ワークスペースパス返却）
- `hermes kanban context <id>` — 親タスクの出力を確認
- `hermes kanban complete <id>` — タスク完了
- `hermes kanban list` / `show` — 進捗確認

**設定要件：**
- Gateway auto-dispatch 有効化（`config.yaml` → `kanban.dispatch_in_gateway: true`）
- 各ARSフェーズ用のワーカープロファイル設定

詳細は `.hermes/plans/2026-06-05_101500-ars-kanban-pipeline.md` を参照。

### 3.1 実装時の重要パターン：Kanbanは耐久オーケストレーション、delegate_taskはsub-agent相当

Claude Code sub-agentの本質は「独立コンテキストを持つ関数呼び出し」。Hermesでは `delegate_task` がこれに相当する。一方、`delegate_task` は親ターン内で同期実行されるため、長期・跨セッションのARS Mode B全体を保持する器にはしない。

**推奨マッピング：**

| 役割 | Hermesで使うもの | 理由 |
|------|------------------|------|
| 6フェーズDAG、依存関係、再開境界 | Hermes Kanban | タスク状態・依存関係・workspaceを耐久化できる |
| 各フェーズ内の専門agent実行 | `delegate_task` | fresh contextで研究質問・文献探索・批判レビュー等を分離できる |
| フェーズ成果物の引き継ぎ | Kanban run metadata + workspace file | 子フェーズが親出力を再読込できる |
| 短期のTDD/検証 | dry-run / fake delegator | 本物の研究生成前にDAG・出力契約・失敗時blockを検証できる |

**成果物保持の落とし穴：** `scratch` workspace は task complete 時にGCされる。ARS本番のように `phase_result.json` や中間文書を後続フェーズが読む場合は、必ず `--workspace dir:/abs/path` または `worktree` を使う。scratchはdry-runの一時確認に限定する。

**phase workerの最小契約：**
1. `kanban claim/context` で task body と親出力を読む。
2. phase番号・mode・topic・上流成果物を正規化して専門agentへ渡す。
3. dry-runでは fake delegator を使い、研究生成なしで契約だけ検証する。
4. 成功時は `phase_result.json` を persistent workspace に書き、同じ要約を run metadata に保存して `kanban complete`。
5. 失敗時は例外を握りつぶさず、再開可能な理由を付けて `kanban block`。

## 4. miya-skills統合ポイント

deep-researchは以下のmiya-skillsと連携可能：

| miya-skillsスキル | 連携箇所 | 状態 |
|-----------------|---------|:---:|
| openalex-literature-survey | bibliography_agent（文献検索） | ✅ 連携可能（OpenAlex API protocol完備） |
| zotero | bibliography_agent, literature_strategist | ✅ 連携可能（SKILL.mdで参照済み） |
| llm-kb-wiki | 全フェーズのoutput保存先 | ❌ 未連携（KBへの自動保存未実装） |
| ziten (RAG) | 文献検索・概念参照 | ❌ 未連携 |
| jstage-jslis-daily-summary | 日本語文献検索 | ❌ 未連携 |

## 5. seimiya研究特化の注意点

| 観点 | 現状 | 対処 |
|------|------|------|
| 情報哲学（Floridi） | ARSにドメイン知識なし | 必要に応じてreferences/に概念マップ追加 |
| 日本語LIS論文 | トリガーに日本語表記のみ | 英語主体。日本語文献はjstage側でカバー |
| PDF翻訳パイプライン | 未対応 | pdf2zh-next → KB保存は独立フロー |
