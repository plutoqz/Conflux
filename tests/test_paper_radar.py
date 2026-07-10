import json
import subprocess
import sys
from pathlib import Path


def test_keyword_relevance_scoring_is_deterministic():
    from conflux.paper_ingestion import load_paper_fixture
    from conflux.paper_ingestion.dedup import deduplicate_papers
    from conflux.paper_ingestion.filters import apply_negative_filters
    from conflux.paper_ingestion.scorer import score_papers
    from conflux.research_profile import load_profile

    profile = load_profile("profiles/example_gis_agent.yaml")
    papers = apply_negative_filters(
        deduplicate_papers(load_paper_fixture("tests/fixtures/papers/arxiv_sample.json")),
        profile,
    )
    scored = score_papers(papers, profile)

    assert len(scored) == 1
    paper, score = scored[0]
    assert paper.id.endswith("2607.00001")
    assert score.score >= 0.62
    assert "geospatial data fusion" in score.matched_keywords
    assert score.reasons


def test_reading_level_thresholds():
    from conflux.paper_ingestion.scorer import reading_level_for_score

    assert reading_level_for_score(0.80) == "deep"
    assert reading_level_for_score(0.40) == "skim"
    assert reading_level_for_score(0.10) == "skip"


def test_analyze_papers_sets_reading_level_and_reasons():
    from conflux.paper_ingestion import load_paper_fixture
    from conflux.paper_ingestion.analyzer import analyze_papers
    from conflux.paper_ingestion.dedup import deduplicate_papers
    from conflux.paper_ingestion.filters import apply_negative_filters
    from conflux.research_profile import load_profile

    profile = load_profile("profiles/example_gis_agent.yaml")
    papers = apply_negative_filters(
        deduplicate_papers(load_paper_fixture("tests/fixtures/papers/arxiv_sample.json")),
        profile,
    )
    analyzed = analyze_papers(papers, profile)

    assert analyzed[0][1].reading_level == "deep"
    assert analyzed[0][1].citation_value == "high"
    assert analyzed[0][1].metadata["score_reasons"]
    assert "language model agents" in analyzed[0][1].method_summary


def test_inbox_report_contains_scores_and_reasons(tmp_path):
    from conflux.paper_ingestion.pipeline import build_inbox_from_fixture

    result = build_inbox_from_fixture(
        "profiles/example_gis_agent.yaml",
        "tests/fixtures/papers/arxiv_sample.json",
        out_dir=tmp_path,
    )

    markdown = result.artifacts.markdown_path.read_text(encoding="utf-8")
    payload = json.loads(result.artifacts.json_path.read_text(encoding="utf-8"))

    assert "# Paper Radar Inbox: GIS Agent Research" in markdown
    assert "## Deep Reads" in markdown
    assert "Knowledge-Grounded Agents for Geospatial Data Fusion" in markdown
    assert "matched keywords" in markdown
    assert payload["profile_id"] == "gis-agent-research"
    assert payload["stats"]["after_filter"] == 1
    assert payload["papers"][0]["analysis"]["reading_level"] == "deep"


def test_paper_inbox_cli_writes_markdown_and_json(tmp_path):
    root = Path(__file__).resolve().parents[1]
    out_dir = tmp_path / "paper-inbox"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "conflux.papers",
            "inbox",
            "--profile",
            "profiles/example_gis_agent.yaml",
            "--fixture",
            "tests/fixtures/papers/arxiv_sample.json",
            "--out-dir",
            str(out_dir),
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Paper inbox built for profile: gis-agent-research" in result.stdout
    assert "Deep/skim/skip: 1/0/0" in result.stdout
    assert (out_dir / "paper_inbox.md").exists()
    assert (out_dir / "paper_inbox.json").exists()
