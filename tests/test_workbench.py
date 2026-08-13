import json
import subprocess
import time
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


def test_model_probe_supports_json_mode_and_large_output_budget(monkeypatch):
    from conflux.workbench import server

    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"choices":[{"message":{"content":"{}"}}]}'

    def fake_urlopen(request, timeout=60):
        captured.update(json.loads(request.data.decode("utf-8")))
        return FakeResponse()

    monkeypatch.setattr(server.urllib.request, "urlopen", fake_urlopen)

    result = server.run_model_probe({
        "base_url": "https://api.example.test/v1",
        "api_key": "key",
        "model": "structured-model",
        "prompt": "return json",
        "max_tokens": 7200,
        "json_mode": True,
    })

    assert result["ok"] is True
    assert captured["max_tokens"] == 7200
    assert captured["response_format"] == {"type": "json_object"}


def test_model_probe_uses_selected_feature_saved_credentials(monkeypatch):
    from conflux.workbench import server

    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"choices":[{"message":{"content":"ready"}}]}'

    def fake_urlopen(request, timeout=60):
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["authorization"] = request.get_header("Authorization")
        return FakeResponse()

    monkeypatch.setattr(server, "_feature_model_settings", lambda feature: {
        "model": "plan-model",
        "base_url": "https://plan.example/v1",
        "api_key": "plan-key",
        "temperature": 0.1,
    })
    monkeypatch.setattr(server.urllib.request, "urlopen", fake_urlopen)

    result = server.run_model_probe({"model_preset": "plan_analysis", "prompt": "ping"})

    assert result["ok"] is True
    assert captured["body"]["model"] == "plan-model"
    assert captured["authorization"] == "Bearer plan-key"


def test_paper_inbox_uses_independent_review_model(monkeypatch, tmp_path):
    from conflux.workbench import server

    captured = {}

    class FakeReviewResult:
        status = type("Status", (), {"value": "success"})()
        error = ""
        output = {"reviews": []}

    monkeypatch.setattr(server, "_feature_model_settings", lambda feature: {
        "model": "review-model",
        "base_url": "https://review.example/v1",
        "api_key": "review-key",
        "temperature": 0.1,
    })

    from conflux.builtin.paper import plugin as paper_plugin
    monkeypatch.setattr(
        paper_plugin,
        "paper_review",
        lambda ctx, **kwargs: captured.update(preset=ctx.config["model_preset"]) or FakeReviewResult(),
    )

    result = server.run_paper_inbox({
        "profile": "profiles/example_gis_agent.yaml",
        "source": "fixture",
        "fixture": "tests/fixtures/papers/arxiv_sample.json",
        "out_dir": str(tmp_path),
        "use_llm_scoring": True,
    })

    assert result["ok"] is True
    assert captured["preset"] == "paper_review"


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


def test_profile_optimizer_retries_and_rejects_echoed_draft(monkeypatch):
    from conflux.workbench import server

    calls = []
    echoed = {
        "fields": ["cs.AI"],
        "keywords": ["knowledge graph", "natural disaster"],
        "description": "研究知识图谱在自然灾害应急响应中的作用",
        "negative_keywords": [],
        "optimization_notes": [],
    }

    def fake_probe(payload):
        calls.append(payload)
        return {"ok": True, "model": "profile-editor", "content": json.dumps(echoed, ensure_ascii=False)}

    monkeypatch.setattr(server, "run_model_probe", fake_probe)
    result = server.optimize_inline_profile({
        "fields": "cs.AI",
        "keywords": "knowledge graph\nnatural disaster",
        "description": "研究知识图谱在自然灾害应急响应中的作用",
        "base_url": "https://api.example.test/v1",
        "api_key": "secret",
        "model": "profile-editor",
    })

    assert result["ok"] is False
    assert "过于接近" in result["error"]
    assert len(calls) == 2


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


