import json
import subprocess
import sys
from pathlib import Path

import yaml


def test_ingestion_policy_thresholds():
    from conflux.paper_ingestion.ingestion_policy import default_policy, decide_ingestion
    from conflux.paper_ingestion.models import PaperAnalysis, PaperRecord

    paper = PaperRecord(id="p1", title="Relevant paper", pdf_url="https://example.test/p1.pdf")

    deep = PaperAnalysis(paper_id="p1", relevance_score=0.72, reading_level="deep")
    assert decide_ingestion(paper, deep).action == "summary_only"

    full_text = PaperAnalysis(paper_id="p1", relevance_score=0.88, reading_level="deep")
    assert decide_ingestion(paper, full_text, policy=default_policy(allow_full_text=True)).action == "full_text"

    skim = PaperAnalysis(paper_id="p1", relevance_score=0.42, reading_level="skim")
    assert decide_ingestion(paper, skim).action == "metadata_only"

    skipped = PaperAnalysis(paper_id="p1", relevance_score=0.12, reading_level="skip")
    assert decide_ingestion(paper, skipped).action == "skip"


def test_summary_only_paper_becomes_document():
    from conflux.knowledge.paper_indexer import paper_to_documents
    from conflux.paper_ingestion.ingestion_policy import decide_ingestion
    from conflux.paper_ingestion.models import PaperAnalysis, PaperRecord

    paper = PaperRecord(
        id="https://arxiv.org/abs/2607.00001",
        title="Knowledge-Grounded Agents for Geospatial Data Fusion",
        abstract="Agents verify geospatial data fusion workflows.",
        authors=["A. Researcher"],
        source="arxiv",
        url="https://arxiv.org/abs/2607.00001",
        pdf_url="https://arxiv.org/pdf/2607.00001",
        categories=["cs.AI"],
    )
    analysis = PaperAnalysis(
        paper_id=paper.id,
        relevance_score=0.72,
        reading_level="deep",
        matched_questions=["How can GIS agents verify data fusion?"],
        method_summary="Agents use knowledge graphs for verification.",
        metadata={"matched_keywords": ["geospatial data fusion"]},
    )
    decision = decide_ingestion(paper, analysis)
    docs = paper_to_documents(paper, analysis, decision)

    assert len(docs) == 1
    assert docs[0].metadata["source_type"] == "LocalPaper"
    assert docs[0].metadata["paper_id"] == paper.id
    assert docs[0].metadata["chunk_id"] == "paper:2607.00001#summary"
    assert "## Abstract" in docs[0].page_content
    assert "geospatial data fusion" in docs[0].page_content


def test_full_text_decision_emits_pdf_chunks_when_text_available():
    from conflux.knowledge.paper_indexer import paper_to_documents
    from conflux.paper_ingestion.ingestion_policy import default_policy, decide_ingestion
    from conflux.paper_ingestion.models import PaperAnalysis, PaperRecord

    paper = PaperRecord(
        id="2607.00001",
        title="Knowledge-Grounded Agents for Geospatial Data Fusion",
        abstract="Agents verify geospatial data fusion workflows.",
        pdf_url="https://arxiv.org/pdf/2607.00001.pdf",
    )
    analysis = PaperAnalysis(
        paper_id=paper.id,
        relevance_score=0.9,
        reading_level="deep",
        method_summary="Knowledge graphs guide verification.",
    )
    decision = decide_ingestion(paper, analysis, policy=default_policy(allow_full_text=True))

    docs = paper_to_documents(
        paper,
        analysis,
        decision,
        full_text="Full paper text about geospatial data fusion verification and agent auditing.",
        full_text_status="success",
    )

    assert decision.action == "full_text"
    assert len(docs) == 2
    assert docs[0].metadata["content_scope"] == "summary"
    assert docs[1].metadata["content_scope"] == "full_text"
    assert docs[1].metadata["chunk_id"] == "paper:2607.00001#fulltext-0"
    assert "Full paper text" in docs[1].page_content


def test_skip_paper_not_indexed():
    from conflux.knowledge.paper_indexer import paper_to_documents
    from conflux.paper_ingestion.ingestion_policy import decide_ingestion
    from conflux.paper_ingestion.models import PaperAnalysis, PaperRecord

    paper = PaperRecord(id="p2", title="Off-topic paper")
    analysis = PaperAnalysis(paper_id="p2", relevance_score=0.05, reading_level="skip")
    decision = decide_ingestion(paper, analysis)

    assert decision.action == "skip"
    assert paper_to_documents(paper, analysis, decision) == []


def test_metadata_only_paper_not_added_as_factual_document():
    from conflux.knowledge.paper_indexer import paper_to_documents
    from conflux.paper_ingestion.ingestion_policy import decide_ingestion
    from conflux.paper_ingestion.models import PaperAnalysis, PaperRecord

    paper = PaperRecord(id="p3", title="Moderately relevant paper")
    analysis = PaperAnalysis(paper_id="p3", relevance_score=0.42, reading_level="skim")
    decision = decide_ingestion(paper, analysis)

    assert decision.action == "metadata_only"
    assert paper_to_documents(paper, analysis, decision) == []


