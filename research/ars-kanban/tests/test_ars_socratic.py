"""Tests for Socratic mode in Kanban phase worker."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path("/opt/data/scripts/ars-kanban/phase_worker.py")
SOC_MODULE = Path("/opt/data/scripts/ars-kanban/socratic_phase.py")


def load_phase_worker():
    spec = importlib.util.spec_from_file_location("ars_phase_worker", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_socratic():
    spec = importlib.util.spec_from_file_location("ars_socratic", SOC_MODULE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


# =========================================================================
# Socratic state management
# =========================================================================

class TestSocraticState(unittest.TestCase):
    """save/load/clear of Socratic dialogue state."""

    def test_default_state_has_all_keys(self):
        soc = load_socratic()
        state = soc.load_socratic_state(None)
        self.assertIn("turn", state)
        self.assertIn("layer", state)
        self.assertIn("insights", state)
        self.assertIn("history", state)
        self.assertIn("converged", state)
        self.assertEqual(state["turn"], 0)
        self.assertEqual(state["layer"], 1)
        self.assertEqual(state["insights"], [])

    def test_save_and_load_roundtrip(self):
        soc = load_socratic()
        with tempfile.TemporaryDirectory() as tmp:
            state = {
                "turn": 3,
                "layer": 2,
                "insights": ["User narrowed topic to information behavior"],
                "history": [{"role": "mentor", "content": "What interests you?"}],
                "converged": False,
                "awaiting_user": True,
                "current_question": "Tell me more",
                "convergence_signals": [],
            }
            soc.save_socratic_state(state, tmp)
            loaded = soc.load_socratic_state(tmp)
            self.assertEqual(loaded["turn"], 3)
            self.assertEqual(loaded["layer"], 2)
            self.assertEqual(len(loaded["insights"]), 1)
            self.assertEqual(len(loaded["history"]), 1)
            self.assertTrue(loaded["awaiting_user"])

    def test_clear_removes_file(self):
        soc = load_socratic()
        with tempfile.TemporaryDirectory() as tmp:
            state = {"turn": 0, "layer": 1, "insights": [], "history": [],
                     "converged": False, "awaiting_user": False, "current_question": None,
                     "convergence_signals": []}
            soc.save_socratic_state(state, tmp)
            state_path = Path(tmp) / soc.SOCRATIC_STATE_FILE
            self.assertTrue(state_path.exists())
            soc.clear_socratic_state(tmp)
            self.assertFalse(state_path.exists())

    def test_corrupted_state_falls_back_to_defaults(self):
        soc = load_socratic()
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / soc.SOCRATIC_STATE_FILE
            state_path.write_text("not valid json")
            loaded = soc.load_socratic_state(tmp)
            self.assertEqual(loaded["turn"], 0)  # default


# =========================================================================
# Socratic mentor prompt building
# =========================================================================

class TestSocraticPrompt(unittest.TestCase):
    """Mentor prompt construction."""

    def test_prompt_contains_topic_and_layer(self):
        soc = load_socratic()
        state = soc.load_socratic_state(None)
        prompt = soc.build_socratic_mentor_prompt(state, "Information Behavior")
        # The prompt is a JSON-encoded string; decode for assertions
        prompt_decoded = json.loads(prompt)
        content = prompt_decoded["content"]
        self.assertIn("Information Behavior", content)
        self.assertIn("(1/5): Problem Framing", content)
        self.assertIn("Socratic Mentor Agent", content)

    def test_prompt_includes_conversation_history(self):
        soc = load_socratic()
        state = {
            "turn": 2,
            "layer": 2,
            "insights": ["clear RQ direction"],
            "history": [
                {"role": "mentor", "content": "What interests you?"},
                {"role": "user", "content": "Information behavior in libraries"},
            ],
            "converged": False,
            "awaiting_user": False,
            "current_question": None,
            "convergence_signals": [],
        }
        prompt = soc.build_socratic_mentor_prompt(state, "Libraries")
        self.assertIn("Information behavior in libraries", prompt)
        self.assertIn("What interests you?", prompt)
        self.assertIn("clear RQ direction", prompt)

    def test_prompt_requires_json_response(self):
        soc = load_socratic()
        state = soc.load_socratic_state(None)
        prompt = soc.build_socratic_mentor_prompt(state, "Test")
        self.assertIn("question", prompt)
        self.assertIn("needs_user_input", prompt)
        self.assertIn("converged", prompt)


# =========================================================================
# Socratic output parsing
# =========================================================================

class TestMentorOutputParsing(unittest.TestCase):
    """Parsing mentor delegate results."""

    def test_parse_json_from_summary(self):
        soc = load_socratic()
        result = {
            "summary": '{"question": "What aspect interests you?", "needs_user_input": true, "insight": null, "converged": false, "convergence_signals": [], "layer": 1}',
            "artifacts": {},
        }
        parsed = soc._parse_mentor_output(result["summary"], result)
        self.assertEqual(parsed["question"], "What aspect interests you?")
        self.assertTrue(parsed["needs_user_input"])
        self.assertFalse(parsed["converged"])

    def test_parse_json_with_insight(self):
        soc = load_socratic()
        result = {
            "summary": '{"question": "Why is that?", "needs_user_input": true, "insight": "User identified gap in existing research", "converged": false, "convergence_signals": ["S1"], "layer": 2}',
            "artifacts": {},
        }
        parsed = soc._parse_mentor_output(result["summary"], result)
        self.assertEqual(parsed["insight"], "User identified gap in existing research")
        self.assertIn("S1", parsed["convergence_signals"])

    def test_parse_converged_result(self):
        soc = load_socratic()
        result = {
            "summary": '{"question": null, "needs_user_input": false, "insight": null, "converged": true, "convergence_signals": ["S1", "S2", "S3"], "layer": 5, "summary": "Final research plan summary"}',
            "artifacts": {},
        }
        parsed = soc._parse_mentor_output(result["summary"], result)
        self.assertTrue(parsed["converged"])
        self.assertEqual(len(parsed["convergence_signals"]), 3)
        self.assertEqual(parsed["summary"], "Final research plan summary")


class TestSocraticCompileSummary(unittest.TestCase):
    """Research plan summary compilation."""

    def test_summary_includes_insights_and_history(self):
        soc = load_socratic()
        state = {
            "turn": 5,
            "layer": 3,
            "insights": ["RQ: How does AI affect learning?"],
            "history": [
                {"role": "mentor", "content": "What interests you?"},
                {"role": "user", "content": "AI in education"},
            ],
            "converged": False,
            "awaiting_user": False,
            "current_question": None,
            "convergence_signals": ["S1"],
        }
        summary = soc._compile_socratic_summary(state)
        self.assertIn("Research Plan Summary", summary)
        self.assertIn("How does AI affect learning?", summary)
        self.assertIn("AI in education", summary)
        self.assertIn("Total turns", summary)
        self.assertIn("S1", summary)


# =========================================================================
# User comment extraction from kanban context
# =========================================================================

class TestCommentExtraction(unittest.TestCase):
    """Extracting user responses from kanban context."""

    def test_extract_simple_comment(self):
        soc = load_socratic()
        context = """# Kanban task

