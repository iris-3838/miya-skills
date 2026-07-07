import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path("/opt/data/workspace/miya-skills/research/ars-kanban/scripts/integrity_check.py")


def load_module():
    spec = importlib.util.spec_from_file_location("integrity_check", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class TestIntegrityCheck(unittest.TestCase):
    def test_failure_modes_are_seven_and_in_canonical_order(self):
        ic = load_module()
        self.assertEqual(
            ic.FAILURE_MODES,
            ["M1", "M2", "M3", "M4", "M5", "M6", "M7"],
        )

    def test_descriptions_cover_all_modes(self):
        ic = load_module()
        for mode in ic.FAILURE_MODES:
            self.assertIn(mode, ic.FAILURE_MODE_DESCRIPTIONS)
            self.assertIsInstance(ic.FAILURE_MODE_DESCRIPTIONS[mode], str)
            self.assertTrue(len(ic.FAILURE_MODE_DESCRIPTIONS[mode]) > 0)

    def test_pre_review_samples_thirty_percent_min_ten(self):
        ic = load_module()
        claims = [{"text": f"claim {i}"} for i in range(25)]
        report = ic.run_integrity_check("pre_review", claims)
        # 30% of 25 = 7.5, so max(10, 7) = 10, capped at total 25
        self.assertEqual(report.claim_sample_count, 10)
        self.assertEqual(report.claim_total, 25)
        self.assertEqual(report.mode, "pre_review")

    def test_pre_review_caps_at_total(self):
        ic = load_module()
        claims = [{"text": "only claim"}]
        report = ic.run_integrity_check("pre_review", claims)
        self.assertEqual(report.claim_sample_count, 1)

    def test_final_check_verifies_all_claims(self):
        ic = load_module()
        claims = [{"text": f"claim {i}"} for i in range(42)]
        report = ic.run_integrity_check("final_check", claims)
        self.assertEqual(report.claim_sample_count, 42)
        self.assertEqual(report.claim_total, 42)
        self.assertEqual(report.mode, "final_check")

    def test_default_report_passes_with_all_clear(self):
        ic = load_module()
        claims = [{"text": "claim"} for _ in range(20)]
        report = ic.run_integrity_check("pre_review", claims)
        self.assertTrue(report.passed)
        self.assertEqual(report.suspected_modes, [])
        for mode in ic.FAILURE_MODES:
            self.assertEqual(report.results[mode], "CLEAR")

    def test_overrides_are_applied(self):
        ic = load_module()
        claims = [{"text": "claim"} for _ in range(20)]
        report = ic.run_integrity_check(
            "pre_review",
            claims,
            overrides={"M2": "SUSPECTED", "M5": "OVERRIDDEN"},
        )
        self.assertFalse(report.passed)
        self.assertEqual(report.results["M2"], "SUSPECTED")
        self.assertEqual(report.results["M5"], "OVERRIDDEN")
        self.assertEqual(report.suspected_modes, ["M2"])
        for mode in [m for m in ic.FAILURE_MODES if m not in ("M2", "M5")]:
            self.assertEqual(report.results[mode], "CLEAR")

    def test_passed_with_all_overridden(self):
        ic = load_module()
        claims = [{"text": "claim"} for _ in range(20)]
        overrides = {mode: "OVERRIDDEN" for mode in ic.FAILURE_MODES}
        report = ic.run_integrity_check("pre_review", claims, overrides=overrides)
        self.assertTrue(report.passed)
        self.assertEqual(report.suspected_modes, [])

    def test_report_round_trip_to_dict(self):
        ic = load_module()
        claims = [{"text": "claim"} for _ in range(20)]
        report = ic.run_integrity_check(
            "pre_review",
            claims,
            overrides={"M3": "SUSPECTED"},
            round_num=2,
            max_rounds=3,
        )
        data = report.to_dict()
        self.assertEqual(data["mode"], "pre_review")
        self.assertEqual(data["round_num"], 2)
        self.assertEqual(data["max_rounds"], 3)
        self.assertFalse(data["passed"])
        self.assertEqual(data["suspected_modes"], ["M3"])
        self.assertIn("results", data)
        self.assertIn("notes", data)

    def test_next_round_advances_round_num(self):
        ic = load_module()
        claims = [{"text": "claim"} for _ in range(20)]
        report = ic.run_integrity_check("pre_review", claims, round_num=1, max_rounds=3)
        next_report = ic.next_round_report(report)
        self.assertEqual(next_report.round_num, 2)
        self.assertEqual(next_report.max_rounds, 3)
        self.assertEqual(next_report.mode, "pre_review")
        self.assertTrue(next_report.passed)

    def test_next_round_enforces_max_rounds(self):
        ic = load_module()
        claims = [{"text": "claim"} for _ in range(20)]
        report = ic.run_integrity_check("pre_review", claims, round_num=3, max_rounds=3)
        with self.assertRaises(ValueError):
            ic.next_round_report(report)


if __name__ == "__main__":
    unittest.main()
