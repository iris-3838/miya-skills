"""ARC Core tests — deterministic unit tests for the arc_core module.

These tests define the expected behavior of the ARC state controller.  The
production implementation is expected to keep this suite GREEN.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# The module under test is implemented; this suite is the GREEN regression boundary.
from scripts import arc_core
from scripts.arc_core import (
    ArcError,
    DependencyError,
    PathPolicyError,
    ManifestError,
    TransitionError,
    RevisionConflict,
    ProjectSpec,
    normalize_project,
    create_initial_manifest,
    transition_manifest,
    validate_candidate,
    validate_provider_status,
    write_manifest_atomic,
    load_manifest,
)


class TestYamlDependency(unittest.TestCase):
    def test_dependency_error_preserves_import_cause(self):
        import_error = ImportError("simulated missing PyYAML")
        with patch.object(arc_core, "yaml", None), patch.object(
            arc_core, "_YAML_IMPORT_ERROR", import_error
        ):
            with self.assertRaises(DependencyError) as context:
                arc_core._require_yaml()
        self.assertIs(context.exception.__cause__, import_error)


class TestNormalizeProject(unittest.TestCase):
    """normalize_project: project root validation and ProjectSpec construction."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory(prefix="arc_normalize_")
        self.root = Path(self.tmpdir.name) / "projects"
        self.root.mkdir()

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_projects_root_required(self):
        """projects_root=None で TypeError または ArcError を上げる。"""
        with self.assertRaises((TypeError, ArcError)):
            normalize_project(
                project_id="test-project",
                path=str(self.root / "test-project"),
                mode="full",
                projects_root=None,
            )

    def test_relative_path_rejected(self):
        """相対pathは PathPolicyError。"""
        with self.assertRaises(PathPolicyError):
            normalize_project(
                project_id="test-project",
                path="relative/path/test-project",
                mode="full",
                projects_root=self.root,
            )

    def test_path_outside_root_rejected(self):
        """projects_root 配下にない絶対pathは PathPolicyError。"""
        with self.assertRaises(PathPolicyError):
            normalize_project(
                project_id="test-project",
                path=str(self.root.parent / "outside" / "test-project"),
                mode="full",
                projects_root=self.root,
            )

    def test_path_traversal_rejected(self):
        """projects_root 内だが .. でroot外に出ようとするpathは PathPolicyError。"""
        with self.assertRaises(PathPolicyError):
            normalize_project(
                project_id="test-project",
                path=str(self.root / ".." / "outside" / "test-project"),
                mode="full",
                projects_root=self.root,
            )

    def test_project_id_path_basename_mismatch_rejected(self):
        """project_id と path 末尾のディレクトリ名が不一致なら PathPolicyError。"""
        with self.assertRaises(PathPolicyError):
            normalize_project(
                project_id="project-alpha",
                path=str(self.root / "project-beta"),
                mode="full",
                projects_root=self.root,
            )

    def test_invalid_mode_rejected(self):
        """許可されていない mode は ArcError。"""
        with self.assertRaises(ArcError):
            normalize_project(
                project_id="test-project",
                path=str(self.root / "test-project"),
                mode="invalid-mode",
                projects_root=self.root,
            )

    def test_symlink_escape_rejected(self):
        """symlink が projects_root 外を指している場合、realpath 解決で PathPolicyError。"""
        import shutil
        root_dir = tempfile.mkdtemp(prefix="arc_test_root_")
        outside_dir = tempfile.mkdtemp(prefix="arc_test_outside_")
        try:
            symlink_path = os.path.join(root_dir, "test-project")
            try:
                os.symlink(outside_dir, symlink_path)
            except (OSError, NotImplementedError, AttributeError):
                raise unittest.SkipTest(
                    "symlink creation not available on this system"
                )
            with self.assertRaises(PathPolicyError):
                normalize_project(
                    project_id="test-project",
                    path=symlink_path,
                    mode="full",
                    projects_root=root_dir,
                )
        finally:
            shutil.rmtree(root_dir, ignore_errors=True)
            shutil.rmtree(outside_dir, ignore_errors=True)

    def test_valid_normalized_project_returns_project_spec(self):
        """全ての条件を満たす入力は ProjectSpec を返す。"""
        spec = normalize_project(
            project_id="test-project",
            path=str(self.root / "test-project"),
            mode="full",
            projects_root=self.root,
        )
        self.assertIsInstance(spec, ProjectSpec)
        self.assertEqual(spec.project_id, "test-project")
        self.assertEqual(spec.mode, "full")
        self.assertTrue(spec.resolved_path.is_relative_to(self.root))

    def test_unicode_project_id_is_allowed(self):
        """日本語を含む単一directory componentのproject_idは許可する。"""
        spec = normalize_project(
            project_id="BatesとHjørlandの比較",
            path=str(self.root / "BatesとHjørlandの比較"),
            mode="full",
            projects_root=self.root,
        )
        self.assertEqual(spec.project_id, "BatesとHjørlandの比較")

    def test_project_id_display_format_controls_are_rejected(self):
        """bidi/zero-width等の不可視format文字をproject IDに許可しない。"""
        for project_id in ("safe\u200bproject", "safe\u202eproject"):
            with self.subTest(project_id=project_id):
                with self.assertRaises(PathPolicyError):
                    normalize_project(
                        project_id=project_id,
                        path=str(self.root / project_id),
                        mode="full",
                        projects_root=self.root,
                    )

    def test_project_id_path_separator_is_rejected(self):
        """project_idにpath separatorを含めてroot外へ出る指定は拒否する。"""
        with self.assertRaises(PathPolicyError):
            normalize_project(
                project_id="research/escape",
                path=str(self.root / "escape"),
                mode="full",
                projects_root=self.root,
            )


