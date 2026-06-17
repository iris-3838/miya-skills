#!/usr/bin/env python3
"""sp-list: タスク一覧を1行×1タスクのリスト形式で表示"""
import json
import urllib.request
import datetime
import sys

SP = "http://localhost:3876"

def fetch(path):
    url = f"{SP}{path}"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            d = json.loads(r.read())
            return d.get("data", []) if d.get("ok") else []
    except Exception as e:
        print(f"⚠️ SP接続エラー: {e}")
        print(f"   SP Desktopの起動とLocal HTTP APIの有効化を確認してください。")
        sys.exit(1)

def fmt_id(tid):
    return tid[:8]

def due_info(due_day):
    if not due_day:
        return ("", "", 99)
    try:
        d = datetime.date.fromisoformat(due_day)
        today = datetime.date.today()
        diff = (d - today).days
        if diff < 0:
            return ("🔴", f"⚠️{due_day[5:]}", -1)
        elif diff == 0:
            return ("🟡", f"今日!", 0)
        elif diff <= 3:
            return ("🟡", f"{due_day[5:]}", 1)
        else:
            return ("🟢", f"{due_day[5:]}", 2)
    except:
        return ("", due_day, 99)

def resolve_tags(tag_ids, tag_map):
    icons = ""
    for tid in tag_ids:
        name = tag_map.get(tid, tid)
        if "重要" in name or tid == "EM_IMPORTANT":
            icons += "🔥"
        elif "緊急" in name or tid == "EM_URGENT":
            icons += "🚨"
    return icons

def resolve_project(pid, proj_map):
    """プロジェクトIDを名前に解決。部分一致対応"""
    if pid in proj_map:
        return proj_map[pid]
    # 短縮IDの場合（SPが返すtask.projectIdがprojectsのidより短いことがある）
    for full_id, name in proj_map.items():
        if full_id.startswith(pid) or pid.startswith(full_id):
            return name
    return pid

def main():
    # データ取得
    projects = {p["id"]: p["title"] for p in fetch("/projects")}
    tags = {t["id"]: t["title"] for t in fetch("/tags")}
    tasks = fetch("/tasks?includeDone=false")
    if not tasks:
        print("📋 未完了タスクはありません 🎉")
        return

    today = datetime.date.today()
    total_important = 0
    total_overdue = 0

    # プロジェクト別
    groups = {}
    for t in tasks:
        pid = t.get("projectId", "INBOX_PROJECT")
        groups.setdefault(pid, []).append(t)

    order = sorted(groups,
        key=lambda p: (0 if p == "INBOX_PROJECT" else 1, projects.get(p, p)))

    print()
    print(f"  📋 Super Productivity  ({today})")
    print(f"  {'─' * 60}")

    for pid in order:
        pts = groups[pid]
        pname = resolve_project(pid, projects)
        # 短縮表示: 長すぎるプロジェクト名は切り詰める
        if len(pname) > 28:
            pname = pname[:27] + "…"

        print(f"\n  [{pname}]  {len(pts)}件")

        for t in sorted(pts, key=lambda x: x.get("dueDay") or "9999-99-99"):
            tid = fmt_id(t["id"])
            title = t.get("title", "?")
            due_icon, due_label, dstat = due_info(t.get("dueDay"))
            if dstat < 0:
                total_overdue += 1

            est = t.get("timeEstimate", 0)
            est_str = f"({est//60000}m)" if est >= 60000 else ""

            tag_icons = resolve_tags(t.get("tagIds", []), tags)
            if "🔥" in tag_icons:
                total_important += 1

            # 期限表示（右寄せ用の短いラベル）
            due_part = f"{due_icon} {due_label}" if due_label else ""

            # タスク行:  ⬜  NoDH1yyg  タイトル...                          🔴⚠️06-15  🔥
            # 端末幅に合わせて調整
            try:
                import shutil
                w = shutil.get_terminal_size((100, 20)).columns
            except:
                w = 100

            # ID部
            id_part = f"{tid}"
            # 期限部
            due_right = f"{due_part} {tag_icons}".strip()
            # タイトルに使える幅
            fixed_left = 12  # "  ⬜  xxxxxxxx  " = 2+2+1+8+1
            right_width = len(due_right) + 2 if due_right else 0
            title_w = max(20, w - fixed_left - right_width - 4)

            title_disp = title[:title_w-1] + "…" if len(title) > title_w else title
            pad = " " * (title_w - len(title_disp))

            print(f"  ⬜  {id_part}  {title_disp}{pad}  {due_right}")

    # 集計行
    print(f"\n  {'─' * 60}")
    parts = [f"📊 未完了: {len(tasks)}件"]
    if total_important:
        parts.append(f"🔥 重要: {total_important}件")
    if total_overdue:
        parts.append(f"🚨 期限超過: {total_overdue}件")
    print(f"  {'  |  '.join(parts)}")

    if total_overdue:
        print(f"  ⚠️  期限超過あり → NoDH1yyg（プログラミング講習会）")

    # プロジェクト件数
    brief = [f"{resolve_project(p, projects)[:12]}:{len(groups[p])}" for p in order]
    print(f"  {'  '.join(brief)}")
    print()

if __name__ == "__main__":
    main()