def test_knowledge_stats_only_counts_primary_reports(tmp_path):
    from conflux.knowledge.stats import gather_knowledge_stats

    reports = tmp_path / "reports"
    query = reports / "workbench" / "query"
    evaluation = reports / "eval"
    test_runs = reports / "test_eval_reports"
    query.mkdir(parents=True)
    evaluation.mkdir()
    test_runs.mkdir()

    (reports / "20260803-research.md").write_text("# Report\n", encoding="utf-8")
    (reports / "20260803-research.html").write_text("<h1>Report</h1>\n", encoding="utf-8")
    (query / "20260803-query.md").write_text("# Query report\n", encoding="utf-8")
    (query / "20260803-query.diagnostic.md").write_text("# Diagnostic\n", encoding="utf-8")
    (query / "20260803-query.draft.md").write_text("# Draft\n", encoding="utf-8")
    (query / "20260803-query.sources.md").write_text("# Sources\n", encoding="utf-8")
    (query / "20260803-query.verified.md").write_text("# Verified\n", encoding="utf-8")
    (query / "run.summary.json").write_text("{}\n", encoding="utf-8")
    (query / "run.trace.jsonl").write_text("{}\n", encoding="utf-8")
    (evaluation / "evaluation.md").write_text("# Evaluation\n", encoding="utf-8")
    (test_runs / "test-report.md").write_text("# Test\n", encoding="utf-8")

    stats = gather_knowledge_stats(tmp_path)

    assert stats["reports"]["total"] == 2
    assert stats["reports"]["by_type"] == {".md": 2}
    assert {item["name"] for item in stats["reports"]["recent"]} == {
        "20260803-research.md",
        "20260803-query.md",
    }


def test_workbench_lists_top_level_and_query_primary_reports(tmp_path, monkeypatch):
    from conflux.workbench import server

    reports = tmp_path / "reports"
    query = reports / "workbench" / "query"
    query.mkdir(parents=True)
    (reports / "top-level.md").write_text("# Report\n", encoding="utf-8")
    (query / "query.md").write_text("# Query\n", encoding="utf-8")
    (query / "query.draft.md").write_text("# Draft\n", encoding="utf-8")
    (query / "query.sources.md").write_text("# Sources\n", encoding="utf-8")
    monkeypatch.setattr(server, "PROJECT_ROOT", tmp_path)

    listed = server._list_report_files(reports)

    assert {item["path"] for item in listed} == {
        "reports/top-level.md",
        "reports/workbench/query/query.md",
    }


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


def test_job_manager_submit_and_list(tmp_path, monkeypatch):
    from conflux.workbench.jobs import JobManager

    # Mock _execute to avoid starting a real research query
    monkeypatch.setattr(JobManager, "_execute", lambda self, run_id, query, payload: None)
    mgr = JobManager(db_path=tmp_path / "conflux.db")
    result = mgr.submit("test query", {"depth": "quick"})
    assert "run_id" in result
    assert result["status"] == "pending"
    assert result["timeout_seconds"] == 180
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
    # _reload_env mutates os.environ outside monkeypatch's bookkeeping; clear
    # every temporary managed key so later no-credential tests stay isolated.
    config_store.save_workbench_env(clear_keys=list(saved.keys()))


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
    assert manager.cancel(running.run_id, reason="timeout") is True
    assert running._cancel_flag.is_set() is True
    assert running.cancel_reason == "timeout"


def test_frontend_has_login_and_backend_owned_timeout_flow():
    html = Path("src/conflux/workbench/static/index.html").read_text(encoding="utf-8")
    app = Path("src/conflux/workbench/static/app.js").read_text(encoding="utf-8")
    timeout_start = app.index("const queryTimeout")
    timeout_end = app.index("}, runTimeoutSeconds * 1000);", timeout_start)
    timeout_block = app[timeout_start:timeout_end]

    assert 'id="authDialog"' in html
    assert "'/api/login'" in app
    assert "requestQueryCancellation(runId, 'timeout')" not in timeout_block
    assert "后端正在保存报告与 trace" in timeout_block
    assert "clearInterval(pollInterval)" not in timeout_block
    assert "300000" not in timeout_block
    assert "交付完整性：" in app
    assert "引用核验：" in app
    assert "未完成扩展问题：" in app
    assert "人工状态写入项目 YAML" in html
    assert "周期审计与摘要" in html


