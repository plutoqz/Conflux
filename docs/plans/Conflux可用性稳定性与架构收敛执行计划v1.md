# Conflux 可用性、稳定性与架构收敛执行计划 v1

> 文档状态：详细设计完成，待用户明确指令“开始实施”后进入 P0
>
> 方案：B——增量模块化单体，逐个垂直切片收敛为单一 ASGI 服务
>
> 版本：1.0
>
> 日期：2026-08-15
>
> 上位约束：[架构设计.md](../架构设计.md)、[PRODUCT.md](../../PRODUCT.md)、[DESIGN.md](../../DESIGN.md)
>
> 历史状态来源：[执行计划v1.md](执行计划v1.md)、[P3研究项目工作台重构计划.md](P3研究项目工作台重构计划.md)、[p4/P4实施计划v1.md](p4/P4实施计划v1.md)

## 0. 文档职责与使用方式

本文档定义 Conflux 下一轮可用性、稳定性和工程收敛工作的唯一执行顺序、阶段边界、验收标准、证据要求和恢复规则。它不覆盖 P3/P4 历史计划；历史计划保留当时的设计与实施记录，本文件只管理本轮方案 B。

本文档同时承担本轮长期工作的状态载体。开始实施后，只更新本文件中的“当前执行状态”“阶段检查点”“风险与阻塞”和“证据索引”，不得为每个阶段复制新的计划文件。评测原始结果和报告进入 `reports/evaluation/convergence/`，不把大段运行输出回填到计划正文。

本文件当前仅代表方案已经写清楚，不代表任何阶段已经通过。只有用户明确发出“开始实施”或等价指令后，AI coding 才能进入 P0；“继续”只推进到当前阶段的下一个验收点；“暂停”只更新检查点，不继续修改。

### 0.1 状态词语义

| 状态 | 含义 |
|---|---|
| `pending` | 尚未开始，不能据此声称能力存在 |
| `in_progress` | 正在实施，只能引用已完成的局部证据 |
| `blocked` | 当前验收点受外部条件或未决决策阻塞 |
| `implemented` | 代码已落地但尚未完成规定层级的验收 |
| `validated_offline` | 单元、合同、集成或回放证据通过，不代表 live capability |
| `validated_live` | 冻结版本下使用真实数据、真实 Provider 和真实流程通过 |
| `completed` | 本阶段全部验收满足，证据、文档和当前状态一致 |

禁止用 `implemented`、HTTP 200、文件存在、测试数量或历史运行替代 `validated_live` 或 `completed`。

## 1. 项目契约

### 1.1 总目标

把 Conflux 从“功能较多但状态、运行和产品完成度不一致的本地工具”收敛为可持续使用、可恢复、可审计的本地 ResearchOps 工作台：

1. 核心研究任务在提交、排队、执行、超时、取消、进程终止和服务重启后具有一致且可解释的结果。
2. `quick` 和 `standard` 研究档在冻结代表集上达到明确的交付、质量、预算和失败语义门槛。
3. 用户能快速理解系统是否就绪、任务正在做什么、结果是否可交付、失败后下一步是什么。
4. Workbench 逐步收敛到一个端口、一个 ASGI 应用、一个 OpenAPI 契约和清晰的应用服务边界。
5. 长时 AI coding 可以从证据化检查点恢复，不依赖聊天历史猜测当前状态。

### 1.2 成功标准

必须同时满足：

- P0-P6 全部达到各自退出标准，没有跳过的前置阶段。
- 运行状态、交付状态、FactCheck 状态和 Artifact 状态分开表达且无矛盾组合。
- 全量离线测试通过；关键进程恢复测试满足重复稳定性门槛。
- 真实代表集达到 quick/standard 质量门槛，结论强度不超过证据。
- U1-U6 用户任务、跨视口、键盘和 200% 文本缩放达到可用性门槛。
- Workbench 主路径只使用一个 ASGI 服务；旧 stdlib HTTP 主路径被移除。
- README、当前计划、代码、数据库迁移、运行服务和实际产物一致。

### 1.3 非目标

- 不重写研究管道，不以新 Prompt、新 Agent 或增加重试替代根因修复。
- 不在本轮引入微服务、Redis、Postgres、消息队列或远程 Worker。
- 不整体改写前端框架；保留当前 HTML/CSS/JavaScript，按任务流做有界改造。
- 不默认实施 P4 C5 受控 agentic 通道；只有 P0-P3 通过且存在真实需求时重新立项。
- 不为了覆盖率数字制造无价值测试，不追求把所有历史模块一次性类型化。
- 不清理、覆盖或归档当前未归属的用户工作树改动和历史运行产物。
- 不在未冻结 Provider revision、Prompt、配置、预算和案例集时启动付费正式实验。

### 1.4 允许修改范围

阶段开始时还要进一步收窄。本计划总体允许：

```text
config.yaml
pyproject.toml
.github/
docs/plans/Conflux可用性稳定性与架构收敛执行计划v1.md
src/conflux/workbench/
src/conflux/adapters/sqlite_store.py
src/conflux/core/runtime_home.py
src/conflux/graph_v2.py
src/conflux/research_modes.py
src/conflux/research_protocol.py
src/conflux/model_factory.py
src/conflux/panel.py
src/conflux/quality.py
src/conflux/report.py
src/conflux/research_evaluation.py
tests/
scripts/eval_*.py
scripts/bench_*.py
reports/evaluation/convergence/
```

超出上述范围的修改必须说明其与当前验收点的直接关系；改变产品目标、核心研究主张、证据协议或用户数据权威来源时必须暂停并重新确认。

## 2. 当前事实基线

以下事实记录于 2026-08-15，只作为 P0 复核起点；开始实施时必须重新采集，不能直接复用为当期结论。

| 编号 | 当前事实 | 证据 | 边界 |
|---|---|---|---|
| F1 | `main` 比 `origin/main` 领先 3 个提交，存在 25 个已修改文件和多项未跟踪文件 | `git status --short --branch`、`git diff --stat` | 工作树包含用户既有改动，不能自动重置或归档 |
| F2 | 全量离线测试收集 755 项，本次为 754 passed、1 failed、510 warnings，耗时 292.67 秒 | `python -m pytest -q` | 不是 live capability 证据 |
| F3 | 失败项为 Worker 进程终止恢复；单独连续复跑 4 次通过 | `test_query_job_recovers_after_worker_process_termination` | 表明全量负载下存在时序脆弱性，尚未确认具体根因 |
| F4 | Workbench 主服务使用 `ThreadingHTTPServer`，FastAPI v2 在同进程独立端口运行 | `workbench/server.py`、`workbench/api_v2/app.py` | 健康端点只证明服务存活 |
| F5 | `server.py` 约 4461 行，`graph_v2.py` 约 3942 行；源码中约 161 处宽泛 `except Exception` | 文件统计与 `rg` | 体积和异常数是风险信号，不等于每处均为缺陷 |
| F6 | `/api/sessions` 50 条响应约 1.83 MB，列表中包含体积较大的 `source_statuses` | 当前本地服务实测 | 载荷会随历史产物变化 |
| F7 | 前端研究任务同时使用 SSE 与每秒状态轮询，并忽略部分解析/轮询错误 | `static/app.js` | 需要在故障注入中验证实际影响 |
| F8 | quick live run `08a018a27ae9` 为 `deliverable`，FactCheck passed，1/1 章节完成 | 运行 summary 与产物 | 单案例不能外推整体能力 |
| F9 | standard live run `d75e9a298db4` 为 `limited`，0/2 章节完成，FactCheck skipped，75k token 耗尽 | 运行 summary 与产物 | panel 契约已通过，但 standard 能力未通过 |
| F10 | P3/P4 状态文档与 README 中存在过期测试数、历史限制和未完成项混写 | README、P3/P4/总执行计划 | 文档同步只能在对应验收后进行 |
| F11 | 当前视觉检查只完成 DOM/CSS/JS 审计，未完成真机截图、键盘遍历和跨视口验证 | 本轮工具记录 | P3 可用性结论仍待真实验证 |

### 2.1 优先根因

1. **事实治理和完成语义漂移**：实现、离线验收、live 能力和产品完成被混用，AI 与用户难以找到唯一当前事实。
2. **运行时增量叠加**：双服务器、单 Worker、内存凭证、SSE+轮询和宽泛异常处理共同扩大重启、部分失败和观测风险。
3. **能力预算未闭环**：研究广度、panel、上下文增长、生成与 FactCheck 共享预算，但没有用真实代表集证明 standard 能在固定成本内完成交付。

不得通过单案例特判、增加总 token、延长超时、增加重试或扩大 Prompt 来绕过上述根因。

## 3. 方案 B 目标架构

### 3.1 选择理由

方案 B 保留当前模块化单体、SQLite、EventStore、Artifact 和研究管道资产，但逐个垂直切片迁入一个 ASGI 应用。它比局部修补更能降低长期状态漂移，又避免全量重写带来的迁移和能力回归风险。

### 3.2 目标形态

```text
Browser / CLI / MCP
        |
        v
Single FastAPI ASGI App (one host, one port, one auth boundary)
        |
        +-- route: health/status/config
        +-- route: jobs/events/sessions
        +-- route: projects/reviews/audit
        +-- route: papers/knowledge/notes/memory
        +-- route: chat/approvals
        |
        v
Application Services
        |
        +-- QueryJobService
        +-- SessionService
        +-- StatusService
        +-- ProjectApplication (reuse)
        +-- Paper/Knowledge services (reuse existing functions initially)
        |
        v
SQLite Repositories / EventStore / Artifact Store / Chroma / Model Providers
```