class TestCreateInitialManifest(unittest.TestCase):
    """create_initial_manifest: 新規プロジェクトの初期manifest生成。"""

    def setUp(self):
        self.spec = ProjectSpec(
            project_id="test-project",
            resolved_path=Path("/tmp/arc-test/test-project"),
            mode="full",
        )

    def test_status_initialized(self):
        """status フィールドが 'initialized'。"""
        manifest = create_initial_manifest(self.spec)
        self.assertEqual(manifest["status"], "initialized")

    def test_current_phase_initialized(self):
        """state.current_phase が 'initialized'。"""
        manifest = create_initial_manifest(self.spec)
        self.assertEqual(manifest["state"]["current_phase"], "initialized")

    def test_revision_zero(self):
        """revision が 0。"""
        manifest = create_initial_manifest(self.spec)
        self.assertEqual(manifest["revision"], 0)

    def test_rq_empty(self):
        """state.rq が空（core=""、sub_questions=[]）。"""
        manifest = create_initial_manifest(self.spec)
        rq = manifest["state"].get("rq", {})
        self.assertEqual(rq.get("core", ""), "")
        self.assertEqual(rq.get("sub_questions", []), [])

    def test_route_ledger_empty(self):
        """state.route_ledger が空で適切な構造を持つ。"""
        manifest = create_initial_manifest(self.spec)
        ledger = manifest["state"].get("route_ledger", {})
        self.assertEqual(ledger.get("completed", []), [])
        self.assertEqual(ledger.get("planned_next", []), [])

    def test_decisions_pending_empty(self):
        """state.decisions_pending が空リスト。"""
        manifest = create_initial_manifest(self.spec)
        self.assertEqual(manifest["state"].get("decisions_pending", []), [])

    def test_blocked_items_empty(self):
        """state.blocked_items が空リスト。"""
        manifest = create_initial_manifest(self.spec)
        self.assertEqual(manifest["state"].get("blocked_items", []), [])

    def test_init_event_present(self):
        """events に1件の init event が含まれている。"""
        manifest = create_initial_manifest(self.spec)
        events = manifest.get("events", [])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["type"], "init")
        self.assertEqual(events[0]["phase"], "initialized")