def test_timeout_and_user_cancel_have_distinct_terminal_states():
    from conflux.workbench.jobs import (
        ResearchJob,
        _JobCancelled,
        _JobTimedOut,
        _enforce_job_stop,
        _finish_without_report,
    )

    timed_out = ResearchJob(
        run_id="timeout",
        query="q",
        status="running",
        timeout_seconds=240,
        cancel_reason="timeout",
        final_answer="partial answer",
        artifacts={"markdown_path": "partial.md"},
    )
    timed_out._cancel_flag.set()
    try:
        _enforce_job_stop(timed_out, time.time())
        raise AssertionError("timeout should stop the job")
    except _JobTimedOut as exc:
        _finish_without_report(timed_out, "timed_out", str(exc))

    cancelled = ResearchJob(run_id="cancel", query="q", status="running", cancel_reason="user")
    cancelled._cancel_flag.set()
    try:
        _enforce_job_stop(cancelled, time.time())
        raise AssertionError("cancel should stop the job")
    except _JobCancelled:
        pass

    deadline = ResearchJob(
        run_id="deadline",
        query="q",
        status="running",
        timeout_seconds=1,
        deadline_at=time.time() - 1,
    )
    try:
        _enforce_job_stop(deadline, time.time() - 2)
        raise AssertionError("backend deadline should stop the job")
    except _JobTimedOut:
        pass

    assert timed_out.status == "timed_out_with_report"
    assert timed_out.final_answer == "partial answer"
    assert timed_out.artifacts == {"markdown_path": "partial.md"}
    assert timed_out.has_report is True
    assert timed_out.warnings
    assert "系统" in timed_out.error
    assert timed_out.cancel_reason == "timeout"
    assert cancelled.status == "running"
    assert deadline.cancel_reason == "timeout"


def test_report_snapshot_survives_later_timeout(tmp_path):
    from conflux.workbench.jobs import (
        ResearchJob,
        _capture_report_snapshot,
        _finish_job,
    )

    job = ResearchJob(run_id="snapshot-timeout", query="q", status="running")
    state = {
        "query": "q",
        "final_answer": "## 回答\n\n已生成报告。",
        "_source_statuses": {},
        "_factcheck_status": "needs_review",
    }

    _capture_report_snapshot(job, state, str(tmp_path), stage="verified")
    _finish_job(job, "timed_out", "APITimeoutError: late verification timeout")

    assert job.status == "timed_out_with_report"
    assert job.final_answer == state["final_answer"]
    assert Path(job.artifacts["markdown_path"]).is_file()
    assert "已生成报告" in Path(job.artifacts["markdown_path"]).read_text(encoding="utf-8")


def test_v2_report_snapshot_does_not_append_legacy_quality_score(tmp_path):
    from conflux.workbench.jobs import ResearchJob, _capture_report_snapshot

    job = ResearchJob(run_id="v2-snapshot", query="q", status="running")
    state = {
        "query": "q",
        "final_answer": "## 回答\n\nV2 报告正文。",
        "_report_markdown": "## 回答\n\nV2 报告正文。",
        "_run_summary": {"mode": "answer_first"},
    }

    _capture_report_snapshot(job, state, str(tmp_path), stage="verified")

    markdown = Path(job.artifacts["markdown_path"]).read_text(encoding="utf-8")
    assert markdown == "## 回答\n\nV2 报告正文。\n"
    assert "质量评分" not in markdown


def test_frontend_displays_partial_success_and_explicit_report_stages():
    app = Path("src/conflux/workbench/static/app.js").read_text(encoding="utf-8")

    assert "timed_out_with_report" in app
    assert "completed_with_warnings" in app
    for label in ("报告初稿", "第一轮核验", "针对性补证", "重新分析", "最终提交"):
        assert label in app


