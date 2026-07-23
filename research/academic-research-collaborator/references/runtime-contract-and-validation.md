# ARC Runtime Contract & Validation

ARC Router が参照する詳細な実行契約。state遷移、証拠範囲、provider handling、path security、Kanban連携、テスト要件を定義する。
Router本文は短く保ち、判断と手順の詳細はこの文書に置く。

## State Machine

### Phase 一覧と遷移

```
[init] → initialized → design → plan → curate → acquisition_pending → reflection → [loop back to design/plan/curate]
                                ↑         ↑            ↑                    │
                                └─────────┴────────────┴────────────────────┘
                                          (HG④: continue/revise)
```

| 遷移元 | 遷移先 | 許可条件 |
|---|---|---|
| — | `initialized` | `project_id`、絶対path、mode を `clarify()` で確認後、`arc_init` が成功 |
| `initialized` | `design` | 初期化manifestのstatus = `initialized` + 初期Human Gate承認 |
| `design` | `plan` | HG① 承認 + `artifacts/design/rq-brief.md` 存在 |
| `plan` | `curate` | HG② 承認 + `artifacts/plan/search-strategy.yaml` 存在 |
| `curate` | `acquisition_pending` | 取得待ち文献あり + acquisition manifest が `pending` |
| `curate` | `reflection` | 取得待ちなし + HG③ 承認 |
| `acquisition_pending` | `reflection` | 全取得待ちが解決 + acquisition manifest が `resolved` |
| `reflection` | `design` / `plan` / `curate` | HG④ `continue`/`revise` + 遷移先の初期artifactが生成済み |

artifact gateに渡す値はproject-relativeなcanonical path（例: `artifacts/design/rq-brief.md`）とする。coreは`./`とWindows separatorを正規化するが、absolute path、prefix/suffix collision、任意の別root pathは受け付けない。実ファイルの存在・内容schema・artifact revisionの検証は、adapter/plugin境界の追加責務である。

### Acquisition entry status

`acquisition_manifest.entries[*].acquisition_status` は次のenumに限定する。

```text
pending | not_attempted | in_progress | acquired | failed | unavailable | not_needed
```

`pending`、`not_attempted`、`in_progress`が一件でも残る場合、`status: resolved`でもreflectionへ進めない。欠落・未知statusはresolvedとして扱わず、遷移を拒否する。`failed`と`unavailable`は取得処理上の終端だが、本文のevidence scopeを`fulltext_ready`へ昇格させない。

### State field semantics

- `state.current_phase` は現在のphaseを表す。初期manifestは `initialized` であり、designを次phaseとして暗黙に示さない。
- `status` は実行状態であり、初期値は `initialized`。phase遷移後は `active`、Human Gate待ちは `paused` とする。
- `revision` はmanifestの楽観的ロック番号。初期値は0で、成功した更新ごとに1だけ増やす。

### 禁止遷移

- `initialized` → `plan`（design未完了）
- `plan` → `reflection`（curate未完了）
- 未承認gateを跨ぐ遷移
- `acquisition_pending` かつ未解決文献がある状態での `reflection`
- manifest revision と Kanban task revision の不一致を無視した遷移

### Evidence Scope

文献の証拠範囲は次の5状態のいずれかで、candidate ledger に必ず記録する。

| 状態 | 意味 | 許容される分析 |
|---|---|---|
| `metadata_only` | 書誌情報のみ | 存在確認、重複検出、引用計数 |
| `abstract_only` | 抄録まで取得 | 抄録に明示された範囲でのみ報告。論証・方法・概念使用の確定的解釈は不可 |
| `fulltext_ready` | 本文取得済み | 主張・根拠・方法・概念・論証の分析が可能 |
| `acquisition_required` | 人手取得待ち | 分析不可。acquisition manifest に記録 |
| `unavailable` | 取得不能（paywall・未公開・消失） | 内容断定不可。存在とアクセス不能理由のみ記録 |

`abstract_only` 文献から `fulltext_ready` 級の主張・論証分析を生成してはならない。
confidence は evidence scope と独立に付与する。

## Provider Contract

### Status 分類

各source runの結果は必ず次のいずれかで記録する。

| provider_status | 意味 | 後続処理 |
|---|---|---|
| `success` | 正常終了 | 結果を候補ledgerへ |
| `zero_hits` | 正常だが0件 | coverage情報として記録 |
| `unavailable` | credential不足・API未到達 | coverage欠損として人間へ報告 |
| `transient_error` | 一時的エラー（5xx, timeout） | 限定的retry後、未解決なら人間へ |
| `rate_limited` | 429等のレート制限 | retry方針を人間に確認 |

`rate_limited` や `unavailable` を `zero_hits` として扱わない。source run manifest に status、error_detail、retry_count、coverage_effect を記録する。

