#!/usr/bin/env python3
"""Pomo cycle manager - runs pomodoro sessions with SP integration."""
import json
import os
import sys
import time
import subprocess
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config.json"
STATUS_FILE = "/tmp/pomo_status.json"

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

def save_status(state):
    with open(STATUS_FILE, "w") as f:
        json.dump(state, f)

def notify(msg):
    """Send notification via SP or terminal bell."""
    print(f"\n🔔 {msg}\n")
    subprocess.run(["curl", "-s", "-X", "POST",
        "http://localhost:3876/api/timer/notify",
        "-H", "Content-Type: application/json",
        "-d", json.dumps({"message": msg})], capture_output=True)

def run_cycle():
    cfg = load_config()
    work_m = cfg["work_minutes"]
    break_m = cfg["break_minutes"]
    long_break_m = cfg["long_break_minutes"]
    max_sessions = cfg["sessions_before_long_break"]
    session_count = 0

    print(f"🍅 Pomo started: {work_m}min work, {break_m}min break, {long_break_m}min long break (every {max_sessions})")
    save_status({"state": "running", "session": 0, "phase": "work", "remaining": work_m * 60})

    try:
        while True:
            session_count += 1
            save_status({"state": "running", "session": session_count, "phase": "work", "remaining": work_m * 60})
            for i in range(work_m * 60, 0, -1):
                save_status({"state": "running", "session": session_count, "phase": "work", "remaining": i})
                time.sleep(1)
            notify(f"Session {session_count} complete! Take a break.")

            if session_count % max_sessions == 0:
                save_status({"state": "running", "session": session_count, "phase": "long_break", "remaining": long_break_m * 60})
                for i in range(long_break_m * 60, 0, -1):
                    save_status({"state": "running", "session": session_count, "phase": "long_break", "remaining": i})
                    time.sleep(1)
                notify("Long break over! Ready for next session.")
            else:
                save_status({"state": "running", "session": session_count, "phase": "break", "remaining": break_m * 60})
                for i in range(break_m * 60, 0, -1):
                    save_status({"state": "running", "session": session_count, "phase": "break", "remaining": i})
                    time.sleep(1)
                notify("Break over! Back to work.")
    except KeyboardInterrupt:
        save_status({"state": "cancelled", "session": session_count})
        print("\nPomo cancelled.")
        sys.exit(0)

if __name__ == "__main__":
    run_cycle()
