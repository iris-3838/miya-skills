#!/usr/bin/env python3
"""CLI wrapper for phase_worker.py."""

from pathlib import Path
import importlib.util
import sys

MODULE_PATH = Path(__file__).with_name("phase_worker.py")
spec = importlib.util.spec_from_file_location("phase_worker", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)

if __name__ == "__main__":
    raise SystemExit(module.main(sys.argv[1:]))
