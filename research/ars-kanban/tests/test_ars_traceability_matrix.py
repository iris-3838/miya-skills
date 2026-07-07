import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path("/opt/data/workspace/miya-skills/research/ars-kanban/scripts/traceability_matrix.py")


def load_module():
    spec = importlib.util.spec_from_file_location("traceability_matrix", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class TestTraceabilityMatrix(unittest.TestCase):
    def test_empty_matrix_defaults_to_accept(self):
        tm = load_module()
        matrix = tm.TraceabilityMatrix()
        matrix.compute_decision()
        self.assertEqual(matrix.new_decision, "Accept")
        self.assertTrue(matrix.can_revise_again)
        self.assertEqual(matrix.verified_count, 0)
        self.assertEqual(matrix.residual_count, 0)

    def test_all_verified_returns_accept(self):
        tm = load_module()
        matrix = tm.TraceabilityMatrix()
        matrix.add_row(
            reviewer_comment_id="R1-1",
            author_claim="Fixed typo in abstract.",
            verified=True,
            evidence="delta.md#L1",
        )
        matrix.compute_decision()
        self.assertEqual(matrix.new_decision, "Accept")
        self.assertEqual(matrix.verified_count, 1)
        self.assertEqual(matrix.residual_count, 0)

    def test_unverified_without_residual_returns_minor(self):
        tm = load_module()
        matrix = tm.TraceabilityMatrix()
        matrix.add_row(
            reviewer_comment_id="R1-1",
            author_claim="Fixed typo in abstract.",
            verified=True,
            evidence="delta.md#L1",
        )
        matrix.add_row(
            reviewer_comment_id="R2-2",
            author_claim="Clarified method.",
            verified=False,
            evidence="delta.md#L5",
        )
        matrix.compute_decision()
        self.assertEqual(matrix.new_decision, "Minor")

    def test_unverified_with_residual_returns_major(self):
        tm = load_module()
        matrix = tm.TraceabilityMatrix()
        matrix.add_row(
            reviewer_comment_id="R1-1",
            author_claim="Fixed typo.",
            verified=True,
            evidence="delta.md#L1",
        )
        matrix.add_row(
            reviewer_comment_id="R2-2",
            author_claim="Clarified method.",
            verified=False,
            evidence="delta.md#L5",
            residual_issue="Methodology description still missing key detail.",
        )
        matrix.compute_decision()
        self.assertEqual(matrix.new_decision, "Major")
        self.assertEqual(matrix.residual_count, 1)

    def test_revision_loop_cap_enforced(self):
        tm = load_module()
        matrix = tm.TraceabilityMatrix(revision_loop_count=2)
        self.assertFalse(matrix.can_revise_again)

    def test_revision_loop_cap_allows_second_loop(self):
        tm = load_module()
        matrix = tm.TraceabilityMatrix(revision_loop_count=1)
        self.assertTrue(matrix.can_revise_again)

    def test_to_dict_roundtrip(self):
        tm = load_module()
        matrix = tm.TraceabilityMatrix(revision_loop_count=2)
        matrix.add_row(
            reviewer_comment_id="R3-1",
            author_claim="Added citation.",
            verified=True,
            evidence="delta.md#L10",
        )
        matrix.compute_decision()
        data = matrix.to_dict()
        self.assertIn("rows", data)
        self.assertIn("new_decision", data)
        self.assertEqual(data["new_decision"], "Accept")
        self.assertEqual(data["max_revision_loops"], 2)
        self.assertFalse(data["can_revise_again"])

    def test_build_traceability_matrix_from_reports(self):
        tm = load_module()
        review_report = {
            "reviewer_comments": [
                {"id": "R1-1", "addressed": True},
                {"id": "R2-2", "addressed": False, "residual_issue": "Needs more detail."},
            ]
        }
        revision_delta = {
            "claims": {
                "R1-1": "Fixed the issue.",
                "R2-2": "Partially addressed.",
            },
            "delta_report_path": "delta.md",
        }
        matrix = tm.build_traceability_matrix(review_report, revision_delta, current_loop_count=1)
        self.assertEqual(len(matrix.rows), 2)
        self.assertTrue(matrix.rows[0].verified)
        self.assertFalse(matrix.rows[1].verified)
        self.assertEqual(matrix.rows[1].residual_issue, "Needs more detail.")
        self.assertEqual(matrix.new_decision, "Major")

    def test_build_traceability_matrix_with_missing_claim(self):
        tm = load_module()
        review_report = {
            "reviewer_comments": [
                {"id": "R1-1", "addressed": False},
            ]
        }
        revision_delta = {"claims": {}, "delta_report_path": "delta.md"}
        matrix = tm.build_traceability_matrix(review_report, revision_delta, current_loop_count=0)
        self.assertEqual(matrix.rows[0].author_claim, "[NO RESPONSE]")
        self.assertFalse(matrix.rows[0].verified)
        self.assertEqual(matrix.new_decision, "Minor")


if __name__ == "__main__":
    unittest.main()
