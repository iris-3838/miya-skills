# Super Productivity Local REST API の制限

## 確認日
YYYY-MM-DD (Hermes Agent 経由)

## `/executeGlobalCommand` の動作確認結果

`POST http://localhost:3876/executeGlobalCommand` に Pomodoro 関連のコマンド名を送信したが、全て `{ok: true}` を返すだけで実際の UI 操作は発生しなかった。

### 試したコマンド名

| コマンド名 | 結果 |
|-----------|------|
| `POMODORO_START` | `{ok: true}` — 何も起きない |
| `POMODORO_PAUSE` | `{ok: true}` — 何も起きない |
| `POMODORO_STOP` | `{ok: true}` — 何も起きない |
| `POMODORO_RESET` | `{ok: true}` — 何も起きない |
| `START_POMODORO` | `{ok: true}` — 何も起きない |
| `POMODORO_SKIP` | `{ok: true}` — 何も起きない |

### 結論

- コマンド名は受け付けられる（404にならない）が、サーバーサイドで実際の処理にマッピングされていない
- SP v1 の Local REST API では Pomodoro の操作はプログラムから行えない
- 代替として `skill: pomo`（ローカルファイルベースのタイマースクリプト）を使用する

## ルーティング制限の確認結果

### 試したエンドポイント

| Method | Path | Status | Body |
|--------|------|--------|------|
| GET | `/health` | 200 | `{"ok":true,"data":{"server":"up","rendererReady":true}}` |
| GET | `/` | 404 | `{"ok":false,"error":{"code":"NOT_FOUND","message":"Route not found"}}` |
| POST | `/task-control/pomodoro` | 404 | `{"ok":false,"error":{"code":"METHOD_NOT_FOUND","message":"..."}}` |
| POST | `/executeGlobalCommand` | 200 | `{"ok":true,"data":"command executed"}`（実効なし） |

### 結論

- SP のルーターは定義済みパスのみを受け付けるホワイトリスト方式
- 定義外のパスへの POST は `METHOD_NOT_FOUND` (≠ `NOT_FOUND`) を返す
- GET/POST の区別も厳密に行われる
- 動的ディスパッチ（任意のコマンド文字列から処理を呼ぶ）は実装されていない

## Task Control エンドポイントの動作確認

### 確認済みの動作

```bash
# タスク開始（正常動作）
curl -s -X POST http://localhost:3876/task-control/current \
  -H "Content-Type: application/json" \
  -d '{"taskId":"TASK_ID"}'
# → タスクタイマーが開始される

# タスク停止（正常動作）
curl -s -X POST http://localhost:3876/task-control/stop
# → タスクタイマーが停止される
```

### 確認済みの制限

- SP 側でポモドーロ機能をオンにしていても、その制御は REST API からはできない
- ポモドーロの状態（進行中かどうか、残り時間など）を取得するエンドポイントも存在しない
- ポモドーロの設定（作業時間/休憩時間など）を API から変更する手段もない

## 関連リソース

- `skill: pomo` — この制限を回避するためのローカルファイルベースのポモドーロタイマースクリプト
