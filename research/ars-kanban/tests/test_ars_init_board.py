import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path("/opt/data/scripts/ars-kanban/init_board.py")


def load_module():
    spec = importlib.util.spec_from_file_location("ars_init_board", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FakeKanban:
    def __init__(self):
        self.boards = []
        self.created = []
        self.links = []
        self.next_id = 1
        self.by_key = {}

    def ensure_board(self, board_slug, *, name, description, default_workdir=None):
        self.boards.append(
            {
                "board_slug": board_slug,
                "name": name,
                "description": description,
                "default_workdir": default_workdir,
            }
        )
        return {"slug": board_slug, "name": name}

    def create_task(self, *, board_slug, title, body, assignee, workspace, idempotency_key, parent_ids=None):
        if idempotency_key in self.by_key:
            return self.by_key[idempotency_key]
        task_id = f"t_{self.next_id:08d}"
        self.next_id += 1
        task = {
            "id": task_id,
            "board_slug": board_slug,
            "title": title,
            "body": body,
            "assignee": assignee,
            "workspace": workspace,
            "idempotency_key": idempotency_key,
            "parent_ids": list(parent_ids or []),
        }
        self.created.append(task)
        self.by_key[idempotency_key] = task
        return task

    def link(self, board_slug, parent_id, child_id):
        edge = (board_slug, parent_id, child_id)
        if edge not in self.links:
            self.links.append(edge)


class TestArsInitBoard(unittest.TestCase):
    def test_slugify_topic_is_stable_and_kebab_case(self):
        init_board = load_module()

        self.assertEqual(init_board.slugify_topic("Bates vs Hjørland"), "bates-vs-hjrland")
        self.assertEqual(init_board.board_slug_for_topic("Bates vs Hjørland"), "ars-bates-vs-hjrland")

    def test_material_passport_contains_schema9_required_fields(self):
        init_board = load_module()

        passport = init_board.build_material_passport(
            topic="Bates vs Hjørland",
            mode="full",
            phase=1,
            origin_date="2026-06-05T00:00:00Z",
        )

        self.assertEqual(passport["origin_skill"], "deep-research")
        self.assertEqual(passport["origin_mode"], "full")
        self.assertEqual(passport["origin_date"], "2026-06-05T00:00:00Z")
        self.assertEqual(passport["verification_status"], "UNVERIFIED")
        self.assertEqual(passport["version_label"], "phase1-v0")
        self.assertIn("repro_lock", passport)

    def test_init_board_creates_six_phase_tasks_with_persistent_workspaces_and_links(self):
        init_board = load_module()
        fake = FakeKanban()
        with tempfile.TemporaryDirectory() as tmp:
            result = init_board.init_board(
                "Bates vs Hjørland",
                kanban=fake,
                workspace_root=Path(tmp),
                assignee="default",
                mode="full",
                origin_date="2026-06-05T00:00:00Z",
            )

        self.assertEqual(result["board_slug"], "ars-bates-vs-hjrland")
        self.assertEqual(len(fake.created), 6)
        self.assertEqual([task["title"] for task in fake.created], [
            "Phase 1: Scoping — Bates vs Hjørland",
            "Phase 2: Investigation — Bates vs Hjørland",
            "Phase 3: Analysis — Bates vs Hjørland",
            "Phase 4: Composition — Bates vs Hjørland",
            "Phase 5: Review — Bates vs Hjørland",
            "Phase 6: Revision — Bates vs Hjørland",
        ])
        # Dependencies are attached at task creation time via parent_ids;
        # init_board must not call a second explicit link that creates duplicate events.
        self.assertEqual(len(fake.links), 0)
        self.assertTrue(all(task["workspace"].startswith("dir:") for task in fake.created))

        first_body = json.loads(fake.created[0]["body"])
        self.assertEqual(first_body["topic"], "Bates vs Hjørland")
        self.assertEqual(first_body["phase"], 1)
        self.assertEqual(first_body["material_passport"]["version_label"], "phase1-v0")
        self.assertIn("research_question_agent", first_body["agents"])

        self.assertEqual(fake.created[1]["parent_ids"], [fake.created[0]["id"]])

    def test_init_board_is_idempotent_for_same_topic(self):
        init_board = load_module()
        fake = FakeKanban()
        with tempfile.TemporaryDirectory() as tmp:
            first = init_board.init_board("Bates vs Hjørland", kanban=fake, workspace_root=Path(tmp))
            second = init_board.init_board("Bates vs Hjørland", kanban=fake, workspace_root=Path(tmp))

        self.assertEqual(first["task_ids"], second["task_ids"])
        self.assertEqual(len(fake.created), 6)
        self.assertEqual(len(fake.links), 0)

    def test_c_mode_expands_phase_2_into_literature_acquisition_and_zotero_investigation(self):
        init_board = load_module()
        fake = FakeKanban()
        with tempfile.TemporaryDirectory() as tmp:
            result = init_board.init_board(
                "Bates vs Hjørland",
                kanban=fake,
                workspace_root=Path(tmp),
                mode="c",
                origin_date="2026-06-05T00:00:00Z",
            )

        self.assertEqual(len(fake.created), 7)
        self.assertEqual(result["phase_sequence"], [1, "2-1", "2-2", 3, 4, 5, 6])
        self.assertEqual([task["title"] for task in fake.created], [
            "Phase 1: Scoping — Bates vs Hjørland",
            "Phase 2-1: Literature Acquisition — Bates vs Hjørland",
            "Phase 2-2: Investigation (Zotero Corpus) — Bates vs Hjørland",
            "Phase 3: Analysis — Bates vs Hjørland",
            "Phase 4: Composition — Bates vs Hjørland",
            "Phase 5: Review — Bates vs Hjørland",
            "Phase 6: Revision — Bates vs Hjørland",
        ])
        self.assertEqual(fake.created[1]["parent_ids"], [fake.created[0]["id"]])
        self.assertEqual(fake.created[2]["parent_ids"], [fake.created[1]["id"]])
        self.assertEqual(fake.created[3]["parent_ids"], [fake.created[2]["id"]])

        phase21_body = json.loads(fake.created[1]["body"])
        self.assertEqual(phase21_body["phase"], "2-1")
        self.assertEqual(phase21_body["phase_name"], "Literature Acquisition")
        self.assertEqual(phase21_body["parent_phase"], 2)
        self.assertEqual(phase21_body["c_mode"]["zotero_collection_path"], "deep-research/bates-vs-hjrland")
        self.assertEqual(phase21_body["c_mode"]["loop_count"], 0)
        self.assertEqual(phase21_body["c_mode"]["max_loops"], 3)
        self.assertEqual(phase21_body["material_passport"]["upstream_dependencies"], ["phase1-v0"])

        phase22_body = json.loads(fake.created[2]["body"])
        self.assertEqual(phase22_body["material_passport"]["upstream_dependencies"], ["phase2-1-v0"])
        phase3_body = json.loads(fake.created[3]["body"])
        self.assertEqual(phase3_body["material_passport"]["upstream_dependencies"], ["phase2-2-v0"])

        sources = phase21_body["c_mode"]["literature_sources"]
        self.assertEqual([s["id"] for s in sources], [
            "openalex", "crossref", "jstage", "cinii_research", "semantic_scholar",
        ])
        self.assertEqual(sources[0]["role"], "primary-international")
        self.assertEqual(sources[1]["role"], "doi-metadata-abstract-fallback")
        self.assertEqual(sources[2]["role"], "primary-japanese-diamond-oa")
        self.assertEqual(sources[3]["role"], "japanese-supplement")
        self.assertTrue(sources[4]["optional"])
        self.assertEqual(sources[4]["api_key_env"], "SEMANTIC_SCHOLAR_API_KEY")
    def test_kanban_cli_omits_assignee_when_not_requested(self):
        init_board = load_module()

        class RecordingKanban(init_board.KanbanCli):
            def __init__(self):
                super().__init__(hermes="hermes")
                self.calls = []

            def _run(self, args, *, check=True):
                args = list(args)
                self.calls.append(args)
                return subprocess.CompletedProcess(args=args, returncode=0, stdout=json.dumps({"id": "t_cli"}), stderr="")

        kanban = RecordingKanban()
        task = kanban.create_task(
            board_slug="ars-test",
            title="Phase 1",
            body="{}",
            assignee=None,
            workspace="dir:/tmp/phase-1",
            idempotency_key="ars-test:phase:1",
            parent_ids=[],
        )

        self.assertEqual(task["id"], "t_cli")
        self.assertNotIn("--assignee", kanban.calls[0])

    def test_kanban_cli_includes_assignee_when_requested(self):
        init_board = load_module()

        class RecordingKanban(init_board.KanbanCli):
            def __init__(self):
                super().__init__(hermes="hermes")
                self.calls = []

            def _run(self, args, *, check=True):
                args = list(args)
                self.calls.append(args)
                return subprocess.CompletedProcess(args=args, returncode=0, stdout=json.dumps({"id": "t_cli"}), stderr="")

        kanban = RecordingKanban()
        kanban.create_task(
            board_slug="ars-test",
            title="Phase 1",
            body="{}",
            assignee="default",
            workspace="dir:/tmp/phase-1",
            idempotency_key="ars-test:phase:1",
            parent_ids=[],
        )

        self.assertIn("--assignee", kanban.calls[0])
        self.assertIn("default", kanban.calls[0])


if __name__ == "__main__":
    unittest.main()
