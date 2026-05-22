---
name: super-productivity
description: Operate Super Productivity's Local REST API (port 3876) for task management — list, create, update, delete, start/stop tasks, manage projects and tags.
tags:
  - sp
  - task-management
  - productivity
  - rest-api
  - docker-networking
  - local-workflow
metadata:
  hermes:
    tags: [sp, task-management, productivity, rest-api]
    related_skills: [pomo]
---

# Super Productivity Local REST API

Super Productivity (SP) のデスクトップアプリがローカルに公開する REST API (`localhost:3876`) を操作する。

公式ドキュメント: https://github.com/super-productivity/super-productivity/wiki/3.01-API#3-local-rest-api

## ⚠️ Usage Priority — タスク管理はSPが最優先

**このユーザーのタスク管理システムはSPが唯一の正解です。**
ユーザーがタスクの追加・変更・完了・一覧表示・期限変更などを依頼してきた場合、**常にSPのREST APIを使うこと。** 内蔵の `todo` ツール（To Do Skills）は一切使わないでください。このルールは明示的に指示されており、違反するとユーザーから訂正が入ります。

- タスク作成 → `POST /tasks`
- タスク更新（完了、期限変更など） → `PATCH /tasks/:id`
- タスク一覧 → `GET /tasks`
- タスク削除 → `DELETE /tasks/:id`

最初に必ず `curl -s http://localhost:3876/health` でSPの稼働を確認してから操作を始めること。

## 前提条件

- SP デスクトップアプリが起動していること
- **設定 → その他 → Enable local HTTP API** が有効になっていること
- Hermes コンテナが `--network host` モードであること（ホストの localhost:3876 に到達するため）

## 疎通確認

```bash
curl -s http://localhost:3876/health
# → {"ok":true,"data":{"server":"up","rendererReady":true}}
```

## レスポンス形式

全APIは統一されたJSONエンベロープ:

```typescript
// 成功
{ "ok": true, "data": <response data> }

// エラー
{ "ok": false, "error": { "code": "<ERROR_CODE>", "message": "<説明>" } }
```

## エンドポイント一覧

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | サーバーとレンダラーの状態確認 |

### Task CRUD

| Method | Path | Description |
|--------|------|-------------|
| GET | `/tasks` | タスク一覧（フィルター可） |
| GET | `/tasks/:id` | タスク詳細 |
| POST | `/tasks` | タスク作成 |
| PATCH | `/tasks/:id` | タスク更新（※制限あり） |
| DELETE | `/tasks/:id` | タスク削除 |

### Task Control（タイムトラッキング）

| Method | Path | Description |
|--------|------|-------------|
| GET | `/status` | 現在のタスクと総タスク数 |
| GET | `/task-control/current` | 現在のタスク詳細 |
| POST | `/task-control/current` | タスクを開始（タイマーON） |
| POST | `/task-control/stop` | 現在のタスクを停止 |
| POST | `/tasks/:id/start` | 特定タスクを開始（上と同等） |

### Task Lifecycle

| Method | Path | Description |
|--------|------|-------------|
| POST | `/tasks/:id/archive` | アーカイブ |
| POST | `/tasks/:id/restore` | アーカイブから復元 |

### Project / Tag（読み取り専用）

| Method | Path | Description |
|--------|------|-------------|
| GET | `/projects` | プロジェクト一覧 |
| GET | `/tags` | タグ一覧 |

## 詳細リファレンス

### GET /tasks — クエリパラメータ

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | string | タイトル部分一致検索（大文字小文字無視） |
| `projectId` | string | プロジェクトIDでフィルター |
| `tagId` | string | タグIDでフィルター。`TODAY` で今日のタスク |
| `includeDone` | boolean | 完了済みを含める（デフォルト: false） |
| `source` | string | `active` | `archived` | `all`（デフォルト: `active`） |

