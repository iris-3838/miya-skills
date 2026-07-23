# ARCの現行runtime契約と設計史の境界

## 権威の順序

1. `academic-research-collaborator` は、実際のARC Routerと現行runtime契約の正本である。
2. 本skillは、research skill群に共通する設計原則・配置・統合判断を扱う。
3. 過去のARC工程図は設計史として保存してよいが、現行Routerと異なるphase名・遷移を実装対象として再利用してはならない。

## 現行ARCの機能モデル

```text
research-design
  → search-plan
  → curate
  → acquisition gate（人手本文取得）
  → reflection
  → human decision
  ↺ 次のdesign / planへ還元
```

4つの名称はroot Routerの機能ラベルであり、個別に自動登録されるskillsではない。support fileに入力、出力、証拠範囲、failure path、human gate、manifest mutation契約を置く。

## 状態の責務分離

| 状態 | 所有者 | 用途 |
|---|---|---|
| RQ、研究phase、判断、証拠範囲 | versioned manifest + event log | 研究上の正本 |
| artifact、検索ログ、分析成果 | project artifact tree | 再現・review・引用 |
| 待機、割当、retry、worker lifecycle | Kanban | 運用上の正本 |
| PDF・書誌 | Zotero / acquisition artifact | 取得・読解の境界 |

Kanban taskの完了だけで研究phaseを進めない。manifest revision、artifact、evidence scopeを検証するreconciliationを経由する。

## 変更時のチェック

- local skillとexternal skillが同名で二重配置になっていないか確認する。Hermesではlocalが優先される。
- Routerの参照先は実在する`references/`、`templates/`、`scripts/`に置き、genericな相対CWDを仮定しない。
- phase名・manifest field名・templateのenumを一括して更新する。
- 文書的な「必ず」は、validator/controllerのテストがある場合だけ機械的保証として主張する。
- 実装前にbundle参照、state transition、path containment、provider failure、Kanban block/restart/reconcileをテストする。

## 退役した表現

`ARC-design → ARC-strategy → ARC-search → ARC-select → ARC-synthesize` は過去の分割案であり、現行runtimeのphase定義ではない。これを再導入するには、Router・schema・artifact contract・migrationを含む明示的な設計変更が必要である。
