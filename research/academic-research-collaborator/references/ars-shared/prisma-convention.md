# ARC PRISMA Convention

PRISMA（Preferred Reporting Items for Systematic Reviews and Meta-Analyses）のフローチャート規約を、ARCの探索透明性フレームワークとして適応する。

ARCではPRISMAをメタ分析の前提ではなく、検索式・DB・除外理由・取得状態を追跡可能にする報告規律として使う。

## モード別の深度

| 要素 | full | lit-review | quick-scan |
|---|---|---|---|
| 検索式の記録 | ✅ 全文 | ✅ 全文 | ✅ 要約 |
| DB・sourceの列挙 | ✅ | ✅ | ✅ |
| 検索日 | ✅ | ✅ | ✅ |
| ヒット数→重複除去→選別のflow | ✅ 詳細 | ✅ 詳細 | ✅ 簡易（件数のみ） |
| 除外理由の分類 | ✅ カテゴリ別 | ✅ カテゴリ別 | — |
| 取得状態の内訳 | ✅ | ✅ | ✅ |
| 検索式変更の理由と日付 | ✅ | ✅ | — |

## Flow Chart テンプレート

```markdown
## PRISMA Flow — [date]

### 検索実行
| DB / Source | 検索式 | ヒット数 |
|---|---|---|
| OpenAlex | `information concept` AND `Bates` | 45 |
| Crossref | `information concept` Bates | 38 |
| Semantic Scholar | 前方引用 (DOI:10.xxx) | 22 |

### 選別フロー
- 総ヒット数: 105
- 重複除去後: 87
- 抄録スクリーニング後（関連性確認）: 23
- 本文確認対象: 18
  - OAで本文取得: 5
  - 機関アクセスで取得: 3
  - 著者プレプリント: 1
  - 取得不能（paywall）: 9
- 採用候補（分析対象）: 12

### 除外理由 内訳
- 関連性なし（抄録判断）: 64
- 重複: 18
- 言語（対象外）: 2
- 資料種別（会議録等）: 1
- 取得不能で抄録からも関連性判断不可: 2
```

## 必須記録項目（full / lit-review）

1. **検索式** — 各DBの実際のクエリ文字列
2. **DB・Source** — 使用した全sourceとそのversion/アクセス日
3. **検索日** — YYYY-MM-DD
4. **ヒット数** — source別・重複除去前
5. **重複除去方法** — DOI/タイトル/著者year のマッチング基準
6. **選別基準** — 採用・除外の判断基準
7. **除外数と理由** — カテゴリ別
8. **取得状態** — fulltext / abstract-only / not-acquired の内訳
9. **検索式変更** — 変更があった場合の旧式・新式・変更理由・変更日

## quick-scan の簡易版

quick-scanでは以下の最小限の記録でよい。

```markdown
## PRISMA Flow (quick)
- 検索日: YYYY-MM-DD
- 使用source: OpenAlex, Crossref
- 総ヒット: 45
- 採用候補: 8
- 除外: 37（関連性なし30、重複7）
- 取得状態: fulltext 3, abstract 5
```

## 禁止事項

- 検索式・DBを記録せずに「PRISMAに準拠」と主張しない
- 除外理由を「関連性なし」に一括せず、可能な限り分類する
- 取得不能文献をフローチャートから消さず、`not-acquired` として明示する
- 検索式を後から修正した場合、変更履歴を消さない