def test_pdf_downloader_reuses_cached_pdf(tmp_path):
    from conflux.paper_ingestion.pdf_downloader import PDFDownloader, arxiv_pdf_url, safe_pdf_id

    cached = tmp_path / "2607.00001.pdf"
    cached.write_bytes(b"%PDF cached content")

    downloader = PDFDownloader(tmp_path)

    assert safe_pdf_id("https://arxiv.org/abs/2607.00001") == "2607.00001"
    assert arxiv_pdf_url("2607.00001") == "https://arxiv.org/pdf/2607.00001.pdf"
    assert downloader.download("https://arxiv.org/abs/2607.00001") == cached


def test_pdf_text_extractor_missing_file_is_structured(tmp_path):
    from conflux.paper_ingestion.pdf_text import extract_pdf_text

    result = extract_pdf_text(tmp_path / "missing.pdf")

    assert result.status == "missing"
    assert result.text == ""


def test_paper_citation_round_trip():
    from conflux.knowledge.citation_resolver import knowledge_source_from_metadata, paper_citation_ref

    metadata = {
        "source_type": "LocalPaper",
        "paper_id": "2607.00001",
        "paper_title": "Knowledge-Grounded Agents",
        "paper_url": "https://arxiv.org/abs/2607.00001",
        "chunk_id": "paper:2607.00001#summary",
        "ingestion_action": "summary_only",
    }

    assert paper_citation_ref(metadata) == "LocalPaper:2607.00001:paper:2607.00001#summary"
    source = knowledge_source_from_metadata(metadata)
    assert source.source_type == "LocalPaper"
    assert source.metadata["citation_ref"] == paper_citation_ref(metadata)


def test_promote_inbox_writes_documents_and_manifest(tmp_path):
    from conflux.knowledge.paper_indexer import promote_inbox
    from conflux.paper_ingestion.pipeline import build_inbox_from_fixture

    inbox_dir = tmp_path / "inbox"
    out_dir = tmp_path / "promoted"
    build_inbox_from_fixture(
        "profiles/example_gis_agent.yaml",
        "tests/fixtures/papers/arxiv_sample.json",
        out_dir=inbox_dir,
    )

    result = promote_inbox(inbox_dir / "paper_inbox.json", out_dir=out_dir)

    assert len(result.documents) == 1
    assert result.artifacts is not None
    assert result.artifacts.manifest_path.exists()
    assert result.artifacts.sources_path.exists()
    written = sorted((out_dir / "papers").glob("*.md"))
    assert len(written) == 1
    text = written[0].read_text(encoding="utf-8")
    assert "source_type: LocalPaper" in text
    assert "citation_ref: LocalPaper:" in text
    manifest = json.loads(result.artifacts.manifest_path.read_text(encoding="utf-8"))
    assert manifest["decisions"][0]["action"] == "summary_only"


def test_document_markdown_quotes_yaml_special_section_values():
    from langchain_core.documents import Document
    from conflux.knowledge.paper_indexer import _document_markdown

    markdown = _document_markdown(Document(
        page_content="# Paper\n\nEvidence.",
        metadata={
            "source_type": "LocalPaper",
            "paper_id": "2503.07675v2",
            "chunk_id": "paper:2503.07675v2#fulltext-15",
            "paper_section": "[8] citation-like heading",
            "full_text_requested": True,
            "full_text_downloaded": True,
            "full_text_extracted": True,
            "full_text_indexed": True,
        },
    ))

    front_matter = markdown.split("---\n", 2)[1]
    parsed = yaml.safe_load(front_matter)
    assert parsed["paper_section"] == "[8] citation-like heading"
    assert parsed["full_text_indexed"] is True


def test_papers_cli_promote_writes_reviewable_outputs(tmp_path):
    root = Path(__file__).resolve().parents[1]
    inbox_dir = tmp_path / "paper-inbox"
    out_dir = tmp_path / "paper-knowledge"

    inbox = subprocess.run(
        [
            sys.executable,
            "-m",
            "conflux.paper_ingestion.cli",
            "inbox",
            "--profile",
            "profiles/example_gis_agent.yaml",
            "--fixture",
            "tests/fixtures/papers/arxiv_sample.json",
            "--out-dir",
            str(inbox_dir),
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert inbox.returncode == 0, inbox.stderr

    promoted = subprocess.run(
        [
            sys.executable,
            "-m",
            "conflux.paper_ingestion.cli",
            "promote",
            str(inbox_dir / "paper_inbox.json"),
            "--out-dir",
            str(out_dir),
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )

    assert promoted.returncode == 0, promoted.stderr
    assert "Promoted documents: 1" in promoted.stdout
    assert "Indexed documents: 0" in promoted.stdout
    assert (out_dir / "paper_promotion_manifest.json").exists()
    assert (out_dir / "paper_knowledge_sources.json").exists()


def test_retrieval_eval_includes_paper_cases():
    payload = json.loads(Path("data/documents/rag-eval-test-cases.json").read_text(encoding="utf-8"))
    cases = payload["test_suites"]["retrieval_quality"]["test_cases"]
    paper_cases = [case for case in cases if str(case["id"]).startswith("paper_")]

    assert len(paper_cases) >= 5
    assert all(case["expected_source"] == "RAG" for case in paper_cases)
    assert any("LocalPaper" in case.get("required_metadata", []) for case in paper_cases)
