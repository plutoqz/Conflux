import json
import subprocess
from io import BytesIO
from pathlib import Path


def test_workbench_status_sanitizes_api_keys(monkeypatch):
    from conflux import config
    from conflux.workbench.server import build_status

    monkeypatch.setenv("OPENAI_API_KEY", "secret-test-key")
    config._config = None

    status = build_status()
    payload = json.dumps(status, ensure_ascii=False)

    assert status["credentials"]["openai_api_key"] is True
    assert "secret-test-key" not in payload


def test_workbench_status_treats_duckduckgo_as_ready_without_api_key(monkeypatch):
    from conflux import config
    from conflux.workbench.server import build_status

    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)
    monkeypatch.setattr(config, "load", lambda: {
        "models": {},
        "embedding": {},
        "web_search": {"provider": "duckduckgo", "max_results": 5},
    })

    status = build_status()

    assert status["defaults"]["web_search"] == {
        "provider": "duckduckgo",
        "max_results": 5,
        "requires_api_key": False,
        "ready": True,
    }


def test_model_probe_uses_custom_openai_compatible_endpoint(monkeypatch):
    from conflux.workbench import server

    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps({
                "model": "demo-model",
                "choices": [{"message": {"content": "ready"}}],
                "usage": {"total_tokens": 3},
            }).encode("utf-8")

    def fake_urlopen(request, timeout=60):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(server.urllib.request, "urlopen", fake_urlopen)

    result = server.run_model_probe({
        "base_url": "https://api.example.test/v1",
        "api_key": "custom-key",
        "model": "demo-model",
        "prompt": "ping",
        "max_tokens": 32,
    })

    assert result["ok"] is True
    assert result["content"] == "ready"
    assert captured["url"] == "https://api.example.test/v1/chat/completions"
    assert captured["body"]["model"] == "demo-model"
    assert captured["body"]["messages"][0]["content"] == "ping"
    assert "custom-key" not in json.dumps(result)


def test_profile_optimizer_returns_reviewable_structured_suggestion(monkeypatch):
    from conflux.workbench import server

    captured = {}
    draft = {
        "fields": "cs.AI",
        "keywords": "knowledge graph\nnatural disaster",
        "description": "研究知识图谱在自然灾害应急响应中的作用",
        "negative_keywords": "protein interaction",
        "base_url": "https://api.example.test/v1",
        "api_key": "secret",
        "model": "profile-editor",
    }

    def fake_probe(payload):
        captured.update(payload)
        return {
            "ok": True,
            "model": "profile-editor",
            "content": """```json
{"fields":["cs.AI"],"keywords":["disaster knowledge graph","emergency response","DISASTER KNOWLEDGE GRAPH"],"description":"如何利用知识图谱支持自然灾害应急响应中的证据整合？","negative_keywords":["protein interaction","clinical medicine"],"optimization_notes":["补充应用场景词","增加排除词"]}
```""",
        }

    monkeypatch.setattr(server, "run_model_probe", fake_probe)
    result = server.optimize_inline_profile(draft)

    assert result["ok"] is True
    assert result["model"] == "profile-editor"
    assert result["profile"]["keywords"] == ["disaster knowledge graph", "emergency response"]
    assert result["profile"]["negative_keywords"] == ["protein interaction", "clinical medicine"]
    assert result["notes"] == ["补充应用场景词", "增加排除词"]
    assert captured["max_tokens"] == 1600
    assert "knowledge graph" in captured["prompt"]
    assert draft["keywords"] == "knowledge graph\nnatural disaster"


def test_saved_inline_profile_preserves_negative_keywords_and_yaml_punctuation(tmp_path, monkeypatch):
    import yaml
    from conflux.workbench import server

    monkeypatch.setattr(server, "PROJECT_ROOT", tmp_path)
    result = server._save_inline_profile({
        "profile_name": "灾害知识图谱",
        "fields": "cs.AI, cs.IR",
        "keywords": "disaster knowledge graph\nemergency response",
        "description": "研究问题：如何整合多源灾害证据？",
        "negative_keywords": "protein interaction, clinical medicine",
    })

    assert result["ok"] is True
    payload = yaml.safe_load(Path(result["path"]).read_text(encoding="utf-8"))
    assert payload["research_questions"] == ["研究问题：如何整合多源灾害证据？"]
    assert payload["negative_keywords"] == ["protein interaction", "clinical medicine"]
    assert payload["fields"] == ["cs.AI", "cs.IR"]


def test_frontend_profile_optimization_is_previewable_and_undoable():
    html = Path("src/conflux/workbench/static/index.html").read_text(encoding="utf-8")
    app = Path("src/conflux/workbench/static/app.js").read_text(encoding="utf-8")

    for element_id in (
        "optimizeProfile",
        "profileOptimization",
        "applyProfileOptimization",
        "dismissProfileOptimization",
        "undoProfileOptimization",
        "profileNegativeKeywords",
    ):
        assert f'id="{element_id}"' in html
    assert "profileOptimizationOriginal = source" in app
    assert "writeInlineProfile(profileOptimizationDraft)" in app
    assert "writeInlineProfile(profileOptimizationOriginal)" in app
    assert "'/api/profile/optimize'" in app


