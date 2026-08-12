"""P2 Project-Driven Paper Radar — acceptance tests."""

import json
import tempfile
from pathlib import Path

import pytest


# ── Phase 1: P2 contracts ─────────────────────────────────────────

class TestP2Contracts:
    def test_project_research_config_defaults(self):
        from conflux.core.p2_contracts import ProjectResearchConfig

        cfg = ProjectResearchConfig(profile="profiles/test.yaml")
        assert cfg.cadence.value == "manual"
        assert cfg.max_candidates == 100
        assert cfg.deep_read_limit == 5
        assert cfg.auto_generate_queries is True
        assert cfg.require_query_review is True
        assert cfg.require_plan_writeback_approval is True

    def test_track_parsing(self):
        from conflux.core.p2_contracts import Track, TrackQuery

        tq = TrackQuery(terms="GIS agent", suffix="workflow", categories=["cs.AI"])
        track = Track(
            id="geo", name="Geo Agents",
            queries=[tq], budget_ratio=0.4,
        )
        assert track.id == "geo"
        assert len(track.queries) == 1
        assert track.budget_ratio == 0.4

    def test_query_spec_id_consistency(self):
        from conflux.core.p2_contracts import PaperSource, QuerySpec

        q1 = QuerySpec(
            id="",
            source=PaperSource.ARXIV, query="test query",
        )
        q2 = QuerySpec(
            id="",
            source=PaperSource.ARXIV, query="test query",
        )
        # Same source+query should produce same id when resolved
        from conflux.paper_radar.query_builder import _spec_id
        assert _spec_id("arxiv", "test query") == _spec_id("arxiv", "test query")

    def test_paper_identity_dedup_key(self):
        from conflux.core.p2_contracts import PaperIdentity

        pi = PaperIdentity(source="arxiv", canonical_id="2401.00001", doi="10.1234/x")
        assert pi.dedup_key == "10.1234/x"

        pi2 = PaperIdentity(source="arxiv", canonical_id="2401.00001")
        assert pi2.dedup_key == "arxiv:2401.00001"

    def test_search_intent_json_serializable(self):
        from conflux.core.p2_contracts import SearchIntent, SearchIntentType

        si = SearchIntent(
            id="test-001",
            project_id="p1",
            type=SearchIntentType.CORE_TOPIC,
            summary="Test intent",
            query_terms=["GIS", "agent"],
            priority=90,
            status="proposed",
        )
        d = si.model_dump()
        assert d["id"] == "test-001"
        assert d["type"] == "core_topic"

    def test_radar_run_result_creation(self):
        from conflux.core.p2_contracts import (
            ProjectResearchContext, RadarRunResult, RadarRunStats,
        )

        ctx = ProjectResearchContext(
            project_id="test",
            overall_goal="Test goal",
            research_questions=["RQ1"],
        )
        stats = RadarRunStats(project_id="test", run_id="r001")
        result = RadarRunResult(
            project_id="test",
            context=ctx,
            stats=stats,
        )
        assert result.project_id == "test"
        assert result.context.overall_goal == "Test goal"


# ── Phase 2: Context builder ──────────────────────────────────────

