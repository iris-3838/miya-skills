"""Tests for ARS C mode Phase 2-1 J-STAGE scraping and CiNii Research collectors."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path("/opt/data/scripts/ars-kanban/c_literature_acquisition.py")


def load_module():
    spec = importlib.util.spec_from_file_location("ars_c_lit", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


# =========================================================================
# J-STAGE scraping tests
# =========================================================================

JSTAGE_SAMPLE_HTML = """<!DOCTYPE html>
<html>
<head><title>JSLIS Vol.71 No.1</title></head>
<body>
<div class="listview-contents">
  <div class="listview-article">
    <p class="listview-article__title">
      <a href="https://www.jstage.jst.go.jp/article/jslis/71/1/71_1/_article/-char/ja"
         class="bluelink-style customTooltip"
         title="情報概念の哲学的基盤：BatesとHjørlandの比較">情報概念の哲学的基盤：BatesとHjørlandの比較</a>
    </p>
    <p class="listview-article__author">山田 太郎, 鈴木 花子</p>
    <p class="listview-article__vol">JSLIS 71(1): 1-20 (2025)</p>
    <a href="https://doi.org/10.1234/jslis.71.1">DOI: 10.1234/jslis.71.1</a>
    <a href="https://www.jstage.jst.go.jp/article/jslis/71/1/71_1/_pdf/-char/ja" class="bluelink-style">PDF</a>
  </div>
  <div class="listview-article">
    <p class="listview-article__title">
      <a href="https://www.jstage.jst.go.jp/article/jslis/71/1/71_18/_article/-char/ja"
         class="bluelink-style customTooltip"
         title="図書館情報学における情報概念の変遷">図書館情報学における情報概念の変遷</a>
    </p>
    <p class="listview-article__author">田中 次郎</p>
    <p class="listview-article__vol">JSLIS 71(1): 21-40 (2025)</p>
  </div>
