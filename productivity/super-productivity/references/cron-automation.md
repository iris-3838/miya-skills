# Cron-based SP Task Automation (no_agent=True pattern)

SP タスクに対して Hermes cron job と `no_agent=True` スクリプトを使った自動化パターン。

## パターン概要

Hermes cron job の `no_agent=True` モードと Python/bash スクリプトを組み合わせて、LLM トークンを消費せずに SP タスクのタイムド・ワークフローを実現する。

```
cron job (no_agent=True, ワンショット)
  └─ script(sleep + curl + print) → stdout がユーザーチャットに配信
```

## いつ使うか

- SP タスクのタイマーを時間指定で開始/停止したい
- ポモドーロ、タイムボックス、作業リマインダーなど反復タイマー
- LLM コストをかけたくない純粋なスクリプト処理
- 長時間バックグラウンドで動かすプロセス（sleep ベース）

## 基本構造

```python
#!/usr/bin/env python3
"""SP cron automation script — stdout is delivered to the user."""
import subprocess, time, json, os, sys

SP_BASE = "http://localhost:3876"

def sp_stop():
    subprocess.run(["curl", "-s", "-X", "POST", f"{SP_BASE}/task-control/stop"],
                   capture_output=True)

def sp_start(task_id):
    subprocess.run(["curl", "-s", "-X", "POST", f"{SP_BASE}/task-control/current",
                    "-H", "Content-Type: application/json",
                    "-d", json.dumps({"taskId": task_id})],
                   capture_output=True)

def notify(msg):
    print(msg, flush=True)
```

## Sleep-based タイマーパターン

スクリプト内で `time.sleep()` を使って時間待ちする。

```python
CANCEL_FILE = "/tmp/sp-automation-cancel"
CHECK_INTERVAL = 15  # 秒

def countdown(minutes):
    """Sleep with periodic cancel checks."""
    total = minutes * 60
    elapsed = 0
    while elapsed < total:
        if os.path.exists(CANCEL_FILE):
            sp_stop()
            notify("⛔ キャンセルされました")
            os.remove(CANCEL_FILE)
            sys.exit(0)
        time.sleep(CHECK_INTERVAL)
        elapsed += CHECK_INTERVAL
```

**注意点:**
- `print(..., flush=True)` で即時出力。cron job の配信はスクリプト終了時に全 stdout を一括送信するため、flush しないと出力が最後までバッファリングされる
- 15-30秒ごとのキャンセルチェックで、キャンセルレイテンシとCPU負荷のバランスを取る
- キャンセルファイル方式（`/tmp/sp-automation-cancel`）はスクリプトとキャンセル用スクリプトで合意されたパスを使う

## Cron job 登録

```python
cronjob(
    action="create",
    name="sp-automation-<description>",
    schedule="30s",     # 即時開始（30秒後）
    repeat=1,           # ワンショット
    no_agent=True,      # LLM不使用、stdout配信
    script="/path/to/script.py",
    deliver="origin",   # 現在のチャットに配信
)
```

## キャンセルスクリプトのテンプレート

```python
#!/usr/bin/env python3
"""Cancel a running automation by setting the cancel flag."""
import os, subprocess
CANCEL_FILE = "/tmp/sp-automation-cancel"
open(CANCEL_FILE, "w").close()
subprocess.run(["curl", "-s", "-X", "POST",
    "http://localhost:3876/task-control/stop"])
print("✅ キャンセルしました")
```

## Pitfalls

1. **長時間実行**: スクリプトが 25分間スリープしても cron スケジューラはプロセスを生かし続ける。ただし、Docker のプロセス管理やホストのリソース制限に注意。
2. **キャンセルファイルの競合**: 同時に複数の automation を動かさないこと。必要なら task_id をファイル名に含める（`/tmp/sp-cancel-<task_id>`）。
3. **stdout バッファリング**: `flush=True` を付けないと cron job の配信が遅延する。`no_agent=True` の出力はスクリプト終了時に一括配信される。
4. **SP 停止状態の確認**: `sp_stop()` は常に成功する（停止中でもエラーにならない）。冪等なので安全。
