# Conflux

Conflux 是一个本地优先的研究工作台，将论文发现、知识入库、多源证据调研和项目进度审计连接起来，并生成可追溯的 Markdown、HTML 和结构化运行产物。

当前项目适合个人研究和工程能力展示，重点包括多源检索编排、Evidence Graph、FactCheck、Chunk 级引用、离线评测和结构化 Trace。可扩展 ResearchOps 架构改造已完成 M0-M2：Plugin SDK、Registry、动态来源协议、第一方 RAG/Web/论文评审插件和 YAML 工作流均已接入。

## 当前技术能力

- LangGraph 工作流并行执行 RAG 和 Web 检索，再由 Model Analyst 读取外部证据进行分析。
- 来源状态协议包含 `success`、`low_relevance`、`no_evidence`、`failed` 和 `fallback`。
- `no_evidence`、`failed` 和 `fallback` 来源不会进入 Evidence Graph 共识投票。
- 来源结果包含声明级 `evidence_refs`、`confidence` 和 `limitations`。
- RAG 结果使用 `[RAG:quantum-crypto.txt#chunk-p0-c0]` 等 Chunk 级引用。
- FactCheck 包含确定性追溯检查和独立模型核查；当前尚未形成自动修订再核查循环。
- Trace JSONL 和 Run Summary JSON 用于检查每次运行的阶段和来源状态。
- 离线评测覆盖检索质量、报告验收、失败来源泄漏和 Prompt Injection。

## 为什么使用 LangGraph

当前调研流程需要明确状态边界、并行检索分支、条件路由和可选 Checkpointer。仓库已接入内存 Checkpointer，并记录 `run_id`、`thread_id`、Checkpoint 后端、来源状态和阶段进度；内存后端不会在进程重启后保留状态，因此当前不能宣称已经支持持久断点恢复。

```mermaid
flowchart TD
    Q["User query"] --> D["dispatch"]
    D --> R["RAG retrieval"]
    D --> W["Web retrieval"]
    R --> M["Model Analyst"]
    W --> M
    M --> E["evidence merge + arbitration"]
    E --> S["synthesize report"]
    S --> F["FactCheck"]
    F --> L{"L4 enabled?"}
    L -->|yes| U["deep retrieval + analysis"]
    L -->|no| O["Markdown + HTML + trace"]
    U --> O
```

## 当前可用于简历展示的能力

- 构建可复现的多源研究系统，包含样例报告、验收检查和来源感知的报告生成。
- 使用 LangGraph 实现并行检索、分阶段分析、内存 Checkpoint 接口和结构化 Trace。
- 构建包含混合检索、Chunk 级引用和离线检索评测的 RAG 流程。
- 设计声明级证据协议、置信度、冲突仲裁和失败来源排除规则。
- 建立覆盖来源失败、证据分歧、幻觉泄漏、Prompt Injection 和报告验收的评测 Harness。

## 仓库结构

```text
.
├── config.yaml
├── .env.example
├── examples/
├── docs/
│   ├── architecture.md       # 已批准的长期架构蓝图
│   └── execution_plan_v1.md  # 已批准，M0-M2 完成 / M3+ 未启动
├── data/documents/
├── prompts/
├── scripts/
│   ├── eval_retrieval.py
│   ├── eval_reports.py
│   └── eval_end_to_end.py
├── src/conflux/
│   ├── __main__.py
│   ├── graph_v2.py
│   ├── checkpointing.py
│   ├── trace.py
│   ├── source_status.py
│   ├── evidence.py
│   ├── report.py
│   ├── acceptance.py
│   ├── tools/
│   └── rag/
└── tests/
```

## 文档与后续方向

- [PRODUCT.md](PRODUCT.md)：当前产品定位和设计原则。
- [DESIGN.md](DESIGN.md)：当前工作台视觉和交互约束。
- [docs/architecture.md](docs/architecture.md)：已批准的可扩展 ResearchOps 长期架构蓝图。
- [docs/execution_plan_v1.md](docs/execution_plan_v1.md)：M0-M2 已完成、M3+ 尚未启动的实施方案和验收记录。

蓝图负责把握项目方向，执行方案负责实现方法和验收标准。M1/M2 已完成核心协议、第一方能力、动态来源和 YAML 工作流；持久 Run Store、Evidence Ledger 等内容尚未开始实施。

## 安装

```powershell
python -m pip install -e ".[dev]"
```

将 `.env.example` 复制为仅供本地使用的 `.env`，不要提交真实密钥。

默认配置使用 OpenAI 兼容服务：

```yaml
models:
  reasoning:
    model: deepseek-v4-flash
    base_url: https://www.dmxapi.cn/v1

embedding:
  model: text-embedding-3-small
  base_url: https://www.dmxapi.cn/v1
```

真实运行需要配置：

```powershell
$env:OPENAI_API_KEY="your-api-key"
```

可选覆盖项：

```powershell
$env:CONFLUX_MODELS__REASONING__API_KEY="your-api-key"
$env:CONFLUX_MODELS__CHEAP__API_KEY="your-api-key"
$env:CONFLUX_EMBEDDING__API_KEY="your-api-key"
$env:SERPAPI_API_KEY="your-serpapi-key"
```

缺少密钥时，CLI 会在发起真实 API 请求前退出并明确说明缺失的凭证。

## 快速开始

构建本地 RAG 索引：

```powershell
python -m conflux --index data/documents
```