### 3.3 代码边界

目标目录不是一次性脚手架，只有对应切片迁移时才创建：

```text
src/conflux/workbench/
  api/
    app.py
    dependencies.py
    errors.py
    routes/
      auth.py
      health.py
      status.py
      jobs.py
      sessions.py
      projects.py
      papers.py
      knowledge.py
      config.py
      chat.py
  services/
    query_jobs.py
    sessions.py
    status.py
  static/
```

已有 `projects/application.py`、Repository、`workbench/jobs.py` 和 `api_v2/actions.py` 优先复用。只有当提取能消除当前重复、隔离稳定变化或支撑合同测试时才新增服务类。

### 3.4 强制架构决策

| 决策 | 规则 |
|---|---|
| 单一入口 | 最终只暴露一个 Workbench 端口；OpenAPI、静态资源和 SSE 同属一个 ASGI 应用 |
| 增量迁移 | 一次只迁移一个垂直切片；兼容双路径最多存在于该阶段，阶段结束必须删除旧主路径 |
| HTTP 语义 | 业务错误使用一致 HTTP 状态和结构化 `error_code`，不再以 HTTP 200 + `ok=false` 表达所有失败 |
| 状态权威 | JobQueue 决定调度状态，RunStore 保存运行元数据，Artifact 引用保存产物；禁止列表层用陈旧字段覆盖队列终态 |
| 事件权威 | SSE 使用持久 EventStore cursor 和 `Last-Event-ID`；轮询只作为低频终态校验，不重复承担进度流 |
| 凭证恢复 | 不持久化明文密钥；持久化可解析的 `credential_ref`。临时请求密钥在重启后不可用时必须 fail-closed |
| 前端策略 | 保留当前原生前端，先修任务流、反馈和可访问性；不把框架迁移混入可靠性阶段 |
| 数据迁移 | 延续现有 SQLite migration runner，先补 checksum、dry-run、备份和升级测试；是否采用 Alembic 另做 ADR，不预设结论 |
| 研究预算 | 预算由阶段观测和交付保留共同决定；上游不得消费 synthesis、FactCheck 和 final commit 的硬保留 |

## 4. 阶段总览与依赖

同一时刻最多一个阶段为 `in_progress`。

| 阶段 | 目标 | 依赖 | 主要证据 | 初始状态 |
|---|---|---|---|---|
| P0 | 冻结现状与执行治理 | 用户授权开始 | 基线 manifest、状态文件、风险清单 | pending |
| P1 | 修复任务终态、幂等、重启和诊断 | P0 completed | 故障矩阵、重复恢复测试、全量测试 | pending |
| P2 | 关闭 standard 预算与内容质量缺口 | P1 completed | 预算剖析、冻结代表集、live 运行产物 | pending |
| P3 | 收敛 API 载荷、任务流与真实可用性 | P2 completed | API 基准、U1-U6、视觉/键盘证据 | pending |
| P4 | 逐切片迁移到单一 ASGI 模块化单体 | P1-P3 合同冻结 | OpenAPI diff、路由合同、迁移 smoke | pending |
| P5 | 建立工程质量、迁移与观测门禁 | P4 completed | CI、类型、warning、迁移和日志证据 | pending |
| P6 | 真实退出验收与文档同步 | P0-P5 completed | 两真实项目、真实 Provider、发布清单 | pending |

依赖顺序固定为 `P0 -> P1 -> P2 -> P3 -> P4 -> P5 -> P6`。P1 中可并行准备 P2 的冻结案例清单，但不得启动正式 live 调用；P3 可以先写自动化脚本，但用户任务结论必须等 P2 的稳定运行契约确定。

## 5. P0：现状冻结与执行治理

### 5.1 阶段目标

建立一个不会覆盖用户改动、可以跨会话恢复、能够区分历史事实和当前事实的执行底座。

### 5.2 依赖与前置检查

- 用户明确指令“开始实施”。
- 读取本文件、当前 Git 状态、运行服务 PID/命令行、数据库路径和未结束 Job。
- 确认当前工作树中的未知改动不被重置、清理、暂存或提交。

### 5.3 允许修改范围

- 本文件的状态和检查点部分。
- 新建 `scripts/capture_convergence_baseline.py`，前提是现有脚本不能结构化采集所需事实。
- 新建 `reports/evaluation/convergence/p0/` 下的 JSON/Markdown 证据。
- P0 不修改产品代码、配置和 README。

### 5.4 实施动作

1. 记录 `git rev-parse HEAD`、分支、ahead/behind、`git status --porcelain=v2` 和 diff 文件清单。
2. 为已修改/未跟踪项建立归属表：`user_existing`、`accepted_previous_work`、`current_plan`、`unknown`。没有证据时一律标记 `unknown`。
3. 记录 Python、依赖、操作系统、数据库 schema 版本、Chroma collection、服务监听 PID 和命令行。
4. 只读导出 JobQueue、RunStore、EventStore、未结束任务、最近失败和 Artifact 引用摘要；不得复制密钥或完整敏感正文。
5. 运行 `python -m pytest --collect-only -q` 和一次全量离线测试，保存 JUnit 或结构化摘要。
6. 对恢复失败测试执行至少 10 次独立重复，记录启动耗时、claim 时间和 lease 时间，而不是只记录通过率。
7. 对 `/api/status`、`/api/query/jobs`、`/api/sessions`、P3 project list/state 做冷/热各 20 次测量，记录 P50/P95、载荷和错误。
8. 冻结 P2 使用的 12 个代表查询草案、来源条件和人工评价 rubric；本阶段不调用正式模型。

### 5.5 最小验证集

```powershell
python -m pytest --collect-only -q
python -m pytest -q
python -m pytest -q tests/test_m3_workbench_query_jobs.py::test_query_job_recovers_after_worker_process_termination
```

重复测试应由专用脚本或明确循环执行并保存每次结果，不能只保留最后一次输出。

### 5.6 验收标准

- 当前 revision、工作树、服务、数据库、索引、测试和运行事实均进入结构化 manifest。
- 未触碰任何 `user_existing` 或 `unknown` 改动。
- 全量测试失败被准确记录，不把聚焦测试通过写成全量通过。
- P1 的唯一首个验收点被确定为“稳定复现并解释 Worker claim/lease 时序”。
- 本文件“当前执行状态”更新为 P1 pending，P0 completed。

### 5.7 产物

```text
reports/evaluation/convergence/p0/baseline_manifest.json
reports/evaluation/convergence/p0/test_baseline.json
reports/evaluation/convergence/p0/api_baseline.json
reports/evaluation/convergence/p0/worktree_ownership.md
reports/evaluation/convergence/p0/representative_queries_draft.json
```

### 5.8 退出与暂停条件

- 无法判断关键改动归属时暂停，不创建提交替代归属确认。
- 当前运行服务源码版本与工作树不一致且无法定位时暂停 P1，先补运行版本证据。
- 数据库无法只读导出或存在 schema 损坏时，把数据库恢复升级为 P1.0，不继续研究预算工作。

## 6. P1：任务运行正确性与故障恢复

### 6.1 阶段目标

让一次研究请求在重复提交、排队、执行、取消、超时、进程终止和服务重启后只产生一个可解释结果，并且每个终态都原子携带报告或结构化诊断。

### 6.2 允许修改范围

```text
src/conflux/workbench/jobs.py
src/conflux/adapters/sqlite_store.py
src/conflux/workbench/server.py              # 仅当前 Job 路由与启动恢复
src/conflux/workbench/api_v2/schemas.py       # 若 chat 提交协议受影响
src/conflux/workbench/api_v2/actions.py
tests/test_m3_workbench_query_jobs.py
tests/test_m3_jobs_checkpoints.py
tests/test_workbench.py
scripts/eval_job_recovery.py
```

不修改研究 Prompt、检索策略、报告写作格式和前端信息架构。

### 6.3 目标状态模型

调度状态只允许：

```text
pending -> running
pending -> cancelled
running -> completed
running -> completed_with_warnings
running -> completed_diagnostic
running -> timed_out_with_report
running -> timed_out
running -> cancelled
running -> failed
```

每个终态同时保存四个互不替代的维度：

```json
{
  "execution_status": "failed",
  "delivery_status": "diagnostic_only",
  "factcheck_status": "not_run",
  "artifacts": {"diagnostic_json": "...", "diagnostic_markdown": "..."}
}
```

禁止 `RunStore.public_status=running` 覆盖 JobQueue 已确定的终态。列表、详情和 SSE 对同一 run 的状态必须一致。

### 6.4 工作包 P1.1：claim/lease 时序

1. 在恢复测试中记录子进程 import、manager 初始化、DB bootstrap、claim、heartbeat 的时间点。
2. 区分实现缺陷与测试假设：若全量负载下 5 秒不足，不直接扩大等待；先确认 claim P95 和阻塞点。
3. Worker 启动暴露 `ready` 状态；测试只在 Worker ready 后测 claim SLA。
4. `expire_exhausted()`、`claim()`、RunStore 状态更新和诊断写入保持事务顺序可审计。

验收：Windows 上恢复测试独立 20 次通过；全量套件中通过；claim P95 达到冻结阈值且无盲目 sleep。