class TestContextBuilder:
    def test_builds_from_project_and_profile(self):
        from conflux.paper_radar.context_builder import build_project_research_context
        from conflux.project_registry.models import ProjectDefinition
        from conflux.research_profile import load_profile

        proj = ProjectDefinition(id="test", name="Test", path=".")
        proj.plan.overall_goal = "Test research goal"
        profile = load_profile("profiles/example_gis_agent.yaml", validate=False)

        ctx = build_project_research_context(proj, profile)

        assert ctx.project_id == "test"
        assert len(ctx.research_questions) == 3
        assert ctx.profile_id == "gis-agent-research"
        assert ctx.profile_version  # non-empty hash
        assert ctx.project_revision

    def test_includes_audit_data(self):
        from conflux.paper_radar.context_builder import build_project_research_context
        from conflux.project_registry.models import ProjectDefinition
        from conflux.research_profile import load_profile

        proj = ProjectDefinition(id="test", name="Test", path=".")
        profile = load_profile("profiles/example_gis_agent.yaml", validate=False)

        audit = {
            "risks": ["Network timeout risk"],
            "evidence_gaps": [{
                "id": "gap-1",
                "description": "No benchmarks for reproducibility",
                "severity": "high",
            }],
        }

        ctx = build_project_research_context(proj, profile, audit=audit)
        assert len(ctx.current_risks) == 1
        assert len(ctx.evidence_gaps) == 1
        assert ctx.evidence_gaps[0].severity == "high"

    def test_context_version_stable(self):
        from conflux.paper_radar.context_builder import build_project_research_context
        from conflux.project_registry.models import ProjectDefinition
        from conflux.research_profile import load_profile

        proj = ProjectDefinition(id="test", name="Test", path=".")
        proj.plan.overall_goal = "Stable goal"
        profile = load_profile("profiles/example_gis_agent.yaml", validate=False)

        ctx1 = build_project_research_context(proj, profile)
        ctx2 = build_project_research_context(proj, profile)

        assert ctx1.profile_version == ctx2.profile_version
        assert ctx1.project_revision == ctx2.project_revision


# ── Phase 3: Intent generator ─────────────────────────────────────

class TestIntentGenerator:
    def test_generates_core_topic_intent(self):
        from conflux.paper_radar.context_builder import build_project_research_context
        from conflux.paper_radar.intent_generator import generate_search_intents
        from conflux.project_registry.models import ProjectDefinition
        from conflux.research_profile import load_profile

        proj = ProjectDefinition(id="test", name="Test", path=".")
        proj.plan.overall_goal = "Test goal"
        profile = load_profile("profiles/example_gis_agent.yaml", validate=False)
        ctx = build_project_research_context(proj, profile)

        intents = generate_search_intents(ctx)

        assert len(intents) >= 1
        core = [i for i in intents if i.type.value == "core_topic"]
        assert len(core) >= 1

    def test_all_intents_have_unique_ids(self):
        from conflux.paper_radar.context_builder import build_project_research_context
        from conflux.paper_radar.intent_generator import generate_search_intents
        from conflux.project_registry.models import ProjectDefinition
        from conflux.research_profile import load_profile

        proj = ProjectDefinition(id="test", name="Test", path=".")
        profile = load_profile("profiles/example_gis_agent.yaml", validate=False)
        ctx = build_project_research_context(proj, profile)

        intents = generate_search_intents(ctx)
        ids = [i.id for i in intents]
        assert len(ids) == len(set(ids))

    def test_deterministic_intent_ids(self):
        from conflux.paper_radar.context_builder import build_project_research_context
        from conflux.paper_radar.intent_generator import generate_search_intents
        from conflux.project_registry.models import ProjectDefinition
        from conflux.research_profile import load_profile

        proj = ProjectDefinition(id="test", name="Test", path=".")
        proj.plan.overall_goal = "Same goal"
        profile = load_profile("profiles/example_gis_agent.yaml", validate=False)
        ctx = build_project_research_context(proj, profile)

        intents1 = generate_search_intents(ctx)
        intents2 = generate_search_intents(ctx)

        assert [i.id for i in intents1] == [i.id for i in intents2]


# ── Phase 3: Query builder ────────────────────────────────────────