### POST /tasks — 作成可能フィールド

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `title` | string | ✅ | 空文字不可 |
| `parentId` | string | ❌ | サブタスクとして作成。親はトップレベルタスクのみ。親のprojectIdを継承、tagIds指定不可 |
| `projectId` | string | ❌ | 親指定時は指定不可（400） |
| `tagIds` | string[] | ❌ | 親指定時は指定不可（400） |
| `notes` | string | ❌ | |
| `isDone` | boolean | ❌ | |
| `timeEstimate` | number | ❌ | ミリ秒 |
| `timeSpent` | number | ❌ | ミリ秒 |
| `dueDay` | string | ❌ | `YYYY-MM-DD` 形式 |
| `dueWithTime` | string | ❌ | ISO日時 |
| `plannedAt` | string | ❌ | ISO日時 |
| `subTaskIds` | - | ❌ | 作成時は指定不可（400） |

### PATCH /tasks/:id — 更新可能フィールド

`title`, `notes`, `isDone`, `timeEstimate`, `timeSpent`, `projectId`, `tagIds`, `dueDay`, `dueWithTime`, `plannedAt`

**更新不可（400 UNSUPPORTED_FIELD）:** `parentId`, `subTaskIds` — リペアレンティング不可。削除して再作成が必要。

**特殊フィールド:**
- `isDone: true` → 自動的に `doneOn` がセットされる
- `dueDay: null` → 期限をクリア

### Task Control

```bash
# タスク開始（/task-control/current 版）
curl -X POST http://localhost:3876/task-control/current \
  -H "Content-Type: application/json" \
  -d '{"taskId": "TASK_ID"}'

# 現在のタスクをクリア
curl -X POST http://localhost:3876/task-control/current \
  -H "Content-Type: application/json" \
  -d '{"taskId": null}'

# 停止
curl -X POST http://localhost:3876/task-control/stop
```

## 実用的なタスク管理操作

### 基本のbash関数（~/.bashrc やスクリプト用）

```bash
SP=http://localhost:3876

# タスク一覧（フィルターなし＝未完了のみ）
sp-ls() {
  curl -s "$SP/tasks$1" | jq -r '.data[] | "\(.id[0:8])  \(.isDone|tostring|.[0:1])  \(.title)"' 2>/dev/null
}

# タスクを作成
sp-add() {
  local title="$1"
  local project="${2:-INBOX_PROJECT}"
  curl -s -X POST "$SP/tasks" \
    -H "Content-Type: application/json" \
    -d "{\"title\":\"$title\",\"projectId\":\"$project\"}" | jq .
}

# タスクを完了
sp-done() {
  curl -s -X PATCH "$SP/tasks/$1" \
    -H "Content-Type: application/json" \
    -d '{"isDone":true}' | jq .
}

# タスクを削除
sp-rm() {
  curl -s -X DELETE "$SP/tasks/$1" | jq .
}

# 現在のタスク表示
sp-now() {
  curl -s "$SP/task-control/current" | jq .
}

# タスクを開始（タイマー）
sp-start() {
  curl -s -X POST "$SP/task-control/current" \
    -H "Content-Type: application/json" \
    -d "{\"taskId\":\"$1\"}" | jq .
}

# タイマー停止
sp-stop() {
  curl -s -X POST "$SP/task-control/stop" | jq .
}

# ステータス表示
sp-status() {
  curl -s "$SP/status" | jq '{currentTask: .data.currentTask.title, taskCount: .data.taskCount}'
}

# プロジェクト一覧
sp-projects() {
  curl -s "$SP/projects" | jq -r '.data[] | "\(.id)  \(.title) (\(.taskIds | length) tasks)"'
}

# タグ一覧
sp-tags() {
  curl -s "$SP/tags" | jq -r '.data[] | "\(.id)  \(.title) (\(.taskIds | length) tasks)"'
}

# 今日のタスク
sp-today() {
  curl -s "$SP/tasks?tagId=TODAY" | jq -r '.data[] | "\(.id[0:8])  \(.title)"'
}

# プロジェクト別タスク
sp-project-tasks() {
  curl -s "$SP/tasks?projectId=$1" | jq -r '.data[] | "\(.id[0:8])  \(.title)"'
}
```

### Environment-specific IDs

Project IDs and tag IDs are per-user/per-SP-instance. Do **not** hardcode real local IDs in this public skill; discover them at runtime with `GET /projects` and `GET /tags`.