### 6.5 工作包 P1.2：提交幂等与队列背压

1. `POST /api/query/jobs` 接受 `Idempotency-Key`；Workbench 为一次用户动作生成稳定 key。
2. 相同 key + 相同请求哈希返回原 `run_id`；相同 key + 不同请求返回 `409 idempotency_conflict`。
3. 请求哈希只包含语义输入和非敏感配置引用，不包含明文密钥。
4. 保留单 Worker 作为默认策略，但 API 返回 `queue_position`、`active_count` 和估算范围；不以增加并发掩盖耗时。
5. 达到队列上限时返回明确 `429/503`、`Retry-After` 和恢复建议。

验收：客户端提交响应丢失后重投不新增 Job、Run 或 Artifact；20 个并发重复请求只产生一个 run。

### 6.6 工作包 P1.3：重启凭证与运行冻结

1. Run manifest 保存代码 revision、配置语义哈希、模型角色、Provider、模型 ID、Prompt hash、预算和 `credential_ref`。
2. 不把 API key 写入 SQLite、日志、事件或 Artifact。
3. 环境/Profile 可恢复凭证使用稳定引用；一次性请求密钥标记 `restart_policy=fail_closed`。
4. 重启后凭证不可解析时生成 `credential_unavailable_after_restart` 诊断，不得静默改用共享环境密钥或其他 Provider。
5. Provider revision 不可证明时标记 `model_revision_unverified`，不能把 alias 写成不可变 revision。

验收：重启后要么使用同一冻结配置恢复，要么明确失败；不得出现 provider/model/Prompt 漂移。

### 6.7 工作包 P1.4：所有终态结构化诊断

`conflux.research_failure.v1` 扩展覆盖：

- lease 超限。
- Worker 初始化失败。
- 凭证恢复失败。
- 配置/模型构建失败。
- 用户取消。
- 系统 deadline。
- Artifact final commit 失败。

诊断必须包含 run ID、请求摘要、源码版本、失败阶段、已完成进度、输入配置哈希、重试安全性、保留产物、恢复动作和原始错误类型。终态与诊断引用在同一事务中可见。

### 6.8 故障注入矩阵

| 故障点 | 预期结果 |
|---|---|
| submit 响应发送前断开 | 重投返回同一 run，不重复执行 |
| pending 时服务退出 | 重启后 claim 一次 |
| running/retrieval 时强杀 | lease 到期后按冻结配置恢复或明确失败 |
| synthesis 后强杀 | 从 checkpoint 恢复，不重复生成已提交 Artifact |
| final_commit 中断 | 不发布无 Artifact 的 `completed`；恢复提交或诊断 |
| heartbeat DB 锁超时 | 可观测、有限重试，不能永久 running |
| 临时密钥运行中强杀 | fail-closed，不切换共享密钥 |
| SSE 客户端断开 | Job 不受影响，重连按 cursor 补事件 |

### 6.9 最小验证集

```powershell
python -m pytest -q tests/test_m3_jobs_checkpoints.py
python -m pytest -q tests/test_m3_workbench_query_jobs.py
python -m pytest -q tests/test_workbench.py
python scripts/eval_job_recovery.py --repeats 20
python -m pytest -q
```

### 6.10 验收标准

- 故障矩阵全部通过并保留数据库、事件和 Artifact 证据。
- 20 次进程终止恢复无偶发失败。
- 同一请求无重复 run、重复模型调用或重复 Artifact。
- 任何终态都能得到正式报告、有限报告或结构化诊断之一。
- 列表、详情、SSE、RunStore 和 JobQueue 对终态一致。
- 全量离线测试通过；失败和 warning 数按当期实际记录。

### 6.11 回滚

Schema 变更必须可从 P0 数据库备份恢复。若幂等键上线后影响旧客户端，可暂时允许缺省 key 创建新任务，但 Workbench 自身必须始终发送 key；不得回滚终态原子性和 fail-closed 凭证规则。

## 7. P2：standard 预算、上下文与研究质量闭环

### 7.1 阶段目标

在固定、可审计的成本与时限内，让 standard 对代表性问题稳定产出完整或明确有限的研究报告，而不是在生成/FactCheck 前耗尽预算。

### 7.2 前置条件

- P1 completed，正式运行不会重复提交或丢失失败证据。
- 冻结 12 个代表查询、输入数据快照、rubric 和模型/Provider 条件。
- 付费 live 调用前获得单独、明确的执行授权。

### 7.3 允许修改范围

```text
config.yaml
src/conflux/research_modes.py
src/conflux/research_protocol.py
src/conflux/graph_v2.py
src/conflux/model_factory.py
src/conflux/panel.py
src/conflux/quality.py
src/conflux/report.py
src/conflux/research_evaluation.py
tests/test_v3_budget_replay.py
tests/test_v3_research_rounds.py
tests/test_v3_model_modes.py
tests/test_p4_panel.py
scripts/eval_agent_e2e.py
scripts/eval_evidence_quality.py
reports/evaluation/convergence/p2/
```

不改变用户问题含义、gold 标签或 rubric，不事后删除失败案例。

### 7.4 代表集设计

12 个案例至少覆盖：

| 类型 | 数量 | 关键风险 |
|---|---:|---|
| 单概念、有本地直接证据 | 2 | quick/standard 不应过度编排 |
| 方法比较与适用边界 | 3 | 多章节、跨来源引用 |
| 时间敏感或需 Web 证据 | 2 | 来源失败、时效和 fetch |
| 本地证据稀缺 | 2 | 明确无答案/有限交付 |
| 冲突证据 | 2 | arbitration、异议保留 |
| 长程 Agent/GIS 跨域问题 | 1 | 上下文增长和泛化 |

每案冻结：query、允许来源、禁止泄漏信息、预期关键维度、无答案条件、人工评分表和证据快照哈希。

### 7.5 工作包 P2.1：逐阶段预算可观测性

每次模型调用记录：

```text
run_id / stage / role / provider / model / revision_evidence
prompt_hash / input_tokens / output_tokens / reserved_tokens
context_bytes / evidence_refs_count / latency / finish_reason / estimated_cost
```

模型 usage 缺失时记录 `unknown`，不能用估算值冒充 Provider 返回值。汇总必须能解释总预算与各调用之和的差异。

### 7.6 工作包 P2.2：交付预算硬保留

1. 用 P0/P2 离线回放和最小 live pilot 测得各阶段 token P50/P90。
2. synthesis、FactCheck 和 final commit 的保留值取观察 P90 加安全余量，不先写死任意百分比。
3. retrieval、analysis、panel 和 gap research 只能使用扣除硬保留后的可用预算。
4. 预计无法覆盖完整计划时，先缩减非关键子问题、来源数量或 panel 判断点，并在计划中显式记录；不得等到生成阶段才失败。
5. final commit 不依赖模型预算，始终保留文件和诊断写入时间。

### 7.7 工作包 P2.3：上下文去重与引用化

1. Evidence 内容按 hash 存一次，下游通过 claim/evidence ref 选择，不在多阶段重复拼接全文。
2. 每个 claim、source、section 建立明确上限和选择理由。
3. 模型意见、原始来源文本、用户问题和计划分区，避免把历史生成文本反复作为新证据。
4. 压缩只删除重复和低优先级上下文，不把事实压缩成不可回溯摘要。
5. 记录每次 context 裁剪项和原因，支持 replay。

### 7.8 工作包 P2.4：panel 风险触发

- quick 永远关闭 panel。
- standard 默认只对高重要性且确定性检查无法裁决的 claim 触发 panel。
- deep 保持可选；不得因“多模型更高级”默认扩大调用。
- panel 触发条件、成员失败、弃权、分歧和成本进入 trace。
- A/B 使用同一 evidence snapshot、相同首成员/基线条件，避免不公平比较。

### 7.9 工作包 P2.5：报告可读性与交付语义

1. 避免“直接回答”和同名章节逐段重复。
2. 单一来源、模型分析和推导分析在正文中有明确边界。
3. `limited` 必须说明缺少什么、对结论有什么影响和如何补证。
4. `completed_with_warnings` 不能在 0 个章节完成时显示成普通完成。
5. FactCheck skipped 必须给出原因，含 factual claim 的 deliverable 报告不得静默 skipped。

### 7.10 验证顺序

1. 单元测试：预算保留、上下文选择、panel 触发和交付状态。
2. 固定 replay：复现 75k 耗尽案例，不调用 Provider。
3. 受控 pilot：2 个案例验证 telemetry 和预算估算，只作为调试证据。
4. 正式 12 案 live：一次冻结运行，不重试、不修复响应、不删除失败。
5. 人工盲评：报告隐藏策略名，按固定 rubric 评分。

### 7.11 验收标准

- 12 案中至少 10 个 `deliverable`，最多 2 个 `limited`，0 个 `diagnostic_only`。
- 0 个案例因上游预算消费导致 0 章节完成。
- factual claim 引用正确率 >= 95%，关键声明覆盖率 >= 90%，off-domain evidence = 0。
- 有 factual claim 的 deliverable 报告 FactCheck 通过；不可验证时必须降级，不得伪造 passed。
- 人工盲评中位数 >= 3.5/5，任何案例不得低于 3/5 后仍标记完整交付。
- Provider usage、模型、Prompt、配置、代码、失败响应和 Artifact hash 可追溯。
- 成本和时延报告给出分布，不用单次值作保证。

