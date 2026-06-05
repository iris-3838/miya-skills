"""Tests for Wording-Pattern Advisory (Kong #257) module."""

import importlib.util
import json
import unittest
from pathlib import Path

MODULE_PATH = Path("/opt/data/scripts/ars-kanban/wording_patterns.py")


def load_wp():
    spec = importlib.util.spec_from_file_location("ars_wp", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


# =========================================================================
# RQ candidate extraction
# =========================================================================

class TestRQCandidateExtraction(unittest.TestCase):
    """extract_rq_candidates finds RQ-like sentences in user utterances."""

    def test_extract_question_mark(self):
        wp = load_wp()
        cands = wp.extract_rq_candidates("How does AI affect learning?")
        self.assertEqual(len(cands), 1)
        self.assertIn("How does AI affect learning", cands[0])

    def test_extract_declarative_rq(self):
        wp = load_wp()
        cands = wp.extract_rq_candidates("The impact of social media on student engagement.")
        self.assertGreaterEqual(len(cands), 1)
        self.assertTrue(any("impact" in c.lower() for c in cands))

    def test_extract_rq_opener(self):
        wp = load_wp()
        cands = wp.extract_rq_candidates("Why do users prefer certain databases over others?")
        self.assertEqual(len(cands), 1)

    def test_no_candidate_short_sentence(self):
        wp = load_wp()
        cands = wp.extract_rq_candidates("Yes.")
        self.assertEqual(cands, [])

    def test_no_candidate_non_rq(self):
        wp = load_wp()
        cands = wp.extract_rq_candidates("I went to the library yesterday.")
        self.assertEqual(cands, [])

    def test_extract_multiple_candidates(self):
        wp = load_wp()
        text = "What is X? And how does Y affect Z?"
        cands = wp.extract_rq_candidates(text)
        self.assertEqual(len(cands), 2)


# =========================================================================
# Domain-native vocabulary detection
# =========================================================================

class TestDomainNativeVocabulary(unittest.TestCase):
    """has_domain_native_vocabulary detects field-specific terms."""

    def test_lis_terms_detected(self):
        wp = load_wp()
        self.assertTrue(wp.has_domain_native_vocabulary("How does information behavior evolve?"))
        self.assertTrue(wp.has_domain_native_vocabulary("A domain-analytic perspective"))

    def test_theorist_names_detected(self):
        wp = load_wp()
        self.assertTrue(wp.has_domain_native_vocabulary("Bates vs Hjørland comparison"))
        self.assertTrue(wp.has_domain_native_vocabulary("Heidegger's hermeneutic approach"))

    def test_methodology_terms_detected(self):
        wp = load_wp()
        self.assertTrue(wp.has_domain_native_vocabulary("Using grounded theory analysis"))
        self.assertTrue(wp.has_domain_native_vocabulary("Phenomenographic methodology"))

    def test_generic_terms_not_detected(self):
        wp = load_wp()
        self.assertFalse(wp.has_domain_native_vocabulary("The impact of AI on learning"))
        self.assertFalse(wp.has_domain_native_vocabulary("Factors affecting satisfaction"))

    def test_empty_input(self):
        wp = load_wp()
        self.assertFalse(wp.has_domain_native_vocabulary(""))


# =========================================================================
# Wording pattern matching
# =========================================================================

class TestWordingPatternMatching(unittest.TestCase):
    """match_wording_patterns detects surface phrasing shells."""

    def test_wp01_impact_effect(self):
        wp = load_wp()
        matches = wp.match_wording_patterns("The impact of AI on education")
        ids = [m["id"] for m in matches]
        self.assertIn("WP01", ids)

    def test_wp02_relationship(self):
        wp = load_wp()
        matches = wp.match_wording_patterns("Investigating the relationship between X and Y")
        ids = [m["id"] for m in matches]
        self.assertIn("WP02", ids)

    def test_wp05_factors(self):
        wp = load_wp()
        matches = wp.match_wording_patterns("Factors influencing user satisfaction")
        ids = [m["id"] for m in matches]
        self.assertIn("WP05", ids)
        # WP15 also matches because "factors ... satisfaction" is in the WP15 trigger set
        matches2 = wp.match_wording_patterns("Factors affecting satisfaction")
        ids2 = [m["id"] for m in matches2]
        self.assertIn("WP15", ids2)

    def test_wp19_technology_enhancement(self):
        wp = load_wp()
        matches = wp.match_wording_patterns("Role of AI in enhancing learning")
        ids = [m["id"] for m in matches]
        self.assertIn("WP19", ids)

    def test_wp_no_match_for_clean_text(self):
        wp = load_wp()
        matches = wp.match_wording_patterns(
            "How does the divergence between Bates and Hjørland reshape LIS practice?"
        )
        self.assertEqual(matches, [])

    def test_wp_multiple_matches(self):
        wp = load_wp()
        matches = wp.match_wording_patterns("The impact of AI on student performance")
        ids = [m["id"] for m in matches]
        # Should match WP01 (impact) and WP10 (effect on performance)
        self.assertIn("WP01", ids)
        self.assertIn("WP10", ids)


# =========================================================================
# Advisory triggering logic
# =========================================================================

class TestAdvisoryTriggering(unittest.TestCase):
    """detect_wording_advisory decides whether to fire the advisory."""

    def test_no_advisory_for_empty_utterance(self):
        wp = load_wp()
        self.assertIsNone(wp.detect_wording_advisory(""))

    def test_no_advisory_without_rq(self):
        wp = load_wp()
        # No RQ-like sentence → no advisory
        self.assertIsNone(wp.detect_wording_advisory("I went to the library."))

    def test_advisory_fires_for_ai_typical_rq(self):
        wp = load_wp()
        advisory = wp.detect_wording_advisory(
            "I want to study the impact of AI on student learning"
        )
        self.assertIsNotNone(advisory)
        self.assertTrue(advisory["triggered"])
        self.assertEqual(advisory["pattern_id"], "WP01")
        self.assertIn("WORDING_PATTERN_ADVISORY", advisory["message"])

    def test_advisory_suppressed_by_domain_vocab(self):
        wp = load_wp()
        # Even though "impact of X on Y" matches WP01, "information behavior" suppresses
        advisory = wp.detect_wording_advisory(
            "How does the impact of AI on information behavior differ across LIS domains?"
        )
        self.assertIsNone(advisory, "Domain-native vocab should suppress advisory")

    def test_advisory_suppressed_by_theorist_name(self):
        wp = load_wp()
        advisory = wp.detect_wording_advisory(
            "What is the impact of Bates's theory on information science?"
        )
        # "Bates" is a theorist name → suppresses
        self.assertIsNone(advisory)

    def test_no_duplicate_advisory_in_history(self):
        wp = load_wp()
        history = [
            {"role": "advisory", "wording_pattern_id": "WP01", "content": "..."},
            {"role": "user", "content": "The impact of X on Y"},
        ]
        advisory = wp.detect_wording_advisory(
            "The impact of cloud computing on data storage",
            history=history,
        )
        # WP01 already fired → no new advisory
        self.assertIsNone(advisory)

    def test_new_advisory_for_different_pattern(self):
        wp = load_wp()
        history = [
            {"role": "advisory", "wording_pattern_id": "WP01", "content": "..."},
        ]
        # Now user uses WP05 (factors), which is different from WP01
        advisory = wp.detect_wording_advisory(
            "Factors affecting adoption of new technology",
            history=history,
        )
        self.assertIsNotNone(advisory)
        self.assertIn(advisory["pattern_id"], ("WP05", "WP15"))


# =========================================================================
# Advisory message format
# =========================================================================

class TestAdvisoryMessageFormat(unittest.TestCase):
    """The advisory message follows the original ARS markdown template."""

    def test_message_contains_required_elements(self):
        wp = load_wp()
        advisory = wp.detect_wording_advisory(
            "Exploring the impact of social media on learning"
        )
        self.assertIsNotNone(advisory)
        msg = advisory["message"]
        self.assertIn("[WORDING_PATTERN_ADVISORY]", msg)
        self.assertIn("I am not judging the idea", msg)
        self.assertIn("field use instead?", msg)
        self.assertIn("WP", msg)  # pattern id present

    def test_message_contains_user_excerpt(self):
        wp = load_wp()
        advisory = wp.detect_wording_advisory(
            "I want to investigate the impact of AI on education"
        )
        self.assertIsNotNone(advisory)
        # excerpt should be a slice of the input
        self.assertLessEqual(len(advisory["excerpt"]), 200)
        self.assertIn("impact of AI", advisory["excerpt"])


# =========================================================================
# History entry conversion
# =========================================================================

class TestAdvisoryHistoryEntry(unittest.TestCase):
    """advisory_to_history_entry serializes advisories for state persistence."""

    def test_entry_has_required_keys(self):
        wp = load_wp()
        advisory = wp.detect_wording_advisory(
            "The impact of social media on learning"
        )
        self.assertIsNotNone(advisory)
        entry = wp.advisory_to_history_entry(advisory)
        self.assertEqual(entry["role"], "advisory")
        self.assertIn("wording_pattern_id", entry)
        self.assertIn("wording_pattern_family", entry)
        self.assertIn("content", entry)


if __name__ == "__main__":
    unittest.main()