class TestQueryBuilder:
    def test_resolves_track_queries(self):
        from conflux.paper_radar.query_builder import resolve_query_specs_from_profile
        from conflux.research_profile import load_profile

        profile = load_profile("profiles/example_gis_agent.yaml", validate=False)
        specs = resolve_query_specs_from_profile(profile)

        assert len(specs) >= 4  # 5 queries * 2 sources = 10, but with budget ratio it varies
        # Check that track IDs are set
        track_ids = {s.track_id for s in specs}
        assert len(track_ids) >= 1

    def test_query_spec_has_required_fields(self):
        from conflux.paper_radar.query_builder import resolve_query_specs_from_profile
        from conflux.research_profile import load_profile

        profile = load_profile("profiles/example_gis_agent.yaml", validate=False)
        specs = resolve_query_specs_from_profile(profile)

        for spec in specs:
            assert spec.id
            assert spec.source
            assert spec.query
            assert spec.max_results > 0
            assert spec.date_window_days > 0

    def test_fallback_when_no_tracks(self):
        from conflux.paper_radar.query_builder import resolve_query_specs_from_profile
        from conflux.research_profile import ResearchProfile

        profile = ResearchProfile(
            id="no-tracks", name="No Tracks",
            fields=["cs.AI"],
            research_questions=["Test RQ"],
            keywords=["test keyword"],
        )
        specs = resolve_query_specs_from_profile(profile)
        assert len(specs) > 0
        # Should have fallback provenance
        provenances = {s.provenance for s in specs}
        assert "fallback_keyword" in provenances or "track_manual" in provenances

    def test_both_sources_when_configured(self):
        from conflux.paper_radar.query_builder import resolve_query_specs_from_profile
        from conflux.research_profile import load_profile

        profile = load_profile("profiles/example_gis_agent.yaml", validate=False)
        specs = resolve_query_specs_from_profile(profile)

        sources = {s.source.value for s in specs}
        assert "arxiv" in sources
        assert "semantic_scholar" in sources


# ── Phase 4: Radar pipeline ───────────────────────────────────────

class TestRadarPipeline:
    def test_radar_run_with_stub_sources(self, monkeypatch):
        """Test full radar run with mocked source execution."""
        from conflux.paper_radar.radar import run_paper_radar
        from conflux.project_registry.models import ProjectDefinition
        from conflux.research_profile import load_profile
        from conflux.paper_ingestion.models import PaperRecord

        def mock_execute(queries, stats=None, db=None):
            return [PaperRecord(
                id="2401.00001",
                title="Test GIS Paper",
                abstract="A test paper about GIS agents.",
                source="arxiv",
                doi="10.1234/test",
            )], [], set()

        monkeypatch.setattr(
            "conflux.paper_radar.radar._execute_queries",
            mock_execute,
        )

        proj = ProjectDefinition(id="test", name="Test", path=".")
        proj.plan.overall_goal = "Test goal"
        profile = load_profile("profiles/example_gis_agent.yaml", validate=False)

        result = run_paper_radar(proj, profile)

        assert result.project_id == "test"
        assert len(result.intents) >= 1
        assert len(result.queries) >= 1
        assert len(result.links) >= 1
        assert result.stats.total_candidates == 1
        assert result.stats.after_dedup == 1
        assert result.links[0].relevance != 0.5

    def test_radar_writes_output(self, monkeypatch, tmp_path):
        from conflux.paper_radar.radar import run_paper_radar
        from conflux.project_registry.models import ProjectDefinition
        from conflux.research_profile import load_profile
        from conflux.paper_ingestion.models import PaperRecord

        def mock_execute(queries, stats=None, db=None):
            return [PaperRecord(
                id="2401.00001", title="Test",
                abstract="Test abstract.", source="arxiv",
            )], [], set()

        monkeypatch.setattr(
            "conflux.paper_radar.radar._execute_queries",
            mock_execute,
        )

        proj = ProjectDefinition(id="test", name="Test", path=".")
        proj.plan.overall_goal = "Test"
        profile = load_profile("profiles/example_gis_agent.yaml", validate=False)

        result = run_paper_radar(proj, profile, out_dir=str(tmp_path))

        # Check output files
        papers_dir = tmp_path / "test" / "papers"
        assert papers_dir.exists()
        latest = papers_dir / "latest.json"
        assert latest.exists()

        data = json.loads(latest.read_text(encoding="utf-8"))
        assert data["project_id"] == "test"
        assert data["link_count"] >= 1

    def test_project_paper_link_creation(self):
        from conflux.paper_radar.radar import _create_project_links
        from conflux.paper_ingestion.models import PaperRecord

        paper = PaperRecord(
            id="2401.00001",
            title="Test Paper",
            source="arxiv",
            doi="10.1234/test",
        )
        # Mock context
        class MockContext:
            profile_version = "abc123"
            project_revision = "def456"

        # Mock intents
        class MockIntent:
            id = "intent-1"
            type = type("Mock", (), {"value": "core_topic"})

        links = _create_project_links(
            [paper], "test-proj",
            [MockIntent()], MockContext(),
            relevance_scores={paper.id: 0.8},
        )
        assert len(links) == 1
        assert links[0].project_id == "test-proj"
        assert links[0].paper_identity.doi == "10.1234/test"
        assert links[0].status.value == "shortlisted"
        assert links[0].relevance == 0.8

    def test_deep_analysis_only_reads_shortlisted_papers(self, monkeypatch):
        from conflux.paper_radar.radar import run_paper_radar
        from conflux.paper_ingestion.models import PaperRecord
        from conflux.project_registry.models import ProjectDefinition
        from conflux.research_profile import load_profile

        monkeypatch.setattr(
            "conflux.paper_radar.radar._execute_queries",
            lambda queries, stats=None, db=None: ([PaperRecord(
                id="unrelated",
                title="Marine biology survey",
                abstract="Protein folding in marine organisms.",
                source="arxiv",
            )], [], set()),
        )
        captured = {}
        monkeypatch.setattr(
            "conflux.paper_radar.radar.run_deep_analysis",
            lambda papers, *args, **kwargs: captured.setdefault("papers", papers) or [],
        )
        project = ProjectDefinition(id="test", name="Test", path=".")
        profile = load_profile("profiles/example_gis_agent.yaml", validate=False)

        result = run_paper_radar(project, profile)

        assert result.stats.shortlisted == 0
        assert result.stats.deep_read == 0
        assert "papers" not in captured


