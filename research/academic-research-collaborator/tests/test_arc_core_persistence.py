"""Tests for ARC project initialization and concurrent manifest writes."""

from __future__ import annotations

import concurrent.futures
import copy
import os
import tempfile
import unittest
from pathlib import Path

from scripts.arc_core import (
    PathPolicyError,
    RevisionConflict,
    create_initial_manifest,
    initialize_project,
    load_manifest,
    normalize_project,
    write_manifest_atomic,
)


class TestInitializeProject(unittest.TestCase):
    def test_initializes_scaffold_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "projects"
            project_path = root / "new-project"
            spec = normalize_project(
                "new-project", project_path, "quick-scan", root
            )
            manifest = initialize_project(spec)
            self.assertTrue(project_path.is_dir())
            self.assertTrue((project_path / "artifacts").is_dir())
            self.assertEqual(manifest["revision"], 0)
            self.assertEqual(
                load_manifest(project_path / "research-manifest.yaml")["project_id"],
                "new-project",
            )

    def test_manifest_override_cannot_escape_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "projects"
            project_path = root / "new-project"
            spec = normalize_project(
                "new-project", project_path, "quick-scan", root
            )
            outside_manifest = Path(tmp) / "outside-manifest.yaml"
            with self.assertRaises(PathPolicyError):
                initialize_project(spec, manifest_path=outside_manifest)
            self.assertFalse(project_path.exists())
            self.assertFalse(outside_manifest.exists())

    def test_refuses_existing_non_arc_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "projects"
            project_path = root / "existing-project"
            project_path.mkdir(parents=True)
            (project_path / "unrelated.txt").write_text("do not overwrite")
            with self.assertRaises(PathPolicyError):
                normalize_project(
                    "existing-project", project_path, "full", root
                )
            self.assertEqual(
                (project_path / "unrelated.txt").read_text(), "do not overwrite"
            )

    def test_refuses_existing_arc_manifest_without_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "projects"
            project_path = root / "existing-project"
            spec = normalize_project(
                "existing-project", project_path, "full", root
            )
            initialize_project(spec)
            with self.assertRaises(PathPolicyError):
                initialize_project(spec)


class TestConcurrentManifestWrites(unittest.TestCase):
    def test_lock_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "projects"
            spec = normalize_project("lock-project", root / "lock-project", "full", root)
            manifest_path = spec.resolved_path / "research-manifest.yaml"
            initial = create_initial_manifest(spec)
            write_manifest_atomic(manifest_path, initial)
            lock_path = manifest_path.with_name(manifest_path.name + ".lock")
            lock_target = Path(tmp) / "unrelated.lock"
            lock_target.write_text("not the manifest lock")
            lock_path.unlink()
            try:
                os.symlink(lock_target, lock_path)
            except (OSError, NotImplementedError, AttributeError):
                self.skipTest("symlink creation not available on this system")
            candidate = copy.deepcopy(initial)
            candidate["revision"] = 1
            candidate["status"] = "active"
            with self.assertRaises(PathPolicyError):
                write_manifest_atomic(
                    manifest_path,
                    candidate,
                    expected_revision=0,
                )
            self.assertEqual(load_manifest(manifest_path)["revision"], 0)

    def test_one_of_two_same_revision_writers_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "projects"
            spec = normalize_project("race-project", root / "race-project", "full", root)
            manifest_path = spec.resolved_path / "research-manifest.yaml"
            initial = create_initial_manifest(spec)
            write_manifest_atomic(manifest_path, initial)
            candidate = copy.deepcopy(initial)
            candidate["revision"] = 1
            candidate["status"] = "active"

            def attempt():
                try:
                    return ("ok", write_manifest_atomic(
                        manifest_path, copy.deepcopy(candidate), expected_revision=0
                    ))
                except RevisionConflict:
                    return ("conflict", None)

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                outcomes = list(pool.map(lambda _unused: attempt(), range(2)))

            self.assertEqual([kind for kind, _ in outcomes].count("ok"), 1)
            self.assertEqual([kind for kind, _ in outcomes].count("conflict"), 1)
            self.assertEqual(load_manifest(manifest_path)["revision"], 1)


if __name__ == "__main__":
    unittest.main()
