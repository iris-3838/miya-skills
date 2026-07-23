"""ARC Core extended tests — transition semantics and paused Human Gate state.

These tests define expected behavior for:
- curate -> acquisition_pending (requires acquisition_manifest with status='pending')
- curate -> reflection (requires acquisition_manifest with status='resolved', no pending entries)
- acquisition_pending -> reflection (requires acquisition_manifest resolved, no pending entries)
- reflection -> design (requires rq-brief artifact)
- pause_manifest() pure function
"""

import copy
import unittest

from scripts.arc_core import (
    TransitionError,
    pause_manifest,
    transition_manifest,
)


def _make_manifest(status="initialized", phase="initialized", revision=0):
    """Minimal ARC manifest fixture for extended transition tests."""
    return {
        "manifest_version": "1.0",
        "project_id": "test-project",
        "revision": revision,
        "status": status,
        "state": {
            "mode": "full",
            "current_phase": phase,
            "completed_phases": [],
            "resume_context": {"blocking_reason": "", "last_artifact": ""},
            "rq": {"core": "", "sub_questions": [], "status": "draft"},
            "route_ledger": {"completed": [], "planned_next": []},
            "decisions_pending": [],
            "blocked_items": [],
        },
        "events": [
            {
                "type": "init",
                "phase": "initialized",
                "timestamp": "2026-01-01T00:00:00",
            }
        ],
    }


# ── curate -> acquisition_pending ──────────────────────────────────────────


class TestCurateToAcquisitionPending(unittest.TestCase):
    """curate -> acquisition_pending: requires acquisition_manifest with pending status."""

    def test_missing_manifest_raises_error(self):
        """acquisition_manifest 引数なし -> TransitionError。"""
        m = _make_manifest(status="active", phase="curate")
        with self.assertRaises(TransitionError):
            transition_manifest(
                m,
                from_phase="curate",
                to_phase="acquisition_pending",
                approved=True,
            )

    def test_resolved_status_raises_transition_error(self):
        """acquisition_manifest status='resolved' は TransitionError。"""
        m = _make_manifest(status="active", phase="curate")
        with self.assertRaises(TransitionError):
            transition_manifest(
                m,
                from_phase="curate",
                to_phase="acquisition_pending",
                approved=True,
                acquisition_manifest={"status": "resolved", "entries": []},
            )

    def test_valid_sets_paused_and_acquisition_pending(self):
        """正当な acquisition_manifest で遷移後、current_phase=acquisition_pending, status=paused。"""
        m = _make_manifest(status="active", phase="curate")
        result = transition_manifest(
            m,
            from_phase="curate",
            to_phase="acquisition_pending",
            approved=True,
            acquisition_manifest={"status": "pending", "entries": [{"id": "lit-1"}]},
        )
        self.assertEqual(result["state"]["current_phase"], "acquisition_pending")
        self.assertEqual(result["status"], "paused")


# ── curate -> reflection ───────────────────────────────────────────────────