def test_frontend_query_failure_keeps_node_progress_visible():
    app = Path("src/conflux/workbench/static/app.js").read_text(encoding="utf-8")

    assert "const progress = $('queryOutput').textContent" in app
    assert "=== 执行结果 ===" in app


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
        return [seen] * 10 if start == 0 else [fresh]

    monkeypatch.setattr(server, "_load_seen_papers", lambda: {"arxiv:seen": {}})
    monkeypatch.setattr(arxiv_source, "profile_arxiv_queries", lambda profile: ["all:agents"])
    monkeypatch.setattr(arxiv_source, "search_arxiv", fake_search)
    monkeypatch.setattr(server.time, "sleep", lambda seconds: None)

    papers, skipped = server._discover_unseen_papers(profile, "arxiv", 1)

    assert [paper.id for paper in papers] == ["fresh"]
    assert skipped == 1
    assert starts == [0, 10]


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
        ("q1", 0): [seen_v2] * 10,
        ("q2", 0): [negative] * 10,
        ("q3", 0): [fresh_one] * 10,
        ("q1", 10): [fresh_two],
        ("q2", 10): [fresh_three],
        ("q3", 10): [],
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


def test_paper_inbox_keeps_candidates_when_review_model_is_unavailable(tmp_path, monkeypatch):
    from conflux.paper_ingestion.models import PaperRecord
    from conflux.research_profile import ResearchProfile
    from conflux.workbench import server

    profile = ResearchProfile(
        id="saved-profile",
        name="Saved",
        fields=["cs.AI"],
        research_questions=[],
        keywords=["knowledge graph"],
    )
    paper = PaperRecord(
        id="paper-1",
        title="Knowledge graph research",
        abstract="Evidence about knowledge graphs.",
        source="arxiv",
    )
    monkeypatch.setattr(server, "load_profile", lambda path: profile)
    monkeypatch.setattr(server, "_discover_unseen_papers", lambda *args: ([paper], 0))
    monkeypatch.setattr(server, "_mark_papers_seen", lambda papers, source: None)
    monkeypatch.setattr(server, "_feature_model_settings", lambda feature: {
        "model": "",
        "base_url": "",
        "api_key": "",
        "temperature": 0.0,
    })

    result = server.run_paper_inbox({
        "profile": "profiles/example.yaml",
        "source": "arxiv",
        "out_dir": str(tmp_path),
        "use_llm_scoring": True,
    })

    assert result["ok"] is True
    assert result["review_status"] == "unreviewed"
    assert [item["id"] for item in result["papers"]] == ["paper-1"]


def test_paper_inbox_treats_all_seen_batch_as_empty_increment(tmp_path, monkeypatch):
    from conflux.research_profile import ResearchProfile
    from conflux.workbench import server

    profile = ResearchProfile(
        id="saved-profile",
        name="Saved",
        fields=["cs.AI"],
        research_questions=[],
        keywords=["knowledge graph"],
    )
    monkeypatch.setattr(server, "load_profile", lambda path: profile)
    monkeypatch.setattr(server, "_discover_unseen_papers", lambda *args: ([], 17))

    result = server.run_paper_inbox({
        "profile": "profiles/example.yaml",
        "source": "arxiv",
        "out_dir": str(tmp_path),
    })

    assert result["ok"] is True
    assert result["papers"] == []
    assert result["stats"]["previously_seen"] == 17
    assert "没有新增论文" in result["message"]


def test_workbench_exposes_larger_paper_discovery_budget():
    html = Path("src/conflux/workbench/static/index.html").read_text(encoding="utf-8")
    app = Path("src/conflux/workbench/static/app.js").read_text(encoding="utf-8")

    assert 'id="maxResults" type="number" min="1" max="500" value="50"' in html
    assert "review_limit: 40" in app


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


def test_frontend_exposes_evidence_backed_progress_audit():
    """P3.5 cycle audit surface (replaces the removed /api/progress/audit)."""
    html = Path("src/conflux/workbench/static/index.html").read_text(encoding="utf-8")
    app = Path("src/conflux/workbench/static/app.js").read_text(encoding="utf-8")

    for element_id in (
        "p3AuditTitle",
        "p3AuditBody",
        "p3RunAudit",
    ):
        assert f'id="{element_id}"' in html
    assert "'/audit'" in app or "'/audit/confirm'" in app
    assert "renderP3AuditDraft" in app
    assert "claim.evidence_refs" in app