# ── Phase 1/2: Domain model extensions ────────────────────────────


class TestUnreviewedSemantics:
    def test_llm_review_failure_marks_link_needs_review(self, monkeypatch):
        from conflux.core.p2_contracts import (
            PaperIdentity,
            PaperLinkStatus,
            ProjectPaperLink,
        )
        from conflux.paper_radar.radar import run_paper_radar
        from conflux.project_registry.models import ProjectDefinition
        from conflux.research_profile import load_profile
        from conflux.paper_ingestion.models import PaperRecord

        def mock_execute(queries, stats=None, db=None):
            return [PaperRecord(
                id="2401.00001", title="Test GIS Paper",
                abstract="A test paper about GIS agents.",
                source="arxiv", doi="10.1234/test",
            )], [], set()

        def fake_links(papers, project_id, intents, context, relevance_scores=None):
            return [ProjectPaperLink(
                project_id=project_id,
                paper_identity=PaperIdentity(source="arxiv", canonical_id="2401.00001"),
                status=PaperLinkStatus.SHORTLISTED,
                relevance=0.9,
            )]

        def fake_deep_analysis(papers, context, intents, *, download_dir=None,
                               max_papers=5, llm_model=None, stats=None):
            # Simulates an LLM review failure recorded by deep analysis.
            assert stats is not None
            stats.needs_review_paper_ids.append("2401.00001")
            return []

        monkeypatch.setattr("conflux.paper_radar.radar._execute_queries", mock_execute)
        monkeypatch.setattr("conflux.paper_radar.radar._create_project_links", fake_links)
        monkeypatch.setattr("conflux.paper_radar.radar.run_deep_analysis", fake_deep_analysis)

        proj = ProjectDefinition(id="test", name="Test", path=".")
        proj.plan.overall_goal = "Test goal"
        proj.research = {"profile": "profiles/example_gis_agent.yaml", "deep_read_limit": 1}
        profile = load_profile("profiles/example_gis_agent.yaml", validate=False)

        result = run_paper_radar(proj, profile)

        assert result.links[0].status == PaperLinkStatus.NEEDS_REVIEW
        assert result.stats.needs_review == 1
        assert result.stats.needs_review_paper_ids == ["2401.00001"]
        # Deterministic fallback suggestions still visible, but the link is not auto-promoted.
        assert result.stats.saved == 0