def test_workbench_runs_offline_inbox_and_promotion(tmp_path, monkeypatch):
    from conflux.workbench.server import run_paper_inbox, run_paper_promotion
    from conflux.workbench import server

    inbox_dir = tmp_path / "inbox"
    promoted_dir = tmp_path / "promoted"

    inbox = run_paper_inbox({
        "profile": "profiles/example_gis_agent.yaml",
        "source": "fixture",
        "fixture": "tests/fixtures/papers/arxiv_sample.json",
        "out_dir": str(inbox_dir),
    })

    assert inbox["ok"] is True
    assert inbox["stats"]["deep"] == 1
    assert Path(inbox_dir / "paper_inbox.json").exists()

    monkeypatch.setattr(server, "PROJECT_ROOT", tmp_path)

    promoted = run_paper_promotion({
        "inbox": str(inbox_dir / "paper_inbox.json"),
        "out_dir": str(promoted_dir),
    })

    assert promoted["ok"] is True
    assert promoted["documents"] == 1
    assert promoted["papers"] == 1
    assert promoted["decisions"] == {"summary_only": 1}
    assert Path(promoted_dir / "paper_promotion_manifest.json").exists()
    report = tmp_path / promoted["report_path"]
    assert report.exists()
    report_text = report.read_text(encoding="utf-8")
    assert "# 论文入库总结" in report_text
    assert "实际写入：1 篇" in report_text
    assert "## 已入库论文" in report_text


def test_workbench_safe_file_read_scope():
    from conflux.workbench.server import _safe_read_path

    assert _safe_read_path("docs/graduate_research_copilot_execution_plan.md") is not None
    assert _safe_read_path(".env") is None
    assert _safe_read_path("config.yaml") is None


def test_markdown_preview_renders_headings_and_escapes_raw_html(tmp_path, monkeypatch):
    from conflux.workbench import server

    docs = tmp_path / "docs"
    docs.mkdir()
    source = docs / "result.md"
    source.write_text("# 中文标题\n\n**结论**\n\n<script>alert(1)</script>\n", encoding="utf-8")
    monkeypatch.setattr(server, "PROJECT_ROOT", tmp_path)

    rendered = server.render_markdown_preview("docs/result.md")

    assert rendered is not None
    assert "<h1>中文标题</h1>" in rendered
    assert "<strong>结论</strong>" in rendered
    assert "<script>alert(1)</script>" not in rendered
    assert "&lt;script&gt;" in rendered


def test_knowledge_stats_reflect_new_papers_even_with_stale_manifest(tmp_path):
    from conflux.knowledge.stats import gather_knowledge_stats

    documents = tmp_path / "data" / "documents"
    papers = documents / "papers" / "papers"
    papers.mkdir(parents=True)
    (documents / "manifest.json").write_text(json.dumps({"total_files": 0}), encoding="utf-8")
    (papers / "paper-2607.00001#summary.md").write_text("# 论文摘要\n", encoding="utf-8")

    stats = gather_knowledge_stats(tmp_path)

    assert stats["totals"]["documents"] >= 2
    assert stats["totals"]["papers"] == 1
    assert stats["corpus"]["_source"] == "filesystem_scan"


def test_csp_header_present_in_responses():
    from conflux.workbench.server import CSP_HEADER

    assert "default-src" in CSP_HEADER
    assert "script-src" in CSP_HEADER
    assert "frame-src 'self'" in CSP_HEADER
    assert "connect-src 'self'" in CSP_HEADER


def test_iframe_has_sandbox_attribute():
    html = Path("src/conflux/workbench/static/index.html").read_text(encoding="utf-8")
    assert 'sandbox="allow-same-origin"' in html


def test_access_token_allows_loopback_when_set(monkeypatch):
    from http.server import BaseHTTPRequestHandler
    from conflux.workbench import server as server_mod

    monkeypatch.setattr(server_mod, "_ACCESS_TOKEN", "test-token-123")
    monkeypatch.setattr(BaseHTTPRequestHandler, "__init__", lambda s, *a, **kw: None)
    handler = server_mod.WorkbenchHandler()
    handler.client_address = ("127.0.0.1", 9999)
    handler.headers = {}
    assert handler._authorize() is True