运行 Phase 2 调研查询：

```powershell
python -m conflux "Explain how Conflux should arbitrate RAG, Web, and Model evidence." --mode phase2 --output-dir reports --stream-events
```

运行本地研究工作台：

```powershell
python -m conflux.workbench --host 127.0.0.1 --port 8765
```

## 插件与 YAML 工作流

查看内置能力、加载用户插件目录并校验工作流：

```powershell
python -m conflux plugin list --verbose
python -m conflux plugin list --plugin-dir path\to\plugins
python -m conflux workflow validate tests\fixtures\architecture\workflows\research_query_v2.yaml --dry-run
python -m conflux workflow run tests\fixtures\architecture\workflows\test_query.yaml --input-json '{"query":"quantum crypto"}'
python -m conflux.paper_ingestion inbox --profile profiles\example_gis_agent.yaml --fixture tests\fixtures\papers\arxiv_sample.json --llm-review
```

也可以使用 `CONFLUX_PLUGIN_DIRS` 指定多个插件目录。M1/M2 插件是可信的进程内 Python 代码，Manifest 权限用于校验和审计，不提供沙箱；YAML 只组合已注册能力，不执行任意 Python。

## 项目进度审计

研究画像中的 `project_paths` 用于登记本地项目。首次运行建立基线：

```powershell
python -m conflux.progress snapshot --profile profiles/example_gis_agent.yaml --out-dir reports/progress
```

后续运行会比较 Git 提交、未提交文件、测试状态、研究产物和报告变化，并生成带证据引用的 Markdown/JSON 审计报告：

```powershell
python -m conflux.progress audit --profile profiles/example_gis_agent.yaml --since last --test-command "python -m pytest -q" --out-dir reports/progress
```

也可以在本地工作台的“进度审计”页面选择画像和项目路径后运行。审计只读取本地证据，不会上传项目文件，也不会执行未明确配置的命令。

## 多项目进度监控

工作台的“项目监控”页面统一展示本地/远程版本、未提交变更、计划基线、文档、实验产物、报告和最近审计结果。首期只支持手动刷新，Git 监控严格只读：不会执行 `pull`、`push`、`checkout` 或 `fetch`。远程检查通过 `git ls-remote` 读取版本；如果远程对象尚未进入本地对象库，界面会明确提示无法计算精确 ahead/behind。

每个项目在 `projects/` 下使用一份 YAML 作为权威配置。项目路径可以是 Git 仓库，也可以是只有文档、数据或实验产物的普通目录。非 Git 目录会显示“Git 不适用”，不会被记为故障。

```yaml
version: 1
id: kg-llm
name: KG + LLM 研究
path: E:\research\kg-llm
documents:
  directories: [docs, notes]
artifacts:
  result_dirs: [experiments, results]
  report_dirs: [reports]
plan:
  overall_goal: 验证知识图谱增强大模型推理的有效性。
  milestones:
  - id: baseline
    title: 完成基线与消融实验
    status: in_progress
  next_actions:
  - 整理实验数据并补充误差分析。
refresh:
  mode: manual
  schedule_enabled: false
  interval_minutes: null
  timezone: Asia/Shanghai
```

“分析项目计划”会读取已配置的 Markdown 文档，通过模型生成结构化计划预览，并结合代码、Git、测试、报告和研究产物进行证据核验。分析结果只有在用户明确选择并确认后才会写入项目 YAML。`schedule_enabled`、`interval_minutes` 和 `next_refresh_at` 已预留给后续定时任务，当前不会启动后台调度。

使用内存 Checkpointer 运行：

```powershell
python -m conflux "Evaluate Loop Engineering in agent workflows." --thread-id demo-loop-001 --checkpoint-backend memory --output-dir reports
```

该后端只在当前进程生命周期内保存状态。跨进程持久恢复属于已批准但尚未实施的方向，不是当前能力。

验证生成的报告：

```powershell
python -m conflux.acceptance path\to\report.md path\to\report.html
```

## 质量门禁

运行单元测试：

```powershell
python -m pytest -q
```

运行离线检索评测：

```powershell
python scripts/eval_retrieval.py --offline
```

运行离线报告评测：

```powershell
python scripts/eval_reports.py --offline
```

显式选择运行真实 API 冒烟测试：

```powershell
python scripts/eval_end_to_end.py --real
```

## 当前离线基线

确定性离线检索评测输出：

- `reports/eval/retrieval_eval.md`
- `reports/eval/retrieval_eval.json`

报告评测输出：

- `reports/eval/report_eval.md`
- `reports/eval/report_eval.json`

这些产物包含 recall@k、hit rate、来源覆盖、无关结果比例、验收通过率、失败来源泄漏、Prompt Injection 泄漏、延迟和成本估算。

## 示例

- [三个来源均成功](examples/three_sources_success.md)
- [Web 失败，RAG 和 Model 成功](examples/web_failed_rag_model_success.md)
- [RAG 与 Web 存在冲突](examples/rag_web_conflict.md)

## 安全

- API Key 只通过环境变量或本地 Secret 配置提供。
- `.env`、生成报告、Chroma 数据库、缓存和运行产物均被 Git 忽略。
- RAG 检索到的 Prompt Injection 文本只作为证据内容，不能成为系统指令。
- `failed` 和 `fallback` 来源对用户可见，但不能成为 Evidence Graph 节点。

## 许可证

项目采用 MIT 许可证，参见 [LICENSE](LICENSE)。
