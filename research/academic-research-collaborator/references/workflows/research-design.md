# ARC Research Design

RQ策定・研究内容設計を行う。Socratic対話入口とDevil's Advocateチェックポイントを含む。

## 事前条件

- projectが `initialized` であること
- `research-manifest.yaml` の `state.current_phase` が `initialized` または `design`
- `arc-context.md` の研究基盤（対象理論家、KBパス、分野）が読込済み

## 入力

- ユーザーの研究関心（発話）
- `arc-context.md` の理論家スキャフォールド
- 既知文献・既存知識（llm-kb参照）

## 手順

### 1. Socratic Entry（必須）

関心をRQ候補へ練り上げる。以下の5層を順に深める。

1. **現象層**: 何が観察されているか
2. **概念層**: どの概念で捉えられているか
3. **理論層**: どの理論的枠組みが関わるか
4. **対立層**: どのような見解の相違があるか
5. **前提層**: どのような暗黙の前提があるか

少なくとも層3までは到達する。ユーザーの関心が具体的な場合は最初の層を飛ばしてもよい。

### 2. RQ Brief の構成

以下の要素を含む `artifacts/design/rq-brief.md` を作成する。

```yaml
core_rq:          # 中心的な問い（1文）
sub_questions:    # 副問い（2〜4個）
scope:
  included:       # 含める範囲
  excluded:       # 意図的に除外する範囲（理由付き）
assumptions:      # 明示的な前提
theoretical_framing:  # 依拠する理論的立場
expected_contribution: # 期待される学術的貢献
known_uncertainties:   # 現時点で不明なこと
```

### 3. Devil's Advocate（必須、design末尾）

RQ、前提、除外範囲、理論的立場に対して反証チェックを行う。

- 逆の結論を支持する証拠はあるか
- 前提が成り立たない条件は何か
- 除外した範囲に重要な反例がないか
- 別の理論的立場からみた盲点は何か

DAの指摘はRQ briefに追記し、人間が採否を判断する。

### 4. Human Gate ①

RQ brief + DA指摘を提示し、ユーザーに以下を確認する。

- RQは研究可能かつ明確か
- 除外範囲は妥当か
- DAの指摘を受け入れるか、理由付きで棄却するか

ユーザーが `approve` するまでplanへ進まない。

## 出力

| artifact | 形式 | 説明 |
|---|---|---|
| `artifacts/design/rq-brief.md` | Markdown | RQ、前提、範囲、DA指摘を含む |
| `research-manifest.yaml` 更新 | YAML | `state.current_phase: design`、`state.rq.core` を記録 |

## Evidence Scope 制約

- このphaseでは文献の内容分析を行わない
- 既知文献の参照は「人間が知っていること」として扱い、書誌収集はcurateで行う
- DAでの反証探索は仮説的なものに留め、実際の文献検索はsearch-plan/curateに委ねる

## Failure Paths

| 状況 | 対応 |
|---|---|
| RQが曖昧で絞り込めない | Socratic対話を続け、少なくとも層2まで具体化する |
| DAが重大な欠陥を指摘 | RQまたは前提を修正し、再度DAを通す |
| ユーザーがRQを保留したい | manifestにdraft状態を記録し、後日再開可能にする |
| lit-reviewモードで既存RQがない | designを省略せず、少なくともliteで実行する |