### API Key

- adapterへのAPI key注入はBWS経由の環境変数のみを使う
- `--api-key` CLI引数、manifest、ログ、artifactにkeyを渡さない
- 実行時の `os.environ` から読む。key不在時は `unavailable` として記録

## Path & Security

### Project Root Validation

`arc_init` は少なくとも以下を検査する。

1. 指定pathが絶対パスであること
2. `os.path.realpath()` 解決後も指定root配下であること
3. `..` によるtraversalがないこと
4. symlink escapeがないこと
5. 既存のARCプロジェクト（同名project_id・異なるpath）と衝突しないこと
6. 非ARCの既存ディレクトリを黙って上書きしないこと

### Atomic Write

manifest 書き込みは次の2段階で行う。

```python
tmp_path = f"{manifest_path}.tmp.{uuid4().hex}"
write_yaml(tmp_path, data)
os.replace(tmp_path, manifest_path)  # atomic on POSIX
```

中断時の `.tmp` ファイルは次回起動時に検出・削除する。

### Revision Conflict

manifest 更新時は `revision` をインクリメントし、書き込み前に現在の `revision` が期待値と一致することを確認する。不一致の場合は上書きせず、conflictとして人間に返す。

## Kanban Contract

### Task-Manifest Binding

Kanban taskは次のminimum metadataを持つ。

```yaml
# task metadata
arc_project_id: "<project_id>"
arc_manifest_revision: <N>
arc_phase: "design" | "plan" | "curate" | "reflection"
arc_artifact_uri: "<絶対path>"
```

### Reconcile Protocol

1. Kanban taskが `completed` になった後、`arc_reconcile` を実行する
2. taskの `arc_manifest_revision` と現manifestの `revision` を比較
3. 不一致 → 遷移せず、reconciliation reviewを作成
4. 一致 + artifact存在 + evidence scope検証 → manifestのphaseを遷移

Kanban taskの完了だけで研究phaseを進めない。

### Workspace

- 研究artifactには Kanban の scratch workspace（完了時に消える）を使わない
- `kanban_create` 時は `workspace: dir:<絶対project root>` を明示する
- またはworkspace指定なしで作成し、workerがmanifestからpathを読む

## Test Categories

実装・変更後、以下のカテゴリを通過してから実行可能と報告する。

### Bundle / Static
- 全 linked reference、template、schema が存在すること
- hardcoded path が `$HOME` または相対参照であること
- 同名skillの二重配置がないこと

### Controller Unit
- 初期化、全phase遷移、禁止遷移の拒否
- evidence scope違反の検出
- atomic write後の破損recovery
- revision conflictの検出
- project root containment違反の拒否

### Hermes Integration
- `skill_view(name, file_path=...)` で全referenceが読めること
- `clarify()` timeout後にstateが進まないこと
- plugin `pre_tool_call` が未初期化projectへの書込みをblockすること
- active skillとして発見され、triggerで起動すること

### Provider Fixture
- success、zero_hits、unavailable、rate_limited、transient_error の全statusが正しく分類されること
- credential不在時に `unavailable` になること（例外を投げない）
- 実APIへの隔離smoke test（read-only、1件）

### Kanban Durability
- `needs_input` block → restart → human unblock → reconcile の一巡
- task完了だけではphaseが進まないこと
- manifest revision不一致時の停止
- 通常workspaceではなく `dir:` workspaceにartifactが残ること

### Behavioral Evaluation
- 実モデル（親・子）でtool traceを測定
- 三項目確認前にRQ・検索・書込みを始めない
- abstract-onlyから本文級解釈をしない
- provider失敗を空結果にしない
- human approvalなしに探索拡張・停止・KB promotionをしない

## Fixture Classification

テスト用fixtureは以下の構造で管理する。

```text
tests/fixtures/
├── projects/
│   ├── empty/                 # 新規project用
│   ├── initialized/           # init済み
│   ├── design-complete/       # design phase完了
│   ├── plan-complete/         # plan phase完了
│   ├── acquisition-pending/   # 取得待ちあり
│   └── broken-manifest/       # 破損manifest
├── manifests/
│   ├── valid-v1.0.yaml
│   ├── missing-phase.yaml
│   ├── wrong-project-id.yaml
│   └── invalid-transition.yaml
├── candidates/
│   ├── fulltext-ready.jsonl
│   ├── abstract-only.jsonl
│   ├── acquisition-required.jsonl
│   └── mixed-scope.jsonl
└── provider-runs/
    ├── success.json
    ├── zero-hits.json
    ├── rate-limited.json
    └── unavailable.json
```

## 変更履歴

| 日付 | 変更 |
|---|---|
| 2026-07-23 | 初版。state machine、evidence scope、provider contract、path security、Kanban contract、test categories を定義。 |
