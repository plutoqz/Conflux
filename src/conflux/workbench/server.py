"""Local HTTP workbench for inspecting and running Conflux workflows."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import mimetypes
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from conflux import config
from conflux.knowledge.paper_indexer import promote_inbox
from conflux.paper_ingestion.pipeline import build_inbox_from_arxiv, build_inbox_from_fixture


PROJECT_ROOT = config.PROJECT_ROOT
DEFAULT_PROFILE = "profiles/example_gis_agent.yaml"
DEFAULT_FIXTURE = "tests/fixtures/papers/arxiv_sample.json"
DEFAULT_INBOX_DIR = "reports/workbench/papers"
DEFAULT_PROMOTE_DIR = "data/documents/papers"
RUN_LOCK = threading.Lock()


def build_status() -> dict[str, Any]:
    """Return sanitized local workbench status."""

    raw = config.load()
    reasoning = dict(raw.get("models", {}).get("reasoning") or {})
    cheap = dict(raw.get("models", {}).get("cheap") or {})
    embedding = dict(raw.get("embedding") or {})

    return {
        "project_root": str(PROJECT_ROOT),
        "profiles": _list_files(PROJECT_ROOT / "profiles", {".yaml", ".yml"}),
        "reports": _list_files(PROJECT_ROOT / "reports", {".md", ".html", ".json"}),
        "paper_outputs": _list_files(PROJECT_ROOT / "data" / "documents" / "papers", {".md", ".json"}),
        "defaults": {
            "profile": DEFAULT_PROFILE,
            "fixture": DEFAULT_FIXTURE,
            "inbox_dir": DEFAULT_INBOX_DIR,
            "promote_dir": DEFAULT_PROMOTE_DIR,
            "reasoning": _sanitize_model_config(reasoning, "OPENAI_API_KEY"),
            "cheap": _sanitize_model_config(cheap, "OPENAI_API_KEY"),
            "embedding": _sanitize_model_config(embedding, "OPENAI_API_KEY"),
        },
        "credentials": {
            "openai_api_key": _has_env("OPENAI_API_KEY"),
            "reasoning_api_key": _has_env("CONFLUX_MODELS__REASONING__API_KEY"),
            "cheap_api_key": _has_env("CONFLUX_MODELS__CHEAP__API_KEY"),
            "embedding_api_key": _has_env("CONFLUX_EMBEDDING__API_KEY"),
            "serpapi_api_key": _has_env("SERPAPI_API_KEY"),
        },
    }


def run_paper_inbox(payload: dict[str, Any]) -> dict[str, Any]:
    """Run the paper inbox pipeline from UI payload."""

    profile = _path_value(payload.get("profile"), DEFAULT_PROFILE)
    out_dir = _path_value(payload.get("out_dir"), DEFAULT_INBOX_DIR)
    source = str(payload.get("source") or "fixture")
    max_results = int(payload.get("max_results") or 10)

    if source == "arxiv":
        result = build_inbox_from_arxiv(profile, max_results=max_results, out_dir=out_dir)
    else:
        fixture = _path_value(payload.get("fixture"), DEFAULT_FIXTURE)
        result = build_inbox_from_fixture(profile, fixture, out_dir=out_dir)

    artifacts = result.artifacts
    papers = [
        {
            "id": paper.id,
            "title": paper.title,
            "url": paper.url,
            "pdf_url": paper.pdf_url,
            "score": analysis.relevance_score,
            "reading_level": analysis.reading_level,
            "citation_value": analysis.citation_value,
            "reasons": analysis.metadata.get("score_reasons") or [],
        }
        for paper, analysis in result.analyzed
    ]
    return {
        "ok": True,
        "profile_id": result.profile.id,
        "stats": result.stats,
        "papers": papers,
        "markdown_path": _rel(artifacts.markdown_path) if artifacts else "",
        "json_path": _rel(artifacts.json_path) if artifacts else "",
    }


def run_paper_promotion(payload: dict[str, Any]) -> dict[str, Any]:
    """Promote paper inbox JSON into knowledge documents."""

    inbox = _path_value(payload.get("inbox"), f"{DEFAULT_INBOX_DIR}/paper_inbox.json")
    out_dir = _path_value(payload.get("out_dir"), DEFAULT_PROMOTE_DIR)
    pinned = payload.get("pin") or []
    if isinstance(pinned, str):
        pinned = [item.strip() for item in pinned.splitlines() if item.strip()]

    result = promote_inbox(
        inbox,
        out_dir=out_dir,
        policy_name=str(payload.get("policy") or "default"),
        allow_full_text=bool(payload.get("full_text")),
        pinned_ids=list(pinned),
        index=bool(payload.get("index")),
        pdf_dir=_optional_path(payload.get("pdf_dir")),
        download_pdfs=bool(payload.get("download_pdfs")),
    )
    actions: dict[str, int] = {}
    for decision in result.decisions:
        actions[decision.action] = actions.get(decision.action, 0) + 1

    artifacts = result.artifacts
    return {
        "ok": True,
        "documents": len(result.documents),
        "indexed": result.indexed_count,
        "decisions": actions,
        "documents_dir": _rel(artifacts.documents_dir) if artifacts else "",
        "manifest_path": _rel(artifacts.manifest_path) if artifacts else "",
        "sources_path": _rel(artifacts.sources_path) if artifacts else "",
    }


def run_model_probe(payload: dict[str, Any]) -> dict[str, Any]:
    """Call an OpenAI-compatible chat completion endpoint."""

    model = str(payload.get("model") or _default_model_name("reasoning")).strip()
    base_url = str(payload.get("base_url") or _default_base_url("reasoning")).strip()
    api_key = str(payload.get("api_key") or _default_api_key("reasoning")).strip()
    prompt = str(payload.get("prompt") or "Reply with a short readiness check.").strip()
    temperature = float(payload.get("temperature") or 0.2)
    max_tokens = int(payload.get("max_tokens") or 256)

    if not model:
        return {"ok": False, "error": "Model name is required."}
    if not base_url:
        return {"ok": False, "error": "Base URL is required."}
    if not api_key:
        return {"ok": False, "error": "API key is required or must be present in local environment."}

    endpoint = _chat_endpoint(base_url)
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=int(payload.get("timeout") or 60)) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1200]
        return {"ok": False, "status": exc.code, "error": detail}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

    elapsed_ms = round((time.perf_counter() - started) * 1000)
    choices = response_payload.get("choices") or []
    content = ""
    if choices:
        message = choices[0].get("message") or {}
        content = str(
            message.get("content")
            or message.get("reasoning_content")
            or choices[0].get("text")
            or ""
        )
    return {
        "ok": True,
        "model": response_payload.get("model") or model,
        "endpoint": endpoint,
        "elapsed_ms": elapsed_ms,
        "content": content,
        "usage": response_payload.get("usage") or {},
    }


def run_query(payload: dict[str, Any]) -> dict[str, Any]:
    """Run a real Conflux query with temporary model overrides."""

    query = str(payload.get("query") or "").strip()
    if not query:
        return {"ok": False, "error": "Query is required."}

    updates = _model_env_updates(payload)
    output_dir = _path_value(payload.get("output_dir"), "reports/workbench/query")
    mode = str(payload.get("mode") or "phase2")
    stream = io.StringIO()
    started = time.perf_counter()
    with RUN_LOCK, _temporary_env(updates), contextlib.redirect_stdout(stream):
        try:
            from conflux.__main__ import query_command

            state = query_command(
                query,
                mode=mode,
                output_dir=output_dir,
                stream_events=False,
                trace_dir=output_dir,
            )
        except SystemExit as exc:
            return {"ok": False, "exit_code": exc.code, "stdout": stream.getvalue()}
        except Exception as exc:
            return {"ok": False, "error": str(exc), "stdout": stream.getvalue()}

    elapsed_ms = round((time.perf_counter() - started) * 1000)
    return {
        "ok": True,
        "elapsed_ms": elapsed_ms,
        "stdout": stream.getvalue()[-6000:],
        "final_answer": str(state.get("final_answer") or "")[:4000],
    }


class WorkbenchHandler(BaseHTTPRequestHandler):
    server_version = "ConfluxWorkbench/0.1"

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            self._send_text(INDEX_HTML, "text/html; charset=utf-8")
            return
        if parsed.path == "/app.css":
            self._send_text(APP_CSS, "text/css; charset=utf-8")
            return
        if parsed.path == "/app.js":
            self._send_text(APP_JS, "application/javascript; charset=utf-8")
            return
        if parsed.path == "/api/status":
            self._send_json(build_status())
            return
        if parsed.path == "/api/file":
            params = urllib.parse.parse_qs(parsed.query)
            self._send_file(params.get("path", [""])[0])
            return
        self.send_error(404)

    def do_POST(self) -> None:
        try:
            payload = self._read_json()
            if self.path == "/api/papers/inbox":
                self._send_json(run_paper_inbox(payload))
                return
            if self.path == "/api/papers/promote":
                self._send_json(run_paper_promotion(payload))
                return
            if self.path == "/api/model/test":
                self._send_json(run_model_probe(payload))
                return
            if self.path == "/api/query/run":
                self._send_json(run_query(payload))
                return
            self.send_error(404)
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=500)

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[workbench] {self.address_string()} - {fmt % args}")

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_text(self, text: str, content_type: str) -> None:
        data = text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_file(self, requested_path: str) -> None:
        path = _safe_read_path(requested_path)
        if path is None or not path.exists() or not path.is_file():
            self.send_error(404)
            return
        content_type = mimetypes.guess_type(path.name)[0] or "text/plain"
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the Conflux local research workbench.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--log-file", help="Optional file for workbench stdout/stderr")
    parser.add_argument("--daemon", action="store_true", help="Start the workbench in a detached background process")
    parser.add_argument("--pid-file", default="reports/workbench-server.pid", help="PID file used with --daemon")
    args = parser.parse_args(argv)

    if args.daemon:
        port = _available_port(args.host, args.port)
        log_file = args.log_file or str(PROJECT_ROOT / "reports" / "workbench-server.log")
        pid_file = Path(args.pid_file)
        if not pid_file.is_absolute():
            pid_file = PROJECT_ROOT / pid_file
        pid_file.parent.mkdir(parents=True, exist_ok=True)
        child_args = [
            sys.executable,
            "-m",
            "conflux.workbench",
            "--host",
            args.host,
            "--port",
            str(port),
            "--log-file",
            log_file,
        ]
        creationflags = 0
        if os.name == "nt":
            creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        proc = subprocess.Popen(
            child_args,
            cwd=str(PROJECT_ROOT),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            creationflags=creationflags,
        )
        pid_file.write_text(str(proc.pid), encoding="utf-8")
        print(f"Conflux workbench started: http://{args.host}:{port}")
        print(f"PID file: {pid_file}")
        print(f"Log file: {log_file}")
        return

    log_handle = None
    if args.log_file:
        log_path = Path(args.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_handle = log_path.open("a", encoding="utf-8")
        sys.stdout = log_handle
        sys.stderr = log_handle

    port = _available_port(args.host, args.port)
    server = ThreadingHTTPServer((args.host, port), WorkbenchHandler)
    print(f"Conflux workbench: http://{args.host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Conflux workbench.", flush=True)
    finally:
        server.server_close()
        if log_handle:
            log_handle.close()


def _available_port(host: str, preferred: int) -> int:
    for port in range(preferred, preferred + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((host, port))
                return port
            except OSError:
                continue
    raise OSError(f"No available port near {preferred}.")


def _list_files(root: Path, suffixes: set[str]) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in suffixes:
            files.append({
                "path": _rel(path),
                "name": path.name,
                "size": path.stat().st_size,
                "modified": int(path.stat().st_mtime),
            })
    return files[-80:]


def _sanitize_model_config(cfg: dict[str, Any], fallback_env: str) -> dict[str, Any]:
    return {
        "provider": cfg.get("provider", "openai_compatible"),
        "model": cfg.get("model", ""),
        "base_url": cfg.get("base_url", ""),
        "temperature": cfg.get("temperature", 0.2),
        "max_tokens": cfg.get("max_tokens", 1024),
        "api_key_present": bool(cfg.get("api_key") or os.environ.get(fallback_env)),
    }


def _has_env(name: str) -> bool:
    return bool(os.environ.get(name))


def _default_model_name(preset: str) -> str:
    raw = config.load()
    return str(((raw.get("models") or {}).get(preset) or {}).get("model") or "")


def _default_base_url(preset: str) -> str:
    raw = config.load()
    return str(((raw.get("models") or {}).get(preset) or {}).get("base_url") or "https://api.openai.com/v1")


def _default_api_key(preset: str) -> str:
    name = f"CONFLUX_MODELS__{preset.upper()}__API_KEY"
    return os.environ.get(name) or os.environ.get("OPENAI_API_KEY") or ""


def _path_value(value: Any, default: str) -> str:
    text = str(value or default).strip()
    path = Path(text).expanduser()
    if path.is_absolute():
        return str(path)
    return str(PROJECT_ROOT / path)


def _optional_path(value: Any) -> str | None:
    text = str(value or "").strip()
    return _path_value(text, text) if text else None


def _rel(path: str | Path) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(resolved)


def _chat_endpoint(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return f"{base}/chat/completions"


def _model_env_updates(payload: dict[str, Any]) -> dict[str, str]:
    updates: dict[str, str] = {}
    base_url = str(payload.get("base_url") or "").strip()
    api_key = str(payload.get("api_key") or "").strip()
    model = str(payload.get("model") or "").strip()
    embedding_base_url = str(payload.get("embedding_base_url") or "").strip()
    embedding_api_key = str(payload.get("embedding_api_key") or "").strip()
    embedding_model = str(payload.get("embedding_model") or "").strip()

    for preset in ("REASONING", "CHEAP"):
        updates[f"CONFLUX_MODELS__{preset}__PROVIDER"] = "openai_compatible"
        if base_url:
            updates[f"CONFLUX_MODELS__{preset}__BASE_URL"] = base_url
        if api_key:
            updates[f"CONFLUX_MODELS__{preset}__API_KEY"] = api_key
        if model:
            updates[f"CONFLUX_MODELS__{preset}__MODEL"] = model
    if embedding_base_url or base_url:
        updates["CONFLUX_EMBEDDING__BASE_URL"] = embedding_base_url or base_url
    if embedding_api_key or api_key:
        updates["CONFLUX_EMBEDDING__API_KEY"] = embedding_api_key or api_key
    if embedding_model:
        updates["CONFLUX_EMBEDDING__MODEL"] = embedding_model
    return updates


@contextlib.contextmanager
def _temporary_env(updates: dict[str, str]):
    old_values = {key: os.environ.get(key) for key in updates}
    try:
        for key, value in updates.items():
            if value:
                os.environ[key] = value
        config._config = None  # type: ignore[attr-defined]
        yield
    finally:
        for key, value in old_values.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        config._config = None  # type: ignore[attr-defined]


def _safe_read_path(requested_path: str) -> Path | None:
    if not requested_path:
        return None
    path = Path(requested_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    try:
        resolved = path.resolve()
    except OSError:
        return None
    allowed = [
        PROJECT_ROOT / "reports",
        PROJECT_ROOT / "data" / "documents" / "papers",
        PROJECT_ROOT / "profiles",
        PROJECT_ROOT / "docs",
        PROJECT_ROOT / "tests" / "fixtures" / "papers",
    ]
    for root in allowed:
        try:
            resolved.relative_to(root.resolve())
            if resolved.name.lower() in {".env", "config.yaml"}:
                return None
            return resolved
        except ValueError:
            continue
    return None


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Conflux Workbench</title>
  <link rel="stylesheet" href="/app.css">
</head>
<body>
  <div class="shell">
    <aside class="side">
      <div class="brand">Conflux</div>
      <nav>
        <button class="nav active" data-target="papers">Papers</button>
        <button class="nav" data-target="promotion">Promotion</button>
        <button class="nav" data-target="model">Model</button>
        <button class="nav" data-target="query">Query</button>
        <button class="nav" data-target="reports">Reports</button>
      </nav>
      <div class="status">
        <div class="label">Runtime</div>
        <div id="keyStatus" class="stack"></div>
      </div>
    </aside>
    <main>
      <header class="topbar">
        <div>
          <h1>Local Research Workbench</h1>
          <p id="rootPath"></p>
        </div>
        <button id="refreshBtn" class="ghost">Refresh</button>
      </header>

      <section id="papers" class="view active">
        <div class="band">
          <h2>Paper Inbox</h2>
          <div class="grid two">
            <label>Profile path<input id="profilePath"></label>
            <label>Output directory<input id="inboxOut"></label>
            <label>Source<select id="paperSource"><option value="fixture">Fixture</option><option value="arxiv">arXiv</option></select></label>
            <label>Fixture path<input id="fixturePath"></label>
            <label>Max results<input id="maxResults" type="number" min="1" max="100" value="10"></label>
          </div>
          <div class="actions">
            <button id="runInbox">Run Inbox</button>
          </div>
        </div>
        <div class="band">
          <div class="split-title"><h2>Inbox Result</h2><span id="inboxStats"></span></div>
          <div class="table-wrap"><table id="papersTable"></table></div>
          <pre id="inboxOutput"></pre>
        </div>
      </section>

      <section id="promotion" class="view">
        <div class="band">
          <h2>Promotion Review</h2>
          <div class="grid two">
            <label>Inbox JSON<input id="promoteInbox"></label>
            <label>Output directory<input id="promoteOut"></label>
            <label>PDF directory<input id="pdfDir"></label>
            <label>Pinned paper IDs<textarea id="pinIds" rows="3"></textarea></label>
          </div>
          <div class="toggles">
            <label><input id="fullText" type="checkbox"> Full text</label>
            <label><input id="downloadPdfs" type="checkbox"> Download PDFs</label>
            <label><input id="indexDocs" type="checkbox"> Index to Chroma</label>
          </div>
          <div class="actions">
            <button id="runPromote">Promote</button>
          </div>
        </div>
        <div class="band"><h2>Promotion Output</h2><pre id="promotionOutput"></pre></div>
      </section>

      <section id="model" class="view">
        <div class="band">
          <h2>Model Probe</h2>
          <div class="grid two">
            <label>Base URL<input id="baseUrl" autocomplete="off"></label>
            <label>Model<input id="modelName" autocomplete="off"></label>
            <label>API key<input id="apiKey" type="password" autocomplete="off"></label>
            <label>Max tokens<input id="maxTokens" type="number" min="32" max="8192" value="256"></label>
            <label>Temperature<input id="temperature" type="number" min="0" max="2" step="0.1" value="0.2"></label>
          </div>
          <label>Prompt<textarea id="probePrompt" rows="4">Reply with a short readiness check for Conflux.</textarea></label>
          <div class="actions"><button id="testModel">Test Model</button></div>
        </div>
        <div class="band"><h2>Probe Output</h2><pre id="modelOutput"></pre></div>
      </section>

      <section id="query" class="view">
        <div class="band">
          <h2>Research Query</h2>
          <label>Question<textarea id="queryText" rows="4">Explain how local paper evidence should be separated from web evidence and model inference.</textarea></label>
          <div class="grid two">
            <label>Output directory<input id="queryOut" value="reports/workbench/query"></label>
            <label>Embedding model<input id="embeddingModel" value=""></label>
            <label>Embedding base URL<input id="embeddingBaseUrl"></label>
            <label>Embedding API key<input id="embeddingApiKey" type="password" autocomplete="off"></label>
          </div>
          <div class="actions"><button id="runQuery">Run Real Query</button></div>
        </div>
        <div class="band"><h2>Query Output</h2><pre id="queryOutput"></pre></div>
      </section>

      <section id="reports" class="view">
        <div class="band">
          <div class="split-title"><h2>Artifacts</h2><button id="reloadReports" class="ghost">Reload</button></div>
          <div class="table-wrap"><table id="reportsTable"></table></div>
        </div>
        <div class="band"><h2>Preview</h2><iframe id="preview"></iframe><pre id="fileText"></pre></div>
      </section>
    </main>
  </div>
  <script src="/app.js"></script>
</body>
</html>
"""