class TestCurateToReflection(unittest.TestCase):
    """curate -> reflection: acquisition_manifest with resolved status, no pending entries."""

    def test_missing_manifest_raises_error(self):
        """acquisition_manifest 引数なし -> TransitionError。"""
        m = _make_manifest(status="active", phase="curate")
        with self.assertRaises(TransitionError):
            transition_manifest(
                m,
                from_phase="curate",
                to_phase="reflection",
                approved=True,
            )

    def test_pending_entries_raises_transition_error(self):
        """acquisition_manifest に pending entry があると TransitionError。"""
        m = _make_manifest(status="active", phase="curate")
        with self.assertRaises(TransitionError):
            transition_manifest(
                m,
                from_phase="curate",
                to_phase="reflection",
                approved=True,
                acquisition_manifest={
                    "status": "resolved",
                    "entries": [{"id": "lit-1", "acquisition_status": "pending"}],
                },
            )

    def test_unknown_entry_status_raises_transition_error(self):
        """未知のacquisition_statusはresolvedとして扱わない。"""
        m = _make_manifest(status="active", phase="curate")
        with self.assertRaises(TransitionError):
            transition_manifest(
                m,
                from_phase="curate",
                to_phase="reflection",
                approved=True,
                acquisition_manifest={
                    "status": "resolved",
                    "entries": [{"id": "lit-1", "acquisition_status": "mystery"}],
                },
            )

    def test_missing_entry_status_raises_transition_error(self):
        """acquisition_status欠落はresolvedとして扱わない。"""
        m = _make_manifest(status="active", phase="curate")
        with self.assertRaises(TransitionError):
            transition_manifest(
                m,
                from_phase="curate",
                to_phase="reflection",
                approved=True,
                acquisition_manifest={
                    "status": "resolved",
                    "entries": [{"id": "lit-1"}],
                },
            )

    def test_mixed_entries_with_pending_raises_transition_error(self):
        """全件 acquired ではなく pending が混ざっていると TransitionError。"""
        m = _make_manifest(status="active", phase="curate")
        with self.assertRaises(TransitionError):
            transition_manifest(
                m,
                from_phase="curate",
                to_phase="reflection",
                approved=True,
                acquisition_manifest={
                    "status": "resolved",
                    "entries": [
                        {"id": "lit-1", "acquisition_status": "acquired"},
                        {"id": "lit-2", "acquisition_status": "pending"},
                    ],
                },
            )

    def test_valid_empty_entries_succeeds(self):
        """entries=[] で遷移成功 -> current_phase=reflection。"""
        m = _make_manifest(status="active", phase="curate")
        result = transition_manifest(
            m,
            from_phase="curate",
            to_phase="reflection",
            approved=True,
            acquisition_manifest={"status": "resolved", "entries": []},
        )
        self.assertEqual(result["state"]["current_phase"], "reflection")

    def test_valid_all_acquired_succeeds(self):
        """全件 acquisition_status='acquired' で遷移成功 -> current_phase=reflection。"""
        m = _make_manifest(status="active", phase="curate")
        result = transition_manifest(
            m,
            from_phase="curate",
            to_phase="reflection",
            approved=True,
            acquisition_manifest={
                "status": "resolved",
                "entries": [
                    {"id": "lit-1", "acquisition_status": "acquired"},
                    {"id": "lit-2", "acquisition_status": "acquired"},
                ],
            },
        )
        self.assertEqual(result["state"]["current_phase"], "reflection")


# ── acquisition_pending -> reflection ──────────────────────────────────────


class TestAcquisitionPendingToReflection(unittest.TestCase):
    """acquisition_pending -> reflection: resolved acquisition_manifest, no pending entries."""

    def test_missing_manifest_raises_error(self):
        """acquisition_manifest 引数なし -> TransitionError。"""
        m = _make_manifest(status="paused", phase="acquisition_pending")
        with self.assertRaises(TransitionError):
            transition_manifest(
                m,
                from_phase="acquisition_pending",
                to_phase="reflection",
                approved=True,
            )

    def test_pending_entries_raises_transition_error(self):
        """acquisition_manifest に pending entries があると TransitionError。"""
        m = _make_manifest(status="paused", phase="acquisition_pending")
        with self.assertRaises(TransitionError):
            transition_manifest(
                m,
                from_phase="acquisition_pending",
                to_phase="reflection",
                approved=True,
                acquisition_manifest={
                    "status": "resolved",
                    "entries": [{"id": "lit-1", "acquisition_status": "pending"}],
                },
            )

    def test_resolved_status_mismatch_raises_transition_error(self):
        """acquisition_manifest status='pending' (≠'resolved') は TransitionError。"""
        m = _make_manifest(status="paused", phase="acquisition_pending")
        with self.assertRaises(TransitionError):
            transition_manifest(
                m,
                from_phase="acquisition_pending",
                to_phase="reflection",
                approved=True,
                acquisition_manifest={"status": "pending", "entries": []},
            )

    def test_valid_resolved_empty_succeeds(self):
        """resolved かつ entries=[] で遷移成功。"""
        m = _make_manifest(status="paused", phase="acquisition_pending")
        result = transition_manifest(
            m,
            from_phase="acquisition_pending",
            to_phase="reflection",
            approved=True,
            acquisition_manifest={"status": "resolved", "entries": []},
        )
        self.assertEqual(result["state"]["current_phase"], "reflection")

    def test_valid_all_acquired_succeeds(self):
        """全件 acquired で遷移成功。"""
        m = _make_manifest(status="paused", phase="acquisition_pending")
        result = transition_manifest(
            m,
            from_phase="acquisition_pending",
            to_phase="reflection",
            approved=True,
            acquisition_manifest={
                "status": "resolved",
                "entries": [{"id": "lit-1", "acquisition_status": "acquired"}],
            },
        )
        self.assertEqual(result["state"]["current_phase"], "reflection")