def test_frontend_exposes_unified_project_monitoring_panel():
    """P3.6: the P3 panel is the only project page; legacy aggregation is gone."""
    html = Path("src/conflux/workbench/static/index.html").read_text(encoding="utf-8")
    app = Path("src/conflux/workbench/static/app.js").read_text(encoding="utf-8")
    css = Path("src/conflux/workbench/static/app.css").read_text(encoding="utf-8")

    for element_id in (
        "projects",
        "projectList",
        "refreshProjects",
        "projectRegisterForm",
        "projectDetailP3",
        "p3WorkItemsTable",
        "p3InboxList",
    ):
        assert f'id="{element_id}"' in html
    for project_tab in ("overview", "work", "evidence", "activity", "inbox"):
        assert f'data-p3-tab="{project_tab}"' in html
    assert "'/api/v1/projects" in app
    assert "'/api/projects/save'" in app
    assert "'/api/projects/research/run'" in app
    # Legacy aggregation endpoints are removed with the old page (plan §17.2).
    for legacy_endpoint in (
        "'/api/projects/refresh'",
        "'/api/projects/plan-analysis'",
        "'/api/projects/charter/generate'",
        "'/api/progress/audit'",
    ):
        assert legacy_endpoint not in app
    assert "data-project-tab=" not in html
    assert ".project-workspace" in css
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
        "p3SettingsSave",
        "p3cfgName",
        "p3cfgDocumentDirs",
    ):
        assert f'id="{element_id}"' in html
    assert 'class="single-line-textarea"' in html
    assert "'/api/v1/projects/' + encodeURIComponent(selectedProjectId) + '/settings'" in app
    assert "'/api/markdown?path='" in app
    assert "JSON.stringify(data, null, 2)" in app
    assert "const merged = statusCache.reports || []" in app
    assert ".single-line-textarea" in css
    assert ".project-plan-section { background: transparent; }" in css
    assert "container-type: inline-size" in css
    assert "@container (min-width: 520px)" in css
    assert ".query-layout > .surface" in css


def test_workbench_config_saves_three_user_model_tiers_and_role_routes(tmp_path, monkeypatch):
    from dotenv import dotenv_values
    from conflux.workbench import config_store

    env_file = tmp_path / ".env.workbench"
    monkeypatch.setattr(config_store, "WORKBENCH_ENV", env_file)
    monkeypatch.setattr(config_store, "_loaded_env_keys", set())
    monkeypatch.setattr(config_store, "_original_env_values", {})

    config_store.save_workbench_env(tier_models={
        "quick": {
            "base_url": "https://quick.example/v1",
            "model": "user-quick",
            "api_key": "quick-key",
            "temperature": 0.1,
        },
        "standard": {
            "base_url": "https://standard.example/v1",
            "model": "user-standard",
            "api_key": "standard-key",
            "temperature": 0.2,
        },
        "deep": {
            "base_url": "https://deep.example/v1",
            "model": "user-deep",
            "api_key": "deep-key",
            "temperature": 0.3,
        },
    })

    saved = dotenv_values(env_file)
    assert saved["CONFLUX_MODELS__QUICK__MODEL"] == "user-quick"
    assert saved["CONFLUX_MODELS__STANDARD__MODEL"] == "user-standard"
    assert saved["CONFLUX_MODELS__DEEP__MODEL"] == "user-deep"
    for tier in ("QUICK", "STANDARD", "DEEP"):
        for role in ("PLANNER", "ANALYST", "RERANKER", "SYNTHESIZER", "VERIFIER"):
            assert saved[f"CONFLUX_RESEARCH__PROFILES__{tier}__{role}_MODEL"] == tier.lower()

    config_store.save_workbench_env(clear_keys=list(saved.keys()))