APP_CSS = """
:root {
  --bg: #f4f2ed;
  --panel: #ffffff;
  --ink: #202124;
  --muted: #69707d;
  --line: #d8d3c8;
  --accent: #0f766e;
  --accent-strong: #0b5d56;
  --warn: #9a6700;
  --soft: #eef7f5;
  --code: #f6f7f8;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font: 14px/1.5 Arial, "Microsoft YaHei", sans-serif;
}
.shell { display: grid; grid-template-columns: 238px 1fr; min-height: 100vh; }
.side {
  background: #18201f;
  color: #f8faf9;
  padding: 22px 16px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}
.brand { font-size: 20px; font-weight: 700; letter-spacing: 0; }
nav { display: grid; gap: 6px; }
.nav, button {
  border: 0;
  border-radius: 6px;
  padding: 10px 12px;
  cursor: pointer;
  font-weight: 650;
}
.nav { text-align: left; background: transparent; color: #dbe5e2; }
.nav.active, .nav:hover { background: #263331; color: #ffffff; }
.status { margin-top: auto; border-top: 1px solid #364340; padding-top: 16px; }
.label { color: #aebbb7; font-size: 12px; text-transform: uppercase; margin-bottom: 8px; }
.stack { display: grid; gap: 8px; }
.chip {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  border-radius: 999px;
  padding: 3px 9px;
  background: #2f3c39;
  color: #e8efed;
  font-size: 12px;
}
.chip.ok { background: #124d43; }
.chip.warn { background: #5a430c; }
main { padding: 24px; min-width: 0; }
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}
h1, h2 { margin: 0; line-height: 1.25; letter-spacing: 0; }
h1 { font-size: 24px; }
h2 { font-size: 16px; }
p { margin: 6px 0 0; color: var(--muted); }
.view { display: none; }
.view.active { display: grid; gap: 16px; }
.band {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 18px;
}
.grid { display: grid; gap: 12px; margin-top: 14px; }
.grid.two { grid-template-columns: repeat(2, minmax(0, 1fr)); }
label { display: grid; gap: 6px; color: #34383f; font-weight: 650; }
input, select, textarea {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 9px 10px;
  background: #fff;
  color: var(--ink);
  font: inherit;
}
textarea { resize: vertical; }
.toggles { display: flex; gap: 18px; flex-wrap: wrap; margin-top: 14px; }
.toggles label { display: flex; align-items: center; gap: 7px; }
.toggles input { width: auto; }
.actions { display: flex; gap: 10px; margin-top: 16px; }
button { background: var(--accent); color: #fff; }
button:hover { background: var(--accent-strong); }
button.ghost {
  background: #ffffff;
  color: var(--accent-strong);
  border: 1px solid var(--line);
}
.split-title { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.table-wrap { overflow: auto; margin-top: 12px; border: 1px solid var(--line); border-radius: 8px; }
table { width: 100%; border-collapse: collapse; background: #fff; }
th, td { padding: 9px 10px; border-bottom: 1px solid var(--line); vertical-align: top; text-align: left; }
th { background: var(--soft); color: #263331; font-size: 12px; text-transform: uppercase; }
td small { color: var(--muted); }
pre {
  min-height: 120px;
  max-height: 430px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  background: var(--code);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px;
}
iframe {
  width: 100%;
  min-height: 520px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
}
#fileText { display: none; }
@media (max-width: 820px) {
  .shell { grid-template-columns: 1fr; }
  .side { position: static; }
  .grid.two { grid-template-columns: 1fr; }
  .topbar { align-items: flex-start; flex-direction: column; }
}
"""