class TestTransitionManifest(unittest.TestCase):
    """transition_manifest: phase 間の状態遷移制御。"""

    def _make_manifest(self, status="initialized", phase="initialized", revision=0):
        return {
            "manifest_version": "1.0",
            "project_id": "test-project",
            "revision": revision,
            "status": status,
            "state": {
                "mode": "full",
                "current_phase": phase,
                "completed_phases": [],
                "rq": {"core": "", "sub_questions": [], "status": "draft"},
                "route_ledger": {"completed": [], "planned_next": []},
                "decisions_pending": [],
                "blocked_items": [],
            },
            "events": [{"type": "init", "phase": "initialized", "timestamp": "2026-01-01T00:00:00"}],
        }

    def test_missing_transition_table_entry_is_transition_error(self):
        """phase table driftでもraw KeyErrorを外へ漏らさない。"""
        manifest = self._make_manifest(status="active", phase="design")
        transition_table = dict(arc_core._ALLOWED_TRANSITIONS)
        transition_table.pop("design")
        with patch.object(arc_core, "_ALLOWED_TRANSITIONS", transition_table):
            with self.assertRaises(TransitionError):
                transition_manifest(
                    manifest,
                    from_phase="design",
                    to_phase="plan",
                    approved=True,
                    artifacts=["artifacts/design/rq-brief.md"],
                )

    # --- initialized → design ---

    def test_initialized_to_design_approved(self):
        """initialized → design は HG① 承認済みで成功。"""
        manifest = self._make_manifest()
        result = transition_manifest(
            manifest, from_phase="initialized", to_phase="design",
            approved=True,
        )
        self.assertEqual(result["state"]["current_phase"], "design")

    def test_initialized_to_design_not_approved_rejected(self):
        """initialized → design は未承認で TransitionError。"""
        manifest = self._make_manifest()
        with self.assertRaises(TransitionError):
            transition_manifest(
                manifest, from_phase="initialized", to_phase="design",
                approved=False,
            )

    # --- initialized → plan (rejected) ---

    def test_initialized_to_plan_rejected(self):
        """initialized → plan は design を経由していないため TransitionError。"""
        manifest = self._make_manifest()
        with self.assertRaises(TransitionError):
            transition_manifest(
                manifest, from_phase="initialized", to_phase="plan",
                approved=True,
            )

    # --- design → plan ---

    def test_design_to_plan_with_approval_and_artifact(self):
        """design → plan は HG① 承認 + rq-brief artifact 存在で成功。"""
        manifest = self._make_manifest(status="active", phase="design")
        result = transition_manifest(
            manifest, from_phase="design", to_phase="plan",
            approved=True,
            artifacts=["artifacts/design/rq-brief.md"],
        )
        self.assertEqual(result["state"]["current_phase"], "plan")

    def test_design_to_plan_without_artifact_rejected(self):
        """design → plan は rq-brief artifact なしで TransitionError。"""
        manifest = self._make_manifest(status="active", phase="design")
        with self.assertRaises(TransitionError):
            transition_manifest(
                manifest, from_phase="design", to_phase="plan",
                approved=True,
                artifacts=[],
            )

    # --- plan → curate ---

    def test_plan_to_curate_with_approval_and_artifact(self):
        """plan → curate は HG② 承認 + search-strategy artifact 存在で成功。"""
        manifest = self._make_manifest(status="active", phase="plan")
        result = transition_manifest(
            manifest, from_phase="plan", to_phase="curate",
            approved=True,
            artifacts=["artifacts/plan/search-strategy.yaml"],
        )
        self.assertEqual(result["state"]["current_phase"], "curate")

    def test_plan_to_curate_without_artifact_rejected(self):
        """plan → curate は search-strategy artifact なしで TransitionError。"""
        manifest = self._make_manifest(status="active", phase="plan")
        with self.assertRaises(TransitionError):
            transition_manifest(
                manifest, from_phase="plan", to_phase="curate",
                approved=True,
                artifacts=[],
            )

    def test_plan_to_curate_without_approval_rejected(self):
        """plan → curate は HG② 未承認で TransitionError。"""
        manifest = self._make_manifest(status="active", phase="plan")
        with self.assertRaises(TransitionError):
            transition_manifest(
                manifest, from_phase="plan", to_phase="curate",
                approved=False,
                artifacts=["artifacts/plan/search-strategy.yaml"],
            )