def test_workbench_config_saves_independent_feature_models_and_vector_collection(tmp_path, monkeypatch):
    from dotenv import dotenv_values
    from conflux.workbench import config_store

    env_file = tmp_path / ".env.workbench"
    monkeypatch.setattr(config_store, "WORKBENCH_ENV", env_file)
    monkeypatch.setattr(config_store, "_loaded_env_keys", set())
    monkeypatch.setattr(config_store, "_original_env_values", {})

    config_store.save_workbench_env(
        feature_models={
            "plan_analysis": {
                "base_url": "https://plan.example/v1",
                "model": "plan-model",
                "api_key": "plan-key",
                "temperature": 0.1,
            },
            "research_radar": {
                "base_url": "https://radar.example/v1",
                "model": "radar-model",
                "api_key": "radar-key",
                "temperature": 0.2,
            },
            "paper_review": {
                "base_url": "https://review.example/v1",
                "model": "review-model",
                "api_key": "review-key",
                "temperature": 0.2,
            },
        },
        vector_collection_name="conflux_docs__new",
    )

    saved = dotenv_values(env_file)
    assert saved["CONFLUX_MODELS__PLAN_ANALYSIS__MODEL"] == "plan-model"
    assert saved["CONFLUX_MODELS__RESEARCH_RADAR__MODEL"] == "radar-model"
    assert saved["CONFLUX_MODELS__PAPER_REVIEW__MODEL"] == "review-model"
    assert saved["CONFLUX_MODELS__PLAN_ANALYSIS__API_KEY"] == "plan-key"
    assert saved["CONFLUX_VECTOR_STORE__COLLECTION_NAME"] == "conflux_docs__new"

    config_store.save_workbench_env(clear_keys=list(saved.keys()))


def test_vector_index_rebuild_preserves_old_collection_until_user_deletes(tmp_path, monkeypatch):
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    from langchain_core.embeddings import Embeddings
    from conflux.rag import indexer
    from conflux.workbench import server

    class FakeEmbeddings(Embeddings):
        def embed_documents(self, texts):
            return [[float(index), 0.0, 1.0] for index, _ in enumerate(texts, start=1)]

        def embed_query(self, text):
            return [1.0, 0.0, 1.0]

    chroma_dir = tmp_path / "chroma"
    source_dir = tmp_path / "documents"
    source_dir.mkdir()
    (source_dir / "paper.md").write_text(
        "---\nchunk_id: paper:1#summary\npaper_id: '1'\n---\n\n# Paper\n\nEvidence.\n",
        encoding="utf-8",
    )
    (source_dir / "paper-full.md").write_text(
        "---\nchunk_id: paper:1#fulltext-0\npaper_id: '1'\npaper_section: introduction\n---\n\n# Full text\n\nDetails.\n",
        encoding="utf-8",
    )
    client = chromadb.PersistentClient(path=str(chroma_dir), settings=ChromaSettings(anonymized_telemetry=False))
    old = client.get_or_create_collection("conflux_docs")
    old.add(ids=["old"], documents=["old"], embeddings=[[0.0, 1.0, 0.0]])

    active = {"name": "conflux_docs"}

    def fake_get(*path, default=None):
        if path == ("vector_store", "persist_dir"):
            return str(chroma_dir)
        if path == ("vector_store", "collection_name"):
            return (
                server.config._context_override_value("CONFLUX_VECTOR_STORE__COLLECTION_NAME")
                or active["name"]
            )
        if path == ("embedding", "model"):
            return "test-embedding"
        return default

    def fake_save_workbench_env(**kwargs):
        active["name"] = kwargs["vector_collection_name"]
        return 1

    monkeypatch.setattr(server.config, "get", fake_get)
    monkeypatch.setattr(indexer, "get", fake_get)
    monkeypatch.setattr(indexer, "create_embedding_model", lambda: FakeEmbeddings())
    monkeypatch.setattr(server, "save_workbench_env", fake_save_workbench_env)

    rebuilt = server.rebuild_knowledge_index({
        "source_dir": str(source_dir),
        "collection_name": "conflux_docs__new",
        "embedding_api_key": "test-key",
        "embedding_model": "test-embedding",
    })

    assert rebuilt["ok"] is True
    assert rebuilt["active_collection"] == "conflux_docs__new"
    names = {str(item if isinstance(item, str) else item.name) for item in client.list_collections()}
    assert names == {"conflux_docs", "conflux_docs__new"}
    assert client.get_collection("conflux_docs").count() == 1
    rebuilt_payload = client.get_collection("conflux_docs__new").get(include=["metadatas"])
    assert client.get_collection("conflux_docs__new").count() == 2
    metadata_by_id = {
        item_id: metadata
        for item_id, metadata in zip(rebuilt_payload["ids"], rebuilt_payload["metadatas"])
    }
    assert metadata_by_id["paper:1#summary"]["content_scope"] == "summary"
    assert metadata_by_id["paper:1#fulltext-0"]["content_scope"] == "full_text"
    assert metadata_by_id["paper:1#fulltext-0"]["full_text_indexed"] is True

    denied = server.delete_knowledge_index({"collection_name": "conflux_docs__new"})
    assert denied["ok"] is False
    deleted = server.delete_knowledge_index({"collection_name": "conflux_docs"})
    assert deleted["ok"] is True
    names = {str(item if isinstance(item, str) else item.name) for item in client.list_collections()}
    assert names == {"conflux_docs__new"}