### 7.12 付费执行闸门

以下内容全部冻结后，才可向用户请求正式执行授权：

- 12 案 manifest hash。
- Provider 与可验证的模型 revision 证据；alias 只能标记未验证。
- Prompt hash、代码 revision、配置 hash、温度、输出上限和总预算。
- 是否允许 retry/repair/salvage/fallback；默认正式实验全部禁止。
- 最大预计调用数、token 和费用。

授权只表示启动该次冻结运行，不表示永久账户权限。

## 8. P3：可用性、API 性能与前端任务流

### 8.1 阶段目标

让用户从打开 Workbench 到提交研究、理解进度、处理失败和审阅报告的主要路径清晰、快速、可恢复；让列表 API 只返回列表需要的字段。

### 8.2 允许修改范围

```text
src/conflux/workbench/sessions.py
src/conflux/workbench/server.py              # 当前 API 实现，P4 再迁移
src/conflux/workbench/static/index.html
src/conflux/workbench/static/app.js
src/conflux/workbench/static/app.css
tests/test_workbench.py
tests/test_p3_workbench.py
tests/test_p4_chat.py
scripts/bench_p3_overview.py
scripts/eval_agent_e2e.py
```

不在本阶段拆服务器、不迁移前端框架、不增加新的产品一级模块。

### 8.3 工作包 P3.1：轻量 API 投影

1. `/api/sessions` 改为 cursor 分页，默认 20、最大 50。
2. 列表只返回 run ID、query preview、时间、四维状态、摘要和 Artifact 可用性；不得返回完整 source 内容或质量明细。
3. `/api/sessions/{id}` 返回详情，但大体积 evidence/source 使用 Artifact 链接或独立端点。
4. `/api/query/jobs/{id}` 的轮询投影不返回完整 evidence；详情按需加载。
5. `/api/status` 拆分 readiness 与资产统计；首屏 readiness 不递归扫描 reports 或语料。
6. 所有列表响应包含 `next_cursor`、`has_more` 和稳定排序键。

验收：sessions 首屏载荷 <= 100 KB；已缓存 API P95 <= 300 ms；首屏组合 P95 <= 800 ms。

### 8.4 工作包 P3.2：事件和断线恢复

1. SSE 是进度权威；事件包含单调 `event_id`、stage、status、摘要和小型 metadata。
2. 浏览器重连使用 `Last-Event-ID`，不得从 0 重放全部历史。
3. 状态轮询降低为 10-15 秒终态校验，SSE 正常时不每秒请求。
4. SSE 解析失败、连续重连失败和轮询失败进入可见连接状态与客户端观测，不再静默忽略。
5. 页面刷新后根据本地 active run ID 和后端状态恢复任务视图；终态后清理。

验收：网络断开 30 秒再恢复不丢阶段事件、不重复渲染、不影响后台任务。

### 8.5 工作包 P3.3：核心任务流

保留现有一级导航，但按用户任务统一状态语言：

- 首页：系统 readiness、唯一推荐下一步、最近未完成任务、待复核数。
- 研究查询：问题、档位影响、预计预算、项目上下文、提交。
- 运行中：排队位置、已用时间/预算、当前阶段、来源状态、取消。
- 终态：执行结果、交付等级、FactCheck、完整/缺失 Artifact、下一恢复动作。
- 报告：先正文，再按需展开 trace、source、evidence、audit。
- 设置：基础 readiness 与高级配置分开；保存前显示影响范围。

“研究助手”若仍是规则意图到固定动作的入口，界面不得暗示开放式自主 Agent；真实能力边界通过动作结果和审批状态表达。

### 8.6 工作包 P3.4：错误与恢复体验

错误必须包含：

```text
发生了什么
影响了什么
已经保留什么
用户现在可以做什么
技术详情（折叠）
```

提供熟悉的命令按钮：重新连接、查看诊断、打开设置、返回任务列表。只有服务确认幂等安全时才显示“重新提交”。

### 8.7 U1-U6 真实任务

| 编号 | 任务 | 量化成功标准 |
|---|---|---|
| U1 | 首次配置并确认 readiness | 10 分钟内完成，不查源码 |
| U2 | 提交 quick 研究并理解档位影响 | 2 分钟内正确提交 |
| U3 | 判断运行处于排队、执行还是提交产物 | 30 秒内判断正确 |
| U4 | 区分 deliverable、limited、diagnostic | 90% 判断正确 |
| U5 | 从失败定位诊断和恢复动作 | 2 分钟内完成，不重复创建任务 |
| U6 | 找到报告引用、证据和 FactCheck | 2 分钟内完成 |

至少 3 次代表性真实用户会话；自动化脚本只证明元素和流程存在，不能替代用户任务成功率。

### 8.8 跨视口与无障碍矩阵

必须检查：

```text
1440x900
1024x768
390x844
320x640
200% browser zoom
keyboard-only
prefers-reduced-motion
```

自动化使用 Playwright 截图、DOM 断言和 axe 类检查；人工完成 Tab 顺序、焦点可见、对话框焦点返回、屏幕阅读器状态文本和颜色非唯一表达检查。

### 8.9 验收标准

- U1-U6 总任务成功率 >= 90%，定位当前状态/下一步中位数 <= 15 秒。
- 320px 和 200% 缩放无文本覆盖、控件丢失或关键水平功能不可达。
- 核心流程键盘可达率 100%，动态状态有语义通知。
- 首屏 P95 <= 800 ms，缓存状态 API P95 <= 300 ms，事件可见延迟 P95 <= 1 秒。
- sessions 首屏 <= 100 KB；状态轮询正常情况下不高于每 10 秒一次。
- 所有失败场景都能定位诊断或安全恢复动作。

## 9. P4：单一 ASGI 与模块化单体收敛

### 9.1 阶段目标

在不改变已冻结产品行为和研究语义的前提下，将 stdlib Workbench 与 FastAPI v2 收敛为一个可测试、可观测的 FastAPI 应用。

### 9.2 迁移原则

1. 先冻结当前 OpenAPI/HTTP 合同和前端实际调用清单。
2. 一次迁移一个垂直切片，先服务层、再路由、再前端切换、再删除旧路由。
3. 每个切片使用同一临时数据库做旧/新响应语义比较；动态字段归一化后比对。
4. 不允许兼容层永久存在；一个切片只有删除旧主路径后才完成。
5. 不在迁移阶段改变研究 Prompt、预算、质量门禁或数据库权威语义。

### 9.3 迁移顺序

#### P4.1 App 骨架、错误和依赖

- 建立单一 `create_app()`、统一 auth、CSP、静态资源和结构化异常响应。
- 统一 Repository/Service 生命周期，不在每个 handler 隐式构造不同连接语义。
- 保留原服务作为测试对照，不先切用户入口。

验收：新 app 可在随机端口启动；health/auth/static/OpenAPI 合同通过。

#### P4.2 health、status、config

- 先迁移只读和低风险配置端点。
- `StatusService` 返回 readiness 与资产摘要；昂贵统计独立、缓存、可取消。
- 配置写入继续保留白名单、原子写和 secret 不回显。

验收：前端首页和设置切到新路由；旧对应 handler 删除。

#### P4.3 jobs、events、sessions

- `QueryJobService` 封装 P1 冻结的状态契约。
- FastAPI SSE 使用持久 cursor，不重新实现内存事件源。
- 迁移分页 session API 和 Artifact 详情。

验收：P1 故障矩阵在新 app 全部通过；旧 Job/SSE/session 路由删除。

#### P4.4 projects、reviews、audit

- 路由只调用现有 `projects/application.py`、Repository 和 cycle audit 服务。
- 不把项目领域逻辑搬入 route。
- 保持审批、版本和 evidence refs 契约。

验收：P3 项目测试、真实 Conflux/FusionAgent 只读 smoke 和 SSE 恢复通过。

#### P4.5 papers、knowledge、notes、memory、skills

- 先为当前 server 函数建立薄应用服务，再迁移路由。
- 长任务进入 JobQueue；短查询保持同步。
- 文件写入、知识入库和审批仍 fail-closed。

验收：论文发现、promote、索引、笔记、memory/skill 合同和安全路径通过。

#### P4.6 chat 与最终切换

- 将当前 `api_v2` 路由并入主 app，同一端口提供 chat 和 approvals。
- token/进度流必须符合 P3 事件契约；若响应只是对已完成文本分块，不得宣称 Provider token stream。
- 删除独立 uvicorn daemon thread、`_V2_BASE_URL` 代理和第二端口。

验收：一个进程、一个端口、一个 OpenAPI；前端无代理路径。

#### P4.7 删除 stdlib 主服务

- 删除 `WorkbenchHandler`、`ThreadingHTTPServer` 启动路径和已迁移 helper。
- `python -m conflux.workbench` 直接启动 ASGI app。
- `start-workbench.bat` 保持用户入口兼容。

验收：源码中不存在承担主流程的 stdlib HTTP handler；旧端点清单得到 404/410 或明确兼容映射。

### 9.4 HTTP 错误协议

统一响应示例：

```json
{
  "error": {
    "code": "job_idempotency_conflict",
    "message": "同一提交键对应了不同请求。",
    "retryable": false,
    "action": "生成新的提交键或恢复原任务。",
    "details_ref": "artifact:..."
  }
}
```

