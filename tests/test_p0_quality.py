"""P0 research quality regression fixtures."""

from __future__ import annotations

import json

from langchain_core.documents import Document
from langchain_core.messages import AIMessage


class ReviewModel:
    def __init__(self, responses=None, *, error: Exception | None = None):
        self.responses = list(responses or [])
        self.error = error
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        if self.error is not None:
            raise self.error
        if not self.responses:
            raise TimeoutError("timed out")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return AIMessage(content=response)


def _review_json(count: int, *, confidence: float = 0.9) -> str:
    return json.dumps([
        {
            "relevance": "relevant",
            "research_value": "method",
            "evidence_quality": "The candidate directly addresses the query.",
            "reasoning": "Semantic topic and method alignment.",
            "confidence": confidence,
            "needs_deeper_review": False,
        }
        for _ in range(count)
    ])


def _candidates(count: int) -> list[dict]:
    return [
        {"id": f"p{index}", "title": f"Paper {index}", "text": f"Research method {index}", "deterministic_score": 0.2}
        for index in range(count)
    ]


def test_semantic_review_isolated_by_batch_and_preserves_deterministic_score():
    from conflux.builtin.research.plugin import evidence_review
    from conflux.core.contracts import StepStatus
    from conflux.sdk.testing import make_plugin_context

    model = ReviewModel([_review_json(4), TimeoutError("APITimeoutError: Request timed out")])
    result = evidence_review(
        make_plugin_context(model=model),
        query="research methods",
        candidates=_candidates(5),
    )

    reviews = result.output["reviews"]
    assert result.status == StepStatus.UNREVIEWED
    assert result.output["reviewed_count"] == 4
    assert result.output["unreviewed_count"] == 1
    assert sum(item["relevance"] == "unreviewed" for item in reviews) == 1
    failed = reviews[-1]
    assert failed["candidate_status"] == "provisional"
    assert failed["deterministic_score"] == 0.2
    assert failed["semantic_score"] is None
    assert failed["error_code"] == "llm_timeout"
    assert model.calls == 3  # successful batch + two bounded attempts for the failed batch


def test_deep_review_failure_keeps_initial_semantic_review():
    from conflux.builtin.research.plugin import evidence_review
    from conflux.sdk.testing import make_plugin_context

    model = ReviewModel([_review_json(2, confidence=0.5), TimeoutError("timed out")])
    result = evidence_review(
        make_plugin_context(model=model),
        query="research methods",
        candidates=_candidates(2),
    )

    reviews = result.output["reviews"]
    assert all(item["review_status"] == "reviewed" for item in reviews)
    assert all(item["candidate_status"] == "needs_deeper_review" for item in reviews)
    assert all(item["deep_review_status"] == "unreviewed" for item in reviews)
    assert all(item["relevance"] == "relevant" for item in reviews)


def test_pipeline_does_not_convert_unreviewed_candidates_to_skip():
    from conflux.paper_ingestion.models import PaperAnalysis, PaperRecord
    from conflux.paper_ingestion.pipeline import _apply_llm_review
    from conflux.research_profile import ResearchProfile

    profile = ResearchProfile(id="p0", name="P0", fields=[], research_questions=[], keywords=["research"])
    papers = [PaperRecord(id="p1", title="Paper", abstract="Research paper")]
    analysis = PaperAnalysis(paper_id="p1", relevance_score=0.41, reading_level="skim")
    model = ReviewModel(error=TimeoutError("timed out"))
    stats = {}

    _apply_llm_review(
        list(zip(papers, [analysis])),
        profile,
        review_model=model,
        stats=stats,
    )

    assert analysis.reading_level == "skim"
    assert analysis.relevance_score == 0.41
    assert analysis.metadata["review_status"] == "unreviewed"
    assert analysis.metadata["candidate_status"] == "provisional"
    assert analysis.metadata["deterministic_score"] == 0.41
    assert stats["unreviewed"] == 1


