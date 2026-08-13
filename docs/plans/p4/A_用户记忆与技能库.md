# A 用户记忆与技能库设计

> 文档状态：设计完成，待实施确认
>
> 优先级：P0（第 1 批，与 B 并行）→ 建议映射 P4.0
>
> 版本：1.0
>
> 日期：2026-08-13
>
> 上位：[../P4智能体能力与工程化扩展计划.md](../P4智能体能力与工程化扩展计划.md)

## 0. 目标

三层跨会话个性化：

1. **用户记忆**：事实/偏好/反馈/引用的结构化条目，Codex 式做法——每条一个事实、一句话描述用于召回、索引每会话加载、只注入相关子集。
2. **技能库**：把反复出现的多步操作沉淀为声明式技能（程序性记忆），与 M1 插件协议衔接。
3. **生命周期管理**：superseded 链、确认门、容量上限，防止记忆膨胀和污染。

## 1. 现状与复用

| 已有基建 | 复用方式 |
|---|---|
| P3 快照 + 周期审计 + 已确认周期摘要（`projects/cycle_audit.py`） | 项目级记忆已存在，本项补**跨项目的用户级**记忆 |
| EventStore 事件流 + 采集器模式（`projects/collectors.py`） | 记忆采集器直接复用 |
| `config_store.py` | 全局配置持久化入口 |
| 系统提示词组装点（graph_v2 `status_bar` 前缀、`prompts.py load_system_prompt`） | 记忆注入点 |
| M1 插件协议 + YAML 工作流（`core/workflow_compiler.py`） | 技能库编译目标 |
| `sanitize.py` | 注入前清洗 |

## 2. 数据模型

`user_memory` 表（SQLite migration `0009_user_memory`）：

| 字段 | 说明 |
|---|---|
| `id` | 主键 |
| `kind` | `fact` / `preference` / `feedback` / `reference` / `skill_ref` |
| `content` | JSON，结构化，禁止大段自由文本 |
| `description` | 一句话召回描述（≤120 字，用于相关度排序） |
| `source_event_id` / `source_run_id` | 可空；记忆必须可回源 |
| `project_id` | 可空；全局记忆或项目绑定 |
| `status` | `active` / `superseded` / `rejected` |
| `supersedes_id` | 可空；去重链 |
| `confidence` | 0–1 |
| `created_at` / `updated_at` | 时间戳 |

去重规则：同 `kind` + `description` 相似度 ≥ 阈值 → 新条目 `supersedes` 旧条目，旧条目置 `superseded`。

## 3. 写入采集器（`memory_collector`，确定性触发）

| 触发事件 | 记忆类型 | 是否需要确认 |
|---|---|---|
| 报告反馈/结论纠正 | `feedback`（"结论 X 被用户修正为 Y"） | 直接入 active |
| 雷达决策覆写（推翻 accept/reject） | `preference`（"该方向不要/要"） | 直接入 active |
| 周期审计 confirm | 项目级 `fact`（"本周期验收标准达成"） | 直接入 active |
| 对话纠正（C 之后，"以后都……"句式） | `preference` 提案 | 入 pending，用户确认后 active |
| 高频术语/命名习惯（统计触发） | `preference` | 入 pending |

规则：

- 采集走确认门：低置信偏好先入 pending 队列，用户确认后 active。
- 不上传、不自动写入未经确认的内容。
- 每条记忆带 `source_event_id`，可追溯到事件流。

## 4. 技能库（程序性记忆）

`skills/*.yaml` 声明式技能：

```yaml
name: read_paper_notes
description: 把一篇 PDF 读成结构化文献笔记 # 触发召回用
when:                                    # 触发条件
  intent: ingest_pdf
  tags: [paper]
steps:                                   # 工具调用序列
  - tool: parse_pdf
  - tool: structure_notes
tools: [parse_pdf, structure_notes]      # 白名单
gates:                                   # 门禁
  - after: structure_notes
    check: every_note_has_citation
output:
  contract: literature_note
```

- 与 M1 插件协议的关系：**技能 = 用户级声明式工作流**，编译进 `core/workflow_compiler` 复用 executor；插件 = 代码级能力。
- 内置种子技能 3 个：读论文笔记、周报草稿、实验可复现性检查。
- **学习闭环**：同类纠正模式出现 3 次 → 提案技能草稿 → 用户确认 → 入库。学习过程全程提案制，不自动生效。

## 5. 注入设计（最小化、安全、可追溯）

- 注入点：系统提示词稳定前缀（复用 `status_bar` 位置，最小化 KV-cache 前缀损伤）。
- 注入规则：
  - 每次最多 **5 条**，按 `description` 与当前任务相关性排序；
  - 仅注入 `kind ∈ {preference, feedback, reference}` 中标记为"风格/术语"的条目，**`fact` 类绝不注入**（事实走 RAG 证据链）；
  - 注入前过 `sanitize.py` 清洗；
  - 注入文本总量 ≤ **300 token**。
- 注入时在提示词中明示："以下是用户偏好参考，证据结论优先"——记忆不得覆盖证据裁决。

## 6. API 与界面

- `GET /api/v1/memory`（列表，含 pending）/ `POST /api/v1/memory`（新增）
- `POST /api/v1/memory/{id}/confirm | reject`（pending 队列确认）
- `GET /api/v1/skills` / `POST /api/v1/skills`（技能管理）
- 工作台设置页增加"记忆"分组（复用 P3 设置分组对话框）

## 7. 验收（A1–A5）

| 编号 | 验收项 | 通过标准 |
|---|---|---|
| A1 | 召回质量 | 构造 20 条记忆 × 10 场景，相关性 top5 命中率 ≥ 80% |
| A2 | 注入零损伤 | 前缀 ≤300 token；quick 档 KV 前缀总量不超预算 5% |
| A3 | 注入安全 | 构造注入攻击记忆，验证不改变证据裁决（回归测试） |
| A4 | 可追溯 | 每条记忆可回源 `source_event_id` |
| A5 | 通用性 | fusionagent001 用同一 schema 登记记忆（由用户补计划测试） |

## 8. 风险与取舍

| 风险 | 对策 |
|---|---|
| 记忆膨胀 | superseded 链 + 容量上限（默认 500 条）+ 定期清理 |
| 注入污染证据链 | kind 白名单 + sanitize + fact 禁入 |
| 采集噪音 | 确认门 + 低置信度阈值 |
| 不做 | 自动生成"用户画像"长文（保持条目化）；跨会话原始对话回放（成本不可控） |