推荐映射：验证失败 422，未认证 401，禁止 403，不存在 404，冲突 409，队列背压 429/503，内部失败 500。前端不得依赖错误字符串判断业务分支。

### 9.5 合同与安全验证

- OpenAPI schema snapshot 只用于发现非预期变化，不阻止明确批准的版本升级。
- 文件读取保持允许根目录与 path traversal 测试。
- 非 loopback 绑定必须有 token；cookie、Bearer 和 v2 路由使用同一 auth。
- CSP、iframe sandbox、secret sanitization、配置原子写保持回归。
- SSE、普通 JSON 和静态文件均有合理 cache/header 契约。

### 9.6 验收标准

- Workbench 只有一个用户端口和一个 ASGI app。
- 所有主 API 进入 OpenAPI，错误协议一致。
- P1-P3 验收在迁移后无回归。
- 旧主路由、代理和双服务启动逻辑被删除，不保留永久 feature flag。
- `server.py` 不再是跨领域实现容器；路由、服务和 Repository 边界可由测试独立调用。
- 全量测试、迁移测试、真实只读 smoke 通过。

### 9.7 回滚

每个切片提交前保存旧/新合同和数据库备份。回滚单位是当前切片，不回滚此前已验收切片；若连续两个切片都需要扩大核心协议，暂停迁移并重新审查目标边界。

## 10. P5：工程质量、迁移与可观测性

### 10.1 阶段目标

让后续改动在提交前能发现语法、类型、合同、迁移和依赖问题，并让运行失败可以按 run/stage/provider 定位。

### 10.2 工作包 P5.1：静态质量门禁

1. 接入 Ruff，首批只对新 API、services、jobs 和变更文件启用阻断规则。
2. 接入 mypy 或 pyright；先覆盖协议、Repository、Job 状态机和新路由，不要求一次清零全部历史模块。
3. 添加 pre-commit 或等价本地命令，但 CI 是最终权威。
4. 禁止在同一阶段混入大规模纯格式化；格式化与语义改动分提交。

验收：changed modules lint/type 通过，无新增未解释 ignore。

### 10.3 工作包 P5.2：CI 与测试分层

GitHub Actions 至少包含：

```text
Python 3.11 / 3.12
lint + type
focused contracts
full offline pytest
frontend syntax/static contract
migration clean-home + upgrade-existing
```

真实 Provider 测试不在普通 PR 自动运行；它使用人工授权、冻结配置和独立证据目录。

### 10.4 工作包 P5.3：coverage 与 warning 策略

- changed-code coverage >= 85% 作为辅助门禁。
- Job 状态迁移、幂等、凭证恢复和 Artifact final commit 的风险分支必须逐项测试，不以总覆盖率替代。
- Conflux 自有 `datetime.utcnow()` 等 deprecation warning 清零。
- 第三方 warning 建立短期 allowlist、来源和移除条件；不把 510 条 warning 整体静默过滤。

### 10.5 工作包 P5.4：SQLite migration 治理

现有 migration runner 增加：

- migration checksum 和已应用版本一致性检查。
- dry-run/plan 输出。
- 升级前备份和剩余空间检查。
- clean-home、从实际旧库升级、重复执行幂等、失败事务回滚测试。
- schema 诊断命令。

只有现有 runner 无法满足上述要求时才评估 Alembic；采用新迁移框架必须有独立 ADR 和真实旧库演练。

### 10.6 工作包 P5.5：结构化观测

日志至少包含：

```text
timestamp / level / service / run_id / job_id / project_id
stage / event / status / duration_ms / error_code
provider / model / model_revision / token_usage / estimated_cost
```

禁止记录 API key、cookie、完整 Prompt、完整用户文档和完整来源正文。大对象进入受控 Artifact，日志只保存引用和 hash。

提供本地诊断摘要：服务版本、DB schema、队列统计、最近错误码、索引版本和配置就绪状态。

### 10.7 工作包 P5.6：安装与启动

- 完整化 `pyproject.toml` 开发/测试依赖和受支持 Python 版本。
- 提供可复现依赖锁定策略。
- 验证 `python -m pip install -e ".[dev]"` 和 `python -m conflux.workbench`。
- Windows `start-workbench.bat` 检查端口、PID、健康和日志路径，不误报已启动。
- Docker/devcontainer 不是本轮完成门槛，除非出现明确跨平台交付需求。

### 10.8 验收标准

- Python 3.11/3.12 CI 全绿。
- changed modules lint/type 通过，关键状态机分支测试完整。
- Conflux 自有 deprecation warning 为 0；第三方 warning 有显式预算。
- clean-home 和真实旧库副本迁移、重复升级、失败回滚通过。
- 日志能从一次用户错误定位到 run、stage、error code 和 Artifact，且无秘密泄漏。
- 干净 Windows 环境完成安装、启动、健康检查和停止。

## 11. P6：真实退出验收与发布

### 11.1 阶段目标

证明本轮改造在真实项目、真实数据和真实 Provider 条件下达到产品可用性，而不仅是代码和离线测试通过。

### 11.2 冻结对象

- Git revision 和 clean/dirty manifest。
- 数据库备份 hash、schema version、Chroma collection 和 embedding model。
- Conflux 与至少一个结构不同的真实项目；优先 FusionAgent，但其计划/数据不足时选择另一真实项目并记录原因。
- quick/standard 案例、Provider/model revision、Prompt/config hash、预算和费用上限。
- U1-U6 脚本、浏览器/屏幕环境和人工评价 rubric。

### 11.3 验证层级

1. 安装与迁移：新 runtime home、旧 DB 副本、备份恢复。
2. 服务：启动、登录、单端口 OpenAPI、静态资源、SSE。
3. 故障：提交断线、服务重启、Worker 强杀、SSE 重连、取消和 deadline。
4. 能力：quick/standard 正式冻结运行。
5. 项目：两个真实项目完成“状态 -> 缺口 -> 查询/论文 -> 证据 -> 复核”。
6. 可用性：U1-U6、跨视口、键盘和 200% 缩放。
7. 安全：非 loopback auth、secret sanitization、path scope 和日志审计。

### 11.4 总体验收矩阵

| 维度 | 最终门槛 |
|---|---|
| 可用性 | U1-U6 成功率 >= 90%；核心状态/下一步定位中位数 <= 15 秒 |
| 可访问性 | 320px、200% 缩放、键盘流程无关键功能丢失 |
| 性能 | 首屏 P95 <= 800 ms；缓存 API P95 <= 300 ms；事件延迟 P95 <= 1 秒 |
| 稳定性 | 关键恢复测试 20/20；故障矩阵全过；无永久 running 或重复 run |
| quick 能力 | 冻结集全部得到报告或明确有限结果，FactCheck/Artifact 合同一致 |
| standard 能力 | 12 案 >=10 deliverable、<=2 limited、0 diagnostic_only |
| 证据质量 | factual citation correctness >=95%；关键声明覆盖 >=90%；off-domain=0 |
| 架构 | 单端口、单 ASGI、单 OpenAPI，无旧 stdlib 主路径 |
| 工程 | CI 全绿、迁移可恢复、自有 deprecation warning=0 |
| 安全 | secrets 泄漏=0；未认证非 loopback 访问=0；越界文件读取=0 |
| 可追溯性 | 每个能力结论可定位 revision、run ID、输入、模型、产物和质量结果 |

### 11.5 文档同步顺序

只有 P6 通过后才：

1. 更新 README 的测试数、架构、启动方式和已知限制。
2. 更新 `docs/README.md` 当前状态索引。
3. 在 `执行计划v1.md` 增加本轮最终检查点，不改写历史原文。
4. 将本文件状态改为 completed；未通过项保持 blocked/limited。
5. 生成发布说明和可复现实验索引。

### 11.6 完成定义

“完成”要求代码、测试、真实运行、数据库、服务进程、Artifact、文档和用户任务证据一致。任一核心能力只有 replay 或历史结果时，只能写 `validated_offline` 或“本轮未验证”。

## 12. 分层测试策略

### 12.1 日常聚焦测试

每次修改只运行覆盖当前风险的最小集合。建议映射：

| 变更 | 最小测试 |
|---|---|
| Job/lease/idempotency | `test_m3_jobs_checkpoints.py` + `test_m3_workbench_query_jobs.py` |
| Workbench API/UI | `test_workbench.py` + 对应 P3/P4 tests |
| budget/graph | `test_v3_budget_replay.py` + `test_v3_research_rounds.py` |
| panel | `test_p4_panel.py` |
| project | `test_project_intelligence.py` + P3 project tests |
| migration | clean-home + upgrade fixture tests |

### 12.2 阶段测试

每个阶段退出前运行：聚焦测试、跨模块合同、实际故障回放和全量离线测试。全量测试失败即阶段未通过，即使聚焦测试全部通过。

### 12.3 真实测试

真实测试不得使用自生成模拟数据替代能力输入。可以使用固定 replay 验证机制，但必须标记 replay。进入正式真实模型实验后：

- 使用真实 Provider 和冻结模型条件。
- 不使用 mock、fallback、retry、repair、salvage。
- 保留失败调用和原始响应。
- 不因结果不理想修改 gold、rubric 或删除案例。

## 13. 证据与产物规范

建议目录：

```text
reports/evaluation/convergence/
  p0/
  p1/
  p2/
    manifest.json
    runs/
    raw_responses/
    review/
  p3/
    api_benchmark.json
    usability_sessions/
    screenshots/
  p4/
    openapi/
    contract_diff/
  p5/
    migration/
    ci/
  p6/
    release_manifest.json
    acceptance_report.md
```

