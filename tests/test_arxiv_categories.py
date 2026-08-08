"""arXiv category filtering tests."""

from __future__ import annotations

import urllib.parse

import pytest

from conflux.paper_ingestion.arxiv_source import search_arxiv


def _capture(monkeypatch, results_xml):
    captured = {}

    def fake_urlopen(url, timeout=30):
        captured["url"] = url
        class _Resp:
            def read(self):
                return results_xml.encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False
        return _Resp()

    monkeypatch.setattr("conflux.paper_ingestion.arxiv_source.urllib.request.urlopen", fake_urlopen)
    return captured


def _empty_feed() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>x</title></feed>"""


def test_search_arxiv_appends_category_constraint(monkeypatch):
    captured = _capture(monkeypatch, _empty_feed())
    search_arxiv("GIS agent OR geospatial LLM", max_results=5, categories=["cs.AI", "cs.CV"])
    url = captured["url"]
    params = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    assert "cat:cs.AI OR cat:cs.CV" in params["search_query"][0]
    assert "GIS agent OR geospatial LLM" in params["search_query"][0]


def test_search_arxiv_without_categories_keeps_query(monkeypatch):
    captured = _capture(monkeypatch, _empty_feed())
    search_arxiv("GIS agent", max_results=5)
    params = urllib.parse.parse_qs(urllib.parse.urlparse(captured["url"]).query)
    assert params["search_query"][0] == "GIS agent"
