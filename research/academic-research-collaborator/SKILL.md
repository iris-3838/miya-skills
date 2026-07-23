---
name: academic-research-collaborator
description: 人間主導のLIS研究を、RQ設計・探索計画・書誌収集・本文取得・反省ループとして伴走し、監査可能なartifactとhuman gateへ導くRouter。
version: 0.2.0
metadata:
  hermes:
    category: research
    tags: [LIS, research-orchestration, literature-search, human-in-the-loop, paywall-aware, theory-comparison]
    related_skills: [literature-human-in-loop-kanban, literature-agent-epistemics, lis-theory-comparison, lis-journal, llm-wiki]
    config:
      - key: arc.projects_root
        description: ARCプロジェクトを置ける許可済みの親ディレクトリ。実際の成果物パスは毎回ユーザーが確認する。
        default: ""
---

# Academic Research Collaborator (ARC)

LIS研究における、人間主導の反復ループを案内するclass-level Routerである。

```text
research-design → search-plan → curate → acquisition gate → reflection
                                  ↑                         │
                                  └──── human decision ──────┘
```

ARCは研究を代行しない。人間はRQ、概念境界、重要性、反証評価、方針変更、停止を決める。agentは問いの精緻化、探索経路、候補整理、provenance、盲点、反対見解の提示を担う。

## いつ使うか

- 新しいLIS研究テーマをRQへ練りたい
- 既存の研究プロジェクトを、artifactと判断履歴から安全に再開したい
- 理論比較・文献探索を、取得状態と不確実性を明示しながら進めたい
- 書誌収集、本文取得、内容分析、知識化を混同せずに運用したい

## Corpus identity and short-deadline pilots

- 現行canonical corpus、プロジェクト固有の作業データ、`_bak/`の歴史資料を別のevidence scopeとして扱う。新しい資料が旧資料と異なる件数・スキーマ・研究対象を示す場合、旧データを黙ってfallbackにしない。
- 現行データの実体が未取得・未確認なら、状態を`documented`/`blocked`/`not_run`として返し、歴史データで結果を代用しない。代替コーパスを使うには、human gateで別corpusとして採用する。
- 短期pilotは、主張を狭く固定する。例えば`author/title/year`、同一入力、同一schema、GROBIDのout-of-the-box baseline、direct LLM、事前固定したsampleと評価規約に限定する。
- 計画文書、実験プロトコル、結果またはブロッカーを別artifactに分ける。未実行の数値をResults欄やtask noteへ補完しない。
- データ所在、gold規約、pilot結果の本文採否、最終研究主張を別々のHuman Gateとして返す。

研究執筆・査読・投稿は別のworkflowで扱う。ARCは執筆前の研究設計・探索・分析還元に集中する。

## 非交渉ルール

1. **RQより先に初期化を確認する。** 新規研究では `project_id`、成果物の絶対path、mode（`quick-scan` / `full` / `lit-review`）を取得し、正規化した値を表示してから明示確認を取る。確認までRQ案、検索、project書込みを始めない。
2. **Router文書だけを強制機構と呼ばない。** `clarify()` は入力確認、tested coreはschema/path/state/evidence検証を担当する。Hermes plugin guardやKanban reconcileが未検証なら、全tool経路の機械的保証を主張せず、必要に応じてread-only scopingに留める。
3. **本文取得を第1級のgateにする。** metadata、abstract、full text、未取得を混同しない。未取得文献の理論内容を推測しない。
4. **重要判断は人間に返す。** 次の大規模探索、採否、RQ変更、取得優先順位、停止、llm-kbへのpromoteを自動確定しない。
5. **provider失敗を空結果にしない。** `success`、`zero_hits`、`unavailable`、`rate_limited`、`transient_error`を固定enumとして記録し、coverage欠損として人間へ返す。`unavailable`、`rate_limited`、`transient_error`を`zero_hits`へ変換しない。
6. **秘密をartifactに保存しない。** API keyをCLI引数・manifest・ログに渡さない。BWS等の安全な環境注入だけを使う。

## 起動と再開

### 新規プロジェクト

1. `clarify()` で三項目を取得する。自由記述の場合も、id・absolute path・modeが全て揃うまで先へ進まない。
2. pathを正規化し、idと末尾名の一致、許可root内、collision、path traversal、symlink escapeを検査する。
3. 確認画面として正規化後の三項目を示し、`initialize` / `revise` / `cancel` を選んでもらう。
4. **確認後のみ** tested state controllerがmanifest、artifact directory、初期eventを作成する。
5. controllerのstatusが `initialized` を返す。初期Human Gateの明示承認後にのみ `initialized → design` を実行し、research-designを開始する。

