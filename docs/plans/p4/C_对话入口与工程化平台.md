# C 对话入口与工程化平台设计

> 文档状态：设计完成，待实施确认
>
> 优先级：P0（第 2 批，依赖 A、B 结论）→ 建议映射 P4.2（含工程卫生横切）
>
> 版本：1.0
>
> 日期：2026-08-13
>
> 上位：[../P4智能体能力与工程化扩展计划.md](../P4智能体能力与工程化扩展计划.md)

## 0. 目标

自然语言统一入口：论文获取入库、问题查询、项目分析总结、实验登记等，以对话形态编排既有能力。同步落地 **FastAPI、token 流式、可观测性（structlog/OTel/Langfuse）、MCP、工程卫生**五项工程栈。`answer_first` 保持唯一研究管道，对话**不改写管道**（ADR-02）。

## 1. 现状与复用

| 已有基建 | 复用方式 |
|---|---|
| stdlib HTTP server + SSE（`workbench/server.py` ~4k 行） | 冻结共存；新功能只进 v2 层 |
| M3 持久 Job + EventStore + `ApprovalRequest` | 任务编排与副作用门禁 |
| P3 `/api/v1/projects/*` 快照 API | 项目状态查询直接复用 |
| `agent.py` ReAct 循环（`bind_tools` + max_iterations=3） | 受控 agentic 通道种子 |
| `prompts/routing/` | 意图分类提示词位置 |
| `/api/v1` 与 legacy 共存先例 | FastAPI v2 与 stdlib 共存模式 |

## 2. 架构：路由 + 编排 + 呈现（三层）

```
用户输入
  → ① 意图路由（确定性优先）
       规则（命令词/关键词）→ 动作白名单
       未命中 → LLM 分类器（结构化输出，非白名单即拒绝）
       仍无法归类 → 澄清问题
  → ② 编排
       动作 → 既有 Job/管道（M3 job、V2 图、P3 API、P4 实验/记忆 API）
       写操作（入库/跑雷达/实验登记）→ 先 ApprovalRequest
  → ③ 呈现
       回答逐条带证据链接 + Run 引用；SSE 进度；token 流式
```

动作白名单（起步集）：`run_radar`、`research_query`、`project_audit`、`cycle_summary`、`experiment_register`、`memory_query`、`ingest_pdf`、`skill_run`。未接入的动作一律明确回答"暂不支持"，不做全功能重做。

## 3. FastAPI v2 层

- 新增 `/api/chat/*` FastAPI 应用（同进程 uvicorn 挂载），老 stdlib 端点冻结共存。
- Pydantic v2 请求/响应模型 + OpenAPI 自动文档（`/docs` 即展示资产）。
- token 流式：SSE/WebSocket 逐 token 输出 + 任务进度事件复用 EventStore。

## 4. 受控 agentic 通道（仅开放类任务）

- 仅开放类任务（失败测试分析、多文件调研等）经路由进入；确定性任务永远走确定性管道。
- 白名单工具 `bind_tools`（`search_rag` / `search_web` / `project_state` / `experiment_query`），`max_iterations ≤ 3`，每步 `BudgetState` 预扣，产出进 Evidence Ledger。
- 工具执行与模型输出分离：工具确定性执行、模型负责判断（延续既有约束）。

## 5. 可观测性（工程栈核心展示点）

- `structlog` 结构化日志贯穿服务端。
- OpenTelemetry span：每次 LLM 调用记录 模型/角色/token/耗时/成本估算，每 run 一棵 span 树。
- Langfuse 自托管导出（可选开关，本地部署）。
- 工作台"观测"页：成本/延迟/质量三块，按节点/角色/模型分组（复用 p33/p36 基线数据格式）。

## 6. MCP 双向

- **Server**：暴露 `search_rag` / `search_web` / `paper_radar` / `project_audit` / `experiment_register` 5 个工具（stdio 传输）——外部 agent（Codex 等）可调用 Conflux 工具，替代已砍掉的"唤起外部 CLI"方向。
- **Client**：config 声明外部 MCP server（arXiv/Zotero 等），工具调用需确认门 + 参数白名单校验。
- 与 M1 插件协议关系：MCP 是对外互操作补充，不替代（ADR-04）。

## 7. 工程卫生横切（与 C 捆绑，不单独立项）

| 项 | 内容 |
|---|---|
| 代码质量 | ruff + mypy + pre-commit 钩子 |
| CI | GitHub Actions 矩阵（3.11/3.12）+ coverage 门禁 |
| 迁移 | Alembic 接管 0001–0009 及后续 migration |
| 分发 | uv + pyproject 完整化 + PyPI 发布流程 |
| 环境 | Docker devcontainer + 单命令安装 |
| Demo | `scripts/p4_demo.py`：全 fixture + 确定性模型，"三篇种子论文 → 雷达 → 入库 → 查询 → 周报"一条命令跑完，零外部 API 依赖 |

## 8. 验收（C1–C7）

| 编号 | 验收项 | 通过标准 |
|---|---|---|
| C1 | 端到端对话 | fixture 剧本 20 任务成功率 ≥ 90% |
| C2 | 证据可追溯 | 对话回答证据链接覆盖率 100% |
| C3 | API 文档 | `/docs` 可访问且覆盖 `/api/chat/*` |
| C4 | 观测 | 观测页可导出成本/延迟报告（对照预算） |
| C5 | 门禁 | 写操作未经确认零执行（测试） |
| C6 | 路由兜底 | 非白名单意图一律转澄清，不幻觉执行（测试） |
| C7 | 零成本 demo | 无网络跑通 demo 脚本 |

## 9. 风险与取舍

| 风险 | 对策 |
|---|---|
| 范围蔓延（"全功能重做"） | 三层边界写死：路由/编排/呈现；未接入动作明示不支持 |
| 路由误判 | 白名单兜底 + 澄清成本低 |
| 对话形态证据退化（变成闲聊） | 每条回答绑定 Run/证据，模板强制 |
| stdlib/FastAPI 共存期混乱 | 新功能只进 v2 层，老端点只读冻结 |
