import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path("/opt/data/workspace/miya-skills/research/ars-kanban/scripts/collaboration_depth.py")


def load_module():
    spec = importlib.util.spec_from_file_location("collaboration_depth", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class TestCollaborationDepth(unittest.TestCase):
    def test_advisory_report_has_four_dimensions(self):
        cd = load_module()
        report = cd.observe_checkpoint(
            "stage-3-review",
            user_turns=2,
            ai_turns=4,
            user_challenges=1,
            user_edits=1,
            high_order_user_contributions=1,
        )
        self.assertEqual(len(report.scores), 4)
        dimensions = {s.dimension for s in report.scores}
        self.assertEqual(
            dimensions,
            {"delegation_intensity", "cognitive_vigilance", "cognitive_reallocation", "zone_classification"},
        )

    def test_overall_score_is_average(self):
        cd = load_module()
        report = cd.observe_checkpoint(
            "stage-1-scoping",
            user_turns=5,
            ai_turns=5,
            user_challenges=0,
            user_edits=0,
            high_order_user_contributions=0,
        )
        report.compute_overall()
        expected = int(sum(s.score for s in report.scores) / 4)
        self.assertEqual(report.overall_score, expected)

    def test_zone_classification(self):
        cd = load_module()
        report = cd.observe_checkpoint(
            "stage-3-review",
            user_turns=2,
            ai_turns=8,
            user_challenges=0,
            user_edits=0,
            high_order_user_contributions=0,
        )
        self.assertEqual(report.zone, "Delegation")

    def test_high_vigilance_zone(self):
        cd = load_module()
        report = cd.observe_checkpoint(
            "stage-3-review",
            user_turns=5,
            ai_turns=5,
            user_challenges=5,
            user_edits=0,
            high_order_user_contributions=0,
        )
        self.assertEqual(report.zone, "Vigilance")

    def test_reallocation_zone(self):
        cd = load_module()
        report = cd.observe_checkpoint(
            "stage-4-revise",
            user_turns=4,
            ai_turns=4,
            user_challenges=0,
            user_edits=4,
            high_order_user_contributions=4,
        )
        self.assertEqual(report.zone, "Reallocation")

    def test_mandatory_gates_skip_observer(self):
        cd = load_module()
        self.assertTrue(cd.should_skip_observer("2.5"))
        self.assertTrue(cd.should_skip_observer("4.5"))
        self.assertFalse(cd.should_skip_observer("3"))
        self.assertFalse(cd.should_skip_observer(1))

    def test_to_dict_roundtrip(self):
        cd = load_module()
        report = cd.observe_checkpoint(
            "stage-5-review",
            user_turns=3,
            ai_turns=3,
            user_challenges=1,
            user_edits=1,
            high_order_user_contributions=1,
        )
        data = report.to_dict()
        self.assertEqual(data["checkpoint"], "stage-5-review")
        self.assertTrue(data["advisory_only"])
        self.assertIn("overall_score", data)
        self.assertIn("zone", data)
        self.assertEqual(len(data["scores"]), 4)

    def test_empty_checkpoint_returns_zero(self):
        cd = load_module()
        report = cd.observe_checkpoint("empty")
        self.assertEqual(report.overall_score, 0)
        self.assertEqual(report.zone, "Mixed")


if __name__ == "__main__":
    unittest.main()