`arc.projects_root` は候補の親ディレクトリであり、成果物pathの代替ではない。パスはハードコードせず、毎回確認する。設定値が空または解決不能なら、controllerは初期化を拒否してread-only scopingに留める。

### 既存プロジェクト

1. manifestを読む。壊れたschema・異なるproject id・未完了migrationを自動修復しない。
2. canonical id/path/mode、current state、pending decision、最後のartifact、Kanban board/task bindingを表示する。
3. 再開するか確認する。mode変更、board binding、migrationは別の明示decisionとして記録する。
4. Kanbanとmanifestが食い違えば、先へ進まずreconciliation/human reviewを作る。

パッケージ内の参考資料は `skill_view(name, file_path=...)` で読む。genericな相対 `read_file` pathを仮定しない。

## 4つの研究機能

| 機能 | 入力 | 最小出力 | Human gate |
|---|---|---|---|
| `research-design` | initialized project、研究関心 | RQ brief、前提、対抗仮説、除外範囲 | HG① RQ確認 |
| `search-plan` | 確認済みRQ | question slice、route spec、known items、coverage claim、停止時の問い | HG② 計画確認 |
| `curate` | 確認済みplan | provider run、候補ledger、除外理由、access/evidence状態、acquisition queue | HG③ 候補・取得判断 |
| `reflection` | fulltext/abstract区別済みのevidence | relation/uncertainty/coverage report、次route候補 | HG④ continue / revise / expand / acquire / stop |

workflow referenceを作成・更新する際は、各文書に入力、出力、許可された証拠範囲、failure path、gate、manifest更新契約を明記する。存在しないworkflowをRouterの送信先として宣言しない。

## モード

| Mode | 深度 | 不変の要件 |
|---|---|---|
| `quick-scan` | 少数のbounded episode、簡易監査 | 4機能をliteで通し、少なくとも一つの反証/盲点確認を行う |
| `full` | route、provenance、PRISMA型探索ログを詳細化 | RQ、計画、候補、方向のhuman gateを維持する |
| `lit-review` | coverage、検索変更、除外・取得状態を最も詳細に記録 | 既存の確認済みRQがない限りdesignを飛ばさない |

PRISMAは固定検索式や自動停止を意味しない。探索式・route・判断・変更理由を追跡可能にする報告規律として使う。

## 探索・証拠の規律

- 語彙検索と関係性探索（前後方引用、著者、批評、共引用、雑誌・資料種別）を分けて記録する。
- known-item validation、反証route、言語・地域・資料種別のcoverage gapを明示する。
- 飽和指標は人間への診断材料であり、固定件数・固定新規率による自動停止規則ではない。
- source type、peer-review status、理論上の役割、RQへの直接性、evidence scopeを分ける。書籍章や原典を一律に低品質扱いしない。
- `metadata_only` / `abstract_only` / `fulltext_ready` / `acquisition_required` / `unavailable` をcandidate ledgerに残す。アクセス不能文献を黙って除外しない。
- `fulltext_ready` はOA URLやlanding pageを発見した状態ではない。人間が本文を取得・開封し、分析可能な本文artifactまたは検証済み添付を確認した場合だけ付与する。

詳細なstate、evidence、provider、Kanban、test契約は [`references/runtime-contract-and-validation.md`](references/runtime-contract-and-validation.md) を読む。設計史・ARS対応は [`references/arc-architecture.md`](references/arc-architecture.md) を参照するが、現runtimeの契約は前者を優先する。

## Deterministic runtime core

schema・path・phase・evidence・provider・atomic manifest更新の決定的境界は、`scripts/arc_core.py` の純粋Python APIで実装する。実行環境にPyYAMLが必要なため、external skill bundleのtestは次で実行する。

```bash
cd /home/miyax/workspace/miya-skills/research/academic-research-collaborator
uv run --with pyyaml python3 -m unittest discover -s tests -p 'test_*.py' -v
```

このcoreはHermes pluginやKanban reconcileをまだ置き換えない。plugin guard・provider adapter・durable reconcileが未配備のruntimeでは、coreのPASSをもって全tool経路のhard gate完了とは報告しない。