def test_access_token_blocks_non_loopback_without_header(monkeypatch):
    from http.server import BaseHTTPRequestHandler
    from conflux.workbench import server as server_mod

    monkeypatch.setattr(server_mod, "_ACCESS_TOKEN", "test-token-123")
    monkeypatch.setattr(BaseHTTPRequestHandler, "__init__", lambda s, *a, **kw: None)
    handler = server_mod.WorkbenchHandler()
    handler.client_address = ("192.168.1.10", 9999)
    handler.headers = {}
    assert handler._authorize() is False


def test_access_token_passes_non_loopback_with_correct_header(monkeypatch):
    from http.server import BaseHTTPRequestHandler
    from conflux.workbench import server as server_mod

    monkeypatch.setattr(server_mod, "_ACCESS_TOKEN", "test-token-123")
    monkeypatch.setattr(BaseHTTPRequestHandler, "__init__", lambda s, *a, **kw: None)
    handler = server_mod.WorkbenchHandler()
    handler.client_address = ("192.168.1.10", 9999)
    handler.headers = {"Authorization": "Bearer test-token-123"}
    assert handler._authorize() is True


def test_access_token_empty_allows_all(monkeypatch):
    from http.server import BaseHTTPRequestHandler
    from conflux.workbench import server as server_mod

    monkeypatch.setattr(server_mod, "_ACCESS_TOKEN", "")
    monkeypatch.setattr(BaseHTTPRequestHandler, "__init__", lambda s, *a, **kw: None)
    handler = server_mod.WorkbenchHandler()
    handler.client_address = ("192.168.1.10", 9999)
    handler.headers = {}
    assert handler._authorize() is True


def test_job_manager_submit_and_list(monkeypatch):
    from conflux.workbench.jobs import JobManager, get_job_manager

    # Mock _execute to avoid starting a real research query
    monkeypatch.setattr(JobManager, "_execute", lambda self, run_id, query, payload: None)
    mgr = get_job_manager()
    result = mgr.submit("test query", {"depth": "quick"})
    assert "run_id" in result
    assert result["status"] == "pending"
    jobs = mgr.list()
    assert any(j["run_id"] == result["run_id"] for j in jobs)


def test_job_manager_get_unknown_returns_none():
    from conflux.workbench.jobs import get_job_manager
    assert get_job_manager().get("nonexistent-run-id") is None


def test_job_manager_cancel_unknown_returns_false():
    from conflux.workbench.jobs import get_job_manager
    assert get_job_manager().cancel("nonexistent-run-id") is False


def test_session_index_returns_list():
    from conflux.workbench.sessions import build_session_index
    sessions = build_session_index()
    assert isinstance(sessions, list)
    for s in sessions:
        assert "run_id" in s


def test_session_detail_unknown_returns_none():
    from conflux.workbench.sessions import get_session_detail
    assert get_session_detail("nonexistent-run-id") is None


