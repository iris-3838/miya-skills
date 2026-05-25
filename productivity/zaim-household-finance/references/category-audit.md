# カテゴリ監査（Cross-Category Audit）

データ品質を維持するため、食費(101)に分類すべき取引が他のカテゴリに漏れていないか定期的に監査する。

## 監査パターン

### パターンA：外食店名なのに食費カテゴリ外

食費(101)以外のカテゴリに分類された取引の中から、店名が外食（ラーメン屋、牛丼、ファストフード等）を示すものを抽出する。

```sql
-- 全カテゴリの全取引から外食キーワードを検索
SELECT t.id, t.date, t.place, t.name, t.amount,
       c.name AS cat_name, g.name AS genre_name
FROM transactions t
JOIN categories c ON t.category_id = c.id
LEFT JOIN genres g ON t.genre_id = g.id
WHERE t.mode = 'payment'
  AND t.active = 1
  AND c.id != 101  -- 食費カテゴリを除外
  AND (
       t.place LIKE '%山岡家%' OR t.place LIKE '%一蘭%'
    OR t.place LIKE '%松屋%'   OR t.place LIKE '%モスバーガー%'
    OR t.place LIKE '%ガスト%'  OR t.place LIKE '%サイゼリヤ%'
    OR t.place LIKE '%やよい軒%' OR t.place LIKE '%Uber Eats%'
    OR t.place LIKE '%ドトール%' OR t.place LIKE '%Cafe%'
    OR t.place LIKE '%ラーメン%' OR t.place LIKE '%うどん%'
    OR t.place LIKE '%焼肉%'   OR t.place LIKE '%すし%'
    OR t.place LIKE '%カレー%'
    -- 対象に応じて拡張
  )
ORDER BY t.date DESC;
```

#### レストランキーワードリスト

よくある外食チェーン・飲食店のキーワード（食費カテゴリ外の監査用）：

- 山岡家, 一蘭, てっしょう, 超人, 豚男爵, ロマノフ
- 松屋, やよい軒, モスバーガー, はなまる, Uber Eats
- ドトール, Cafe, カフェ, coffee
- ラーメン, うどん, そば, 焼肉, すし, 寿司, 牛丼, カレー
- ガスト, サイゼリヤ, バーミヤン, ココス, デニーズ
- マクドナルド, ケンタッキー, すき家, 吉野家, なか卯
- びっくりドンキー, CoCo壱番屋, 天下一品, 大戸屋, 王将
- オリオン餃子, 特級鶏蕎麦, 伊堂寺, 焼肉和

**注意**: 「ざわ」のような短いキーワードは「くまざわ書店」(書店)などに誤マッチする。キーワードは長めに、または部分一致を確認して使うこと。

### パターンB：食費(101)内の誤分類

食費カテゴリ内で、ジャンル（食料品/昼ご飯/晩ご飯/カフェ）が適切か確認する。

```sql
-- 食費カテゴリで、店名から期待されるジャンルと実際のジャンルを比較
SELECT t.id, t.date, t.place, t.name, t.amount,
       g.name AS current_genre
FROM transactions t
JOIN genres g ON t.genre_id = g.id
WHERE t.mode = 'payment'
  AND t.active = 1
  AND t.category_id = 101
ORDER BY t.genre_id, t.date;
```

### パターンC：食料品以外の全取引一覧

食費カテゴリで食料品(10101)以外に分類されている全取引を確認する。

```sql
SELECT t.id, t.date, t.place, t.name, t.amount,
       g.name AS genre_name
FROM transactions t
JOIN genres g ON t.genre_id = g.id
WHERE t.mode = 'payment'
  AND t.active = 1
  AND t.category_id = 101
  AND t.genre_id != 10101
ORDER BY t.genre_id, t.date;
```

## よくある誤分類パターン

| ケース | 実態 | あるべきカテゴリ | 実際にありがちな誤分類 |
|--------|------|----------------|---------------------|
| モスバーガーなどのファストフード | 昼食/夕食 | 食費/昼ご飯 or 晩ご飯 | 交際費/飲み会 |
| ランチミーティング | 自分だけの食事 | 食費/昼ご飯 | 交際費/会議費 |
| コンビニで買った総菜・弁当 | 食料品 | 食費/食料品 | 日用雑貨/消耗品 |
| ドラッグストアでの食品のみ購入 | 食料品 | 食費/食料品 | 日用雑貨/消耗品 |
| オンラインフードデリバリー | 外食 | 食費/該当ジャンル | 交際費 or 日用雑貨 |

## 監査実行手順

1. ローカルDBを最新に同期: `python3 zaim.py sync`
2. パターンAで食費カテゴリ外の外食疑いをチェック
3. パターンBで食費内のジャンル矛盾をチェック
4. パターンCで食料品以外の全取引をレビュー
5. 誤分類があれば Zaim API で修正（`api.update()` を使用）

## 修正方法

誤分類を見つけた場合の修正手順:

```python
import zaim, os

api = zaim.Api(
    consumer_key=os.environ['ZAIM_CONSUMER_KEY'],
    consumer_secret=os.environ['ZAIM_CONSUMER_SECRET'],
    access_token=os.environ['ZAIM_ACCESS_TOKEN'],
    access_token_secret=os.environ['ZAIM_ACCESS_TOKEN_SECRET']
)

# カテゴリ修正 (例: 交際費→食費/昼ご飯)
api.update(
    mode='payment',
    money_id=9931543375,
    category_id=101,      # 食費
    genre_id=10104,       # 昼ご飯
    amount=1330,
    date='2026-02-12',
    name='モスバーガー',
    place='トナリエつくばスクエア',
    from_account_id=0
)
```

**注意**: PUTは未指定フィールドをデフォルト値にリセットする。`api.update()` を使えばライブラリが全フィールドを維持するが、生の `requests.put()` を使う場合は全フィールドを明示指定すること。