実装・再監査の具体的な順序、fixtureのpitfall、同時writer検証は `references/runtime-fix-playbook.md` を参照する。RED/green fixtureの実在性・独立reviewの時点差・atomic failure検証は `references/test-fixture-quality-gates.md` を参照する。

### Deterministic core maintenance lessons

- **schemaを先にcanonical化する。** template、workflow、controller、testsでfieldのnesting・enum・初期値を一致させ、static PASSだけでsemantic PASSと報告しない。
- **status enumは閉じる。** acquisition entryの欠落・未知値を「resolved」と解釈せず拒否する。終端状態（failed/unavailable）と本文のevidence scope（fulltext_ready）を混同しない。
- **Unicode pathをASCII slugへ狭めない。** 日本語project IDを許可しつつ、single directory component、separator、制御文字、予約名、root containment、symlink escapeを検証する。
- **manifest writeは競合込みで設計する。** safe YAML、temp+fsync+replace、revision conflictだけでなく、read-check-write全体をlockして同時writerを直列化する。
- **検証層を分離する。** static bundle、semantic contract、model behavioral smoke、deterministic core/pluginを別々に判定し、prompt依存のPASSをhard gate完了と呼ばない。
- **fixtureとreviewerの実行rootを明示する。** profile-local skillの相対pathを仮定せず絶対pathまたは明示workdirを渡し、code変更後はstale bytecodeを避けて全testを再実行する。
- **履歴artifactを壊さない。** canonical KB noteは旧監査結論を消さず、追記節で修正後の判定・未実装範囲・実測値を記録する。view/check/test後に対象ファイルだけcommit/pushする。

## Hermesへの分配

| Hermes primitive | 用途 | 使わない用途 |
|---|---|---|
| `clarify()` | 即時の確認・選択 | 数時間〜数日の取得待ち |
| Kanban | durable human gate、retry、worker再開 | canonical研究主張の唯一の保管先 |
| `delegate_task` | boundedな独立検証・route比較 | durable state、human gate、親artifactの直接確定 |
| state controller / plugin | init、transition、path/evidence検証 | RQの意味解釈 |
| literature adapter | bounded retrievalと正規化 | 内容分析、Zotero書込み |
| llm-kb | 人間承認後の検証済み知識 | raw run、未決task、秘密 |

Kanbanを使う場合は、専用または明示的にbindingしたboardと絶対 `dir:` workspaceを用いる。既存boardを名前推測で再利用・移行しない。`kanban_*` toolsetが利用できないruntimeでは、agentが永続workerであるかのように振る舞わず、pending decisionをartifactへ保存して人間に再開方法を示す。

## 実装後の再監査

実装変更後は、次の4つを別々に判定する。詳細手順は `references/implementation-reaudit.md` に置く。

1. **Static bundle**: skill discovery、linked reference、YAML構文、内部path。
2. **Semantic contract**: manifest/template/workflowのfield、nesting、enum、phase遷移。
3. **Behavioral smoke**: 実モデルが初期化前に質問し、未承認書込み・検索・promoteを避けるか。
4. **Deterministic runtime**: controller、validator、atomic write、revision/reconcile、plugin guardの実装とtest。

Static bundleやbehavioral smokeのPASSを、deterministic runtimeの存在証拠として報告しない。model-generated manifestがruntime契約らしいfieldを含んでいても、templateとcontrollerを別途検証する。

OA URL・landing pageの発見は`fulltext_ready`ではない。人間が本文取得・開封・分析可能性を確認した場合だけ`fulltext_ready`とする。providerの0件は、`unavailable`、`rate_limited`、`transient_error`を除外して`zero_hits`と判定しない。

## 検証前の完了宣言をしない

実装・変更後は、少なくとも以下を通してから「実行可能」と報告する。

1. bundle/static test：linked reference、template、schema、hardcoded pathを検査
2. controller unit test：初期化、遷移、復旧、evidence scope、競合更新
3. Hermes integration：skill discovery、clarify timeout、plugin/hook、toolset
4. Kanban durability：block → restart → human unblock → reconcile
5. provider fixture testと、隔離したlive smoke test
6. 実際の親・子モデルでtool traceを測るbehavioral evaluation
7. 既存研究へのread-only shadow pilot

テスト詳細とfixture分類は `references/runtime-contract-and-validation.md`、静的preflight手順は `references/static-preflight.md` を参照する。