class TestProjectSeenState:
    def _radar_fixture(self, monkeypatch, tmp_path):
        from conflux.core.p2_contracts import (
            PaperIdentity,
            PaperLinkStatus,
            ProjectPaperLink,
        )
        from conflux.paper_radar.radar import run_paper_radar
        from conflux.project_registry.models import ProjectDefinition
        from conflux.research_profile import load_profile
        from conflux.paper_ingestion.models import PaperRecord

        def mock_execute(queries, stats=None, db=None):
            return [PaperRecord(
                id="2401.00001", title="Test GIS Paper",
                abstract="A test paper about GIS agents.",
                source="arxiv", doi="10.1234/test",
            )], [], set()

        def fake_links(papers, project_id, intents, context, relevance_scores=None):
            return [ProjectPaperLink(
                project_id=project_id,
                paper_identity=PaperIdentity(source="arxiv", canonical_id="2401.00001"),
                status=PaperLinkStatus.SHORTLISTED,
                relevance=0.9,
            )]

        called = {"deep": 0}

        def fake_deep_analysis(papers, context, intents, *, download_dir=None,
                               max_papers=5, llm_model=None, stats=None):
            called["deep"] += 1
            return []

        monkeypatch.setattr("conflux.paper_radar.radar._execute_queries", mock_execute)
        monkeypatch.setattr("conflux.paper_radar.radar._create_project_links", fake_links)
        monkeypatch.setattr("conflux.paper_radar.radar.run_deep_analysis", fake_deep_analysis)

        proj = ProjectDefinition(id="test", name="Test", path=".")
        proj.plan.overall_goal = "Test goal"
        proj.research = {"profile": "profiles/example_gis_agent.yaml", "deep_read_limit": 5}
        profile = load_profile("profiles/example_gis_agent.yaml", validate=False)
        return run_paper_radar(proj, profile, out_dir=str(tmp_path)), called

    def test_stable_rejected_is_not_re_reviewed(self, monkeypatch, tmp_path):
        from conflux.paper_radar.radar import _project_seen_path
        seen_path = _project_seen_path(tmp_path, "test")
        seen_path.parent.mkdir(parents=True, exist_ok=True)
        seen_path.write_text(
            '{"arxiv:2401.00001": {"status": "rejected", "at": "2026-08-08T00:00:00"}}',
            encoding="utf-8",
        )

        result, called = self._radar_fixture(monkeypatch, tmp_path)

        assert called["deep"] == 0
        assert result.stats.skipped_seen_rejected == 1
        assert result.stats.deep_read == 0

    def test_run_persists_seen_state_and_isolation(self, monkeypatch, tmp_path):
        from conflux.paper_radar.radar import (
            _load_project_seen,
            _project_seen_path,
            _save_project_seen,
        )

        result, called = self._radar_fixture(monkeypatch, tmp_path)

        seen_path = _project_seen_path(tmp_path, "test")
        assert seen_path.exists()
        seen = _load_project_seen(tmp_path, "test")
        assert seen["arxiv:2401.00001"]["status"] == "shortlisted"
        # Another project is isolated from this seen state.
        assert _load_project_seen(tmp_path, "other-project") == {}
        # Persist into a different project and confirm it stays separate.
        _save_project_seen(tmp_path, "other-project", result.links)
        assert _load_project_seen(tmp_path, "other-project")["arxiv:2401.00001"]["status"] == "shortlisted"
        assert _load_project_seen(tmp_path, "test")["arxiv:2401.00001"]["status"] == "shortlisted"