APP_JS = """
const $ = (id) => document.getElementById(id);
let statusCache = null;

async function api(path, payload) {
  const res = await fetch(path, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload || {})
  });
  return await res.json();
}

async function refreshStatus() {
  const res = await fetch('/api/status');
  statusCache = await res.json();
  $('rootPath').textContent = statusCache.project_root;
  $('profilePath').value = statusCache.defaults.profile;
  $('fixturePath').value = statusCache.defaults.fixture;
  $('inboxOut').value = statusCache.defaults.inbox_dir;
  $('promoteInbox').value = statusCache.defaults.inbox_dir + '/paper_inbox.json';
  $('promoteOut').value = statusCache.defaults.promote_dir;
  $('baseUrl').value = statusCache.defaults.reasoning.base_url || 'https://api.openai.com/v1';
  $('modelName').value = statusCache.defaults.reasoning.model || '';
  $('embeddingBaseUrl').value = statusCache.defaults.embedding.base_url || '';
  $('embeddingModel').value = statusCache.defaults.embedding.model || '';
  renderCredentials(statusCache.credentials);
  renderReports();
}

function renderCredentials(creds) {
  const rows = [
    ['OPENAI', creds.openai_api_key],
    ['Reasoning', creds.reasoning_api_key],
    ['Cheap', creds.cheap_api_key],
    ['Embedding', creds.embedding_api_key],
    ['Search', creds.serpapi_api_key]
  ];
  $('keyStatus').innerHTML = rows.map(([name, ok]) =>
    `<span class="chip ${ok ? 'ok' : 'warn'}">${name}: ${ok ? 'set' : 'empty'}</span>`
  ).join('');
}

function nav(target) {
  document.querySelectorAll('.nav').forEach(btn => btn.classList.toggle('active', btn.dataset.target === target));
  document.querySelectorAll('.view').forEach(view => view.classList.toggle('active', view.id === target));
}

function renderPapers(papers) {
  const head = '<tr><th>Level</th><th>Score</th><th>Title</th><th>Reasons</th></tr>';
  const rows = papers.map(p => `<tr>
    <td><span class="chip">${p.reading_level}</span></td>
    <td>${Number(p.score).toFixed(3)}</td>
    <td><strong>${escapeHtml(p.title)}</strong><br><small>${escapeHtml(p.id)}</small></td>
    <td>${escapeHtml((p.reasons || []).join('; '))}</td>
  </tr>`).join('');
  $('papersTable').innerHTML = head + rows;
}

function renderReports() {
  if (!statusCache) return;
  const rows = [...statusCache.reports, ...statusCache.paper_outputs].reverse();
  const head = '<tr><th>File</th><th>Size</th><th>Open</th></tr>';
  $('reportsTable').innerHTML = head + rows.map(item => `<tr>
    <td>${escapeHtml(item.path)}</td>
    <td>${item.size}</td>
    <td><button class="ghost" data-open="${escapeHtml(item.path)}">Open</button></td>
  </tr>`).join('');
  document.querySelectorAll('[data-open]').forEach(btn => btn.onclick = () => openFile(btn.dataset.open));
}

async function openFile(path) {
  const url = '/api/file?path=' + encodeURIComponent(path);
  if (path.endsWith('.html')) {
    $('preview').style.display = 'block';
    $('fileText').style.display = 'none';
    $('preview').src = url;
    return;
  }
  const res = await fetch(url);
  const text = await res.text();
  $('preview').style.display = 'none';
  $('fileText').style.display = 'block';
  $('fileText').textContent = text;
}

function modelPayload() {
  return {
    base_url: $('baseUrl').value,
    model: $('modelName').value,
    api_key: $('apiKey').value,
    prompt: $('probePrompt').value,
    temperature: Number($('temperature').value || 0.2),
    max_tokens: Number($('maxTokens').value || 256)
  };
}

function escapeHtml(text) {
  return String(text || '').replace(/[&<>"']/g, ch => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[ch]));
}

document.querySelectorAll('.nav').forEach(btn => btn.onclick = () => nav(btn.dataset.target));
$('refreshBtn').onclick = refreshStatus;
$('reloadReports').onclick = refreshStatus;

$('runInbox').onclick = async () => {
  $('inboxOutput').textContent = 'Running...';
  const data = await api('/api/papers/inbox', {
    profile: $('profilePath').value,
    source: $('paperSource').value,
    fixture: $('fixturePath').value,
    out_dir: $('inboxOut').value,
    max_results: Number($('maxResults').value || 10)
  });
  $('inboxOutput').textContent = JSON.stringify(data, null, 2);
  if (data.ok) {
    $('inboxStats').textContent = `deep/skim/skip ${data.stats.deep}/${data.stats.skim}/${data.stats.skip}`;
    $('promoteInbox').value = data.json_path;
    renderPapers(data.papers || []);
    await refreshStatus();
  }
};

$('runPromote').onclick = async () => {
  $('promotionOutput').textContent = 'Running...';
  const data = await api('/api/papers/promote', {
    inbox: $('promoteInbox').value,
    out_dir: $('promoteOut').value,
    pdf_dir: $('pdfDir').value,
    full_text: $('fullText').checked,
    download_pdfs: $('downloadPdfs').checked,
    index: $('indexDocs').checked,
    pin: $('pinIds').value
  });
  $('promotionOutput').textContent = JSON.stringify(data, null, 2);
  await refreshStatus();
};

$('testModel').onclick = async () => {
  $('modelOutput').textContent = 'Running...';
  const data = await api('/api/model/test', modelPayload());
  $('modelOutput').textContent = JSON.stringify(data, null, 2);
};

$('runQuery').onclick = async () => {
  $('queryOutput').textContent = 'Running...';
  const data = await api('/api/query/run', {
    ...modelPayload(),
    query: $('queryText').value,
    output_dir: $('queryOut').value,
    embedding_base_url: $('embeddingBaseUrl').value,
    embedding_api_key: $('embeddingApiKey').value,
    embedding_model: $('embeddingModel').value
  });
  $('queryOutput').textContent = JSON.stringify(data, null, 2);
  await refreshStatus();
};

refreshStatus();
"""
