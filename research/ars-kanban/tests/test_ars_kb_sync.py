"""Tests for llm-kb integration (Phase 6)."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, "/opt/data/scripts/ars-kanban")
from kb_sync import (
    _concepts_dir,
    git_commit,
    make_topic_slug,
    save_and_push,
    save_phase_to_kb,
)


class TestKbSync(unittest.TestCase):
    """LLM-KB save operations."""

    def test_make_topic_slug_is_safe(self):
        self.assertEqual(make_topic_slug("Bates vs Hjørland"), "bates-vs-hjrland")
        self.assertEqual(make_topic_slug("Simple"), "simple")
        self.assertEqual(make_topic_slug(""), "research")

    def test__concepts_dir_returns_none_for_missing_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            concepts = _concepts_dir(Path(tmp))
            self.assertIsNotNone(concepts)
            self.assertEqual(concepts, Path(tmp) / "concepts")

    def test_save_phase_to_kb_creates_markdown_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            kb_dir = Path(tmp)
            path = save_phase_to_kb(
                topic="Bates vs Hjørland",
                phase=1,
                phase_name="Scoping",
                summary="RQ and methodology defined.",
                artifacts={"rq": "How do Bates and Hjørland differ?"},
                kb_dir=kb_dir,
            )
            self.assertIsNotNone(path)
            self.assertTrue(path.exists())
            content = path.read_text(encoding="utf-8")
            self.assertIn("Phase 1: Scoping — Bates vs Hjørland", content)
            self.assertIn("RQ and methodology defined", content)
            self.assertIn("How do Bates and Hjørland differ?", content)

    def test_save_phase_to_kb_creates_index_and_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            kb_dir = Path(tmp)
            save_phase_to_kb("Bates vs Hjørland", 1, "Scoping", "summary", {}, kb_dir=kb_dir)

            topic_slug = make_topic_slug("Bates vs Hjørland")
            topic_dir = kb_dir / "concepts" / topic_slug
            index_file = topic_dir / "index.md"
            log_file = topic_dir / "log.md"
            self.assertTrue(index_file.exists(), f"index.md missing at {index_file}")
            self.assertTrue(log_file.exists(), f"log.md missing at {log_file}")

    def test_save_idempotent_does_not_duplicate_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            kb_dir = Path(tmp)
            save_phase_to_kb("Bates vs Hjørland", 1, "Scoping", "summary", {}, kb_dir=kb_dir)
            save_phase_to_kb("Bates vs Hjørland", 1, "Scoping", "summary", {}, kb_dir=kb_dir)

            topic_slug = make_topic_slug("Bates vs Hjørland")
            log_file = kb_dir / "concepts" / topic_slug / "log.md"
            content = log_file.read_text(encoding="utf-8")
            # phase-1-scoping.md should appear only once in the log
            self.assertEqual(content.count("phase-1-scoping.md"), 1)

    def test_save_and_push_returns_result_with_kb_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            kb_dir = Path(tmp)
            result = save_and_push(
                "Bates vs Hjørland", 1, "Scoping", "summary", {},
                skip_push=True,
                kb_dir=kb_dir,
            )
            self.assertTrue(result["saved"])
            self.assertIsNotNone(result["kb_path"])
            self.assertEqual(result["topic_slug"], "bates-vs-hjrland")

    def test_git_commit_with_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            kb_dir = Path(tmp)
            # Init a bare git repo
            subprocess.run(["git", "init"], cwd=str(kb_dir), capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(kb_dir), capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=str(kb_dir), capture_output=True)

            save_phase_to_kb("Bates vs Hjørland", 1, "Scoping", "summary", {}, kb_dir=kb_dir)

            result = git_commit("ars-kanban: Phase 1 (Scoping) — Bates vs Hjørland", kb_dir=kb_dir)
            self.assertTrue(result)

    def test_git_commit_no_op_when_no_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            kb_dir = Path(tmp)
            subprocess.run(["git", "init"], cwd=str(kb_dir), capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(kb_dir), capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=str(kb_dir), capture_output=True)

            result = git_commit("no changes", kb_dir=kb_dir)
            self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