# ── reflection -> design ───────────────────────────────────────────────────


class TestReflectionToDesign(unittest.TestCase):
    """reflection -> design: rq-brief artifact required."""

    def test_absent_artifact_raises_transition_error(self):
        """rq-brief artifact なしは TransitionError。"""
        m = _make_manifest(status="active", phase="reflection")
        with self.assertRaises(TransitionError):
            transition_manifest(
                m,
                from_phase="reflection",
                to_phase="design",
                approved=True,
                artifacts=[],
            )

    def test_artifact_suffix_collision_is_rejected(self):
        """canonical pathの前に文字列を足しただけのartifactは拒否する。"""
        m = _make_manifest(status="active", phase="reflection")
        with self.assertRaises(TransitionError):
            transition_manifest(
                m,
                from_phase="reflection",
                to_phase="design",
                approved=True,
                artifacts=["rogueartifacts/design/rq-brief.md"],
            )

    def test_windows_style_artifact_path_is_normalized(self):
        """Windows形式のseparatorでもartifact suffix判定が壊れない。"""
        m = _make_manifest(status="active", phase="reflection")
        result = transition_manifest(
            m,
            from_phase="reflection",
            to_phase="design",
            approved=True,
            artifacts=[r"artifacts\design\rq-brief.md"],
        )
        self.assertEqual(result["state"]["current_phase"], "design")

    def test_valid_with_rq_brief_succeeds(self):
        """artifacts/design/rq-brief.md 存在で current_phase=design に遷移。"""
        m = _make_manifest(status="active", phase="reflection")
        result = transition_manifest(
            m,
            from_phase="reflection",
            to_phase="design",
            approved=True,
            artifacts=["artifacts/design/rq-brief.md"],
        )
        self.assertEqual(result["state"]["current_phase"], "design")


# ── pause_manifest ─────────────────────────────────────────────────────────


class TestPauseManifest(unittest.TestCase):
    """pause_manifest: return paused deep copy without mutating input."""

    def test_returns_copy_with_paused_status(self):
        """戻り値の status が 'paused'。"""
        m = _make_manifest(status="active", phase="curate")
        result = pause_manifest(m, reason="awaiting provider results")
        self.assertEqual(result["status"], "paused")

    def test_sets_blocking_reason(self):
        """state.resume_context.blocking_reason が reason に設定される。"""
        m = _make_manifest(status="active", phase="curate")
        result = pause_manifest(m, reason="awaiting provider results")
        self.assertEqual(
            result["state"]["resume_context"]["blocking_reason"],
            "awaiting provider results",
        )

    def test_increments_revision(self):
        """revision が +1 される。"""
        m = _make_manifest(status="active", phase="curate", revision=3)
        result = pause_manifest(m, reason="paused for review")
        self.assertEqual(result["revision"], 4)

    def test_does_not_mutate_input(self):
        """引数 manifest は変更されない（deep immutable semantics）。"""
        m = _make_manifest(status="active", phase="curate")
        original = copy.deepcopy(m)
        pause_manifest(m, reason="some reason")
        self.assertEqual(m, original)

    def test_does_not_mutate_nested_state(self):
        """state や events などのネスト構造も変更されない。"""
        m = _make_manifest(status="active", phase="curate")
        original_state = copy.deepcopy(m["state"])
        original_events = copy.deepcopy(m["events"])
        pause_manifest(m, reason="some reason")
        self.assertEqual(m["state"], original_state)
        self.assertEqual(m["events"], original_events)

    def test_with_empty_blocking_reason(self):
        """reason='' でも paused + blocking_reason='' になる。"""
        m = _make_manifest(status="active", phase="curate")
        result = pause_manifest(m, reason="")
        self.assertEqual(result["status"], "paused")
        self.assertEqual(result["state"]["resume_context"]["blocking_reason"], "")

    def test_without_approval_not_required(self):
        """pause_manifest は Human Gate 承認不要（ステータス変更のみ）。"""
        m = _make_manifest(status="active", phase="plan")
        result = pause_manifest(m, reason="need more time")
        self.assertEqual(result["status"], "paused")
        self.assertEqual(result["state"]["current_phase"], "plan")


if __name__ == "__main__":
    unittest.main()
