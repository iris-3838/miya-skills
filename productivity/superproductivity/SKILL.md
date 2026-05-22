---
name: superproductivity
category: productivity
description: Query, summarize, and manage tasks from the Super Productivity desktop app's local REST API. Weekly task summaries, deadline tracking, and progress overviews.
trigger: User mentions 'super productivity', 'SP', 'sp', 'weekly task summary', '今週のタスクまとめ', or asks about their task list / todos
---

# Super Productivity (SP) Local REST API

Super Productivity desktop app exposes a local REST API at **`http://localhost:3876`**.

**All responses** follow the envelope pattern: `{"ok": true/false, "data": ..., "error": {"code": "...", "message": "..."}}`

## Quick Health Check

```bash
curl -s http://localhost:3876/health
# → {"ok":true,"data":{"server":"up","rendererReady":true}}
```

## Endpoint Reference

### Tasks — `/tasks`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/tasks` | List all active (non-done) tasks |
| GET | `/tasks/:id` | Get single task details |
| POST | `/tasks` | Create a new task |
| PATCH | `/tasks/:id` | Update task fields |
| DELETE | `/tasks/:id` | Delete a task |
| POST | `/tasks/:id/start` | Start time tracking |
| POST | `/tasks/:id/stop` | Stop time tracking |
| POST | `/tasks/:id/archive` | Archive |
| POST | `/tasks/:id/restore` | Restore from archive |

**PATCH-supported fields:** `title`, `projectId`, `tagIds`, `parentId`, `dueDay`, `isDone`, `timeSpent`, `notes`

**Unsupported:** `subTaskIds` (returns `UNSUPPORTED_FIELD`)

### Projects — `/projects` (read-only)
- `GET /projects` — List all projects
- No create/update/delete endpoints exposed

### Tags — `/tags` (read-only)
- `GET /tags` — List all tags
- No create/update/delete endpoints exposed

### Time Tracking — `/task-control`
- `GET /task-control/current` — Currently tracked task + start time
- `POST /task-control/stop` — Stop active tracking

### Status
- `GET /status` — System status; includes `taskCount` (total including done)

## Weekly Task Summary Workflow

This is the primary use case when a user asks for their weekly overview.

### Step 1: Fetch raw data
```python
from hermes_tools import terminal
import json

tasks  = json.loads(terminal("curl -s http://localhost:3876/tasks")['output'])['data']
projs  = {p['id']: p['title'] for p in json.loads(terminal("curl -s http://localhost:3876/projects")['output'])['data']}
tags   = {t['id']: t['title'] for t in json.loads(terminal("curl -s http://localhost:3876/tags")['output'])['data']}
```

### Step 2: Group and annotate
- Group tasks by `projectId` using the project name map
- For each task, decode `tagIds` into readable labels
  - `EM_IMPORTANT` → 🔥 important
  - `EM_URGENT` → 🚨 urgent
  - `KANBAN_IN_PROGRESS` → 🔄 in-progress
  - `TODAY` → 📅 today
  - custom tag IDs → user-defined labels (discover via `GET /tags`)

### Step 3: Check deadlines
- `dueDay` field: `"YYYY-MM-DD"` format (string, not a timestamp)
- Compare against today's date to find overdue & upcoming items

### Step 4: Format output
Present as:
```
📋 今週のタスクまとめ（YYYY/MM/DD 曜日）

📁 ProjectName (N件)
  ⬜ 🚨 Task title (締切: YYYY-MM-DD)
  ✅ 完了したタスク

📊 集計
  アクティブタスク: N件
  🔥 重要: N件  🚨 緊急: N件  🔄 進行中: N件
  ⚠️ 期限超過: N件
  📅 今週の締切: N件
```

## Known Limitations & Pitfalls

- `/tasks` returns **only active (non-done) tasks**. Done/archived tasks are inaccessible via the REST API (no query param changes this).
- `taskCount` from `/status` includes done tasks → will be higher than `/tasks` length.
- Port 3876 is hardcoded in the desktop app; not configurable.
- No auth — localhost-only binding assumed.
- `parentId` + `tagIds`/`projectId` in the same PATCH can 400.
- Project/Tag CRUD is UI-only; no REST endpoints exist.

## Quick Task Creation Workflow

When the user asks to add a task to SP (often prefixed with `sp` in their message), follow this:

### Setup: load this skill

The user expects the `superproductivity` skill to be loaded whenever they say **"sp"** in their message. Always load it before proceeding.

### Steps

1. **Health check** — `curl -s http://localhost:3876/health`
2. **Discover project ID** — if unknown, `GET /projects` and find the right project by title/alias. Save to memory if new.
3. **Create task** — `POST /tasks` with `title`, `projectId`, optionally `dueDay`
4. **Add tags** — `PATCH /tasks/:id` with `tagIds` for urgency/priority

See `references/sp-quick-create.md` for exact `curl` commands and common tag IDs.

### Pitfall: user says "sp as <project>"

When the user says "sp ... as <project>" (or similar), the "as X" refers to the **project name** in SP. Look up the project by matching `X` against project titles (case-insensitive fuzzy match). Do not hardcode user-specific aliases in this public skill.

## Environment-Specific IDs

Store the user's project/tag IDs in **memory** (not in this skill) — they change per-user and per-SP instance. Use the memory tool to save these after discovery.

Memory example:
```
memory(action='add', target='memory', content='SP project IDs: INBOX_PROJECT=Inbox, PROJECT_ID=ProjectName, ...')
memory(action='add', target='memory', content='SP tag IDs: TODAY=Today, KANBAN_IN_PROGRESS=in-progress, EM_IMPORTANT=important, EM_URGENT=urgent')
```
