---
name: pomo
description: "Pomodoro timer with customizable work/break intervals. Commands: /pomo start, /pomo status, /pomo cancel."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
---

# Pomo — Pomodoro Timer

Pomo is a terminal-based Pomodoro timer integrated with Super Productivity (SP). It tracks work sessions and breaks, sending notifications when sessions complete.

## Default Configuration

- **Work session:** 25 minutes
- **Short break:** 5 minutes
- **Long break:** 15 minutes (after 4 sessions)
- **Sessions before long break:** 4

Configuration is stored in `config.json` and can be modified via `pomo-config.py`.

## Commands

```
/pomo start        Start a new pomodoro cycle
/pomo status       Check current timer status
/pomo cancel       Cancel current timer
```

## Architecture

- `pomo-cycle.py` — Main cycle manager (timer logic, SP integration)
- `pomo-config.py` — Configuration reader/writer
- `pomo-cancel.py` — Cancel running timer
- `config.json` — Timer presets

## Integration

Pomo sends session events to Super Productivity (SP) at `http://localhost:3876` for task tracking integration.

## Scripts

The scripts in this skill directory can be run from the terminal:
```bash
python3 scripts/pomo-cycle.py
python3 scripts/pomo-config.py
python3 scripts/pomo-cancel.py
```