## Comments
- default (2026-06-05): I'm interested in information behavior

## Body
{}
"""
        comment = soc.extract_last_user_comment(context)
        self.assertEqual(comment, "I'm interested in information behavior")

    def test_extract_no_comments(self):
        soc = load_socratic()
        context = """# Kanban task

## Body
{}
"""
        comment = soc.extract_last_user_comment(context)
        self.assertIsNone(comment)

    def test_extract_multiline_comment(self):
        soc = load_socratic()
        context = """# Kanban task

## Comments
- default (2026-06-05): first line
- default (2026-06-05): second line here

## Body
{}
"""
        comment = soc.extract_last_user_comment(context)
        self.assertEqual(comment, "second line here")


# =========================================================================
# Phase worker Socratic dispatch
# =========================================================================

class TestSocraticDispatch(unittest.TestCase):
    """phase_worker.run_phase_task dispatches to Socratic mode."""

    def test_socratic_mode_calls_socratic_phase(self):
        """When mode is 'socratic', run_socratic_phase must be called."""
        worker = load_phase_worker()
        soc = load_socratic()

        body = json.dumps({
            "phase": 1,
            "mode": "socratic",
            "topic": "Test topic",
        })
        context = f"# Kanban task\n\n## Body\n{body}\n"
        kanban = _FakeKanban(context)
        delegator = _FakeDelegator()  # returns default dry-run result

        result = worker.run_phase_task("t_soc", kanban=kanban, delegator=delegator)

        # Socratic mode starts, mentor gets called, needs input → blocks
        self.assertIn(result["status"], ("blocked", "completed"),
                      "Socratic phase should either block or complete")


# =========================================================================
# Wording-Pattern Advisory integration with socratic_phase
# =========================================================================

class TestSocraticWordingAdvisory(unittest.TestCase):
    """When user response matches a wording pattern, kanban.comment fires."""

    def test_advisory_fires_on_ai_typical_rq(self):
        """User says 'I want to study the impact of AI on learning' → WP01 advisory."""
        soc = load_socratic()
        body = {"phase": 1, "mode": "socratic", "topic": "Test"}

        # Pre-populate state with awaiting_user=True
        state = soc.load_socratic_state(None)
        state["awaiting_user"] = True

        kanban_ctx = (
            "# Kanban task\n\n"
            "## Comments\n"
            "- seimiya (2026-06-05): I want to study the impact of AI on student learning\n\n"
            "## Body\n"
            + json.dumps(body)
            + "\n"
        )
        kanban = _FakeKanban(kanban_ctx)
        delegator = _FakeDelegator()

        with tempfile.TemporaryDirectory() as tmp:
            soc.save_socratic_state(state, tmp)
            result = soc.run_socratic_phase(
                "t_advisory", kanban=kanban, delegator=delegator,
                body=body, workspace_path=tmp,
            )
            # Verify advisory was emitted as a comment
            self.assertTrue(
                any("WORDING_PATTERN_ADVISORY" in c[1] for c in kanban.comments),
                f"Expected advisory comment, got: {kanban.comments}",
            )
            # State history should contain the advisory entry
            reloaded = soc.load_socratic_state(tmp)
            advisory_entries = [
                e for e in reloaded["history"] if e.get("role") == "advisory"
            ]
            self.assertGreaterEqual(len(advisory_entries), 1)
            self.assertEqual(advisory_entries[0]["wording_pattern_id"], "WP01")

    def test_advisory_suppressed_by_domain_vocab(self):
        """User says 'Bates vs Hjørland impact on LIS' → no advisory (domain vocab)."""
        soc = load_socratic()
        body = {"phase": 1, "mode": "socratic", "topic": "Test"}

        state = soc.load_socratic_state(None)
        state["awaiting_user"] = True

        kanban_ctx = (
            "# Kanban task\n\n"
            "## Comments\n"
            "- seimiya (2026-06-05): The impact of Bates on information behavior research\n\n"
            "## Body\n"
            + json.dumps(body)
            + "\n"
        )
        kanban = _FakeKanban(kanban_ctx)
        delegator = _FakeDelegator()

        with tempfile.TemporaryDirectory() as tmp:
            soc.save_socratic_state(state, tmp)
            soc.run_socratic_phase(
                "t_noadvisory", kanban=kanban, delegator=delegator,
                body=body, workspace_path=tmp,
            )
            # No advisory should fire (Bates + information behavior = domain vocab)
            self.assertFalse(
                any("WORDING_PATTERN_ADVISORY" in c[1] for c in kanban.comments),
                f"Expected no advisory, got: {kanban.comments}",
            )

    def test_advisory_does_not_break_socratic_flow(self):
        """Even with adversarial user input, Socratic flow continues."""
        soc = load_socratic()
        body = {"phase": 1, "mode": "socratic", "topic": "Test"}

        state = soc.load_socratic_state(None)
        state["awaiting_user"] = True

        kanban_ctx = (
            "# Kanban task\n\n"
            "## Comments\n"
            "- seimiya (2026-06-05): Exploring the impact of social media on learning\n\n"
            "## Body\n"
            + json.dumps(body)
            + "\n"
        )
        kanban = _FakeKanban(kanban_ctx)
        delegator = _FakeDelegator()

        with tempfile.TemporaryDirectory() as tmp:
            soc.save_socratic_state(state, tmp)
            result = soc.run_socratic_phase(
                "t_flow", kanban=kanban, delegator=delegator,
                body=body, workspace_path=tmp,
            )
            # Socratic must still produce a normal result
            self.assertIn(result["status"], ("blocked", "completed"))
            # Mentor was still called
            self.assertEqual(delegator.call_index, 1)


class _FakeKanban:
    def __init__(self, context_text):
        self.context_text = context_text
        self.completed = []
        self.blocked = []
        self.comments = []

    def context(self, task_id):
        return self.context_text

    def complete(self, task_id, summary, metadata):
        self.completed.append((task_id, summary, metadata))

    def block(self, task_id, reason):
        self.blocked.append((task_id, reason))

    def comment(self, task_id, body):
        self.comments.append((task_id, body))


class _FakeDelegator:
    def __init__(self, results=None):
        # Return sequential results for Socratic dialogue turns
        self.results = results or [
            {
                "summary": json.dumps({
                    "question": "What brings you to this research topic?",
                    "needs_user_input": True,
                    "insight": None,
                    "converged": False,
                    "convergence_signals": [],
                    "layer": 1,
                }),
                "artifacts": {},
            },
        ]
        self.call_index = 0
        self.calls = []

    def run(self, goal, context, toolsets):
        self.calls.append({"goal": goal, "context": context, "toolsets": toolsets})
        result = self.results[self.call_index % len(self.results)]
        self.call_index += 1
        return result


if __name__ == "__main__":
    unittest.main()
