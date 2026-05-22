#!/usr/bin/env python3
"""Cancel a running pomodoro session."""
import json
import os
import signal

STATUS_FILE = "/tmp/pomo_status.json"

def cancel():
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE) as f:
            status = json.load(f)
        os.remove(STATUS_FILE)
        print(f"🍅 Pomo cancelled (session {status.get('session', '?')})")
    else:
        print("No active pomo session.")
    sys.exit(0)

if __name__ == "__main__":
    import sys
    cancel()