def test_vector_index_rebuild_reports_invalid_front_matter_path(tmp_path):
    from conflux.workbench import server

    source_dir = tmp_path / "documents"
    source_dir.mkdir()
    invalid = source_dir / "invalid.md"
    invalid.write_text(
        "---\npaper_section: [8] invalid citation heading\n---\n\n# Paper\n",
        encoding="utf-8",
    )

    result = server.rebuild_knowledge_index({"source_dir": str(source_dir)})

    assert result["ok"] is False
    assert "知识文档解析失败" in result["error"]
    assert str(invalid) in result["error"]


def test_workbench_defaults_full_rebuild_to_all_documents():
    html = Path("src/conflux/workbench/static/index.html").read_text(encoding="utf-8")

    assert 'id="rebuildSourceDir" value="data/documents"' in html


def test_query_model_override_targets_only_selected_user_tier():
    from conflux.workbench.jobs import _model_env_updates

    updates = _model_env_updates({
        "depth": "deep",
        "base_url": "https://models.example/v1",
        "model": "user-deep-model",
        "api_key": "secret",
    })

    assert updates["CONFLUX_MODELS__DEEP__MODEL"] == "user-deep-model"
    assert "CONFLUX_MODELS__REASONING__MODEL" not in updates
    assert updates["CONFLUX_RESEARCH__PROFILES__DEEP__PLANNER_MODEL"] == "deep"
    assert updates["CONFLUX_RESEARCH__PROFILES__DEEP__VERIFIER_MODEL"] == "deep"


def test_query_without_model_override_keeps_configured_role_presets():
    from conflux.workbench.jobs import _model_env_updates

    updates = _model_env_updates({"depth": "standard"})

    assert "CONFLUX_MODELS__STANDARD__PROVIDER" not in updates
    assert "CONFLUX_RESEARCH__PROFILES__STANDARD__PLANNER_MODEL" not in updates
    assert updates["CONFLUX_RESEARCH__DEPTH"] == "standard"


def test_deep_query_inherits_configured_retrieval_width():
    from conflux.workbench import jobs, server

    for builder in (jobs._model_env_updates, server._model_env_updates):
        updates = builder({"depth": "deep"})
        assert "CONFLUX_RETRIEVAL__TOP_K" not in updates
        assert "CONFLUX_RETRIEVAL__FINAL_K" not in updates


def test_depth_preset_metadata_uses_configured_retrieval_width(monkeypatch):
    from conflux.workbench import config_store

    def fake_get(*path, default=None):
        values = {
            ("retrieval", "top_k"): 60,
            ("retrieval", "final_k"): 20,
        }
        return values.get(path, default)

    monkeypatch.setattr(config_store.config, "get", fake_get)

    assert config_store.get_depth_preset("quick").retrieval_top_k == 3
    assert config_store.get_depth_preset("standard").retrieval_top_k == 60
    assert config_store.get_depth_preset("standard").retrieval_final_k == 20
    assert config_store.get_depth_preset("deep").retrieval_top_k == 60
    assert config_store.get_depth_preset("deep").retrieval_final_k == 20