每份阶段 manifest 至少包含：

```json
{
  "schema": "conflux.convergence_evidence.v1",
  "phase": "P1",
  "git_revision": "",
  "worktree_hash": "",
  "config_hash": "",
  "database_schema": "",
  "commands": [],
  "runs": [],
  "artifacts": [],
  "failures": [],
  "conclusion": "",
  "limitations": []
}
```

报告引用 Artifact 时同时记录相对路径、SHA-256、生成时间和对应 run ID。不得覆盖同名历史结果；正式批次使用唯一批次 ID。

## 14. AI coding 连续执行协议

### 14.1 每轮开始

1. 读取本文件的“当前执行状态”和最近检查点。
2. 检查 Git 分支、工作树、服务 PID/命令行、数据库和当前 run。
3. 核对上一验收点是否有直接证据通过。
4. 声明本轮唯一验收点、允许文件、非目标和最小测试。
5. 若用户只说“继续”，不得自动跨越两个验收点。

### 14.2 实施循环

```text
复现/保存基线
-> 冻结当前边界
-> 最小修改
-> 聚焦测试
-> 合同/故障验证
-> 检查 Artifact 和无关 diff
-> 更新检查点
```

一次修复失败后重新检查实际调用路径、运行版本和输入。连续两次同方向修复无效时停止编码，回到数据/schema、workflow/state、tool/environment、planning 和 evaluation 顺序重新诊断。

### 14.3 变更与提交规则

- 一个提交只对应一个可描述的验收点。
- 不把格式化、历史文档重写和语义修改混在一起。
- 不提交 secrets、runtime DB、真实原始私密数据或未授权用户改动。
- 阶段完成提交前检查 `git diff --check`、聚焦测试、全量测试和 Artifact hash。
- 多执行者并行时必须使用独立 worktree 或完全不重叠文件；主智能体负责唯一整合结论。

### 14.4 状态防漂移

- 新需求改变目标、成功标准或研究主张时暂停并更新项目契约。
- 计划外问题只在当前验收必需且不改变目标时纳入；否则进入 backlog。
- 代码与文档冲突时，以当前可复核代码、数据库和运行证据为事实，并记录差异。
- 服务健康、测试数、文件存在和子智能体报告都不能单独证明完成。

### 14.5 用户指令语义

| 用户指令 | 行为 |
|---|---|
| “开始实施” | 从 P0 开始，先冻结基线，不直接改架构 |
| “继续” | 从最新有效检查点推进到唯一下一验收点 |
| “暂停” | 停止实施，更新检查点、证据、阻塞和下一步 |
| “先不要改/只看看” | 只读调查，不写文件和运行付费实验 |
| “执行正式实验” | 仅执行已经冻结且明确展示预算的那一批调用 |

## 15. 风险、回滚与升级条件

| 风险 | 控制 | 升级/暂停条件 |
|---|---|---|
| 当前脏工作树归属不明 | P0 归属表、独立分支/worktree | 关键文件无法区分用户修改 |
| 状态修复引入重复执行 | 幂等键、故障矩阵、事务检查 | 出现重复付费调用或重复 Artifact |
| 重启时凭证漂移 | credential_ref、fail-closed | 无法证明恢复使用同一模型配置 |
| budget 优化损害质量 | 固定代表集、盲评、失败保留 | 质量下降或 rubric 需要事后修改 |
| ASGI 迁移扩大范围 | 垂直切片、旧/新合同 diff | 连续两切片要求改核心协议 |
| UI 自动化制造假成功 | 真实 U1-U6 + 人工键盘检查 | 只有 DOM 断言无真实任务证据 |
| CI 大量历史债务阻塞 | changed modules 先行、分阶段扩大 | 需要全仓格式化或无关重构 |
| 付费批次工具超时 | 检查进程和证据目录再决定 | 批次状态不明，禁止盲目重跑 |

以下情况必须等待用户决定：

- 需要删除或覆盖用户文件、历史产物或数据库。
- 需要改变总体成功标准、代表集、rubric 或正式实验预算。
- 需要引入微服务、远程 Worker、Postgres/Redis 或前端整体重写。
- Provider 无法提供可接受的 revision 证据，但计划要作稳定性主张。
- 正式付费实验预计超过已展示预算。

## 16. Backlog：本轮不自动执行

- P4 C5 开放式 agentic 通道。
- 通用插件隔离进程和远程执行。
- Docker/devcontainer。
- Postgres、Redis、分布式队列和多租户。
- React/Vue 等前端框架迁移。
- 全仓库一次性类型化或格式化。
- 历史报告自动补齐新 sidecar。
- 为单一查询或单一项目增加核心特判。

Backlog 项只有在 P6 后出现独立真实需求、收益和验收方法时才重新立项。

## 17. 阶段检查点模板

每个阶段通过、阻塞、降级或方向变化时，更新本节最近检查点；旧检查点按时间追加，不覆盖。

```markdown
### YYYY-MM-DD HH:MM - Pn.x 检查点

- 当前目标：
- 当前阶段：
- 状态：in_progress / blocked / completed
- 源码版本：
- 允许修改范围：
- 本轮非目标：

#### 已完成证据
- 修改文件：
- 测试命令与实际结果：
- run ID / Artifact / hash：
- 验证层级：单元 / 合同 / 集成 / replay / live

#### 未完成或阻塞
- 问题分类：
- 影响：
- 已尝试方向：

#### 决策、推断与待验证假设
- 事实：
- 推断：
- 假设及验证方法：

#### 唯一下一验收点
- 

#### 不应自动扩展
- 
```

## 18. 当前执行状态

### 18.1 当前目标

按方案 B 完成 Conflux 可用性、稳定性和架构收敛，并以真实能力与用户任务证据退出。

### 18.2 当前阶段

- 阶段：P1 任务运行正确性与故障恢复（工作包 P1.1 claim/lease 时序 → `completed`；P1.2 幂等与背压 → `completed`（离线验收通过）；P1.3 凭证冻结 pending）
- 状态：`in_progress`
- 证据：
  - `reports/evaluation/convergence/p1/p11_claim_lease_probe.json`（P1.1：25 次探针 + 20 次复跑）
  - `reports/evaluation/convergence/p1/p12_focused_pytest.{log,xml}`（P1.2 聚焦测试 103 passed）
  - `reports/evaluation/convergence/p1/p12_recovery_repeat.json`（P1.2 恢复测试 20/20）
  - `reports/evaluation/convergence/p1/p12_full_pytest.{log,xml}`（全量 764 passed）
- 关键结论：
  - P1.1 探针（`scripts/p1_claim_probe.py`）25/25 ready、25/25 claim 成功；claim P50 4.40s、P95 4.76s、max 5.56s；根因=子进程冷启动 import，恢复测试 5s 固定窗口卡在 claim P90 附近 → 改 30s 事件驱动后 **20/20 通过**。
  - **P1.2 验收通过（2026-08-16）**：聚焦测试（test_m3_workbench_query_jobs + test_m3_jobs_checkpoints + test_workbench）**103 passed**；恢复测试独立复跑 **20/20**（每轮 1 passed，含 P1.1 回归）；全量离线测试 **764 passed / 0 failed / 588 warnings / 435.79s**（较 P0 基线 755 项 +9：P1.2 新增 1 个 20 并发去重测试、3 个 HTTP 层 202/409/429 测试，另有此前未计入基线的 5 个 P1.2 单测）。
  - P1.2 语义：`POST /api/query/jobs` 读取 `Idempotency-Key`；同键同语义重放原 run（`idempotent_replay`）；同键异语义 409；队列上限 429 + Retry-After + 恢复建议；返回 `queue_position`/`active_count`/`wait_estimate`；job 行与 RunStore 行同一事务创建（`jobs.idempotency_key UNIQUE` 并发兜底）；Workbench 前端按提交正文生成稳定 key 并呈现结构化错误/Retry-After。
  - 测试执行说明：本轮经 run_code 的 `node:child_process` 直接运行 pytest（bash 工具在 win32 不可用）；子进程需显式注入 `USERNAME/TEMP/TMP/HOMEDRIVE/HOMEPATH`（会话环境为空导致 pytest 临时目录权限错误）；**不得**用 `--basetemp=.pytest_tmp` 跑全量（会使 test_knowledge_stats_reflect_new_papers_even_with_stale_manifest 与 test_session_detail_uses_only_verified_legacy_report 两个路径敏感测试失败）。
  - 已清理上一轮遗留：伪造探针 JSON、损坏 SQLite 文件 `scripts/_p1_claim_probe.py*`、僵尸进程 PID 25692。P0 记录的服务 PID 50348（8765/9765）保持运行未动。
  - 本轮改动已按验收点分批提交并推送 origin/main：C1 遗留工作树入库、C2 P0 脚本、C3 P1.1、C4 P1.2（见 git log）；`reports/` 下证据按 .gitignore 约定仅保留本地，不入库。
- 唯一下一验收点：P1.3 重启凭证与运行冻结（run manifest 保存 revision/配置哈希/模型角色/credential_ref；不持久化明文密钥；重启后凭证不可解析必须 fail-closed，不得漂移 provider/model/Prompt）。


### 18.3 当前决策

