import json
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


def test_workbench_runs_offline_inbox_and_promotion(tmp_path):
    from conflux.workbench.server import run_paper_inbox, run_paper_promotion

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

    promoted = run_paper_promotion({
        "inbox": str(inbox_dir / "paper_inbox.json"),
        "out_dir": str(promoted_dir),
    })

    assert promoted["ok"] is True
    assert promoted["documents"] == 1
    assert promoted["decisions"] == {"summary_only": 1}
    assert Path(promoted_dir / "paper_promotion_manifest.json").exists()


def test_workbench_safe_file_read_scope():
    from conflux.workbench.server import _safe_read_path

    assert _safe_read_path("docs/graduate_research_copilot_execution_plan.md") is not None
    assert _safe_read_path(".env") is None
    assert _safe_read_path("config.yaml") is None
