"""Tests for ARS C mode Phase 2-1 literature acquisition engine."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path("/opt/data/scripts/ars-kanban/c_literature_acquisition.py")


def load_module():
    spec = importlib.util.spec_from_file_location("ars_c_lit", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FakeZotero:
    def __init__(self):
        self.collections_data = []
        self.created_collections = []
        self.created_items = []

    def collections(self, start=0):
        return self.collections_data[start:start + 100]

    def create_collections(self, payload):
        result = {"success": {}}
        for idx, data in enumerate(payload):
            key = f"C{len(self.created_collections) + 1:05d}"
            self.created_collections.append({"key": key, "data": data})
            self.collections_data.append({"key": key, "data": {"key": key, **data}})
            result["success"][str(idx)] = key
        return result

    def item_template(self, item_type):
        return {"itemType": item_type, "creators": [], "tags": [], "collections": []}

    def create_items(self, items):
        self.created_items.extend(items)
        return {"success": {str(i): f"I{i:05d}" for i, _ in enumerate(items)}}


class TestOpenAlexParsing(unittest.TestCase):
    def test_reconstruct_openalex_abstract(self):
        mod = load_module()
        inverted = {"Information": [0], "is": [1], "contested": [2], ".": [3]}
        self.assertEqual(mod.reconstruct_openalex_abstract(inverted), "Information is contested .")

    def test_openalex_work_to_record_extracts_oa_url_and_venue(self):
        mod = load_module()
        work = {
            "id": "https://openalex.org/W123",
            "doi": "https://doi.org/10.1000/xyz",
            "title": "Information as thing revisited",
            "publication_year": 2024,
            "authorships": [{"author": {"display_name": "Marcia Bates"}}],
            "abstract_inverted_index": {"Information": [0], "as": [1], "thing": [2]},
            "open_access": {"is_oa": True, "oa_status": "gold", "oa_url": "https://example.org/paper.pdf"},
            "primary_location": {"source": {"display_name": "Journal of Documentation"}},
            "cited_by_count": 12,
        }
        record = mod.openalex_work_to_record(work)
        self.assertEqual(record["doi"], "10.1000/xyz")
        self.assertEqual(record["title"], "Information as thing revisited")
        self.assertEqual(record["authors"], ["Marcia Bates"])
        self.assertEqual(record["abstract"], "Information as thing")
        self.assertEqual(record["venue"], "Journal of Documentation")
        self.assertTrue(record["is_oa"])
        self.assertEqual(record["oa_url"], "https://example.org/paper.pdf")


class TestCrossRefParsing(unittest.TestCase):
    def test_crossref_message_to_record_strips_jats_markup(self):
        mod = load_module()
        msg = {
            "DOI": "10.5555/abc",
            "title": ["Domain analysis and information"],
            "abstract": "<jats:p>This paper studies <i>domain analysis</i>.</jats:p>",
            "author": [{"given": "Birger", "family": "Hjørland"}],
            "container-title": ["Knowledge Organization"],
            "published-print": {"date-parts": [[2020]]},
        }
        record = mod.crossref_message_to_record(msg)
        self.assertEqual(record["doi"], "10.5555/abc")
        self.assertEqual(record["abstract"], "This paper studies domain analysis.")
        self.assertEqual(record["authors"], ["Birger Hjørland"])
        self.assertEqual(record["year"], 2020)


class TestZoteroMapping(unittest.TestCase):
    def test_record_to_zotero_item_maps_metadata_and_tags(self):
        mod = load_module()
        z = FakeZotero()
        record = {
            "title": "Information and knowledge",
            "doi": "10.1234/test",
            "authors": ["Marcia Bates", "Birger Hjørland"],
            "year": 2026,
            "venue": "JASIST",
            "abstract": "Abstract text",
            "source": "openalex",
            "is_oa": False,
            "oa_url": None,
        }
        item = mod.record_to_zotero_item(record, z, collection_key="CROOT")
        self.assertEqual(item["itemType"], "journalArticle")
        self.assertEqual(item["title"], "Information and knowledge")
        self.assertEqual(item["DOI"], "10.1234/test")
        self.assertEqual(item["creators"][0]["lastName"], "Bates")
        self.assertEqual(item["creators"][1]["lastName"], "Hjørland")
        self.assertIn("CROOT", item["collections"])
        self.assertIn({"tag": "deep-research"}, item["tags"])
        self.assertIn({"tag": "source:openalex"}, item["tags"])
        self.assertIn({"tag": "access:non-oa"}, item["tags"])

    def test_ensure_collection_path_creates_nested_collections(self):
        mod = load_module()
        z = FakeZotero()
        key = mod.ensure_collection_path(z, "deep-research/bates-vs-hjorland")
        self.assertEqual(key, "C00002")
        self.assertEqual([c["data"]["name"] for c in z.created_collections], ["deep-research", "bates-vs-hjorland"])
        self.assertFalse(z.created_collections[0]["data"]["parentCollection"])
        self.assertEqual(z.created_collections[1]["data"]["parentCollection"], "C00001")


class TestRecordPreview(unittest.TestCase):
    def setUp(self):
        self.mod = load_module()
        self.records = [
            {"title": "Information as thing", "authors": ["Marcia Bates"], "year": 2006, "venue": "JASIST", "doi": "10.1002/asi.123", "is_oa": True, "source": "openalex", "abstract": "A foundational paper."},
            {"title": "Domain analysis", "authors": ["Birger Hjørland"], "year": 2002, "venue": "JDoc", "doi": "10.1108/abc", "is_oa": False, "source": "openalex", "abstract": "A methodological paper."},
            {"title": "Information needs and information seeking", "authors": ["Carol Kuhlthau", "T.D. Wilson"], "year": 2000, "venue": "LISR", "doi": "", "is_oa": False, "source": "openalex", "abstract": ""},
        ]

    def test_format_records_for_preview_numbers_correctly(self):
        text = self.mod.format_records_for_preview(self.records)
        self.assertIn("[1]", text)
        self.assertIn("[2]", text)
        self.assertIn("[3]", text)
        self.assertIn("Marcia Bates", text)
        self.assertIn("🟢 OA", text)
        self.assertIn("🔒 non-OA", text)
        self.assertIn("(no abstract)", text)
        self.assertIn("10.1002/asi.123", text)

    def test_parse_selection_handles_ranges_and_commas(self):
        parse = self.mod.parse_selection
        self.assertEqual(parse("1,3", 10), [0, 2])
        self.assertEqual(parse("1,3,5-8,10", 10), [0, 2, 4, 5, 6, 7, 9])
        self.assertEqual(parse("all", 5), [0, 1, 2, 3, 4])
        self.assertEqual(parse(" ALL ", 3), [0, 1, 2])
        self.assertEqual(parse("", 5), [])
        self.assertEqual(parse("0,100", 5), [])  # out of range
        self.assertEqual(parse("2,1", 5), [0, 1])  # deduped + sorted


class TestTwoPhaseWorkflow(unittest.TestCase):
    def test_collect_records_for_preview_saves_to_workspace(self):
        mod = load_module()
        body = {"topic": "information behavior", "c_mode": {"zotero_collection_path": "deep-research/test"}}

        def fake_fetcher(url, params):
            return {"results": [
                {"id": "W1", "doi": "10.1/test", "title": "Test paper", "publication_year": 2024,
                 "authorships": [{"author": {"display_name": "Alice"}}],
                 "abstract_inverted_index": {"Test": [0]},
                 "open_access": {"is_oa": False, "oa_status": "", "oa_url": ""},
                 "primary_location": {"source": {"display_name": "Test Journal"}},
                 "cited_by_count": 5},
            ]}

        with tempfile.TemporaryDirectory() as tmp:
            records = mod.collect_records_for_preview(body, workspace_path=tmp, fetcher=fake_fetcher)
            self.assertEqual(len(records), 1)
            records_path = Path(tmp) / "literature_records.json"
            self.assertTrue(records_path.exists())
            loaded = json.loads(records_path.read_text())
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0]["title"], "Test paper")

    def test_export_selected_to_zotero_registers_only_selected(self):
        mod = load_module()
        z = FakeZotero()
        records = [{"title": f"Paper{i}", "doi": f"10.{i}/test", "authors": ["Author"], "year": 2025, "venue": "J", "source": "openalex", "is_oa": False, "oa_url": "", "abstract": "abstract"} for i in range(5)]

        with tempfile.TemporaryDirectory() as tmp:
            records_path = Path(tmp) / "literature_records.json"
            records_path.write_text(json.dumps(records, ensure_ascii=False) + "\n")
            result = mod.export_selected_to_zotero(tmp, [0, 2, 4], zotero=z, collection_path="deep-research/test")
            self.assertEqual(result["selected"], 3)
            self.assertEqual(result["total"], 5)
            self.assertEqual(len(z.created_items), 3)
            self.assertEqual(z.created_items[0]["title"], "Paper0")
            self.assertEqual(z.created_items[1]["title"], "Paper2")
            self.assertEqual(z.created_items[2]["title"], "Paper4")

    def test_export_selected_to_zotero_rejects_empty_collection_no_zotero(self):
        mod = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            records_path = Path(tmp) / "literature_records.json"
            records_path.write_text("[]")
            result = mod.export_selected_to_zotero(tmp, [], zotero=None, collection_path="deep-research/test")
            self.assertIn("skipped", result["status"])

    def test_export_selected_to_zotero_writes_success_file(self):
        mod = load_module()
        z = FakeZotero()
        records = [{"title": "Paper", "doi": "10.1/abc", "authors": ["Author"], "year": 2025, "venue": "J", "source": "openalex", "is_oa": True, "oa_url": "", "abstract": "A"}]
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "literature_records.json").write_text(json.dumps(records) + "\n")
            result = mod.export_selected_to_zotero(tmp, [0], zotero=z, collection_path="deep-research/test")
            export_path = Path(tmp) / "zotero_export.json"
            self.assertTrue(export_path.exists())
            export_data = json.loads(export_path.read_text())
            self.assertEqual(export_data["collection_path"], "deep-research/test")

    def test_parse_selection_accepts_newlines_and_spaces(self):
        mod = load_module()
        self.assertEqual(mod.parse_selection("1 2 3\n4", 5), [0, 1, 2, 3])
        self.assertEqual(mod.parse_selection("1, 2, 3", 5), [0, 1, 2])


if __name__ == "__main__":
    unittest.main()