class TestDomainExtensions:
    def test_research_profile_loads_tracks(self):
        from conflux.research_profile import load_profile

        profile = load_profile("profiles/example_gis_agent.yaml", validate=False)
        tracks = profile.get_tracks()

        assert len(tracks) == 3
        assert tracks[0].id == "geo_agents"
        assert len(tracks[0].queries) == 2
        assert tracks[1].id == "agent_verification"
        assert tracks[2].id == "reproducibility"
        verification_categories = {
            category
            for query in tracks[1].queries
            for category in (query.categories or [])
        }
        assert "cs.LO" in verification_categories

    def test_project_definition_roundtrips_research(self):
        from conflux.project_registry.models import ProjectDefinition

        d = ProjectDefinition(id="p1", name="P1", path=".")
        d.research = {"profile": "profiles/gis.yaml", "cadence": "daily"}

        payload = d.to_dict()
        assert "research" in payload
        assert payload["research"]["cadence"] == "daily"

        d2 = ProjectDefinition.from_dict(payload)
        assert d2.research is not None
        assert d2.research["profile"] == "profiles/gis.yaml"

    def test_project_yaml_parses_research_section(self):
        import yaml
        from conflux.project_registry.models import ProjectDefinition

        yaml_text = """
id: test
name: Test
path: .
research:
  profile: profiles/example_gis_agent.yaml
  sources:
    - arxiv
    - semantic_scholar
  cadence: weekly
  max_candidates: 50
"""
        payload = yaml.safe_load(yaml_text)
        proj = ProjectDefinition.from_dict(payload)

        assert proj.research is not None
        assert proj.research["profile"] == "profiles/example_gis_agent.yaml"
        assert proj.research["max_candidates"] == 50


# ── Phase 4: Source module ────────────────────────────────────────

class TestSemanticScholarSource:
    def test_normalization(self):
        from conflux.paper_ingestion.semantic_scholar_source import _normalize_s2_paper

        paper = _normalize_s2_paper({
            "paperId": "test123",
            "title": "Test Paper",
            "abstract": "An abstract.",
            "authors": [{"name": "Smith, J."}, {"name": "Jones, R."}],
            "year": 2024,
            "externalIds": {"DOI": "10.1234/test", "ArXiv": "2401.00001"},
            "publicationVenue": {"name": "Test Journal"},
            "fieldsOfStudy": ["Computer Science"],
            "citationCount": 42,
        })

        assert paper.source == "semantic_scholar"
        assert paper.doi == "10.1234/test"
        assert len(paper.authors) == 2
        assert paper.venue == "Test Journal"

    def test_normalization_minimal(self):
        from conflux.paper_ingestion.semantic_scholar_source import _normalize_s2_paper

        paper = _normalize_s2_paper({
            "paperId": "min",
            "title": "Minimal",
        })
        assert paper.source == "semantic_scholar"
        assert paper.id == "min"
        assert paper.abstract == ""
        assert paper.authors == []

    def test_doi_resolver_no_network(self):
        from conflux.paper_ingestion.semantic_scholar_source import resolve_paper_by_doi
        # Should handle empty/missing gracefully
        assert resolve_paper_by_doi("") is None
        assert resolve_paper_by_doi("   ") is None


# ── Phase D: Deep analyzer ─────────────────────────────────────────