**Project examples:**
| ID | 名前 | 用途 |
|----|------|------|
| `INBOX_PROJECT` | Inbox | デフォルト/未分類 |
| `PROJECT_ID_1` | PROJECT_A | 例 |
| `PROJECT_ID_2` | PROJECT_B | 例 |

**Tags:**
| ID | 名前 | 意味 |
|----|------|------|
| `TODAY` | Today | 今日のタスク |
| `KANBAN_IN_PROGRESS` | in-progress | 進行中 |
| `EM_IMPORTANT` | important | 重要 |
| `EM_URGENT` | urgent | 緊急 |
| `CUSTOM_TAG_ID` | Custom tag | ユーザー定義タグ |

## よく使う操作例

```bash
# === クイックリファレンス（コピペ用）===

# 1. 今日やること確認
curl -s http://localhost:3876/tasks?tagId=TODAY | jq -r '.data[] | "☐ \(.title) [\(.projectId)]"'

# 2. 重要な未完了タスク
curl -s "http://localhost:3876/tasks?tagId=EM_IMPORTANT&includeDone=false" | \
  jq -r '.data[] | "☐ \(.title) [\(.projectId)]"'

# 3. 緊急のタスク
curl -s "http://localhost:3876/tasks?tagId=EM_URGENT&includeDone=false" | \
  jq -r '.data[] | "☐ \(.title) [\(.projectId)]"'

# 4. 全タスク数確認
curl -s http://localhost:3876/status | jq '{count: .data.taskCount, current: .data.currentTask.title}'

# 5. タスクを作成（Inbox）
curl -s -X POST http://localhost:3876/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"やること","projectId":"INBOX_PROJECT","tagIds":["EM_IMPORTANT"]}' | jq .

# 6. サブタスクを作成
# まず親を作ってIDを取得し、そのIDを parentId に指定
curl -s -X POST http://localhost:3876/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"サブタスク","parentId":"PARENT_ID"}' | jq .

# 7. タスクを完了
curl -s -X PATCH http://localhost:3876/tasks/TASK_ID \
  -H "Content-Type: application/json" \
  -d '{"isDone":true}' | jq .

# 8. タスクを削除
curl -s -X DELETE http://localhost:3876/tasks/TASK_ID | jq .

# 9. タスクを検索
curl -s "http://localhost:3876/tasks?query=キーワード" | jq -r '.data[] | "\(.id)  \(.title)"'

# 10. アーカイブ/復元
curl -s -X POST http://localhost:3876/tasks/TASK_ID/archive
curl -s -X POST http://localhost:3876/tasks/TASK_ID/restore

# 11. プロジェクト別にタスクを表示
for p in INBOX_PROJECT PROJECT_ID_1 PROJECT_ID_2; do
  name=$(curl -s http://localhost:3876/projects | jq -r ".data[] | select(.id==\"$p\") | .title")
  echo "=== $name ==="
  curl -s "http://localhost:3876/tasks?projectId=$p&includeDone=false" | \
    jq -r '.data[] | "  ☐ \(.title)"'
done

# 12. 現在作業中のタスクを開始
curl -s -X POST http://localhost:3876/task-control/current \
  -H "Content-Type: application/json" \
  -d '{"taskId":"TASK_ID"}' | jq .

# 13. 現在の作業を停止
curl -s -X POST http://localhost:3876/task-control/stop | jq .
```

## 週次タスクサマリー Workflow

ユーザーが「今週のタスクまとめ」「週次サマリー」「進捗まとめ」などを求めた場合は、SP APIから `tasks`, `projects`, `tags` を取得し、プロジェクト別・タグ別・期限別に集計する。

### 取得・集計の基本

```python
from hermes_tools import terminal
import json, datetime

SP = "http://localhost:3876"
health = json.loads(terminal(f"curl -s {SP}/health")['output'])
assert health.get('ok')

tasks = json.loads(terminal(f"curl -s '{SP}/tasks?includeDone=false'")['output'])['data']
projects = {p['id']: p['title'] for p in json.loads(terminal(f"curl -s {SP}/projects")['output'])['data']}
tags = {t['id']: t['title'] for t in json.loads(terminal(f"curl -s {SP}/tags")['output'])['data']}
```

