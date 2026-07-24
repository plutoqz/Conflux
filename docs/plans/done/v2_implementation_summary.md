# V2 实施完成摘要

> 日期：2026-07-22

## 已完成的交付物

| 文件 | 用途 |
|------|------|
| `docs/plans/research_query_redesign.md` | 重构方案文档（含审阅修正） |
| `docs/plans/p15_baseline_snapshot.md` | P1.5 基线快照 |
| `src/conflux/graph_v2.py` | V2 answer_first 管道（6步） + 旧 multi-agent graph re-export |
| `src/conflux/evaluation_v2.py` | V2 评测框架（支持 A/B 对比） |
| `src/conflux/_graph_v2_legacy.py` | 旧 multi-agent graph 保留（git 历史恢复） |
| `src/conflux/__main__.py` | 新增 `answer_first` 管道路由 |

## V2 管道架构

```
decompose → retrieve → generate → synthesize → audit → finalize
  拆解       检索      并发分节    全局综合   后置审计    组装报告
```

**关键参数**：
- 最大并发章节数：3
- 每节目标长度：2000 字
- 可信度判定：external_evidence_coverage ≥50%→high, ≥20%→medium, 否则 low
- 功能开关：`research.pipeline: answer_first`（config.yaml）

## 如何运行

### 切换到 V2 管道

编辑 `config.yaml`：
```yaml
research:
  pipeline: answer_first  # 从 p15 切换
```

### 运行查询

```bash
python -m conflux research "GIS处理自动化研究目前有哪些瓶颈？" --depth standard --output-dir reports/v2
```

### A/B 对比评测

```bash
# 1. 先运行 P1.5 基线（已存在）
# 2. 运行 V2
# 3. 生成对比报告
python -m conflux.evaluation_v2 \
  --baseline reports/evaluation/minimal-representative-batch.json \
  --summary gis-limitations=reports/v2/<run_id>.summary.json \
  --output reports/evaluation/v2_batch.json
```

## 与 P1.5 的关键差异

| 方面 | P1.5 (基线) | V2 (新) |
|------|------------|---------|
| 管道步骤 | dispatch→planning→fanout→coverage循环→synthesis→verify→factcheck  | decompose→retrieve→generate→synthesize→audit→finalize |
| 维度来源 | Planner (25s, 常超时→通用模板) | LLM拆解(20s, 失败时原问题做唯一子问题) |
| 章节写作 | 批量1次调用, max 3200 tokens | 每节1次调用, 并发最多3, 每节约2000 tokens |
| 预算重点 | 分析约75%, 写作约23%时间/5%输出能力 | 写作约50%时间/输出能力 |
| 引用控制 | grounding逐句检查→拒绝正文 | 结构化摘要自主标注+后置审计 |
| 交付判定 | deliverable/limited/diagnostic_only 三态 | run_status/report_available/confidence 三正交字段 |
| 截断行为 | 硬截断 + "受运行预算限制" 免责声明 | 软限制 + finish_reason 检查 |
| 可信度 | 逐句置信度表格 + 硬门禁 | 确定性指标 → LLM自然语言化 |

## 待完成

以下项目由 [research_query_redesign.md](../research_query_redesign.md) 的 H-K 阶段统一定义和跟踪，本摘要不重复维护状态：

| 阶段 | 内容 | 跟踪位置 |
|------|------|---------|
| H | V2真实API A/B对比评测 | [research_query_redesign.md](../research_query_redesign.md) §H |
| I | 根据盲评结果调整prompt/参数 | [research_query_redesign.md](../research_query_redesign.md) §I |
| J | 硬编码清理 | [research_query_redesign.md](../research_query_redesign.md) §J |
| K | 清理到期废弃代码 | [research_query_redesign.md](../research_query_redesign.md) §K |