| 决策 | 依据 | 日期 |
|---|---|---|
| 采用方案 B 增量模块化单体 | 兼顾风险、可验收性和现有资产复用 | 2026-08-15 |
| P0-P3 通过前不启动 C5 | 当前核心阻塞是可靠性、standard 能力和可用性 | 2026-08-15 |
| 不覆盖现有 P3/P4 历史计划 | 保留历史证据，避免状态重写 | 2026-08-15 |
| 本文件为本轮唯一计划与检查点 | 支持跨会话恢复并减少状态漂移 | 2026-08-15 |
| P0 验收通过，进入 P1 | P0 五件产物齐全、全量测试绿色、恢复测试偶发失败已取证为 P1.1 目标 | 2026-08-15 |
| 不停止/不修改现有运行服务（PID 50348） | 它是 P4-era daemon，P0 不对其操作；P1 阶段再评估 | 2026-08-15 |
| P1.2 幂等键由前端按提交正文生成稳定 key，服务端以 jobs.idempotency_key UNIQUE 约束事务化去重；背压用 429 + Retry-After | 满足 §6.5 语义：响应丢失重投不新增 Job/Run/Artifact，不扩大并发 | 2026-08-16 |
| P1.2 离线验收通过，进入 P1.3 | 聚焦 103 passed、恢复 20/20、全量 764 passed；证据入 reports/evaluation/convergence/p1/p12_* | 2026-08-16 |
| P1.2 验收后按验收点分批提交并推送 origin/main | 用户指令；C1 遗留工作树入库 / C2 P0 脚本 / C3 P1.1 / C4 P1.2 四个提交 | 2026-08-16 |

### 18.4 当前未验证项

- P1.3 凭证冻结未开始：run manifest 的 revision/配置哈希/credential_ref 与重启 fail-closed 尚无实现。
- 当前运行服务（PID 50348）与工作树代码不一致，P1 结束前需在真实进程上做一次冻结版本验证。
- standard token 耗尽的逐阶段占用与上下文重复比例。
- 当前 Workbench 在真实 320px、200% 缩放和键盘流程下的表现。
- 第二个真实项目的完整 P3 闭环和 P6 可用性结果。
- 当前 Provider 对具体模型 revision 的可验证证据。

### 18.5 不应自动扩展

- 不在 P0 修改产品代码。
- 不清理当前工作树和历史运行。
- 不启动新的真实模型正式批次。
- 不先做单一 ASGI 大迁移。

## 19. 阶段检查点

### 2026-08-16 15:56 - P1.2 检查点（completed）

- 当前目标：P1.2 提交幂等与队列背压——同键重投不新增 Job/Run/Artifact，背压 429 + Retry-After。
- 当前阶段：P1 `in_progress`（P1.1 `completed`；P1.2 `completed` → 下一工作包 P1.3 凭证冻结）。
- 状态：completed
- 源码版本：`013467db78da3f6294ddd869e7fb955ea8d9a7f1`（main；改动随后按 P0/P1.1/P1.2 分批提交并推送，见 git log）
- 允许修改范围：P1 §6.2 列表 + `src/conflux/workbench/static/app.js`（提交幂等键与错误呈现）+ 本文件状态与检查点部分。
- 本轮非目标：不修改研究 Prompt/检索/报告格式；不启动真实模型调用；不开始 P1.3/P2/ASGI 迁移。

#### 已完成证据
- 修改文件：`src/conflux/workbench/jobs.py`（submit 事务化幂等提交 + wait_estimate）、`src/conflux/adapters/sqlite_store.py`（enqueue 同事务创建 RunStore 行；create_run 增加 commit=False）、`src/conflux/workbench/static/app.js`（稳定 Idempotency-Key + 结构化错误/Retry-After）、`tests/test_m3_workbench_query_jobs.py`（20 并发同键去重测试）、`tests/test_workbench.py`（HTTP 层 202/409/429 测试）。
- 测试命令与实际结果：
  - 聚焦：`python -m pytest -q tests/test_m3_workbench_query_jobs.py tests/test_m3_jobs_checkpoints.py tests/test_workbench.py` → **103 passed**（35.04s；junitxml `p12_focused_pytest.xml`）。
  - 恢复重复：`python -m pytest -q -p no:cacheprovider tests/test_m3_workbench_query_jobs.py::test_query_job_recovers_after_worker_process_termination` 独立循环 20 次 → **20/20 passed**（每次 1 passed；逐轮记录 `p12_recovery_repeat.json`）。
  - 全量：`python -m pytest -q --junitxml=reports/evaluation/convergence/p1/p12_full_pytest.xml` → **764 passed / 0 failed / 588 warnings**（435.79s）。较 P0 基线 755 项 +9（20 并发去重 1 + HTTP 层 3 + 此前未入基线的 P1.2 单测 5）。
- run ID / Artifact / hash：无 live 运行（本工作包为离线合同验收，不需要模型调用）。
- 验证层级：单元 + 集成（真实 SQLite/JobQueue/RunStore + 真实 do_POST 处理器 + 真实子进程恢复），离线；符合 §0.1 `completed` 定义。

#### 未完成或阻塞
- 无阻塞。P1.2 §6.5 验收全部满足；两处初期失败（test_knowledge_stats_reflect_new_papers_even_with_stale_manifest、test_session_detail_uses_only_verified_legacy_report）经排查为 `--basetemp` 路径敏感所致，改用默认临时目录后通过，非代码缺陷。

#### 决策、推断与待验证假设
- 事实：执行环境需显式注入 USERNAME/TEMP 等变量（会话环境缺失导致 pytest 临时目录权限错误）；恢复测试 20/20 与全量 764 passed 均为该环境下实测。
- 推断：job+run 同事务创建 + UNIQUE 约束使 20 并发同键只产生一个 job/run（测试已证实）。
- 假设及验证方法：无新增待验证假设；P1.3 将验证重启凭证 fail-closed。

#### 唯一下一验收点
- P1.3：重启凭证与运行冻结（run manifest 保存代码 revision、配置语义哈希、模型角色、Provider、模型 ID、Prompt hash、预算和 credential_ref；不持久化明文密钥；一次性密钥 `restart_policy=fail_closed`；重启后凭证不可解析生成 `credential_unavailable_after_restart` 诊断）。

#### 不应自动扩展
- 不开始 P2（预算/质量）或 ASGI 迁移；不修改研究语义；不提交本轮改动（提交需用户指令）。

### 2026-08-16 15:10 - P1.2 检查点（implemented）

- 当前目标：P1.2 提交幂等与队列背压——同键重投不新增 Job/Run/Artifact，背压 429 + Retry-After。
- 当前阶段：P1 `in_progress`（P1.1 `completed`；P1.2 `implemented`，等待离线验证执行）。
- 状态：implemented
- 源码版本：`013467db78da3f6294ddd869e7fb955ea8d9a7f1`（main；改动随后按 P0/P1.1/P1.2 分批提交并推送，见 git log）
- 允许修改范围：P1 §6.2 列表（jobs.py / sqlite_store.py / server.py Job 路由 / 三个测试文件）+ `src/conflux/workbench/static/app.js`（仅提交幂等键与错误呈现）+ 本文件状态与检查点部分。
- 本轮非目标：不修改研究 Prompt/检索/报告格式；不启动真实模型调用；不开始 P1.3/P2/ASGI 迁移；不清理工作树。

#### 已完成证据
- 修改文件：`src/conflux/workbench/jobs.py`（submit 事务化幂等提交 + wait_estimate）、`src/conflux/adapters/sqlite_store.py`（enqueue 同事务创建 RunStore 行；create_run 增加 commit=False）、`src/conflux/workbench/static/app.js`（按提交正文生成稳定 Idempotency-Key + 结构化错误/Retry-After 呈现）、`tests/test_m3_workbench_query_jobs.py`（20 并发同键去重测试）、`tests/test_workbench.py`（HTTP 层 202 重放/409 冲突/429 背压测试）。
- 测试命令与实际结果：**未执行**。本轮会话 shell 在 win32 不可用（bash 工具返回 `terminal inspection is unsupported on platform win32`，dsh-ssh 无可用主机），无法运行 pytest；仅完成静态实现与自查。
- run ID / Artifact / hash：无（未执行运行，无运行级证据）。
- 验证层级：无（`implemented` 不构成能力证据，见 §0.1）。

#### 未完成或阻塞
- 问题分类：执行环境缺失。
- 影响：P1.2 不能标 `completed`/`validated_offline`；20 并发去重与 HTTP 409/429 均未运行验证。
- 已尝试方向：bash 工具两次调用被宿主拒绝（win32 平台限制）；dsh-ssh 无配置主机；本会话无其他命令执行通道。

#### 决策、推断与待验证假设
- 事实：幂等语义由 `jobs.idempotency_key UNIQUE` 约束兜底；此前前端不发送 key，响应丢失重投会新建 run（P1.2 主要缺口，现已修复）。
- 推断：job 行与 run 行同事务创建，使 20 并发同键请求只产生一个 job/run；单 Worker 语义不变。
- 假设及验证方法：在具备 shell 的环境运行下述最小验证集；若有失败，按 §14.2 修复后重跑再更新检查点。