class TestValidateCandidate(unittest.TestCase):
    """validate_candidate: 文献候補の evidence scope 検証。"""

    def test_metadata_only_accepted(self):
        """metadata_only は有効な evidence scope。"""
        candidate = {"id": "item-1", "evidence_scope": "metadata_only"}
        result = validate_candidate(candidate)
        self.assertTrue(result["valid"])

    def test_abstract_only_accepted(self):
        """abstract_only は有効な evidence scope。"""
        candidate = {"id": "item-2", "evidence_scope": "abstract_only"}
        result = validate_candidate(candidate)
        self.assertTrue(result["valid"])

    def test_fulltext_ready_accepted(self):
        """fulltext_ready は human_acquired=True と共に有効。"""
        candidate = {
            "id": "item-3",
            "evidence_scope": "fulltext_ready",
            "human_acquired": True,
        }
        result = validate_candidate(candidate)
        self.assertTrue(result["valid"])

    def test_acquisition_required_accepted(self):
        """acquisition_required は有効な evidence scope。"""
        candidate = {"id": "item-4", "evidence_scope": "acquisition_required"}
        result = validate_candidate(candidate)
        self.assertTrue(result["valid"])

    def test_unavailable_accepted(self):
        """unavailable は有効な evidence scope。"""
        candidate = {"id": "item-5", "evidence_scope": "unavailable"}
        result = validate_candidate(candidate)
        self.assertTrue(result["valid"])

    def test_unknown_scope_rejected(self):
        """認識不能な evidence_scope は拒否。"""
        candidate = {"id": "item-6", "evidence_scope": "unknown_scope"}
        result = validate_candidate(candidate)
        self.assertFalse(result["valid"])

    def test_fulltext_ready_without_human_acquired_rejected(self):
        """fulltext_ready は human_acquired=True なしで拒否。"""
        candidate = {
            "id": "item-7",
            "evidence_scope": "fulltext_ready",
            # human_acquired なし
        }
        result = validate_candidate(candidate)
        self.assertFalse(result["valid"])

    def test_fulltext_ready_with_human_acquired_false_rejected(self):
        """fulltext_ready は human_acquired=False で拒否。"""
        candidate = {
            "id": "item-8",
            "evidence_scope": "fulltext_ready",
            "human_acquired": False,
        }
        result = validate_candidate(candidate)
        self.assertFalse(result["valid"])


class TestValidateProviderStatus(unittest.TestCase):
    """validate_provider_status: provider 実行結果 status の検証。"""

    def test_success_accepted(self):
        """success は有効。"""
        result = validate_provider_status("success")
        self.assertTrue(result["valid"])

    def test_zero_hits_accepted(self):
        """zero_hits は有効。"""
        result = validate_provider_status("zero_hits")
        self.assertTrue(result["valid"])

    def test_unavailable_accepted(self):
        """unavailable は有効。"""
        result = validate_provider_status("unavailable")
        self.assertTrue(result["valid"])

    def test_transient_error_accepted(self):
        """transient_error は有効。"""
        result = validate_provider_status("transient_error")
        self.assertTrue(result["valid"])

    def test_rate_limited_accepted(self):
        """rate_limited は有効。"""
        result = validate_provider_status("rate_limited")
        self.assertTrue(result["valid"])

    def test_error_rejected(self):
        """error は無効。"""
        result = validate_provider_status("error")
        self.assertFalse(result["valid"])

    def test_unknown_status_rejected(self):
        """unknown は無効。"""
        result = validate_provider_status("unknown")
        self.assertFalse(result["valid"])

    def test_random_string_rejected(self):
        """ランダム文字列は無効。"""
        result = validate_provider_status("this_is_not_a_valid_status")
        self.assertFalse(result["valid"])


