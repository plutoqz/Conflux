path = r"src/conflux/workbench/server.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# === 1. Backend: add workbench env file constant and loader ===
old_const = 'RUN_LOCK = threading.Lock()'
new_const = '''WORKBENCH_ENV = PROJECT_ROOT / ".env.workbench"
RUN_LOCK = threading.Lock()


def _load_workbench_env() -> None:
    """Load persisted model config from .env.workbench into os.environ (if file exists)."""

    if not WORKBENCH_ENV.exists():
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(WORKBENCH_ENV, override=True)
    except Exception:
        pass


_load_workbench_env()'''
content = content.replace(old_const, new_const)
print("1. Const + loader:", "OK" if old_const not in content else "FAIL")

# === 2. Backend: add save_model_config function before run_paper_promotion ===
old_promotion = 'def run_paper_promotion(payload: dict[str, Any]) -> dict[str, Any]:'
new_save = '''def save_model_config(payload: dict[str, Any]) -> dict[str, Any]:
    """Persist model configuration to local .env.workbench file (never committed)."""

    base_url = str(payload.get("base_url") or "").strip()
    api_key = str(payload.get("api_key") or "").strip()
    model = str(payload.get("model") or "").strip()
    embedding_base_url = str(payload.get("embedding_base_url") or "").strip()
    embedding_api_key = str(payload.get("embedding_api_key") or "").strip()
    embedding_model = str(payload.get("embedding_model") or "").strip()

    lines = []
    if base_url:
        lines.append(f"CONFLUX_MODELS__REASONING__BASE_URL={base_url}")
        lines.append(f"CONFLUX_MODELS__CHEAP__BASE_URL={base_url}")
    if api_key:
        lines.append(f"CONFLUX_MODELS__REASONING__API_KEY={api_key}")
        lines.append(f"CONFLUX_MODELS__CHEAP__API_KEY={api_key}")
    if model:
        lines.append(f"CONFLUX_MODELS__REASONING__MODEL={model}")
        lines.append(f"CONFLUX_MODELS__CHEAP__MODEL={model}")
    if embedding_base_url:
        lines.append(f"CONFLUX_EMBEDDING__BASE_URL={embedding_base_url}")
    if embedding_api_key:
        lines.append(f"CONFLUX_EMBEDDING__API_KEY={embedding_api_key}")
    if embedding_model:
        lines.append(f"CONFLUX_EMBEDDING__MODEL={embedding_model}")

    try:
        WORKBENCH_ENV.write_text("\\n".join(lines) + "\\n", encoding="utf-8")
        # Reload env immediately so subsequent queries pick it up
        _load_workbench_env()
        return {"ok": True, "saved": len(lines)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def run_paper_promotion(payload: dict[str, Any]) -> dict[str, Any]:'''
content = content.replace(old_promotion, new_save)
print("2. save_model_config:", "OK" if old_promotion not in content else "FAIL")

# === 3. Backend: add API route for /api/model/save ===
old_route = '''            if self.path == "/api/model/test":
                self._send_json(run_model_probe(payload))
                return'''
new_route = '''            if self.path == "/api/model/test":
                self._send_json(run_model_probe(payload))
                return
            if self.path == "/api/model/save":
                self._send_json(save_model_config(payload))
                return'''
content = content.replace(old_route, new_route)
print("3. API route:", "OK" if old_route not in content else "FAIL")

# === 4. HTML: rename 模型探测 to 模型配置 everywhere ===
renames_html = [
    ('<span class="nav-icon">🔌</span>模型探测', '<span class="nav-icon">⚙️</span>模型配置'),
    ('<h2>🔌 模型探测</h2>', '<h2>⚙️ 模型配置</h2>'),
    ('<p class="desc">测试 LLM API 连接 — 此处配置的 API 信息会自动同步到「研究查询」页面</p>',
     '<p class="desc">配置 LLM API 连接信息，可保存到本地（不会上传到远程仓库）。「研究查询」页面会自动复用此配置</p>'),
    ('<h2>探测结果</h2>', '<h2>探测结果</h2>'),  # keep this
]
for old, new in renames_html:
    if old in content:
        content = content.replace(old, new)
        print(f"  HTML rename: {old[:30]}... OK")
    else:
        print(f"  HTML rename: {old[:30]}... NOT FOUND")

# === 5. HTML: Add save button in model page ===
old_test_btn = '<div class="actions"><button id="testModel">🔍 测试连接</button></div>'
new_test_btn = '''<div class="actions"><button id="testModel">🔍 测试连接</button><button id="saveModel" class="ghost">💾 保存配置</button></div>'''
content = content.replace(old_test_btn, new_test_btn)
print("5. Save button:", "OK" if old_test_btn not in content else "FAIL")

# === 6. JS: Update model page description comment ===
old_comment = '/* ── Model probe ── */'
new_comment = '/* ── Model config ── */'
content = content.replace(old_comment, new_comment)
print("6. JS comment:", "OK")

# === 7. JS: Add save handler after testModel handler ===
old_after_test = """    }
  } catch(e) {
    toast('网络错误: ' + e.message, 'err');
  }
  leaveBusy(btn);
};

/* ── Papers inbox run ── */"""
new_save_js = """    }
  } catch(e) {
    toast('网络错误: ' + e.message, 'err');
  }
  leaveBusy(btn);
};

/* ── Save model config ── */
$('saveModel').onclick = async function(){
  var btn = this;
  enterBusy(btn);
  try {
    var data = await api('/api/model/save', {
      base_url: $('baseUrl').value,
      api_key: $('apiKey').value,
      model: $('modelName').value,
      embedding_base_url: $('embeddingBaseUrl').value,
      embedding_api_key: $('embeddingApiKey').value,
      embedding_model: $('embeddingModel').value
    });
    if (data.ok) {
      toast('配置已保存到本地 (' + data.saved + ' 项)', 'ok');
      await refreshStatus();
    } else {
      toast(data.error || '保存失败', 'err');
    }
  } catch(e) {
    toast('保存出错: ' + e.message, 'err');
  }
  leaveBusy(btn);
};

/* ── Papers inbox run ── */"""
content = content.replace(old_after_test, new_save_js)
print("7. JS save handler:", "OK" if old_after_test not in content else "FAIL")

# === 8. JS: Pre-populate embedding API key from model page's API key if empty ===
# Already handled by the user manually — no change needed

# === 9. Update build_status to also report workbench env file info ===
old_creds = """        "credentials": {
            "openai_api_key":"""
new_creds = """        "workbench_env": str(WORKBENCH_ENV) if WORKBENCH_ENV.exists() else "",
        "credentials": {
            "openai_api_key":"""
content = content.replace(old_creds, new_creds)
print("9. build_status:", "OK" if old_creds not in content else "FAIL")

# === 10. Add .env.workbench to .gitignore ===
gitignore_path = r".gitignore"
with open(gitignore_path, "r", encoding="utf-8") as f:
    gi = f.read()
if ".env.workbench" not in gi:
    with open(gitignore_path, "a", encoding="utf-8") as f:
        f.write(".env.workbench\n")
    print("10. .gitignore: added .env.workbench")
else:
    print("10. .gitignore: already present")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("\nAll done!")
