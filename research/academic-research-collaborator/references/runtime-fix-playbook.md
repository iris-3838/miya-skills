# ARC Runtime Fix Playbook

ARC Routerやworkflow referenceを、prompt依存の設計から決定的runtimeへ引き上げる際の再利用手順。

## 適用トリガー

- manifest/template/workflowのfieldやnestingに不一致が見つかった
- behavioral smokeは通るが、controller・validator・atomic persistenceがない
- phase遷移、evidence scope、provider failureをLLM指示だけで制御している

## 実装順序

1. **canonical schemaを先に固定する。** `research-manifest.yaml`と`acquisition_manifest.yaml`、runtime contract、workflow referenceのfield・nesting・enum・phase名を照合する。初期値は`revision: 0`、`status: initialized`、`state.current_phase: initialized`にする。
2. **Staticとsemanticを分離する。** ファイル存在・YAML構文・referenceリンクのPASSを、schema意味整合性のPASSと混同しない。`16/16 PASS`のようなstatic結果だけで実行可能と報告しない。
3. **REDテストを先に作る。** path containment、`..`、symlink、project collision、Human Gate、後半phaseのacquisition条件、evidence scope、provider enum、atomic write、revision conflict、同時writerを実際のfixtureで固定する。
4. **最小coreを実装する。** `normalize_project`、`initialize_project`、`create_initial_manifest`、`transition_manifest`、`pause_manifest`、candidate/provider validator、safe YAML loader、atomic writerを純粋関数として分離する。
5. **後半phaseも検証する。** `curate → acquisition_pending`にはpending acquisition manifest、`curate/acquisition_pending → reflection`にはresolvedかつ未解決entryなし、reflectionからのloop-backには初期artifactを要求する。取得待ち中は`status: paused`と理由・revision・eventを記録する。
6. **永続性を競合込みで試験する。** temp file + flush/fsync + replaceだけでなく、read/check/writeの競合窓をlockまたは同等のcompare-and-swapで閉じ、同一revisionの同時writerが一つだけ成功することを確認する。
7. **親セッションで再検証する。** 子agentのsummary・「テスト済み」報告・生成物のside effectを証拠とみなさず、親が対象fileを読み直し、focused testと全suiteを実行する。
8. **Hermes hard gateは別層として報告する。** pure coreがGREENでも、`pre_tool_call`/plugin、Kanban reconcile、provider adapterが未実装なら全tool経路の強制性を主張しない。

## fixtureレビューのpitfall

- **delegated reviewはsnapshotである。** subagentのテスト件数・行番号・未実装報告を、そのまま現行状態の証拠にしない。親が対象ファイルを再読し、レビュー時点と現在の差分を確認してから、focused testと全suiteを現行コードで再実行する。古い45件レビューが、後から追加済みの`pause_manifest`や後半transitionを未実装と報告することがある。
- symlink escapeテストは、単なるsymlink風の文字列ではなく、root配下からroot外を指す実symlinkを作る。作成できない環境だけ`SkipTest`にする。
- schema移行後は、テストfixtureの旧status（例：`design_done`）とRED説明・docstringを検索して更新する。実装を旧enum受け入れで緩めない。
- artifact gateは単純な`endswith()`にしない。canonicalなproject-relative path（例：`artifacts/design/rq-brief.md`）を、separator正規化後にexact matchする。`rogueartifacts/...`、absolute path、別root pathを拒否するテストを置く。実ファイル存在・project root containment・内容schema・artifact revisionは別のadapter/plugin境界で検証する。
- phase tableの`PHASES`と`_ALLOWED_TRANSITIONS`がdriftしてもraw `KeyError`を出さない。lookupは`.get(from_phase, frozenset())`等で閉じ、table entry欠落を`TransitionError`として検証する。
- acquisition entryのstatusは閉じたenumとして扱う。欠落・未知値をresolved扱いせず、`pending` / `not_attempted` / `in_progress`を一件でも残したらreflectionを拒否する。`failed` / `unavailable`は終端状態でも`fulltext_ready`を意味しない。
- revisionテストは、呼び出し側が`revision: 1`を渡せたことだけを確認しない。current revision + 1以外を拒否し、serialization失敗時に元manifest保持・temporary file cleanupを確認する。同時writerは同一revisionから一件だけ成功し、一件はconflictになることを確認する。
- manifest templateのeventコメントとcore生成eventを同期する。少なくとも`id`、`type`、`phase`、`from_phase`、`to_phase`、`reason`、`revision`、`timestamp`の命名・enumを照合する。
- project IDのASCII制約は自動的に導入しない。ARC契約がUnicode／日本語basenameを許す場合は、日本語pathの正常系テストを追加する。
- TestNormalizeProject等のpath policy fixtureは`TemporaryDirectory`で隔離する。固定`/tmp/...`を使う場合でも作成・symlink・cleanupの責務を明示する。
- expected file listを拡張するときは既存項目を置換せず追記する。変更後に全ファイル実在、YAML、内部リンクを再実行する。
- reviewerやsubagentには対象skillの絶対pathと明示workdirを渡す。相対path誤解や古いbytecodeが出た場合は、親が現物を再読し、cacheを除去して全suiteを再実行する。

## 代表的な検証コマンド

PyYAMLがプロジェクト環境に宣言されていない場合でも、`uv run --with pyyaml`で一時依存として検証できる。

```bash
uv run --with pyyaml python3 -m unittest discover \
  -s tests -p 'test_*.py' -v
```

テスト後は、モデルbehavioral smoke、Hermes discovery、plugin/toolset、Kanban durabilityを別々の判定層として記録する。

## KB handoff

- canonical noteは旧監査の結論を削除せず、`P0修正後の再検証`節として追記する。
- KB操作は現在cwdに依存させず、絶対path付き`git -C "$KB" ...`または明示workdirで実行する。view generatorもKB repoのcwdで実行する。
- HTTPS remoteでcredential helperが未設定なら、次のcredential helper fallbackを再試行する。これは失敗を恒久的制約として保存するのではなく、復旧手順である。

```bash
git -C "$KB" -c credential.helper='!gh auth git-credential' pull --rebase origin main
uv run python tools/build_views.py
uv run python tools/build_views.py --check
uv run pytest
git -C "$KB" add -- knowledge/<canonical-note>.md
git -C "$KB" -c credential.helper='!gh auth git-credential' push origin main
git -C "$KB" log -1 --oneline
git -C "$KB" status --short --branch
```

対象canonical fileだけをstageし、未追跡の作業物を`git add -A`で混入させない。
