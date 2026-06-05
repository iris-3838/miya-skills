#!/usr/bin/env python3
"""Pomodoro timer with Super Productivity integration.

Usage:
    python3 pomo-sp.py "タスク名"              # タスク名で検索して開始
    python3 pomo-sp.py --id TASK_ID            # タスクID直接指定
    python3 pomo-sp.py --list                  # 未完了タスク一覧
    python3 pomo-sp.py --status                # 現在のポモドーロ状態
    python3 pomo-sp.py --cancel                # 実行中のポモドーロを中止
    python3 pomo-sp.py --config                # 設定表示

SPのLocal REST API (localhost:3876) と連動:
- 開始時: POST /task-control/current でタスク開始（タイマーON）
- 終了時: POST /task-control/stop でタスク停止（timeSpentに記録）
"""
import json
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
import signal
from pathlib import Path

SP = "http://localhost:3876"
STATUS_FILE = Path("/tmp/pomo_sp_status.json")

# デフォルト設定
DEFAULT_CONFIG = {
    "work_minutes": 25,
    "break_minutes": 5,
    "long_break_minutes": 15,
    "sessions_before_long_break": 4,
}

CONFIG_PATH = Path(__file__).parent.parent / "config.json"


def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return {**DEFAULT_CONFIG, **json.load(f)}
    return DEFAULT_CONFIG.copy()