def test_web_cascade_records_fallback_provider(monkeypatch):
    from conflux.tools import web

    monkeypatch.setenv("BING_SEARCH_API_KEY", "test-key")
    monkeypatch.setattr(web, "_search_duckduckgo", lambda query, max_results=5: (_ for _ in ()).throw(TimeoutError("ddg timeout")))
    monkeypatch.setattr(web, "_search_bing", lambda query, max_results=5: [{
        "title": "Flood research",
        "snippet": "A useful result with enough context for semantic review.",
        "url": "https://example.gov/flood",
    }])
    monkeypatch.setattr(web, "get", lambda *path, default=None: {
        ("web_search", "fallback_providers"): ["duckduckgo", "bing"],
        ("web_search", "max_results"): 3,
        ("research", "max_rewrite_attempts"): 0,
    }.get(tuple(path), default))

    results, trace, used = web._search_cascade(
        ["flood research"],
        3,
        preferred="duckduckgo",
        required_results=1,
    )

    assert results[0]["provider_source"] == "bing"
    assert used == ["duckduckgo", "bing"]
    assert trace[0]["status"] == "failed"
    assert trace[1]["provider"] == "bing"
    assert trace[1]["status"] == "success"


def test_search_web_integration_uses_bing_after_garbage_primary(monkeypatch):
    from conflux.source_status import parse_source_results
    from conflux.tools import web

    monkeypatch.setenv("BING_SEARCH_API_KEY", "test-key")
    monkeypatch.setattr(web, "_search_duckduckgo", lambda query, max_results=5: [{
        "title": "Social page",
        "snippet": "Unrelated page",
        "url": "https://www.instagram.com/example",
    }])
    monkeypatch.setattr(web, "_search_bing", lambda query, max_results=5: [{
        "title": "Flood risk report",
        "snippet": "Official flood risk assessment report with methods and findings.",
        "url": "https://example.gov/flood-risk",
    }])
    monkeypatch.setattr(web, "_search_academic_sources", lambda query, max_results: [])
    monkeypatch.setattr(web, "_fetch_web_results", lambda results: [{
        **item,
        "fetch": web.FetchedContent(
            url=item["url"],
            final_url=item["url"],
            title=item["title"],
            text="Official flood risk assessment research reports methods and findings for flood planning.",
            content_type="text/html",
            content_kind="html",
            status="success",
            retrieved_at="2026-07-18T00:00:00+00:00",
            content_hash="abc",
        ),
    } for item in results])
    monkeypatch.setattr(web, "get", lambda *path, default=None: {
        ("web_search", "provider"): "duckduckgo",
        ("web_search", "fallback_providers"): ["duckduckgo", "bing"],
        ("web_search", "max_results"): 3,
        ("research", "max_rewrite_attempts"): 0,
    }.get(tuple(path), default))

    parsed = parse_source_results(str(web.search_web.invoke({"query": "flood report"})))
    result = parsed[-1]
    trace = result.metadata["provider_trace"]
    assert result.status in {"success", "low_relevance"}
    assert any(item["provider"] == "bing" and item["status"] == "success" for item in trace)
    assert "example.gov" in result.content


def test_query_plan_contains_bilingual_rewrites_for_limitations():
    from conflux.query_planner import plan_queries

    plan = plan_queries("深度估计的内涝模型有哪些局限性", target="rag", max_subqueries=6)
    text = " ".join(plan.to_dict()["bilingual_queries"] + plan.subqueries).lower()
    assert "urban flooding" in text
    assert "limitations" in text
    assert "future work" in text


def test_rag_tool_recalls_english_document_from_chinese_query():
    from conflux.source_status import parse_source_results
    from conflux.tools.rag import create_rag_tool

    class Retriever:
        def search(self, query):
            if "urban flooding" in query.lower() or "limitations" in query.lower():
                return [Document(
                    page_content="Urban flooding depth estimation has limitations under sparse sensors.",
                    metadata={
                        "chunk_id": "paper#limitations",
                        "source": "paper-en",
                        "paper_section": "limitations",
                        "query_dense_score": 0.82,
                    },
                )]
            return []

    parsed = parse_source_results(str(create_rag_tool(Retriever()).invoke({
        "query": "内涝深度估计模型有哪些局限性",
    })))
    result = parsed[-1]
    assert result.status == "success"
    assert result.metadata["query_rewrites"]
    assert "paper-en" in result.metadata["matched_sources"]


