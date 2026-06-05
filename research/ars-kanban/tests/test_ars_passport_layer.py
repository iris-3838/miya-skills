"""Tests for the Material Passport compatibility layer (Phase 5)."""

import json
import tempfile
import unittest
from pathlib import Path

# Import passport_layer directly since we need to test it
import sys
sys.path.insert(0, "/opt/data/scripts/ars-kanban")
import passport_layer as pp  # noqa: E402


class TestPassportSchema9Validation(unittest.TestCase):
    """Schema 9 Material Passport required fields validation."""

    def test_valid_passport_passes_validation(self):
        passport = {
            "origin_skill": "deep-research",
            "origin_mode": "full",
            "origin_date": "2026-06-05T00:00:00Z",
            "verification_status": "UNVERIFIED",
            "version_label": "phase1-v0",
            "repro_lock": None,
        }
        errors = pp.validate_passport(passport, strict=False)
        self.assertEqual(errors, [])

    def test_missing_required_field_detected(self):
        passport = {
            "origin_skill": "deep-research",
            "origin_mode": "full",
            # missing origin_date
            "verification_status": "UNVERIFIED",
            "version_label": "phase1-v0",
        }
        errors = pp.validate_passport(passport, strict=False)
        self.assertTrue(any("origin_date" in e for e in errors))

    def test_invalid_verification_status_rejected(self):
        passport = {
            "origin_skill": "deep-research",
            "origin_mode": "full",
            "origin_date": "2026-06-05T00:00:00Z",
            "verification_status": "INVALID_STATUS",
            "version_label": "phase1-v0",
        }
        errors = pp.validate_passport(passport, strict=False)
        self.assertTrue(any("INVALID_STATUS" in e for e in errors))

    def test_strict_mode_raises_on_error(self):
        passport = {"origin_skill": "deep-research"}
        with self.assertRaises(pp.PassportValidationError):
            pp.validate_passport(passport, strict=True)

    def test_all_valid_statuses_accepted(self):
        for status in pp.VALID_STATUSES:
            passport = {
                "origin_skill": "deep-research",
                "origin_mode": "full",
                "origin_date": "2026-06-05T00:00:00Z",
                "verification_status": status,
                "version_label": "v1",
            }
            errors = pp.validate_passport(passport, strict=False)
            self.assertEqual(errors, [])


class TestPassportHashAndUpgrade(unittest.TestCase):
    """Content hash computation and passport evolution."""

    def test_content_hash_is_deterministic(self):
        data = {"phase": 1, "mode": "full"}
        h1 = pp.compute_content_hash(data)
        h2 = pp.compute_content_hash(data)
        self.assertEqual(h1, h2)

    def test_content_hash_changes_on_content_difference(self):
        h1 = pp.compute_content_hash({"phase": 1})
        h2 = pp.compute_content_hash({"phase": 2})
        self.assertNotEqual(h1, h2)

    def test_upgrade_passport_sets_required_fields(self):
        passport = {
            "origin_skill": "deep-research",
            "origin_mode": "full",
            "origin_date": "2026-06-05T00:00:00Z",
            "verification_status": "UNVERIFIED",
            "version_label": "phase1-v0",
        }
        upgraded = pp.upgrade_passport(
            passport,
            new_status="VERIFIED",
            new_version_suffix="investigation-v0",
            downstream_dependency="scoping-v0",
        )

        self.assertEqual(upgraded["verification_status"], "VERIFIED")
        self.assertEqual(upgraded["version_label"], "investigation-v0")
        self.assertIn("scoping-v0", upgraded.get("upstream_dependencies", []))
        self.assertIn("integrity_pass_date", upgraded)
        self.assertEqual(upgraded["repro_lock"], None)
        self.assertEqual(upgraded["reset_boundary"], [])
        # content_hash is NOT set by upgrade_passport — it is the caller's
        # responsibility to compute it from the actual execution result.

    def test_upgrade_preserves_upstream_dependencies(self):
        passport = {
            "origin_skill": "deep-research",
            "origin_mode": "full",
            "origin_date": "2026-06-05T00:00:00Z",
            "verification_status": "UNVERIFIED",
            "version_label": "phase1-v0",
            "upstream_dependencies": ["topic-analysis-v0"],
        }
        upgraded = pp.upgrade_passport(
            passport,
            downstream_dependency="topic-analysis-v0",
        )
        deps = upgraded["upstream_dependencies"]
        self.assertEqual(len(deps), 1)  # not duplicated

    def test_version_label_auto_increment(self):
        passport = {
            "origin_skill": "deep-research",
            "origin_mode": "full",
            "origin_date": "2026-06-05T00:00:00Z",
            "verification_status": "UNVERIFIED",
            "version_label": "phase1-v0",
        }
        upgraded = pp.upgrade_passport(passport)
        self.assertEqual(upgraded["version_label"], "phase1-v1")


class TestPassportChain(unittest.TestCase):
    """Multi-phase passport chain verification."""

    def _make_passport(self, phase, label, deps=None):
        p = {
            "origin_skill": "deep-research",
            "origin_mode": "full",
            "origin_date": "2026-06-05T00:00:00Z",
            "verification_status": "UNVERIFIED",
            "version_label": label,
            "repro_lock": None,
        }
        if deps:
            p["upstream_dependencies"] = deps
        return p

    def test_valid_chain_passes(self):
        chain = [
            self._make_passport(1, "scoping-v0"),
            self._make_passport(2, "investigation-v0", deps=["scoping-v0"]),
            self._make_passport(3, "analysis-v0", deps=["investigation-v0"]),
        ]
        errors = pp.verify_passport_chain(chain)
        self.assertEqual(errors, [])

    def test_missing_dependency_detected(self):
        chain = [
            self._make_passport(1, "scoping-v0"),
            self._make_passport(2, "investigation-v0", deps=[]),
        ]
        errors = pp.verify_passport_chain(chain)
        self.assertTrue(any("scoping-v0" in e for e in errors))


class TestMergePhasePassport(unittest.TestCase):
    """Phase-to-phase passport merging."""

    def test_merge_with_upstream_works(self):
        upstream = {
            "origin_skill": "deep-research",
            "origin_mode": "full",
            "origin_date": "2026-06-05T00:00:00Z",
            "verification_status": "VERIFIED",
            "version_label": "scoping-v0",
            "upstream_dependencies": [],
        }
        phase_body = {
            "phase": 2,
            "phase_name": "Investigation",
            "material_passport": {
                "origin_skill": "deep-research",
                "origin_mode": "full",
                "version_label": "investigation-v0",
            },
        }
        merged = pp.merge_phase_passport(upstream, phase_body)
        mp = merged["material_passport"]
        self.assertEqual(mp["version_label"], "investigation-v0")
        self.assertEqual(mp["verification_status"], "UNVERIFIED")
        self.assertIn("scoping-v0", mp.get("upstream_dependencies", []))


class TestPhaseVersionLabels(unittest.TestCase):
    """PHASE_VERSION_LABELS mapping."""

    def test_all_six_phases_mapped(self):
        expected_names = {
            1: "scoping",
            2: "investigation",
            3: "analysis",
            4: "composition",
            5: "review",
            6: "revision",
        }
        for phase in range(1, 7):
            self.assertIn(phase, pp.PHASE_VERSION_LABELS)
            label = pp.PHASE_VERSION_LABELS[phase]
            self.assertIn(expected_names[phase], label)
            self.assertIn("-v0", label)


if __name__ == "__main__":
    unittest.main()
