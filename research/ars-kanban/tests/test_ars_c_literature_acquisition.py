"""Tests for ARS C mode Phase 2-1 literature acquisition engine."""

import importlib.util
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


if __name__ == "__main__":
    unittest.main()
