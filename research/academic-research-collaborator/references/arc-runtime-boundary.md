# ARC Runtime Boundary

`research-skill-architecture` と `academic-research-collaborator` の境界を定義する。
両者は同一external research skill bundle内に共存するが、責務と優先順位が異なる。

## 正本の優先順位

1. **`academic-research-collaborator/SKILL.md`** — ARC runtimeの唯一のRouter。現行の研究機能・命名・phase遷移はこの文書が正本。
2. **`references/runtime-contract-and-validation.md`** — state machine、evidence scope、provider contract、path securityの詳細契約。
3. **`research-skill-architecture/SKILL.md`** — 設計原則・配置方針・既存スキル統合マップ。Routerの再定義はしない。

実行時の判断で衝突した場合、上記の優先順位に従う。

## 旧設計との線引き

過去の5工程案（`design → strategy → search → select → synthesize`）は設計史であり、現行実装の命名・phase遷移として再利用しない。

| 過去 | 現在 | 備考 |
|---|---|---|
| `design` | `research-design` | RQ策定・研究設計 |
| `strategy` | — | `search-plan` に吸収 |
| `search` | `curate` | 書誌収集・候補整理 |
| `select` | — | HG③（候補選別）としてcurateのgateに |
| `synthesize` | `reflection` | 分析・還元 |

再導入が必要な場合は、Router、schema、artifact、manifest migrationを含む明示的な設計変更を行い、本ファイルと `research-skill-architecture` の両方を更新する。

## 変更時のチェックリスト

ARCの構造変更（命名変更、phase追加/削除/統合、gate位置変更）を行う場合：

1. `academic-research-collaborator/SKILL.md` のルーティングテーブルを更新
2. `references/arc-architecture.md` の仕様を更新
3. `references/runtime-contract-and-validation.md` のstate machine図と遷移表を更新
4. `templates/research-manifest.yaml` のschemaを更新し、migrationを定義
5. `research-skill-architecture/SKILL.md` の統合マップを更新
6. workflow referenceが新旧混在しないことを確認
7. 既存のKanban board bindingに影響があるか確認

## 非推奨パターン

- 事前合意なしに、`research-skill-architecture` の文言だけでRouterのphase名・遷移を上書きする
- 旧5工程名を現行Routerの参照ファイル内で使い続ける
- 「どちらの設計も有効」として実装判断を曖昧にする