def test_rag_tool_calls_injected_query_rewriter_once():
    from conflux.source_status import parse_source_results
    from conflux.tools.rag import create_rag_tool

    class CountingRewriter:
        def __init__(self):
            self.calls = 0

        def rewrite(self, query, *, target="rag"):
            self.calls += 1
            return ["urban flooding limitations"]

    class Retriever:
        def search(self, query):
            return [Document(
                page_content="Urban flooding models have documented limitations under sparse observations.",
                metadata={
                    "chunk_id": "paper#limitations",
                    "source": "paper-en",
                    "paper_section": "limitations",
                    "query_dense_score": 0.9,
                },
            )]

    rewriter = CountingRewriter()
    parsed = parse_source_results(str(create_rag_tool(
        Retriever(),
        query_rewriter=rewriter,
    ).invoke({"query": "urban flooding limitations"})))

    assert parsed[-1].status in {"success", "low_relevance"}
    assert rewriter.calls == 1


def test_dense_score_is_current_query_score_and_not_paper_discovery_score():
    from conflux.rag.retriever import HybridRetriever

    class VectorStore:
        def similarity_search_with_score(self, query, k):
            return [Document(
                page_content="English paper about flood depth estimation limitations.",
                metadata={"chunk_id": "p#limitations", "relevance_score": 0.99},
            ),  # type: ignore[misc]
            ]

        def get(self, include=None):
            return {
                "ids": ["p#limitations"],
                "documents": ["English paper about flood depth estimation limitations."],
                "metadatas": [{"chunk_id": "p#limitations", "relevance_score": 0.99}],
            }

    # Return the proper Chroma tuple shape while retaining legacy metadata.
    store = VectorStore()
    store.similarity_search_with_score = lambda query, k: [(Document(
        page_content="English paper about flood depth estimation limitations.",
        metadata={"chunk_id": "p#limitations", "relevance_score": 0.99},
    ), 0.25)]
    doc = HybridRetriever(store).search("内涝模型局限性")[0]
    assert doc.metadata["dense_distance"] == 0.25
    assert doc.metadata["dense_score"] < 0.9
    assert doc.metadata["score_source"] == "current_query_dense"


def test_rag_score_does_not_use_legacy_relevance_score_as_dense_hint():
    from conflux.tools.rag import _score_docs

    scored = _score_docs("query unique term", [Document(
        page_content="Unrelated text.",
        metadata={"chunk_id": "legacy", "relevance_score": 1.0},
    )])
    assert scored[0]["breakdown"]["dense_hint"] is None
    assert scored[0]["score"] < 0.25


def test_full_text_chunks_keep_section_metadata_and_four_state_flags():
    from conflux.knowledge.paper_indexer import _full_text_documents
    from conflux.paper_ingestion.ingestion_policy import default_policy, decide_ingestion
    from conflux.paper_ingestion.models import PaperAnalysis, PaperRecord

    paper = PaperRecord(id="p-section", title="Sectioned paper", abstract="Abstract", pdf_url="https://example.test/p.pdf")
    analysis = PaperAnalysis(paper_id=paper.id, relevance_score=0.9, reading_level="deep")
    decision = decide_ingestion(paper, analysis, policy=default_policy(allow_full_text=True))
    docs = _full_text_documents(
        paper,
        analysis,
        decision,
        "## Methods\nA method paragraph.\n\n## Limitations\nA limitation paragraph.",
        chunk_chars=45,
    )

    assert docs
    assert any(doc.metadata["paper_section"] == "method" for doc in docs)
    assert any(doc.metadata["paper_section"] == "limitations" for doc in docs)
    for doc in docs:
        assert doc.metadata["full_text_requested"] is True
        assert doc.metadata["full_text_downloaded"] is True
        assert doc.metadata["full_text_extracted"] is True
        assert doc.metadata["full_text_indexed"] is False
        assert doc.metadata["content_hash"]


