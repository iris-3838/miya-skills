---
name: sp
description: Alias for super-productivity — load this to use the Super Productivity Local REST API for task management.
tags:
  - alias
  - super-productivity
  - task-management
---

# sp → super-productivity

これは `super-productivity` skill のエイリアス。`super-productivity` をloadして使う。

→ `skill_view(name='super-productivity')` を先にloadすること。

```bash
# このskillをloadすると自動的にsuper-productivityが使える状態になる
# 以下、よく使う操作のショートカット：

# 今日のタスク
curl -s "http://localhost:3876/tasks?tagId=TODAY" | jq -r '.data[] | "☐ \(.title)"'

# ステータス確認
curl -s http://localhost:3876/status | jq '{count: .data.taskCount}'

# タスク追加 (Inbox)
curl -s -X POST http://localhost:3876/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"やること","projectId":"INBOX_PROJECT"}'

# タスク完了
curl -s -X PATCH http://localhost:3876/tasks/TASK_ID \
  -H "Content-Type: application/json" \
  -d '{"isDone":true}'

# タイマー開始/停止
curl -s -X POST http://localhost:3876/task-control/current \
  -H "Content-Type: application/json" \
  -d '{"taskId":"TASK_ID"}'
curl -s -X POST http://localhost:3876/task-control/stop
```

詳細なAPIリファレンスやbash関数は `skill_view(name='super-productivity')` 参照。