class TestDeepAnalyzer:
    def test_download_pdf_requires_explicit_url(self):
        from conflux.paper_radar.deep_analyzer import _download_pdf

        class Downloader:
            calls = 0

            def download(self, paper_id, pdf_url):
                self.calls += 1

        downloader = Downloader()

        result = _download_pdf({"id": "2401.00001", "source": "arxiv"}, downloader)

        assert result is None
        assert downloader.calls == 0

    def test_chunk_text_with_page_markers(self):
        from conflux.paper_radar.deep_analyzer import _chunk_text

        intro = "Introduction text here." + " More context. " * 10  # ~170 chars
        method = "This is the method section with detailed description of our experimental approach and evaluation strategy. " * 3  # ~250 chars
        text = f"{intro}\n[[CONFLUX_PAGE:1]]\n{intro}\n\n[[CONFLUX_PAGE:2]]\n{method}"
        chunks = _chunk_text(text)
        assert len(chunks) >= 1
        page_nums = {c["page"] for c in chunks}
        assert 1 in page_nums or 2 in page_nums or 0 in page_nums

    def test_chunk_text_plain_abstract(self):
        from conflux.paper_radar.deep_analyzer import _chunk_text

        text = "We propose a novel method for GIS agent workflows." * 50  # ~1600 chars
        chunks = _chunk_text(text)
        assert len(chunks) == 1
        assert chunks[0]["page"] == 0

    def test_score_chunks_scores_sections(self):
        from conflux.paper_radar.deep_analyzer import _score_chunks
        from conflux.core.p2_contracts import ProjectResearchContext

        ctx = ProjectResearchContext(
            project_id="test",
            overall_goal="Build better GIS agents with knowledge graphs",
            research_questions=["How to integrate knowledge graphs with geospatial reasoning?"],
        )
        chunks = [
            {"page": 1, "chunk_idx": 0, "text": "GIS agents with knowledge graphs for geospatial data fusion."},
            {"page": 2, "chunk_idx": 0, "text": "unrelated biology research topic paper."},
        ]
        scored = _score_chunks(chunks, ctx)
        assert scored[0]["page"] == 1
        assert scored[0]["score"] > scored[1]["score"]

    def test_has_method_content_detection(self):
        from conflux.paper_radar.deep_analyzer import _has_method_content
        from conflux.core.p2_contracts import ProjectResearchContext

        ctx = ProjectResearchContext(
            project_id="test",
            overall_goal="GIS agent workflow research",
            research_questions=["How to verify agent workflows?"],
        )
        chunks = [{"page": 3, "chunk_idx": 0, "text": "Our method uses a three-stage pipeline with evaluation benchmarks for agent verification."}]
        assert _has_method_content(chunks, ctx)

    def test_run_deep_analysis_abstract_only(self):
        from conflux.paper_radar.deep_analyzer import run_deep_analysis
        from conflux.core.p2_contracts import (
            PaperIdentity, ProjectPaperLink, ProjectResearchContext, SearchIntent, SearchIntentType,
        )

        ctx = ProjectResearchContext(
            project_id="test",
            overall_goal="GIS agent geospatial data fusion",
            research_questions=["How can agents improve geospatial workflows?"],
        )
        pi = PaperIdentity(source="arxiv", canonical_id="2401.00001")
        link = ProjectPaperLink(project_id="test", paper_identity=pi, relevance=0.85)
        paper_dict = {
            "id": "2401.00001",
            "title": "Knowledge-Grounded GIS Agents",
            "abstract": "A novel framework for GIS agent workflow verification.",
            "source": "arxiv",
        }
        intents = [SearchIntent(id="i1", project_id="test", type=SearchIntentType.CORE_TOPIC, summary="GIS agents")]
        suggestions = run_deep_analysis([(link, paper_dict)], ctx, intents, max_papers=1)
        assert len(suggestions) >= 1
        assert suggestions[0].type.value == "link_evidence"


# ── Phase E: Server handlers ───────────────────────────────────────

class TestResearchServerHandlers:
    def test_paper_list_and_actions(self):
        from conflux.workbench.server import (
            _write_research_cache, get_project_research_papers,
            apply_paper_action, get_project_research_coverage,
        )

        cache = {
            "project_id": "test-e",
            "links": [
                {
                    "paper_identity": {"canonical_id": "p1", "doi": "10.1/t", "source": "arxiv"},
                    "status": "discovered", "relevance": 0.9, "evidence_utility": "method",
                    "matched_intent_ids": ["i1"],
                },
            ],
            "intents": [{"id": "i1", "type": "core_topic"}],
            "stats": {"sources_used": ["arxiv"]},
        }
        _write_research_cache("test-e", cache)

        papers = get_project_research_papers("test-e")
        assert papers["ok"]
        assert papers["total"] == 1

        r = apply_paper_action({"project_id": "test-e", "paper_id": "p1", "action": "save"})
        assert r["ok"]
        assert r["new_status"] == "saved"

        cov = get_project_research_coverage("test-e")
        assert cov["ok"]
        assert cov["covered_papers"] == 1

    def test_paper_action_invalid(self):
        from conflux.workbench.server import apply_paper_action
        r = apply_paper_action({"project_id": "x", "paper_id": "x", "action": "delete"})
        assert not r["ok"]

    def test_paper_list_missing_project(self):
        from conflux.workbench.server import get_project_research_papers
        r = get_project_research_papers("nonexistent")
        assert not r["ok"]
