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
curl -s "http://localhost:3876/tasks?tagId=TODAY" | jq -r '.data[] | "☐ \\(.title)"'

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

## sp list — タスク一覧を見やすく表示

`sp list` は現在の未完了タスクをプロジェクト別・期限順で表形式に可視化する。

```bash
# 使用法
python3 scripts/sp-list.py

# エイリアス登録（~/.bashrc などに追加）
alias sp-list='python3 /opt/data/workspace/miya-skills/productivity/sp/scripts/sp-list.py'
```

### 出力例

```
  📋 Super Productivity  (2026-06-17)
  ────────────────────────────────────────────────────────────

  [Inbox]  4件
  ⬜  NoDH1yyg  プログラミング講習会のことを先生にメール                              🔴 ⚠️06-15
  ⬜  8nKVgKrI  電気・水道代の払込を確認する                                        🟡 今日!
  ⬜  jPdo3ga8  今年度用のマニュアル作成                                             🟢 06-20

  [TERMATLAS/KALC]  1件
  ⬜  ajITAkVj  termatlas進捗まとめ・整理                                   🟢 06-19

  [GRADTHESIS/YOKOYAMALAB]  1件
  ⬜  hBYs0-HZ  プロ入メール（先生確認待ち）

  ────────────────────────────────────────────────────────────
  📊 未完了: 6件  |  🚨 期限超過: 1件
  ⚠️  期限超過あり → NoDH1yyg（プログラミング講習会）
  Inbox:4  TERMATLAS/KA:1  GRADTHESIS/YOK:1
```

詳細なAPIリファレンスやbash関数は `skill_view(name='super-productivity')` 参照。