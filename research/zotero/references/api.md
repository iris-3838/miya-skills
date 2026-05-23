# Zotero Web API Reference (pyzotero)

## 認証

- API Key: Zotero アカウント設定 → Feeds/API Keys で発行
- User ID: `curl -H "Zotero-API-Key: <KEY>" https://api.zotero.org/keys/current` の `userID`
- 認証情報は `/workspace/.private/zotero_credentials.json` に保管

## 主要メソッド (pyzotero)

| カテゴリ | メソッド | 説明 |
|---------|---------|------|
| Collection | `collections()` | 全コレクション取得 |
| Collection | `collections_top()` | トップレベルのみ |
| Collection | `collections_sub(key)` | サブコレクション |
| Collection | `collection(key)` | 個別取得 |
| Collection | `all_collections(collid)` | 再帰的に全取得 |
| Collection | `create_collections([...])` | 作成 (name, parentCollection) |
| Collection | `update_collection({...})` | 更新 (name変更, 親変更) |
| Collection | `delete_collection(dict, version)` | 削除 |
| Item | `items()` | 全アイテム (format, q等でフィルタ) |
| Item | `items_top()` | トップレベルのみ |
| Item | `item(key)` | 個別取得 |
| Item | `collection_items(key)` | コレクション内アイテム |
| Item | `create_items([...])` | 作成 (itemType, title, creators等) |
| Item | `update_item({...})` | 更新 |
| Item | `delete_item(dict, version)` | 削除 |
| Item | `item_template(type)` | 新規アイテムのテンプレート取得 |
| Tag | `tags()` | 全タグ取得 |
| Export | `item_versions(since=)` | 差分同期用バージョン |
| Export | `items(format='bibtex')` | BibTeX等でエクスポート |
| Sync | `deleted(since=)` | 削除済みアイテム取得 |

## Collection データ構造

```json
{
  "key": "ABC123",
  "version": 42,
  "data": {
    "key": "ABC123",
    "name": "コレクション名",
    "parentCollection": "DEF456",  // false ならトップレベル
    "numItems": 5,
    "version": 42
  }
}
```

## Item データ構造（主要フィールド）

```json
{
  "itemType": "journalArticle",
  "title": "論文タイトル",
  "creators": [{"creatorType": "author", "firstName": "太郎", "lastName": "山田"}],
  "date": "2024",
  "DOI": "10.1234/example",
  "tags": [{"tag": "keyword"}],
  "collections": ["ABC123"],
  "extra": "カスタムメモ"
}
```

## フォルダ構造の整理（重要）

Zoteroのcollectionは階層構造を持ち、`parentCollection` フィールドで親子関係を表現する。

**具体例: 「移動」によりフォルダ整理**

```
Before:                        After:
研究                           研究
├── 論文A                      ├── 論文A
├── 論文B                      ├── 論文B
データ収集                      └── データ収集
├── 実験1                           ├── 実験1
└── 実験2                           └── 実験2
(「データ収集」がトップレベル)       (「研究」の下に移動)
```

`move` コマンドで `parentCollection` を変更するだけで階層構造を整理できる。
アイテム自体は移動されず、collectionの所属関係のみが変わる。