</div>
</body>
</html>"""


class TestJstageScraping(unittest.TestCase):
    def test_parse_jstage_listview_extracts_articles(self):
        mod = load_module()
        records = mod.parse_jstage_listview(JSTAGE_SAMPLE_HTML, journal_key="jslis")
        self.assertEqual(len(records), 2)

    def test_jstage_record_has_expected_fields(self):
        mod = load_module()
        records = mod.parse_jstage_listview(JSTAGE_SAMPLE_HTML, journal_key="jslis")
        r = records[0]
        self.assertEqual(r["title"], "情報概念の哲学的基盤：BatesとHjørlandの比較")
        self.assertEqual(r["authors"], ["山田 太郎", "鈴木 花子"])
        self.assertEqual(r["doi"], "10.1234/jslis.71.1")
        self.assertEqual(r["source"], "jstage")
        self.assertEqual(r["venue"], "JSLIS")
        self.assertTrue(r["is_oa"])
        self.assertIn("pdf", r["oa_url"])

    def test_jstage_record_without_doi_is_ok(self):
        mod = load_module()
        records = mod.parse_jstage_listview(JSTAGE_SAMPLE_HTML, journal_key="jslis")
        self.assertEqual(records[1]["doi"], "")
        self.assertEqual(records[1]["title"], "図書館情報学における情報概念の変遷")


# =========================================================================
# CiNii Research OpenSearch tests
# =========================================================================

CINII_SAMPLE_JSON = {
    "@context": "...",
    "items": [
        {
            "@id": "https://cir.nii.ac.jp/crid/123456789",
            "title": "情報概念の再検討：BatesとHjørlandの理論的対立",
            "dc:creator": ["山田 太郎", "鈴木 花子"],
            "prism:publicationName": "日本図書館情報学会誌",
            "prism:issn": "1340-3713",
            "prism:volume": "70",
            "prism:number": "2",
            "prism:startingPage": "15",
            "prism:endingPage": "30",
            "prism:publicationDate": "2024-03",
            "prism:doi": "10.1234/jslis.70.2.15",
            "description": "<jats:p>本論文は情報概念の理論的基盤を検討する。</jats:p>",
            "link": "https://cir.nii.ac.jp/crid/123456789",
            "rdfs:seeAlso": [{"@id": "https://cir.nii.ac.jp/crid/123456789"}],
            "dc:identifier": [
                {"@type": "cir:NAID", "@value": "40021056871"},
                {"@type": "cir:DOI", "@value": "10.1234/jslis.70.2.15"},
            ],
        },
        {
            "@id": "https://cir.nii.ac.jp/crid/987654321",
            "title": "Domain Analysis and Information Science",
            "dc:creator": ["Birger Hjørland", "Jesper W. Schneider"],
            "prism:publicationName": "Knowledge Organization",
            "prism:publicationDate": "2023",
            "description": "A methodological paper without JATS tags",
        },
    ],
}


class TestCiniiOpenSearch(unittest.TestCase):
    def test_parse_cinii_opensearch_extracts_items(self):
        mod = load_module()
        records = mod.parse_cinii_opensearch(CINII_SAMPLE_JSON)
        self.assertEqual(len(records), 2)

    def test_cinii_record_has_normalized_fields(self):
        mod = load_module()
        records = mod.parse_cinii_opensearch(CINII_SAMPLE_JSON)
        r = records[0]
        self.assertEqual(r["title"], "情報概念の再検討：BatesとHjørlandの理論的対立")
        self.assertEqual(r["authors"], ["山田 太郎", "鈴木 花子"])
        self.assertEqual(r["doi"], "10.1234/jslis.70.2.15")
        self.assertEqual(r["venue"], "日本図書館情報学会誌")
        self.assertEqual(r["year"], 2024)
        self.assertEqual(r["source"], "cinii")
        self.assertIn("理論的基盤", r.get("abstract", ""))
        self.assertFalse(r["is_oa"])

    def test_cinii_record_finds_doi_in_dc_identifier_array(self):
        mod = load_module()
        records = mod.parse_cinii_opensearch(CINII_SAMPLE_JSON)
        r = records[0]
        self.assertEqual(r["doi"], "10.1234/jslis.70.2.15")

    def test_cinii_record_without_doi_is_ok(self):
        mod = load_module()
        records = mod.parse_cinii_opensearch(CINII_SAMPLE_JSON)
        r = records[1]
        self.assertEqual(r["doi"], "")
        self.assertEqual(r["authors"], ["Birger Hjørland", "Jesper W. Schneider"])


# =========================================================================
# Integration test: all collectors merged
# =========================================================================

class TestCollectorIntegration(unittest.TestCase):
    def test_collect_records_for_preview_calls_all_sources(self):
        """Verify multi-source dispatch calls OpenAlex, J-STAGE, and CiNii."""
        mod = load_module()
        body = {"topic": "情報概念", "c_mode": {"zotero_collection_path": "deep-research/test"}}

        def fake_openalex(url, params):
            return {"results": [
                {"id": "W1", "doi": "10.1/test", "title": "International paper",
                 "publication_year": 2024, "authorships": [{"author": {"display_name": "Alice"}}],
                 "abstract_inverted_index": {"Test": [0]},
                 "open_access": {"is_oa": True, "oa_status": "gold", "oa_url": ""},
                 "primary_location": {"source": {"display_name": "Intl J"}},
                 "cited_by_count": 5},
            ]}

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(mod, "search_jstage_recent", return_value=[
                {"title": "Jp paper", "authors": ["Taro"], "doi": "", "source": "jstage",
                 "year": 2025, "venue": "JSLIS", "is_oa": True, "abstract": ""},
            ]):
                with patch.object(mod, "fetch_json") as mock_fetch:
                    mock_fetch.return_value = CINII_SAMPLE_JSON
                    records = mod.collect_records_for_preview(
                        body, workspace_path=tmp, fetcher=fake_openalex,
                    )

        self.assertGreaterEqual(len(records), 2)
        sources = {r["source"] for r in records}
        self.assertIn("openalex", sources)
        self.assertIn("jstage", sources)
