#!/usr/bin/env python3
"""Pomo configuration tool - view/edit timer settings."""
import json
import sys
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config.json"

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
    print("Config saved.")

def show_config():
    cfg = load_config()
    print("Pomo Configuration:")
    print(f"  Work session:         {cfg['work_minutes']} min")
    print(f"  Short break:          {cfg['break_minutes']} min")
    print(f"  Long break:           {cfg['long_break_minutes']} min")
    print(f"  Sessions before long: {cfg['sessions_before_long_break']}")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        show_config()
    elif len(sys.argv) == 3:
        cfg = load_config()
        key = sys.argv[1]
        try:
            cfg[key] = int(sys.argv[2])
            save_config(cfg)
        except ValueError:
            print(f"Invalid value: {sys.argv[2]} (must be integer)")
        except KeyError:
            print(f"Unknown key: {key}")
    else:
        print("Usage: pomo-config.py [key value]")
