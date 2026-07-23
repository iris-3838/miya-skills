# ARC Implementation Re-audit Protocol

ARCのworkflow referenceやRouterを変更した後に、static bundle、runtime contract、モデル行動、決定的実装を混同せずに再監査するための手順。

## 判定層を分ける

`PASS`は一種類ではない。報告では必ず次を分離する。

1. **Static bundle PASS**: ファイル存在、YAML構文、内部参照、linked reference読込。
2. **Semantic contract PASS**: manifest/template/workflowのfield、nesting、enum、phase遷移が一致。
3. **Behavioral PASS**: 実モデルが初期化前に質問し、未承認書込みを避け、再開時に確認する。
4. **Deterministic runtime PASS**: controller、validator、atomic writer、plugin guard、revision/reconcile testが機械的に通る。

Static bundle PASSだけで「実行可能」「production-ready」と報告しない。

## 再監査手順

### 1. Skill discovery

- `skill_view`でRouter本体と、Routerが参照する各referenceを個別に読む。
- `hermes -p <profile> skills list`で実際のprofileから発見されることを確認する。
- 同名local/external skillの衝突と、linked fileの実在性を確認する。

### 2. Semantic contract check

- templateをYAMLとしてparseする。
- runtime contractが要求する必須fieldを抽出する。
- workflow reference内の`state.*`、artifact path、enum、phase名をtemplateと照合する。
- 実際にmodelが生成したfixtureもparseし、template由来のschemaと混同しない。
- `current_phase`が現在phaseなのか次phaseなのか、`status`との関係を明示する。

最低限、次を検査する。

```text
manifest: revision / status / project_path / artifact_dir / events
state: mode / current_phase / completed_phases / pending gates
candidate: evidence_scope / acquisition_status / provider_status
provider: success / zero_hits / unavailable / transient_error / rate_limited
```

### 3. Safe behavioral smoke

本番project・KB・Kanbanを使わず、使い捨ての絶対pathを用いる。

- 初期三項目なし: RQ、検索、書込みを始めず、project_id・path・mode確認で停止するか。
- 明示的initializeあり: scaffoldだけを作り、検索・Kanban・KB promotionを行わないか。
- 別session resume: manifestをread-onlyで読み、状態を表示してresume/cancel確認で停止するか。
- 書込み対象・temp projectが終了後に残っていないことを確認する。

モデルが正しく振る舞っても、それはdeterministic guardの証拠ではない。prompt依存のbehavioral PASSとして記録する。

### 4. Deterministic implementation check

次の実体をsource tree・profile config・plugin registryで探す。

- state controller (`init`, `status`, `transition`, `reconcile`)
- schema/path validator
- atomic writeとrevision conflict handling
- `pre_tool_call`または同等のhard guard
- provider adapterのactive配備
- Kanbanとmanifestのrevision binding

reference文書に関数名が書かれているだけなら未実装として扱う。

### 現在のprofile-local実装

`academic-research-collaborator/scripts/arc_core.py` は、schema/path/evidence/provider/transition/atomic-write/revisionの決定的coreである。以下で検証する。

```bash
uv run --with pyyaml python3 -m unittest discover -s tests -p 'test_*.py' -v
```

このcoreのPASSは、Hermes plugin guard、Kanban reconcile、provider adapterが実装済みであることを意味しない。これらは別の未実装層として報告する。

### 5. 失敗時の報告

以下のように分類して報告する。

```text
Static bundle: PASS/FAIL
Semantic contract: PASS/FAIL
Behavioral smoke: PASS/FAIL/INCONCLUSIVE
Deterministic runtime: PASS/FAIL/NOT_IMPLEMENTED
```

PTYやUI制御コードで観測不能になった場合は、機能失敗と断定せず`INCONCLUSIVE`としてプロセスを終了する。非対話smoke、source/config検査、fixture testなど別の観測経路を使う。

## よくある誤判定

- 「16/16ファイルcheck PASS」→ manifest schemaも合格した、としない。
- modelがmanifestを書けた → controllerが存在する、としない。
- OA URLがある → `fulltext_ready`、としない。
- providerの応答0件 → `zero_hits`、としない。`unavailable`、`rate_limited`、`transient_error`を保持する。
- Kanban boardをCLIで読めた → model-visible Kanban toolsetとreconcileが有効、としない。
- 旧workflow文書が存在する → 現行Routerの実行経路、としない。

## 変更後の次の実装順

1. templateとruntime contractの統一
2. 失敗するcontroller unit test
3. 純粋Pythonのstate/path/evidence/atomic-write core
4. Hermes tool/plugin adapter
5. Kanban durable reconcile
6. provider live smokeとread-only shadow pilot