def test_missing_full_text_is_reported_without_claiming_extraction():
    from conflux.knowledge.paper_indexer import _load_full_text, paper_to_documents
    from conflux.paper_ingestion.ingestion_policy import default_policy, decide_ingestion
    from conflux.paper_ingestion.models import PaperAnalysis, PaperRecord

    paper = PaperRecord(id="p-missing", title="Missing PDF", pdf_url="https://example.test/missing.pdf")
    analysis = PaperAnalysis(paper_id=paper.id, relevance_score=0.9, reading_level="deep")
    decision = decide_ingestion(paper, analysis, policy=default_policy(allow_full_text=True))
    text, status = _load_full_text(paper, decision, pdf_dir=None, download_pdfs=False, out_dir=None)
    docs = paper_to_documents(paper, analysis, decision, full_text=text, full_text_status=status)

    assert decision.action == "full_text"
    assert status == "not_downloaded"
    assert text == ""
    assert docs[0].metadata["full_text_requested"] is True
    assert docs[0].metadata["full_text_downloaded"] is False
    assert docs[0].metadata["full_text_extracted"] is False


def test_index_documents_upserts_changed_content_by_logical_chunk_id():
    from conflux.rag.indexer import index_documents

    class Store:
        def __init__(self):
            self.items = {}

        def get(self, include=None):
            return {
                "ids": list(self.items),
                "documents": [self.items[item][0] for item in self.items],
                "metadatas": [self.items[item][1] for item in self.items],
            }

        def add_documents(self, documents, ids):
            for document, item_id in zip(documents, ids):
                self.items[item_id] = (document.page_content, document.metadata)

        def update_documents(self, ids, documents):
            self.add_documents(documents, ids)

    store = Store()
    first = Document(page_content="old limitations", metadata={"chunk_id": "paper#limitations"})
    changed = Document(page_content="new limitations", metadata={"chunk_id": "paper#limitations"})
    assert index_documents(store, [first]) == 1
    assert index_documents(store, [first]) == 0
    assert index_documents(store, [changed]) == 1
    assert store.items["paper#limitations"][0] == "new limitations"
    assert store.items["paper#limitations"][1]["content_version"]
    metadata_changed = Document(
        page_content="new limitations",
        metadata={"chunk_id": "paper#limitations", "content_scope": "full_text", "full_text_indexed": True},
    )
    assert index_documents(store, [metadata_changed]) == 1
    assert store.items["paper#limitations"][1]["full_text_indexed"] is True


def test_index_documents_rejects_incompatible_embedding_dimension(monkeypatch):
    from conflux.rag.indexer import EmbeddingIndexMismatchError, index_documents

    class Collection:
        name = "conflux_docs"
        metadata = None

        def peek(self, limit):
            return {"embeddings": [[0.0] * 1024]}

        def modify(self, metadata):
            raise AssertionError("incompatible collection metadata must not be modified")

    class Embedding:
        def embed_query(self, text):
            return [0.0] * 1536

    class Store:
        _collection = Collection()
        _collection_name = "conflux_docs"
        embeddings = Embedding()

        def get(self, include=None):
            return {"ids": [], "documents": [], "metadatas": []}

        def add_documents(self, documents, ids):
            raise AssertionError("documents must not be written to an incompatible collection")

    monkeypatch.setattr("conflux.rag.indexer.get", lambda *args, **kwargs: "text-embedding-v4")
    document = Document(page_content="new paper", metadata={"chunk_id": "paper#summary"})

    try:
        index_documents(Store(), [document])
        raise AssertionError("dimension mismatch should fail before indexing")
    except EmbeddingIndexMismatchError as exc:
        assert exc.collection_name == "conflux_docs"
        assert exc.stored_dimension == 1024
        assert exc.current_dimension == 1536
        assert "旧索引未被修改" in str(exc)


def test_trace_event_exposes_retrieval_and_provider_diagnostics():
    from conflux.source_status import SourceResult
    from conflux.trace import event_from_state_key

    text = SourceResult(
        source="Web",
        status="low_relevance",
        content="A web result",
        metadata={
            "result_count": 3,
            "kept_count": 1,
            "provider_trace": [{"provider": "duckduckgo", "status": "failed"}, {"provider": "bing", "status": "success"}],
        },
    ).to_tool_text()
    event = event_from_state_key("web_result", text)

    assert event is not None
    assert event.status == "low_relevance"
    assert event.metadata["result_count"] == 3
    assert event.metadata["kept_count"] == 1
    assert event.metadata["provider_trace"][1]["provider"] == "bing"