class TestWriteManifestAtomicAndLoadManifest(unittest.TestCase):
    """write_manifest_atomic / load_manifest: atomic 書き込みと整合性。"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="arc_test_")
        self.manifest_path = os.path.join(self.tmpdir, "research-manifest.yaml")
        self.initial_data = {
            "manifest_version": "1.0",
            "project_id": "test-project",
            "revision": 0,
            "status": "initialized",
            "state": {"current_phase": "initialized", "mode": "full"},
            "events": [{"type": "init", "phase": "initialized"}],
        }
        # Write initial manifest
        write_manifest_atomic(self.manifest_path, self.initial_data, expected_revision=None)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_revision_conflict_raises(self):
        """expected_revision 不一致で RevisionConflict。"""
        with self.assertRaises(RevisionConflict):
            updated = dict(self.initial_data, revision=1, status="active")
            write_manifest_atomic(
                self.manifest_path, updated,
                expected_revision=42,  # 実際の revision=0 と不一致
            )

    def test_original_manifest_unchanged_on_conflict(self):
        """RevisionConflict 発生後も既存manifestは変更されない。"""
        with self.assertRaises(RevisionConflict):
            updated = dict(self.initial_data, revision=1, status="active")
            write_manifest_atomic(
                self.manifest_path, updated,
                expected_revision=42,
            )
        # 再読み込みして元の内容を確認
        loaded = load_manifest(self.manifest_path)
        self.assertEqual(loaded["revision"], 0)
        self.assertEqual(loaded["status"], "initialized")

    def test_revision_must_increment_exactly_one(self):
        """candidate revisionがcurrent+1でなければ拒否する。"""
        updated = dict(self.initial_data, revision=7, status="active")
        with self.assertRaises(ManifestError):
            write_manifest_atomic(
                self.manifest_path,
                updated,
                expected_revision=0,
            )
        loaded = load_manifest(self.manifest_path)
        self.assertEqual(loaded["revision"], 0)

    def test_serialization_failure_cleans_temp_and_preserves_original(self):
        """safe_dump失敗時もtempを残さず、既存manifestを保持する。"""
        updated = dict(self.initial_data, revision=1, status="active")
        yaml_error = arc_core.yaml.YAMLError("simulated serialization failure")
        with patch.object(arc_core.yaml, "safe_dump", side_effect=yaml_error):
            with self.assertRaises(ManifestError):
                write_manifest_atomic(
                    self.manifest_path,
                    updated,
                    expected_revision=0,
                )
        self.assertEqual(load_manifest(self.manifest_path)["revision"], 0)
        self.assertEqual(
            list(Path(self.tmpdir).glob("research-manifest.yaml.tmp.*")), []
        )

    def test_successful_write_increments_revision(self):
        """正常更新で revision が +1 される。"""
        updated = dict(self.initial_data, revision=1, status="active")
        write_manifest_atomic(
            self.manifest_path, updated,
            expected_revision=0,
        )
        loaded = load_manifest(self.manifest_path)
        self.assertEqual(loaded["revision"], 1)
        self.assertEqual(loaded["status"], "active")

    def test_no_temp_file_remains_after_successful_write(self):
        """正常書き込み後に .tmp ファイルが存在しない。"""
        updated = dict(self.initial_data, revision=1, status="active")
        write_manifest_atomic(
            self.manifest_path, updated,
            expected_revision=0,
        )
        tmp_files = [f for f in os.listdir(self.tmpdir) if ".tmp" in f]
        self.assertEqual(tmp_files, [])

    def test_broken_yaml_raises_manifest_error(self):
        """破損YAMLは ManifestError。"""
        # ファイルを破損YAMLで上書き
        with open(self.manifest_path, "w") as f:
            f.write("{invalid: yaml: broken: [}\n")
        with self.assertRaises(ManifestError):
            load_manifest(self.manifest_path)


if __name__ == "__main__":
    unittest.main()
