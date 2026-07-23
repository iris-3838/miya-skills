# ARC deterministic-core test fixture quality gates

ARC coreのRED→GREEN実装と独立reviewで、仕様そのものではなくfixtureの弱さを見落とさないためのチェックリスト。

## 1. Security fixture must exercise the security boundary

- symlink escape testは、許可root内に実際のsymlinkを作り、root外の実在directoryを指させる。単にsymlink風の文字列を渡すだけではpath policyを検証できない。
- symlink作成不可の環境だけ`SkipTest`にし、root・outsideのTemporaryDirectoryを必ず`finally`で削除する。
- traversal、basename mismatch、Unicode basename、separator入りIDを別々のfixtureとして持つ。

## 2. Isolate filesystem tests

- `/tmp/arc-test`のような共有・固定pathを使わず、`TemporaryDirectory`をtest classの`setUp`/`tearDown`で管理する。
- `normalize_project`のテストも、実際に書込みを行わなくてもrootを一時directoryにする。テスト環境の残存symlink・権限・別セッションのfixtureに影響されないようにする。
- 初期化・manifest書込みテストはprojectごとに独立したtemporary rootを作る。

## 3. Keep manifest fixtures semantically coherent

- `state.current_phase`と`status`を同じ契約に合わせる。phaseが`design`なら通常statusは`active`、Human Gate待ちなら`paused`とする。
- transition testは、失敗させたい条件以外を全て有効にする。例えばartifact不足を検証するtestに、status不整合を混ぜない。
- acquisition entryの欠落・未知statusをresolvedとして扱わない。許可enum、pending判定、終端状態（failed/unavailable）を個別に試す。

## 4. Test both sides of optimistic persistence

- `expected_revision`の不一致だけでなく、candidateのrevisionが`current + 1`でない場合も拒否することを検証する。
- conflict発生後にmanifestを再読込し、revision・status・本文が元のままであることを確認する。
- `safe_dump`やserializerをfixture内で失敗させ、atomic writeが既存manifestを保ち、一時ファイルを残さないことを確認する。temp判定は実装のprefix（例：`research-manifest.yaml.tmp.*`）を使う。
- concurrent writer testは同じexpected revisionから複数writerを実行し、成功1件・RevisionConflict 1件・最終revisionを確認する。

## 5. Review timing and final authority

- delegateしたreviewerには、絶対skill path、明示workdir、対象revisionを渡す。profileのcurrent working directoryを暗黙に仮定しない。
- 非同期reviewの途中結果は、親側の後続修正より古い可能性がある。reviewerの失敗がfixtureやstale bytecode由来なら、原因を切り分ける。
- delegate結果には開始時点の対象ファイル・test count・workdirを付記し、親側で現行ファイルと照合する。reviewerが「変更した」「テストが通った」と報告しても、side effectはread-backと再実行で検証する。
- 後続修正後に届いた古いbatch結果は、現行treeへ盲目的に再適用しない。symlink fixture、status、event schema、Unicode policyなどの個別主張を現在のコード・tests・docsに照合し、既に反映済みなら「旧snapshot」として記録だけする。
- review完了後に親セッションで、全test・compile・static bundleを最終状態に対して再実行する。最終tool出力を判定の根拠とし、途中のREDやreviewerの古いtest結果を最終結果として報告しない。
- 独立reviewのPASSはdeterministic coreの品質評価であり、Hermes plugin hard gate・Kanban reconcile・filesystem sandboxの実装証明ではない。

## 6. Completion evidence

最低限、次を記録する。

```text
py_compile: PASS
unittest discover: N tests, OK
static files/YAML/internal links: PASS
behavioral no-init smoke: PASS or INCONCLUSIVE
independent review: verdict + remaining findings
```

production-readyを宣言する前に、未実装層を明記する。