### 出力形式の例

```text
📋 今週のタスクまとめ（YYYY/MM/DD）

📁 ProjectName (N件)
  ☐ 🚨 Task title（締切: YYYY-MM-DD）
  ☐ 🔥 Important task

📊 集計
  アクティブタスク: N件
  🔥 重要: N件 / 🚨 緊急: N件 / 🔄 進行中: N件
  ⚠️ 期限超過: N件
  📅 今週の締切: N件
```

### タグの読み替え

- `EM_IMPORTANT` → 🔥 important
- `EM_URGENT` → 🚨 urgent
- `KANBAN_IN_PROGRESS` → 🔄 in-progress
- `TODAY` → 📅 today
- その他のタグIDは `GET /tags` で表示名を解決する

## レスポンスのTaskオブジェクト構造

```typescript
{
  id: string,              // 一意識別子
  title: string,           // タイトル
  subTaskIds: string[],    // サブタスクID一覧
  parentId?: string,       // 親タスクID（サブタスクの場合）
  projectId: string,       // プロジェクトID
  tagIds: string[],        // タグID一覧
  isDone: boolean,         // 完了フラグ
  doneOn?: number,         // 完了日時（ms）
  created: number,         // 作成日時（ms）
  modified?: number,       // 更新日時（ms）
  timeSpent: number,       // 計測済み時間（ms）
  timeSpentOnDay: Record<string, number>,  // 日別作業時間 {"YYYY-MM-DD": ms}
  timeEstimate: number,    // 見積もり時間（ms）
  dueDay?: string,         // 期限日 "YYYY-MM-DD"
  dueWithTime?: string,    // 期限日時（ISO）
  plannedAt?: string,      // 予定日時（ISO）
  notes?: string,          // メモ
  attachments: [],         // 添付ファイル
  reminderIds?: string[],  // リマインダーID
  archived?: boolean,      // アーカイブ状態
}
```

## エラーコード

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `TASK_NOT_FOUND` | 404 | タスクが存在しない |
| `NOT_FOUND` | 404 | ルートが見つからない |
| `INVALID_INPUT` | 400 | リクエストボディが不正 |
| `UNSUPPORTED_FIELD` | 400 | 変更不可フィールドを指定 |
| `INTERNAL_ERROR` | 500 | サーバー内部エラー |

## 関連リソース

- **`references/cron-automation.md`** — SP タスク × Hermes cron job の自動化パターン（`no_agent=True` + Python スクリプト）。ポモドーロタイマー、タイムボックス、作業リマインダー向け。
- **`references/api-limitations.md`** — SP Local REST API の制限詳細（`/executeGlobalCommand` の動作確認結果、ルーティング制限のテスト記録）。
- **`skill: pomo`** — ポモドーロタイマー実装。SP と統合済み。

## 注意点・既知の問題

- **Electron専用**: Web版やモバイル版では利用不可
- **認証なし**: localhost限定のため認証なし。外部公開厳禁
- **ポート固定**: 3876固定（v1では変更不可）
- **タイムアウト**: レンダラー応答に15秒のタイムアウト
- **リペアレンティング不可**: 既存タスクの親子関係変更は非対応。削除して再作成
- **Dockerネットワーク**: `--network host` 必須。ブリッジネットワークだと到達不可
- **`/executeGlobalCommand` 非対応**: `POST /executeGlobalCommand` に `{"name": "POMODORO_START"}` 等を送ると `{ok: true}` は返るが、実際のボタン押下は発生せず何も起きない。Pomodoro の開始/停止/リセットは REST API 経由では操作不可。SP のポモドーロを操作したい場合は `skill: pomo`（ローカルファイルベースのタイマースクリプト）を使用する。
- **制限的ルーター**: SP Local REST API はホワイトリスト方式のルーティング。定義外のエンドポイントへの POST は `METHOD_NOT_FOUND` を返す。動的なコマンドディスパッチは行われない。
- **タイムトラッキングの単位**: 時間系フィールドはすべて**ミリ秒**
- **jq必須**: 上記の操作例は `jq` を前提としている