def test_workbench_config_merge_keeps_reasoning_and_unrelated_secrets(tmp_path, monkeypatch):
    from dotenv import dotenv_values
    from conflux.workbench import config_store

    env_file = tmp_path / ".env.workbench"
    env_file.write_text(
        "OPENAI_API_KEY=reasoning-key\n"
        "SERPAPI_API_KEY=search-key\n"
        "CONFLUX_ACCESS_TOKEN=access-key\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config_store, "WORKBENCH_ENV", env_file)
    monkeypatch.setattr(config_store, "_loaded_env_keys", set())
    monkeypatch.setattr(config_store, "_original_env_values", {})

    config_store.save_workbench_env(
        model="demo-model",
        embedding_api_key="embedding-key",
        depth="standard",
    )

    saved = dotenv_values(env_file)
    assert saved["OPENAI_API_KEY"] == "reasoning-key"
    assert saved["CONFLUX_EMBEDDING__API_KEY"] == "embedding-key"
    assert saved["SERPAPI_API_KEY"] == "search-key"
    assert saved["CONFLUX_ACCESS_TOKEN"] == "access-key"


def test_workbench_config_saves_web_search_provider_and_key(tmp_path, monkeypatch):
    from dotenv import dotenv_values
    from conflux.workbench import config_store

    env_file = tmp_path / ".env.workbench"
    monkeypatch.setattr(config_store, "WORKBENCH_ENV", env_file)
    monkeypatch.setattr(config_store, "_loaded_env_keys", set())
    monkeypatch.setattr(config_store, "_original_env_values", {})

    config_store.save_workbench_env(
        web_search_provider="serpapi",
        serpapi_api_key="search-secret",
    )

    saved = dotenv_values(env_file)
    assert saved["CONFLUX_WEB_SEARCH__PROVIDER"] == "serpapi"
    assert saved["SERPAPI_API_KEY"] == "search-secret"
    config_store.save_workbench_env(clear_keys=["CONFLUX_WEB_SEARCH__PROVIDER", "SERPAPI_API_KEY"])


def test_workbench_config_clear_restores_parent_environment(tmp_path, monkeypatch):
    from dotenv import dotenv_values
    from conflux.workbench import config_store

    key = "CONFLUX_TEST_MANAGED_KEY"
    env_file = tmp_path / ".env.workbench"
    env_file.write_text(f"{key}=workbench-value\n", encoding="utf-8")
    monkeypatch.setenv(key, "parent-value")
    monkeypatch.setattr(config_store, "WORKBENCH_ENV", env_file)
    monkeypatch.setattr(config_store, "_loaded_env_keys", set())
    monkeypatch.setattr(config_store, "_original_env_values", {})

    config_store._reload_env()
    assert config_store.os.environ[key] == "workbench-value"

    config_store.save_workbench_env(clear_keys=[key])
    assert key not in dotenv_values(env_file)
    assert config_store.os.environ[key] == "parent-value"


def test_session_detail_uses_only_verified_legacy_report(tmp_path, monkeypatch):
    from conflux.workbench import sessions

    run_id = "exact-run-id"
    summary = tmp_path / f"{run_id}.summary.json"
    summary.write_text(json.dumps({"run_id": run_id}), encoding="utf-8")
    correct = tmp_path / "correct.md"
    correct.write_text(f"# Report\n\n- 查询：verified query\n- Run id: {run_id}\n", encoding="utf-8")
    wrong = tmp_path / "newer.md"
    wrong.write_text("# Other\n\n- 查询：wrong query\n- Run id: another-run\n", encoding="utf-8")
    monkeypatch.setattr(sessions, "_REPORTS_ROOT", tmp_path)

    assert sessions.get_session_detail("exact-run") is None
    detail = sessions.get_session_detail(run_id)
    assert detail is not None
    assert detail["query"] == "verified query"
    assert detail["report_md_available"] is True
    assert detail["report_md_path"] == str(correct)


def test_access_cookie_uses_derived_value(monkeypatch):
    from http.server import BaseHTTPRequestHandler
    from conflux.workbench import server as server_mod

    monkeypatch.setattr(server_mod, "_ACCESS_TOKEN", "test-token-123")
    monkeypatch.setattr(BaseHTTPRequestHandler, "__init__", lambda s, *a, **kw: None)
    handler = server_mod.WorkbenchHandler()
    handler.client_address = ("192.168.1.10", 9999)
    handler.headers = {"Cookie": f"{server_mod._AUTH_COOKIE}={server_mod._auth_cookie_value()}"}

    assert "test-token-123" not in server_mod._auth_cookie_value()
    assert handler._authorize() is True


def test_login_route_sets_cookie_before_authorization(monkeypatch):
    from http.server import BaseHTTPRequestHandler
    from conflux.workbench import server as server_mod

    monkeypatch.setattr(server_mod, "_ACCESS_TOKEN", "test-token-123")
    monkeypatch.setattr(BaseHTTPRequestHandler, "__init__", lambda s, *a, **kw: None)
    captured = {}

    def fake_send_json(self, payload, status=200, headers=None):
        captured.update(payload=payload, status=status, headers=headers or {})

    monkeypatch.setattr(server_mod.WorkbenchHandler, "_send_json", fake_send_json)
    handler = server_mod.WorkbenchHandler()
    body = json.dumps({"token": "test-token-123"}).encode("utf-8")
    handler.client_address = ("192.168.1.10", 9999)
    handler.path = "/api/login"
    handler.headers = {"Content-Length": str(len(body))}
    handler.rfile = BytesIO(body)

    handler.do_POST()

    cookie = captured["headers"]["Set-Cookie"]
    assert captured["status"] == 200
    assert captured["payload"]["authenticated"] is True
    assert "HttpOnly" in cookie
    assert "SameSite=Strict" in cookie
    assert "test-token-123" not in cookie


def test_job_manager_rejects_cancelling_terminal_job():
    from conflux.workbench.jobs import JobManager, ResearchJob

    manager = JobManager()
    completed = ResearchJob(run_id="completed", query="q", status="completed")
    running = ResearchJob(run_id="running", query="q", status="running")
    manager._jobs = {completed.run_id: completed, running.run_id: running}

    assert manager.cancel(completed.run_id) is False
    assert completed._cancel_flag.is_set() is False
    assert manager.cancel(running.run_id) is True
    assert running._cancel_flag.is_set() is True


def test_frontend_has_login_and_timeout_cancellation_flow():
    html = Path("src/conflux/workbench/static/index.html").read_text(encoding="utf-8")
    app = Path("src/conflux/workbench/static/app.js").read_text(encoding="utf-8")
    timeout_start = app.index("const queryTimeout")
    timeout_end = app.index("}, 300000);", timeout_start)
    timeout_block = app[timeout_start:timeout_end]

    assert 'id="authDialog"' in html
    assert "'/api/login'" in app
    assert "requestQueryCancellation(runId)" in timeout_block
    assert "clearInterval(pollInterval)" not in timeout_block


def test_dashboard_distribution_bars_and_metric_dividers_are_scaled():
    css = Path("src/conflux/workbench/static/app.css").read_text(encoding="utf-8")
    app = Path("src/conflux/workbench/static/app.js").read_text(encoding="utf-8")

    assert ".micro-bar > span { display: block; width: 100%" in css
    assert ".metric-list > div:nth-last-child(-n+2)" not in css
    assert ".metric-list .metric-wide" in css
    assert "const categoryMax" in app
    assert "Number(info.count || 0) / categoryMax" in app


def test_online_discovery_pages_past_seen_arxiv_results(monkeypatch):
    from conflux.paper_ingestion import arxiv_source
    from conflux.paper_ingestion.models import PaperRecord
    from conflux.research_profile import ResearchProfile
    from conflux.workbench import server

    profile = ResearchProfile(
        id="test-profile",
        name="Test",
        fields=["cs.AI"],
        research_questions=[],
        keywords=["agents"],
    )
    seen = PaperRecord(id="seen", title="Seen", source="arxiv")
    fresh = PaperRecord(id="fresh", title="Fresh", source="arxiv")
    starts = []

    def fake_search(query, *, max_results=10, start=0):
        starts.append(start)
        return [seen] if start == 0 else [fresh]

    monkeypatch.setattr(server, "_load_seen_papers", lambda: {"arxiv:seen": {}})
    monkeypatch.setattr(arxiv_source, "profile_arxiv_queries", lambda profile: ["all:agents"])
    monkeypatch.setattr(arxiv_source, "search_arxiv", fake_search)
    monkeypatch.setattr(server.time, "sleep", lambda seconds: None)

    papers, skipped = server._discover_unseen_papers(profile, "arxiv", 1)

    assert [paper.id for paper in papers] == ["fresh"]
    assert skipped == 1
    assert starts == [0, 1]


def test_online_discovery_round_robins_queries_and_preserves_seen_negative_filters(monkeypatch):
    from conflux.paper_ingestion import arxiv_source
    from conflux.paper_ingestion.models import PaperRecord
    from conflux.research_profile import ResearchProfile
    from conflux.workbench import server

    profile = ResearchProfile(
        id="test-profile",
        name="Test",
        fields=["cs.AI"],
        research_questions=[],
        keywords=["knowledge graph", "natural disaster", "emergency response"],
        negative_keywords=["protein interaction"],
    )
    seen_v2 = PaperRecord(id="2601.00001v2", title="Already seen", source="arxiv")
    negative = PaperRecord(id="negative", title="Protein interaction knowledge graph", source="arxiv")
    fresh_one = PaperRecord(id="fresh-one", title="Disaster graph", source="arxiv")
    fresh_two = PaperRecord(id="fresh-two", title="Emergency graph", source="arxiv")
    fresh_three = PaperRecord(id="fresh-three", title="Response graph", source="arxiv")
    calls = []

    pages = {
        ("q1", 0): [seen_v2],
        ("q2", 0): [negative],
        ("q3", 0): [fresh_one],
        ("q1", 1): [fresh_two],
        ("q2", 1): [fresh_three],
        ("q3", 1): [],
    }

    def fake_search(query, *, max_results=10, start=0):
        calls.append((query, start))
        return pages.get((query, start), [])

    monkeypatch.setattr(server, "_load_seen_papers", lambda: {"arxiv:2601.00001v1": {}})
    monkeypatch.setattr(arxiv_source, "profile_arxiv_queries", lambda profile: ["q1", "q2", "q3"])
    monkeypatch.setattr(arxiv_source, "search_arxiv", fake_search)
    monkeypatch.setattr(server.time, "sleep", lambda seconds: None)

    papers, skipped = server._discover_unseen_papers(profile, "arxiv", 3)

    assert [paper.id for paper in papers] == ["fresh-one", "fresh-two", "fresh-three"]
    assert skipped == 1
    assert calls[:3] == [("q1", 0), ("q2", 0), ("q3", 0)]
    assert negative not in papers


def test_llm_scores_update_reading_levels_stats_and_saved_artifacts(tmp_path):
    from conflux.paper_ingestion.inbox_report import write_inbox_artifacts
    from conflux.paper_ingestion.models import PaperAnalysis, PaperRecord
    from conflux.paper_ingestion.pipeline import PaperInboxResult
    from conflux.research_profile import ResearchProfile
    from conflux.workbench import server

    profile = ResearchProfile(
        id="profile",
        name="Profile",
        fields=["cs.AI"],
        research_questions=[],
        keywords=["knowledge graph"],
    )
    promoted = PaperRecord(id="promoted", title="Relevant paper")
    guarded = PaperRecord(id="guarded", title="Weak lexical paper")
    promoted_analysis = PaperAnalysis(
        paper_id="promoted",
        relevance_score=0.40,
        reading_level="skim",
    )
    guarded_analysis = PaperAnalysis(
        paper_id="guarded",
        relevance_score=0.24,
        reading_level="skip",
    )
    analyzed = [(promoted, promoted_analysis), (guarded, guarded_analysis)]
    artifacts = write_inbox_artifacts(profile, analyzed, out_dir=tmp_path, stats={})
    result = PaperInboxResult(profile=profile, analyzed=analyzed, stats={}, artifacts=artifacts)

    server._apply_llm_scores_to_inbox(result, {
        "promoted": {"score": 90, "reason": "Directly addresses the research question."},
        "guarded": {"score": 100, "reason": "Model-only high score."},
    })

    saved = json.loads((tmp_path / "paper_inbox.json").read_text(encoding="utf-8"))
    saved_by_id = {item["paper"]["id"]: item["analysis"] for item in saved["papers"]}
    assert promoted_analysis.relevance_score == 0.65
    assert promoted_analysis.reading_level == "deep"
    assert guarded_analysis.relevance_score == 0.62
    assert guarded_analysis.reading_level == "skim"
    assert result.stats == {"deep": 1, "skim": 1, "skip": 0, "llm_scored": 2}
    assert saved_by_id["promoted"]["reading_level"] == "deep"
    assert saved_by_id["promoted"]["metadata"]["deterministic_score"] == 0.4


def test_frontend_distinguishes_combined_keyword_and_ai_scores():
    app = Path("src/conflux/workbench/static/app.js").read_text(encoding="utf-8")

    assert "<th>综合分</th>" in app
    assert "<th>关键词分</th><th>AI 分</th>" in app
    assert "paper.keyword_score" in app


def test_seen_paper_history_migrates_existing_inbox(tmp_path, monkeypatch):
    from conflux.workbench import server

    reports = tmp_path / "reports" / "workbench" / "papers"
    reports.mkdir(parents=True)
    (reports / "paper_inbox.json").write_text(json.dumps({
        "papers": [{
            "paper": {
                "id": "2604.13888v1",
                "source": "arxiv",
                "title": "Existing paper",
            }
        }]
    }), encoding="utf-8")
    monkeypatch.setattr(server, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(server, "SEEN_PAPERS_PATH", tmp_path / "reports" / "workbench" / ".seen_papers.json")

    seen = server._load_seen_papers()

    assert "arxiv:2604.13888v1" in seen
    assert seen["arxiv:2604.13888v1"]["title"] == "Existing paper"


def test_existing_profile_semantic_scholar_uses_online_discovery(tmp_path, monkeypatch):
    from conflux.paper_ingestion.models import PaperRecord
    from conflux.research_profile import ResearchProfile
    from conflux.workbench import server

    profile = ResearchProfile(
        id="saved-profile",
        name="Saved",
        fields=["cs.AI"],
        research_questions=[],
        keywords=["multi-agent"],
    )
    paper = PaperRecord(
        id="s2-paper",
        title="Multi-agent research",
        abstract="multi-agent evidence",
        source="semantic_scholar",
    )
    captured = {}

    monkeypatch.setattr(server, "load_profile", lambda path: profile)

    def fake_discover(actual_profile, source, max_results):
        captured.update(profile=actual_profile, source=source, max_results=max_results)
        return [paper], 0

    monkeypatch.setattr(server, "_discover_unseen_papers", fake_discover)
    monkeypatch.setattr(server, "_mark_papers_seen", lambda papers, source: None)

    result = server.run_paper_inbox({
        "profile_mode": "file",
        "profile": "profiles/example.yaml",
        "source": "semantic_scholar",
        "max_results": 10,
        "out_dir": str(tmp_path),
    })

    assert result["ok"] is True
    assert captured == {"profile": profile, "source": "semantic_scholar", "max_results": 10}
    assert result["papers"][0]["id"] == "s2-paper"


def test_semantic_scholar_normalizes_publication_dates(monkeypatch):
    from conflux.workbench import server

    payload = {
        "data": [
            {
                "paperId": "dated-paper",
                "title": "Knowledge Graphs and Large Language Models",
                "abstract": "A survey of integrated methods.",
                "publicationDate": "2025-06-12",
                "year": 2025,
                "authors": [{"name": "Test Author"}],
                "externalIds": {},
                "url": "https://www.semanticscholar.org/paper/dated-paper",
                "openAccessPdf": None,
            },
            {
                "paperId": "year-only-paper",
                "title": "LLM Grounding with Knowledge Graphs",
                "abstract": "A year-only publication record.",
                "publicationDate": None,
                "year": 2024,
                "authors": [],
                "externalIds": {},
                "url": "https://www.semanticscholar.org/paper/year-only-paper",
                "openAccessPdf": None,
            },
        ]
    }

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(payload).encode("utf-8")

    monkeypatch.setattr(server, "_wait_for_semantic_scholar_slot", lambda: None)
    monkeypatch.setattr(server.urllib.request, "urlopen", lambda request, timeout: FakeResponse())

    papers = server._search_semantic_scholar("knowledge graph LLM", max_results=2)

    assert papers[0].published_at.isoformat() == "2025-06-12T00:00:00"
    assert papers[1].published_at.isoformat() == "2024-01-01T00:00:00"
    assert papers[0].to_dict()["published_at"] == "2025-06-12T00:00:00"


def test_semantic_scholar_retries_rate_limits_and_sends_api_key(monkeypatch):
    from conflux.workbench import server

    response_payload = {
        "data": [{
            "paperId": "recovered-paper",
            "title": "Recovered after rate limiting",
            "publicationDate": "2025-01-02",
            "externalIds": {},
        }]
    }
    requests = []
    sleeps = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(response_payload).encode("utf-8")

    def fake_urlopen(request, timeout):
        requests.append(request)
        if len(requests) < 3:
            raise server.urllib.error.HTTPError(
                request.full_url,
                429,
                "Too Many Requests",
                {},
                BytesIO(),
            )
        return FakeResponse()

    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "test-s2-key")
    monkeypatch.setattr(server, "_wait_for_semantic_scholar_slot", lambda: None)
    monkeypatch.setattr(server.random, "uniform", lambda start, end: 0.0)
    monkeypatch.setattr(server.time, "sleep", sleeps.append)
    monkeypatch.setattr(server.urllib.request, "urlopen", fake_urlopen)

    papers = server._search_semantic_scholar("knowledge graph LLM", max_results=1)

    assert [paper.id for paper in papers] == ["recovered-paper"]
    assert sleeps == [2.0, 4.0]
    assert len(requests) == 3
    assert any(
        key.lower() == "x-api-key" and value == "test-s2-key"
        for key, value in requests[0].header_items()
    )


def test_semantic_scholar_final_rate_limit_is_returned_as_raw_api_error(tmp_path, monkeypatch):
    from conflux.research_profile import ResearchProfile
    from conflux.workbench import server

    profile = ResearchProfile(
        id="rate-limit-profile",
        name="Rate limit profile",
        fields=["cs.AI"],
        research_questions=["How are knowledge graphs combined with LLMs?"],
        keywords=["knowledge graph", "large language model"],
    )
    error = server.urllib.error.HTTPError(
        "https://api.semanticscholar.org/graph/v1/paper/search",
        429,
        "Too Many Requests",
        {},
        BytesIO(),
    )

    monkeypatch.setattr(server, "load_profile", lambda path: profile)
    monkeypatch.setattr(
        server,
        "_discover_unseen_papers",
        lambda actual_profile, source, max_results: (_ for _ in ()).throw(error),
    )

    result = server.run_paper_inbox({
        "profile_mode": "file",
        "profile": "profiles/kg_llm_integration.yaml",
        "source": "semantic_scholar",
        "max_results": 10,
        "out_dir": str(tmp_path),
    })

    assert result == {
        "ok": False,
        "error": "semantic_scholar 搜索失败：HTTP Error 429: Too Many Requests",
    }


def test_paper_search_error_uses_summary_and_collapsible_raw_details():
    html = Path("src/conflux/workbench/static/index.html").read_text(encoding="utf-8")
    app = Path("src/conflux/workbench/static/app.js").read_text(encoding="utf-8")

    assert 'id="inboxError"' in html
    assert 'role="alert"' in html
    assert '<details id="inboxErrorDetails"' in html
    assert "查看具体报错" in html
    assert "搜索过于频繁，已被限流，建议稍后再试。" in app
    assert "JSON.stringify(data, null, 2)" in app


def test_workbench_progress_audit_creates_and_compares_baseline(tmp_path):
    from conflux.workbench.server import run_progress_audit

    project = tmp_path / "project"
    project.mkdir()

    def git(*args):
        return subprocess.run(
            ["git", *args],
            cwd=project,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=True,
        )

    git("init")
    git("config", "user.name", "Workbench Test")
    git("config", "user.email", "workbench@example.com")
    (project / "README.md").write_text("# Project\n", encoding="utf-8")
    git("add", "README.md")
    git("commit", "-m", "Initial project")

    profile = tmp_path / "profile.yaml"
    profile.write_text("\n".join([
        "id: progress-profile",
        "name: Progress Profile",
        "fields: [cs.AI]",
        f"research_questions: [{json.dumps('What changed?')}]",
        "keywords: [progress]",
        f"project_paths: [{json.dumps(str(project))}]",
    ]), encoding="utf-8")
    output = tmp_path / "audit-output"
    payload = {
        "profile": str(profile),
        "project_path": str(project),
        "out_dir": str(output),
    }

    first = run_progress_audit(payload)
    (project / "method.py").write_text("VALUE = 1\n", encoding="utf-8")
    git("add", "method.py")
    git("commit", "-m", "Add research method")
    second = run_progress_audit(payload)

    assert first["ok"] is True
    assert first["report"]["baseline_status"] == "created"
    assert second["report"]["baseline_status"] == "compared"
    assert second["report"]["real_progress"][0]["evidence_refs"][0].startswith("git:")
    assert Path(second["markdown_path"]).exists()
    assert Path(second["snapshot_path"]).exists()


def test_frontend_exposes_evidence_backed_progress_audit():
    html = Path("src/conflux/workbench/static/index.html").read_text(encoding="utf-8")
    app = Path("src/conflux/workbench/static/app.js").read_text(encoding="utf-8")

    for element_id in (
        "progress",
        "progressProfile",
        "progressProjectPath",
        "progressTestCommand",
        "runProgressAudit",
        "realProgressList",
        "progressRiskList",
        "weakSignalsList",
        "nextActionsList",
    ):
        assert f'id="{element_id}"' in html
    assert "'/api/progress/audit'" in app
    assert "renderProgressAudit(data)" in app
    assert "item.evidence_refs" in app


def test_frontend_exposes_unified_project_monitoring_panel():
    html = Path("src/conflux/workbench/static/index.html").read_text(encoding="utf-8")
    app = Path("src/conflux/workbench/static/app.js").read_text(encoding="utf-8")
    css = Path("src/conflux/workbench/static/app.css").read_text(encoding="utf-8")

    for element_id in (
        "projects",
        "projectList",
        "refreshProjects",
        "refreshSelectedProject",
        "projectRegisterForm",
        "projectRepoState",
        "projectTimeline",
        "projectActualEvidence",
        "analyzeProjectPlan",
        "applyPlanAnalysis",
        "generateProjectCharter",
        "applyProjectCharter",
        "auditSelectedProject",
        "projectAuditProgressList",
        "projectConfigPath",
    ):
        assert f'id="{element_id}"' in html
    for project_tab in ("overview", "plan", "evidence", "settings"):
        assert f'data-project-tab="{project_tab}"' in html
    assert "'/api/projects/refresh'" in app
    assert "'/api/projects/save'" in app
    assert "'/api/projects/plan-analysis'" in app
    assert "'/api/projects/plan-analysis/apply'" in app
    assert "'/api/projects/charter/generate'" in app
    assert "'/api/projects/charter/apply'" in app
    assert "repo.is_repository" in app
    assert "nav('progress')" not in app[app.index("async function auditSelectedProject"):app.index("function renderAuditItems")]
    assert ".project-workspace" in css
    assert ".plan-timeline" in css
    assert "--sidebar: #0c485e" in css
    assert "--sidebar-active: #3b755f" in css
    assert "--control-height: 40px" in css
    assert "min-height: var(--control-height)" in css


def test_frontend_exposes_fixed_knowledge_reports_search_and_project_settings():
    html = Path("src/conflux/workbench/static/index.html").read_text(encoding="utf-8")
    app = Path("src/conflux/workbench/static/app.js").read_text(encoding="utf-8")
    css = Path("src/conflux/workbench/static/app.css").read_text(encoding="utf-8")

    for element_id in (
        "webSearchProvider",
        "serpapiApiKey",
        "saveProjectSettings",
        "projectNameConfig",
        "projectDocumentFilesConfig",
        "planAnalysisError",
        "planAnalysisErrorDetail",
    ):
        assert f'id="{element_id}"' in html
    assert 'class="single-line-textarea"' in html
    assert "'/api/projects/settings'" in app
    assert "'/api/markdown?path='" in app
    assert "JSON.stringify(data, null, 2)" in app
    assert "const merged = statusCache.reports || []" in app
    assert ".single-line-textarea" in css
    assert ".project-plan-section { background: transparent; }" in css
    assert "container-type: inline-size" in css
    assert "@container (min-width: 520px)" in css
    assert ".query-layout > .surface" in css


def test_project_refresh_contract_is_manual_and_scheduler_is_inactive(tmp_path, monkeypatch):
    import yaml
    from conflux.workbench import server

    project = tmp_path / "project"
    project.mkdir()
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    (projects_dir / "manual.yaml").write_text(yaml.safe_dump({
        "id": "manual",
        "name": "Manual project",
        "path": "project",
        "refresh": {
            "mode": "manual",
            "schedule_enabled": False,
            "interval_minutes": 120,
            "next_refresh_at": "",
        },
    }, sort_keys=False), encoding="utf-8")
    monkeypatch.setattr(server, "PROJECT_ROOT", tmp_path)

    result = server.build_projects_overview()

    assert result["refresh_mode"] == "manual"
    assert result["scheduler_active"] is False
    assert result["projects"][0]["project"]["refresh"]["interval_minutes"] == 120
    assert result["projects"][0]["repository"]["sync_status"] == "not_applicable"