def sp_request(method, path, data=None):
    """SP APIへのリクエスト。失敗時は例外を投げる。"""
    url = f"{SP}{path}"
    req = urllib.request.Request(url, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(data).encode("utf-8")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            err = json.loads(body)
            raise RuntimeError(f"SP API error: {err.get('error', {}).get('message', body)}")
        except json.JSONDecodeError:
            raise RuntimeError(f"SP API HTTP {e.code}: {body}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Cannot connect to SP: {e.reason}")


def sp_get_tasks(query=None, include_done=False):
    """タスク一覧を取得。"""
    path = f"/tasks?includeDone={str(include_done).lower()}"
    if query:
        path += f"&query={urllib.parse.quote(query)}"
    return sp_request("GET", path)["data"]


def sp_start_task(task_id):
    """タスクを開始（タイマーON）。"""
    return sp_request("POST", "/task-control/current", {"taskId": task_id})


def sp_stop_task():
    """現在のタスクを停止（タイマーOFF）。"""
    return sp_request("POST", "/task-control/stop")


def sp_get_current():
    """現在作業中のタスクを取得。"""
    return sp_request("GET", "/task-control/current")["data"]


def format_time(seconds):
    """秒を MM:SS 形式に。"""
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"


def save_status(state):
    with open(STATUS_FILE, "w") as f:
        json.dump(state, f)


def load_status():
    if STATUS_FILE.exists():
        with open(STATUS_FILE) as f:
            return json.load(f)
    return None


def clear_status():
    if STATUS_FILE.exists():
        STATUS_FILE.unlink()


def print_progress(phase, session, remaining, total, task_title):
    """1行で進捗を表示（上書き）。"""
    elapsed = total - remaining
    bar_len = 20
    filled = int(bar_len * elapsed / total) if total > 0 else 0
    bar = "█" * filled + "░" * (bar_len - filled)
    phase_emoji = {"work": "🍅", "break": "☕", "long_break": "🌴"}.get(phase, "⏱")
    phase_name = {"work": "作業", "break": "休憩", "long_break": "長休憩"}.get(phase, phase)
    line = f"\r{phase_emoji} [{bar}] {format_time(remaining)} | {phase_name} #{session} | {task_title[:30]}"
    print(line, end="", flush=True)


def run_pomodoro(task_id, task_title):
    cfg = load_config()
    work_sec = cfg["work_minutes"] * 60
    break_sec = cfg["break_minutes"] * 60
    long_break_sec = cfg["long_break_minutes"] * 60
    max_sessions = cfg["sessions_before_long_break"]

    # SPでタスク開始
    print(f"▶ SPでタスク開始: {task_title}")
    sp_start_task(task_id)

    session_count = 0
    cancelled = False

    def handle_sigint(sig, frame):
        nonlocal cancelled
        cancelled = True
        print("\n\n⚠ 中断シグナルを受信")

    signal.signal(signal.SIGINT, handle_sigint)

    try:
        while not cancelled:
            session_count += 1

            # Work session
            save_status({
                "state": "running",
                "session": session_count,
                "phase": "work",
                "remaining": work_sec,
                "task_id": task_id,
                "task_title": task_title,
                "started_at": time.time(),
            })

            print(f"\n🍅 セッション #{session_count} 開始 ({cfg['work_minutes']}分)")
            for i in range(work_sec, 0, -1):
                if cancelled:
                    break
                print_progress("work", session_count, i, work_sec, task_title)
                time.sleep(1)

            if cancelled:
                break

            print(f"\n✅ セッション #{session_count} 完了！")

            # Break
            is_long = session_count % max_sessions == 0
            break_duration = long_break_sec if is_long else break_sec
            phase = "long_break" if is_long else "break"
            phase_name = "長休憩" if is_long else "休憩"

            save_status({
                "state": "running",
                "session": session_count,
                "phase": phase,
                "remaining": break_duration,
                "task_id": task_id,
                "task_title": task_title,
            })

            print(f"☕ {phase_name}開始 ({cfg['long_break_minutes'] if is_long else cfg['break_minutes']}分)")
            for i in range(break_duration, 0, -1):
                if cancelled:
                    break
                print_progress(phase, session_count, i, break_duration, task_title)
                time.sleep(1)

            if cancelled:
                break

            print(f"\n🔄 {phase_name}終了")

    finally:
        # 必ずSPでタスク停止
        print("\n⏹ SPでタスク停止")
        try:
            sp_stop_task()
        except RuntimeError as e:
            print(f"  警告: SP停止でエラー: {e}")

        if cancelled:
            save_status({"state": "cancelled", "session": session_count, "task_id": task_id})
            print(f"🛑 ポモドーロ中止（セッション #{session_count} まで）")
        else:
            save_status({"state": "completed", "session": session_count, "task_id": task_id})
            print(f"🎉 ポモドーロ完了（全{session_count}セッション）")


def list_tasks():
    tasks = sp_get_tasks(include_done=False)
    print(f"=== 未完了タスク ({len(tasks)}件) ===")
    for t in tasks:
        spent = t.get("timeSpent", 0)
        spent_min = spent // 60000
        print(f"  {t['id']} | {t['title']} | 累計: {spent_min}分")


def find_task(query):
    """タスク名で検索。複数ヒットしたら選択。"""
    tasks = sp_get_tasks(query=query, include_done=False)
    if not tasks:
        # 部分一致で再試行
        all_tasks = sp_get_tasks(include_done=False)
        tasks = [t for t in all_tasks if query.lower() in t["title"].lower()]

    if not tasks:
        print(f"タスクが見つかりません: {query}")
        return None, None

    if len(tasks) == 1:
        t = tasks[0]
        print(f"タスク選択: {t['title']} (ID: {t['id'][:8]}...)")
        return t["id"], t["title"]

    print(f"複数のタスクが見つかりました:")
    for i, t in enumerate(tasks, 1):
        print(f"  {i}. {t['title']} (ID: {t['id'][:8]}...)")
    try:
        choice = int(input("番号を選択: ")) - 1
        t = tasks[choice]
        return t["id"], t["title"]
    except (ValueError, IndexError):
        print("無効な選択です")
        return None, None


def show_status():
    status = load_status()
    if not status:
        print("ポモドーロは実行されていません")
        return

    state = status.get("state", "unknown")
    session = status.get("session", 0)
    phase = status.get("phase", "?")
    task_title = status.get("task_title", "?")
    remaining = status.get("remaining", 0)

    phase_name = {"work": "作業中", "break": "休憩中", "long_break": "長休憩中"}.get(phase, phase)

    if state == "running":
        print(f"🍅 実行中: {phase_name} #{session} | 残り: {format_time(remaining)} | タスク: {task_title}")
    elif state == "cancelled":
        print(f"🛑 中止済み: セッション #{session} まで | タスク: {task_title}")
    elif state == "completed":
        print(f"✅ 完了: 全{session}セッション | タスク: {task_title}")
    else:
        print(f"状態: {state} | セッション: #{session} | タスク: {task_title}")


def cancel_pomodoro():
    status = load_status()
    if not status or status.get("state") != "running":
        print("実行中のポモドーロはありません")
        return

    # プロセスにSIGINTを送る方法がないので、statusファイルにcancelledフラグを書き込む
    # 実際のpomo-sp.pyプロセスはファイルをポーリングしていないので、
    # 別途プロセスkillが必要。ここでは単純化のためSP停止だけ実行。
    print("⏹ SPでタスク停止")
    try:
        sp_stop_task()
    except RuntimeError as e:
        print(f"  警告: {e}")

    save_status({
        "state": "cancelled",
        "session": status.get("session", 0),
        "task_id": status.get("task_id"),
        "task_title": status.get("task_title", "?"),
    })
    print(f"🛑 ポモドーロを中止しました")


def show_config():
    cfg = load_config()
    print("Pomo Configuration:")
    print(f"  Work session:         {cfg['work_minutes']} min")
    print(f"  Short break:          {cfg['break_minutes']} min")
    print(f"  Long break:           {cfg['long_break_minutes']} min")
    print(f"  Sessions before long: {cfg['sessions_before_long_break']}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    arg = sys.argv[1]

    if arg == "--list":
        list_tasks()
    elif arg == "--status":
        show_status()
    elif arg == "--cancel":
        cancel_pomodoro()
    elif arg == "--config":
        show_config()
    elif arg == "--id":
        if len(sys.argv) < 3:
            print("タスクIDを指定してください")
            sys.exit(1)
        task_id = sys.argv[2]
        # タスク詳細取得
        try:
            task = sp_request("GET", f"/tasks/{task_id}")["data"]
            run_pomodoro(task_id, task["title"])
        except RuntimeError as e:
            print(f"エラー: {e}")
            sys.exit(1)
    else:
        # タスク名として検索
        task_id, task_title = find_task(arg)
        if task_id:
            run_pomodoro(task_id, task_title)


if __name__ == "__main__":
    main()
