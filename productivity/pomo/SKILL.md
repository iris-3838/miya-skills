---
name: pomo
description: "Pomodoro timer with SP task-time tracking integration. Commands: standalone cycle or SP-linked session."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
related_skills: [super-productivity]
---

# Pomo — Pomodoro Timer

Pomodoro timer with two modes:

1. **Standalone** (`pomo-cycle.py`) — plain timer, no external dependencies
2. **SP-linked** (`pomo-sp.py`) — timer synced to Super Productivity task time tracking

## Default Configuration

- **Work session:** 25 minutes
- **Short break:** 5 minutes
- **Long break:** 15 minutes (after 4 sessions)
- **Sessions before long break:** 4

Configuration is stored in `config.json` and can be modified via `pomo-config.py`.

## Architecture

| Script | Purpose |
|--------|---------|
| `pomo-sp.py` | **SP-linked pomodoro** — select SP task by name/ID, start timer, auto track time in SP |
| `pomo-cycle.py` | Standalone timer cycle (no SP dependency) |
| `pomo-config.py` | View/edit timer settings |
| `pomo-cancel.py` | Cancel a running standalone session |
| `config.json` | Timer presets |

## SP-linked Pomodoro (`pomo-sp.py`)

Requires Super Productivity desktop app running with Local REST API enabled (`localhost:3876`).

```bash
# Start by task name (fuzzy search)
python3 scripts/pomo-sp.py "タスク名"

# Start by exact task ID
python3 scripts/pomo-sp.py --id TASK_ID

# List active SP tasks
python3 scripts/pomo-sp.py --list

# Check current timer status
python3 scripts/pomo-sp.py --status

# Cancel running session (stops SP timer too)
python3 scripts/pomo-sp.py --cancel
```

**How it works:**
- Start: calls `POST /task-control/current` → SP task timer ON
- During session: progress bar with remaining time
- On completion or Ctrl+C: calls `POST /task-control/stop` → SP records elapsed time to `timeSpent` / `timeSpentOnDay`

## Standalone Pomodoro (`pomo-cycle.py`)

No SP required. Runs in terminal with basic notifications.

```bash
python3 scripts/pomo-cycle.py
```

## Scripts

```bash
python3 scripts/pomo-sp.py --help     # SP-linked mode
python3 scripts/pomo-cycle.py         # Standalone mode
python3 scripts/pomo-config.py        # View config
python3 scripts/pomo-config.py work_minutes 30   # Change setting
```

## Pitfalls

- **SP must be running**: `pomo-sp.py` fails if SP desktop app is not active or Local HTTP API is disabled
- **Port 3876 only**: SP Local REST API uses fixed port; requires `--network host` if running in Docker
- **No mid-session task switch**: Stop current session first, then start a new one on a different task
- **Terminal approval may be required**: In environments with `approvals.mode: manual`, running `pomo-sp.py` via `terminal()` or `execute_code` may prompt the user for approval before execution. Use `hermes --yolo` or set `approvals.mode: smart` if running unattended.
- **Ctrl+C interrupts cleanly**: SIGINT during a session triggers the finally block, which stops the SP timer and records elapsed time. No orphaned SP timers.
- **`/api/timer/notify` does NOT exist**: older versions of this skill referenced a fictional endpoint. Always use `/task-control/current` and `/task-control/stop`