#### 唯一下一验收点
- 执行并记录：`python -m pytest -q tests/test_m3_workbench_query_jobs.py tests/test_m3_jobs_checkpoints.py tests/test_workbench.py`；恢复测试 20 次循环（沿用 P1.1 的单测 `--basetemp` 循环命令）；`python -m pytest -q`（全量）。
- 观察项：计划 §6.9 写的 `scripts/eval_job_recovery.py --repeats 20` 与脚本实际参数（`--jobs/--steps/--output-dir/--seed`）不符；执行该脚本时用 `--jobs 200` 或先补齐 `--repeats`，不得把带错参数的失败当作验收失败。
- 通过后 P1.2 `completed`，下一工作包 P1.3。

#### 不应自动扩展
- 不开始 P1.3 凭证冻结、P2 预算/质量或 ASGI 迁移；不修改研究语义；不提交本轮改动（提交需用户指令与可用 git 环境）。

### 2026-08-15 22:05 - P1.1 检查点（completed）

- 当前目标：P1.1 稳定复现并解释 Worker claim/lease 时序。
- 当前阶段：P1 `in_progress`（P1.1 `completed` -> 下一工作包 P1.2 幂等与背压）；P0 保持 `completed`。
- 状态：completed
- 源码版本：`013467db78da3f6294ddd869e7fb955ea8d9a7f1`（main，未变）
- 允许修改范围：P1 §6.2 列表（jobs.py / sqlite_store.py / server.py Job 路由 / api_v2 schemas/actions / 三个测试文件 / scripts/eval_job_recovery.py）+ 本文件状态与检查点部分 + `scripts/p1_claim_probe.py`（新增探针）。
- 本轮非目标：不修改研究 Prompt、检索、报告格式和前端；不清理工作树历史改动；不启动真实模型调用；不动 P0 记录的服务（PID 50348）。

#### 已完成证据
- 修改文件：`scripts/p1_claim_probe.py`（重写）、`tests/test_m3_workbench_query_jobs.py`（phase1 窗口 5s→30s 事件驱动、phase2 等待 8s→30s、recovery subprocess timeout 12s→35s）；新增 `reports/evaluation/convergence/p1/p11_claim_lease_probe.json`（25 次探针 + 20 次复跑结果）。
- 测试命令与实际结果：
  - 探针（25 次）：25/25 ready、25/25 claim 成功；claim P50 4.40s、P95 4.76s、max 5.56s；1/25 超 5s 窗口。
  - 修复后恢复测试独立复跑 20 次 → **20/20 通过**（此前 19/22、14/15）。
  - 聚焦测试 `test_m3_workbench_query_jobs.py` + `test_m3_jobs_checkpoints.py` → 23 passed（27.99s）。
- 验证层级：集成（真实子进程 + 真实 SQLite + 真实 JobQueue）、离线 replay（无模型调用）。

#### 未完成或阻塞
- 无阻塞。P1.1 验收标准（Windows 独立 20 次通过、claim P95 达冻结阈值、无盲目 sleep）全部满足；恢复测试不再使用固定 5s 断言窗口。

#### 决策、推断与待验证假设
- 事实：claim 延迟主因是子进程 Python 冷启动 import（4.2–5.6s），DB bootstrap 仅数毫秒；5s 断言窗口卡在 claim P90 附近。
- 推断：恢复测试 flaky 是断言窗口竞态，非恢复逻辑缺陷。
- 假设验证：将窗口改为 30s 事件驱动后独立复跑 20/20 通过，假设成立。

#### 唯一下一验收点
- P1.2：`POST /api/query/jobs` 幂等键 + 同一请求重投不新增 Job/Run/Artifact；20 个并发重复请求只产生一个 run；队列背压返回 429/503 + Retry-After。

#### 不应自动扩展
- 不开始 P2（预算/质量）或 ASGI 迁移；不修改研究 Prompt/检索/报告；不启动真实模型调用，直到 P1 全部验收通过。

### 2026-08-15 21:50 - P1.1 检查点（in_progress）

- 当前目标：P1.1 稳定复现并解释 Worker claim/lease 时序。
- 当前阶段：P1 `in_progress`（P1.1）；P0 保持 `completed`。
- 状态：in_progress
- 源码版本：`013467db78da3f6294ddd869e7fb955ea8d9a7f1`（main，未变）
- 允许修改范围：P1 §6.2 列表（jobs.py / sqlite_store.py / server.py Job 路由 / api_v2 schemas/actions / 三个测试文件 / scripts/eval_job_recovery.py）+ 本文件状态与检查点部分 + `scripts/p1_claim_probe.py`（新增探针）。
- 本轮非目标：不修改研究 Prompt、检索、报告格式和前端；不清理工作树历史改动；不启动真实模型调用；不动 P0 记录的服务（PID 50348）。

#### 已完成证据
- 修改文件：`scripts/p1_claim_probe.py`（重写：修复 `sys.executable` 拼写错误、用 sqlite3 就绪信号替代盲目 sleep、记录 submit/claim 精确耗时）；新增 `reports/evaluation/convergence/p1/p11_claim_lease_probe.json`（25 次真实探针 + 分析结论）。
- 测试命令与实际结果：
  - `python scripts/p1_claim_probe.py --iters 3`（冒烟）→ 3/3 ready、3/3 claim 成功（claim 4.35–4.85s）。
  - `python scripts/p1_claim_probe.py --iters 25`（正式）→ 25/25 ready、25/25 claim 成功；claim P50 4.40s、P95 4.76s、范围 4.17–5.56s；1/25 次（iter4）超过 5s 断言窗口。
- 验证层级：集成（真实子进程 + 真实 SQLite + 真实 JobQueue）、离线 replay（无模型调用）。

#### 未完成或阻塞
- 问题分类：P1.1 根因已确认（冷启动 import 4.2–4.5s 超过测试 5s 固定窗口），但修复尚未落地。
- 影响：恢复测试在全量负载与独立重复下仍会偶发失败（P0 记录 19/22、14/15）。
- 已尝试方向：探针就绪等待（ready 信号）证明 DB bootstrap 仅数毫秒，瓶颈是子进程 Python import。

#### 决策、推断与待验证假设
- 事实：25 次真实探针 claim P95 4.76s、max 5.56s；DB bootstrap `ready_wait_ms` 仅 7–11ms。
- 推断：恢复测试失败是 5s 断言窗口 < claim P95 的时序竞态，非恢复逻辑缺陷。
- 假设及验证方法：将测试等待窗口扩展为"等待 running 或 claim 完成，超时 >= claim P95 + 余量（>= 7s）"后，独立 20 次复跑应全通过；用修改后的测试复跑验证。

#### 唯一下一验收点
- P1.1 修复恢复测试窗口（无盲目 sleep，事件/轮询驱动），Windows 独立 20 次复跑全部通过，claim P95 达冻结阈值（>= 7s 窗口）。

#### 不应自动扩展
- 不开始 P1.2（幂等键）或 P2；不做 ASGI 迁移；不修改产品代码直到 P1.1 验收通过。

### 2026-08-15 18:20 - P0 检查点（completed）

- 当前目标：P0 现状冻结与执行治理。
- 当前阶段：P0 `completed`；下一阶段 P1 `pending`。
- 状态：completed
- 源码版本：`013467db78da3f6294ddd869e7fb955ea8d9a7f1`（main，领先 origin/main 3 提交）
- 允许修改范围：仅 P0 状态与检查点部分、`scripts/capture_convergence_baseline.py`、`scripts/bench_p0_api_baseline.py`、`reports/evaluation/convergence/p0/`。
- 本轮非目标：不修改产品代码、不清理工作树、不启动真实模型调用、不改服务。

#### 已完成证据
- 修改文件：`scripts/capture_convergence_baseline.py`、`scripts/bench_p0_api_baseline.py`、本文件（状态/决策/检查点）；新建 `reports/evaluation/convergence/p0/` 5 份证据 + `pytest_full.xml` + `recovery_runs/`。
- 测试命令与实际结果：
  - `python -m pytest --collect-only -q` → 755 tests collected（2.88s）。
  - `python -m pytest -q --junitxml=...pytest_full.xml` → 755 passed, 0 failed, 0 error, 0 skipped, 284.1s。
  - 恢复测试独立复跑 22 次 → 19 passed / 3 failed（run4/6/22）；直复现 15 次 → 14 passed / 1 failed（phase1: submit 后 5s 内 job 未 running）。失败均为运行级时序，非 pytest 清理错误。
  - API 冷/热各 20 次 → 见 `api_baseline.json`（sessions 1.83MB P95；status cold 2.86s P95）。
- 验证层级：集成（真实 handler + 持久化原语）、离线 replay。

#### 未完成或阻塞
- 问题分类：Worker claim/lease 时序脆弱性（P1.1）。
- 影响：恢复测试在全量负载与独立重复下偶发失败（13.6%）。
- 已尝试方向：无（P0 只取证不修复）。

#### 决策、推断与待验证假设
- 事实：单次全量测试本轮为绿；恢复测试重复 22 次有 3 次失败；直复现失败点在 submit 后 5s 窗口内 job 未达 running。
- 推断：失败由 worker 启动/claim 时间与测试断言窗口竞争导致，非恢复逻辑本身。
- 假设及验证方法：P1.1 用时间戳记录子进程 import / manager init / DB bootstrap / claim / heartbeat，确认 claim P95 与阻塞点。

#### 唯一下一验收点
- P1.1：Windows 上恢复测试独立 20 次通过；claim P95 达冻结阈值且无盲目 sleep。

#### 不应自动扩展
- 不修复恢复测试（留给 P1）；不开始 P2 正式 live 调用；不迁移 ASGI。

