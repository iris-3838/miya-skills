# ARC Firm Rules (IRON RULE)

全ワークフローが遵守すべき不変の規則。ARS deep-researchのIRON RULEをARC向けに適応。

## 1. 証拠範囲を混同しない

`fulltext_ready` / `abstract_only` / `metadata_only` / `acquisition_required` / `unavailable` の5状態を常に区別する。

- `abstract_only` から本文の論証・方法・概念使用を断定しない
- `metadata_only` / `unavailable` の文献の内容を推測で埋めない
- confidence は evidence scope に応じて付与する

## 2. 人間の判断を自動化しない

以下の判断をagentが自動確定してはならない。

- RQの最終決定
- 探索計画の承認
- 候補の採用・除外
- 継続・分岐・拡張・停止の方針決定
- llm-kbへの知識promote
- 取得不能文献の黙った除外

## 3. 失敗を隠蔽しない

- API エラー（429, 5xx, timeout）を空結果として扱わない
- credential不足を `unavailable` として明示する
- coverage欠損を人間に報告する
- 不完全な結果で「完了」と宣言しない

## 4. 探索の境界を守る

- 人間が承認したepisodeの範囲を超えて自動拡張しない
- 候補数が上限を超えた場合、大量要約で処理せず、分割または絞り込みを提案する
- 人間の明示的な指示なしに新しい検索経路を追加しない

## 5. 秘密を保存しない

- API keyをCLI引数・manifest・ログ・artifactに渡さない
- 認証情報は環境変数（BWS経由）からのみ注入する
- 出力に秘密が混入した場合は `[REDACTED]` に置換する

## 6. 状態の一貫性を保つ

- phase遷移は承認済みgateとartifact存在を確認してから行う
- manifestとKanban taskのrevisionが一致しない場合は先に進まない
- 破損manifestを自動修復しない
- atomic writeで中途半端な状態を残さない

## 7. 検証前に完了を宣言しない

- bundle/static test → controller unit → integration → Kanban durability → behavioral evaluation の順に通過する
- 未テストの状態で「実行可能」と報告しない
- テストの成功条件は `references/runtime-contract-and-validation.md` に定義する

## Anti-Patterns

以下はARCの禁止パターンである。

1. 最初に全探索計画と大量の子タスクを作る
2. 人間の方針確認なしに次の探索を開始する
3. paywall文献の内容を抄録や引用から推測して埋める
4. 本文未取得の文献を分析完了にする
5. 1タスクに「全部探す・全部読む・全部整理する」を詰め込む
6. 大量候補を一度に人間へ渡す
7. agentの推奨経路を人間の承認なしに採用する
8. 検索結果が多いことを探索成功とみなす
9. 入手不能文献を黙って除外する
10. block理由を「情報不足」「調査中」のように曖昧にする
11. 固定閾値（新規率20%未満等）で自動停止する
12. 出版形態のTierだけで理論文献を序列化する