def test_job_status_exposes_complete_markdown_artifact_path():
    from conflux.workbench.jobs import JobManager, ResearchJob

    manager = JobManager()
    manager._jobs["report-run"] = ResearchJob(
        run_id="report-run",
        query="q",
        status="completed",
        final_answer="x" * 5000,
        pipeline="p1",
        artifacts={"markdown_path": "reports/workbench/query/report.md"},
    )

    status = manager.get("report-run")
    assert status is not None
    assert status["report_md_path"] == "reports/workbench/query/report.md"
    assert status["pipeline"] == "p1"
    assert status["final_answer_truncated"] is True


def test_full_text_missing_history_is_reselectable(monkeypatch):
    from conflux.paper_ingestion import arxiv_source
    from conflux.paper_ingestion.models import PaperRecord
    from conflux.research_profile import ResearchProfile
    from conflux.workbench import server

    profile = ResearchProfile(
        id="repair",
        name="Repair",
        fields=["cs.AI"],
        research_questions=[],
        keywords=["geospatial agent"],
    )
    paper = PaperRecord(id="2604.13888v2", title="Repairable", source="arxiv")
    monkeypatch.setattr(server, "_load_seen_papers", lambda: {
        "arxiv:2604.13888": {"status": "inboxed", "title": "Repairable"},
    })
    monkeypatch.setattr(server, "build_paper_ingestion_audit", lambda: {
        "papers": [{
            "identity": "arxiv:2604.13888",
            "status": "full_text_missing",
        }],
    })
    monkeypatch.setattr(arxiv_source, "profile_arxiv_queries", lambda profile: ["all:agent"])
    monkeypatch.setattr(arxiv_source, "search_arxiv", lambda *args, **kwargs: [paper])

    papers, skipped = server._discover_unseen_papers(profile, "arxiv", 1)

    assert [item.id for item in papers] == ["2604.13888v2"]
    assert skipped == 0


def test_legacy_unknown_source_is_recovered_for_arxiv_ids():
    from conflux.workbench.server import _normalized_paper_source

    assert _normalized_paper_source("unknown", "2410.12376v2") == "arxiv"
    assert _normalized_paper_source("", "2604.13888v1") == "arxiv"
    assert _normalized_paper_source("unknown", "custom-paper") == "unknown"


def test_promotion_history_records_actual_missing_full_text(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from langchain_core.documents import Document
    from conflux.knowledge import paper_indexer
    from conflux.paper_ingestion.models import PaperRecord
    from conflux.workbench import server

    seen_path = tmp_path / ".seen_papers.json"
    seen_path.write_text(json.dumps({
        "arxiv:2604.13888": {"status": "inboxed", "title": "Paper"},
    }), encoding="utf-8")
    monkeypatch.setattr(server, "SEEN_PAPERS_PATH", seen_path)
    paper = PaperRecord(id="2604.13888v1", title="Paper", source="arxiv")
    monkeypatch.setattr(paper_indexer, "load_inbox_payload", lambda path: [(paper, None)])
    result = SimpleNamespace(
        decisions=[SimpleNamespace(paper_id=paper.id, action="full_text")],
        documents=[Document(page_content="summary", metadata={
            "paper_id": paper.id,
            "content_scope": "summary",
            "full_text_status": "not_downloaded",
        })],
    )

    server._update_seen_after_promotion(result, inbox="ignored.json", indexed=True)

    saved = json.loads(seen_path.read_text(encoding="utf-8"))
    assert saved["arxiv:2604.13888"]["status"] == "full_text_missing"
    assert saved["arxiv:2604.13888"]["full_text_status"] == "not_downloaded"


def test_frontend_exposes_three_model_tiers_markdown_result_and_ingestion_audit():
    html = Path("src/conflux/workbench/static/index.html").read_text(encoding="utf-8")
    app = Path("src/conflux/workbench/static/app.js").read_text(encoding="utf-8")

    for tier in ("quick", "standard", "deep"):
        for suffix in ("BaseUrl", "ModelName", "ApiKey", "Temperature"):
            assert f'id="{tier}{suffix}"' in html
    assert 'id="queryReportPreview"' in html
    assert 'id="paperIngestionAudit"' in html
    assert "tier_models: allTierModelsPayload()" in app
    assert "'/api/markdown?path=' + encodeURIComponent(reportPath)" in app
