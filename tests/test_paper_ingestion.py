import json
import subprocess
import sys
from pathlib import Path


def test_fixture_loader_returns_paper_records():
    from conflux.paper_ingestion import load_paper_fixture

    papers = load_paper_fixture("tests/fixtures/papers/arxiv_sample.json")

    assert len(papers) == 3
    assert papers[0].id == "https://arxiv.org/abs/2607.00001"
    assert papers[0].title == "Knowledge-Grounded Agents for Geospatial Data Fusion"
    assert papers[0].authors == ["A. Researcher", "B. Cartographer"]
    assert papers[0].pdf_url == "https://arxiv.org/pdf/2607.00001"
    assert papers[0].published_at is not None


def test_arxiv_record_normalization():
    from conflux.paper_ingestion.arxiv_source import normalize_arxiv_entry

    paper = normalize_arxiv_entry({
        "id": "https://arxiv.org/abs/2607.12345",
        "title": "  Agentic GIS\nWorkflows  ",
        "summary": "  Agents verify GIS workflows.\n",
        "authors": [{"name": "Ada"}, {"name": "Grace"}],
        "published": "2026-07-03T00:00:00Z",
        "categories": ["cs.AI"],
        "links": [
            {"href": "https://arxiv.org/pdf/2607.12345", "title": "pdf", "type": "application/pdf"}
        ],
    })

    assert paper.id == "2607.12345"
    assert paper.source == "arxiv"
    assert paper.title == "Agentic GIS Workflows"
    assert paper.authors == ["Ada", "Grace"]
    assert paper.pdf_url == "https://arxiv.org/pdf/2607.12345"
    assert paper.categories == ["cs.AI"]


def test_dedup_by_id_and_title():
    from conflux.paper_ingestion import deduplicate_papers, load_paper_fixture

    papers = load_paper_fixture("tests/fixtures/papers/arxiv_sample.json")
    unique = deduplicate_papers(papers)

    assert len(unique) == 2
    assert unique[0].id == "https://arxiv.org/abs/2607.00001"
    assert "cs.DB" in unique[0].categories


def test_negative_filter_removes_off_topic_paper():
    from conflux.paper_ingestion import apply_negative_filters, deduplicate_papers, load_paper_fixture
    from conflux.research_profile import load_profile

    profile = load_profile("profiles/example_gis_agent.yaml")
    papers = deduplicate_papers(load_paper_fixture("tests/fixtures/papers/arxiv_sample.json"))
    kept = apply_negative_filters(papers, profile)

    assert len(kept) == 1
    assert kept[0].title == "Knowledge-Grounded Agents for Geospatial Data Fusion"


def test_parse_arxiv_feed():
    from conflux.paper_ingestion.arxiv_source import parse_arxiv_feed

    feed = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2607.00003v1</id>
    <title>Auditable Agent Workflows</title>
    <summary>Workflow provenance for agent systems.</summary>
    <published>2026-07-04T00:00:00Z</published>
    <author><name>D. Engineer</name></author>
    <arxiv:doi>10.0000/example</arxiv:doi>
    <category term="cs.SE" />
    <link href="http://arxiv.org/abs/2607.00003v1" rel="alternate" />
    <link href="http://arxiv.org/pdf/2607.00003v1" type="application/pdf" title="pdf" />
  </entry>
</feed>
"""
    papers = parse_arxiv_feed(feed, matched_query="all:agent")

    assert len(papers) == 1
    assert papers[0].id == "2607.00003v1"
    assert papers[0].doi == "10.0000/example"
    assert papers[0].matched_queries == ["all:agent"]


def test_profile_arxiv_queries_combine_topic_direction_and_category_constraints():
    from conflux.paper_ingestion.arxiv_source import profile_arxiv_queries
    from conflux.research_profile import ResearchProfile

    profile = ResearchProfile(
        id="disaster-kg",
        name="Disaster KG",
        fields=["cs.AI", "physics.geo-ph", "knowledge representation"],
        research_questions=[],
        keywords=["knowledge graph", "knowledge representation", "natural disaster", "emergency response"],
    )

    queries = profile_arxiv_queries(profile, max_queries=3)

    assert len(queries) == 3
    assert 'all:"knowledge graph" AND all:"natural disaster"' in queries[0]
    assert 'all:"knowledge graph" AND all:"emergency response"' in queries[1]
    assert 'all:"knowledge graph" OR all:"knowledge representation"' in queries[2]
    assert 'all:"natural disaster" OR all:"emergency response"' in queries[2]
    assert "(cat:cs.AI OR cat:physics.geo-ph)" in queries[0]
    assert "knowledge representation" not in queries[0]


def test_papers_cli_load_fixture_and_crawl_dry_run():
    root = Path(__file__).resolve().parents[1]

    load_result = subprocess.run(
        [sys.executable, "-m", "conflux.paper_ingestion.cli", "load-fixture", "tests/fixtures/papers/arxiv_sample.json"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert load_result.returncode == 0, load_result.stderr
    assert "Loaded 2 unique papers" in load_result.stdout

    dry_run = subprocess.run(
        [
            sys.executable,
            "-m",
            "conflux.paper_ingestion.cli",
            "crawl",
            "--profile",
            "profiles/example_gis_agent.yaml",
            "--source",
            "arxiv",
            "--dry-run",
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert dry_run.returncode == 0, dry_run.stderr
    payload = json.loads(dry_run.stdout)
    assert payload["source"] == "arxiv"
    assert payload["profile_id"] == "gis-agent-research"
    assert payload["queries"]
