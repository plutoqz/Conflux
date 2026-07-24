# P1.5 基线快照

> 日期：2026-07-22
>
> 用途：V2 方案 A/B 对比评测的对照组。记录当前 P1.5 管线（`research.pipeline=p15`）在代表性查询集上的表现。
>
> 数据来源：`reports/evaluation/minimal-representative-batch.json`（3 个已执行的 WP7 代表性案例）及 `reports/workbench/query/` 中的报告产物。

## 1. 环境

| 配置项 | 值 |
|--------|-----|
| `research.pipeline` | `p15` |
| `research.depth` | `standard` |
| `research.generalization.enabled` | `true` |
| 模型 | MiniMax-M3 (openai_compatible) |
| 超时 | 240s |
| Token 预算 | 75000 |

## 2. 代表性查询集（12 题）

所有查询定义来自 `evaluation/generalized_research_representative_set.json`。当前仅有 3 个案例有实际运行记录。

| # | case_id | 查询 | 领域 | 类别 | 已运行 |
|---|---------|------|------|------|:---:|
| 1 | `gis-limitations` | GIS处理自动化研究目前有哪些瓶颈？ | GIS/GeoAI | broad_review_or_limitations | ✅ |
| 2 | `software-agent-limitations` | 当前自主编码智能体进入生产软件工程的主要瓶颈是什么？ | software_engineering | broad_review_or_limitations | ✅ |
| 3 | `policy-ai-governance` | 高影响公共决策中的生成式AI治理目前存在哪些主要制度与实施缺口？ | policy_governance | broad_review_or_limitations | ❌ |
| 4 | `gis-architecture-design` | 如何设计一个可审计、可恢复的LLM驱动GIS自动化架构？ | GIS/GeoAI | technical_comparison_or_design | ❌ |
| 5 | `materials-method-comparison` | 材料发现中图神经网络与等变神经网络的证据、适用边界和计算取舍有何差异？ | materials_energy | technical_comparison_or_design | ❌ |
| 6 | `data-lakehouse-comparison` | 湖仓一体、数据网格与传统数据仓库在治理和实时分析上的机制与取舍是什么？ | data_systems | technical_comparison_or_design | ❌ |
| 7 | `clinical-ai-causality` | 临床决策支持中的自动化偏差通过哪些机制影响医生判断，现有证据强度如何？ | medicine_life_science | causal_mechanism_or_evidence_review | ❌ |
| 8 | `battery-degradation-causality` | 快充通过哪些机制加速锂离子电池退化，不同实验条件下的证据是否一致？ | materials_energy | causal_mechanism_or_evidence_review | ❌ |
| 9 | `recent-geoai-agents` | 截至2026年，GeoAI智能体在真实地理处理任务上的验证进展和未决问题是什么？ | GIS/GeoAI | recent_status | ❌ |
| 10 | `recent-clinical-agents` | 截至2026年，临床LLM智能体的前瞻性验证与监管状态如何？ | medicine_life_science | recent_status | ❌ |
| 11 | `empty-rag-policy` | 当前主要司法辖区对基础模型透明度义务有哪些可核验差异？ | policy_governance | rag_empty_web_available | ✅ |
| 12 | `empty-rag-security` | 当前软件供应链签名与构建溯源标准的实施差异和剩余缺口是什么？ | software_engineering | rag_empty_web_available | ❌ |

## 3. 已运行案例的基线指标

### 3.1 `gis-limitations` — GIS处理自动化研究目前有哪些瓶颈？

| 指标 | 值 |
|------|-----|
| run_id | `245f93f1726c` |
| 耗时 | 144.2s |
| 实际 tokens | 31,515 / 75,000 |
| Planner | **超时**（failed: 1） |
| Analyst | 被预算拒绝（rejected: 2） |
| Section Synthesizer | 1 次调用，4424 tokens |
| Verifier | 1 次调用，7495 tokens |
| Reranker | 9 次调用，19596 tokens |
| **交付状态** | **diagnostic_only** |
| factcheck | needs_review |
| high_importance_coverage | 0.0 |
| gate_eligible_external_evidence | 4 |
| 核心维度 evidence_scarce | 3/4 |
| citation_coverage | 0.2 |

**报告特征**：4 个通用模板维度（范围与成熟度边界、机制与方法限制、实施与运行约束、评估/风险与开放问题）。每节有少量引用文本但无深度分析。第 4 节"评估、风险与开放问题"无任何外部证据。跨维度综合仅为"这些维度不是彼此独立的清单"。

### 3.2 `software-agent-limitations` — 当前自主编码智能体进入生产软件工程的主要瓶颈是什么？

| 指标 | 值 |
|------|-----|
| run_id | `5437e8ae556e` |
| 耗时 | 159.0s |
| 实际 tokens | 28,016 / 75,000 |
| Planner | **超时**（failed: 1） |
| Analyst | 被预算拒绝（rejected: 1） |
| Section Synthesizer | **超时**（failed: 1，耗时 55s） |
| Verifier | 1 次调用，7735 tokens |
| **交付状态** | **diagnostic_only** |
| factcheck | needs_review |
| high_importance_coverage | 0.0 |
| gate_eligible_external_evidence | **0** |
| 核心维度 evidence_scarce | 4/4 |

**报告特征**：与 gis-limitations **完全相同的 4 个通用模板维度**。所有章节均为"本轮尚未取得足以形成外部事实结论的正文证据"。零条外部证据。置信度附录只有一条 `待核验` 条目。这是最差的基线案例——完全空报告。

### 3.3 `empty-rag-policy` — 当前主要司法辖区对基础模型透明度义务有哪些可核验差异？

| 指标 | 值 |
|------|-----|
| run_id | `86b4415f70e1` |
| 耗时 | 183.0s |
| 实际 tokens | 41,183 / 75,000 |
| Planner | **超时**（failed: 1） |
| Analyst | 1 次调用，5037 tokens |
| Evidence Verifier | 被预算拒绝（rejected: 2） |
| Verifier | 1 次调用，15961 tokens |
| **交付状态** | **diagnostic_only** |
| factcheck | needs_review |
| high_importance_coverage | 0.0 |
| gate_eligible_external_evidence | **0** |
| 核心维度 evidence_scarce | 5/13 |

**报告特征**：硬编码的司法辖区维度（13 个维度：EU、US、UK、CN × 义务/适用范围/执行状态 + 跨辖区比较轴）。章节内容为确定性文本拼接，非 LLM 生成。每节仅包含引用片段和"待核验"标记，无分析。

## 4. 基线聚合

| 聚合指标 | 值 |
|----------|-----|
| 运行数 | 3 |
| deliverable | 0 |
| limited | 0 |
| diagnostic_only | **3** |
| Planner 超时率 | **100%**（3/3） |
| Analyst 被预算拒绝率 | **100%**（3 次总调用中有 3 次被拒绝） |
| Section Synthesizer 超时率 | 33%（1/3） |
| 平均 gate_eligible_external_evidence | 1.3 |
| high_importance_coverage 均值 | 0.0 |
| 平均耗时 | 161.7s |
| 平均实际 tokens | 33,571 |

## 5. 关键定性基线观察

以下是从实际报告中提取的、可作为 V2 对比锚点的定性特征：

### 5.1 Planner 超时 → 通用维度

所有 3 个已运行案例的 Planner 全部超时。结果：gis-limitations 和 software-agent-limitations 使用完全相同的 4 个通用模板维度（范围与成熟度边界、机制与方法限制、实施与运行约束、评估/风险与开放问题），尽管两个查询分别属于 GIS 和软件工程领域。

### 5.2 覆盖矩阵从未达标

所有 3 个案例的 `high_importance_coverage` 均为 0.0。所有案例的覆盖停止原因均为 `coverage_iteration_budget_exhausted`。

### 5.3 合成输出极度匮乏

- gis-limitations：每节约 400-600 字符，引用来自 ArcGIS 产品文档 chunk
- software-agent-limitations：所有节均为"本轮尚未取得足以形成外部事实结论的正文证据"——完全空报告
- empty-rag-policy：确定性 fallback 字符串拼接，非 LLM 生成

### 5.4 Fallback 污染

"（本节受运行预算限制，剩余细节见未覆盖问题。）" 出现在每份报告的多个章节中。

### 5.5 硬编码种子 URL 偏置

empty-rag-policy 的 Web 搜索因匹配预置的 `基础模型 + 透明度/监管` 条件而注入了 4 个预设 URL。这使该案例获得了比其他 2 个案例更多的"外部引用"，但来源固定且可能过时。

## 6. V2 对比评测计划

V2 评测将基于以下维度的对比：

| 维度 | 基线特征 | V2 目标 |
|------|---------|---------|
| 交付率 | 0%（所有 diagnostic_only） | > 80% 至少 partial+report_available |
| Planner 超时率 | 100% | < 30%（20s 简化查询拆解） |
| 维度领域相关性 | 通用四段模板 | 查询特异子问题 |
| 平均报告长度 | ~1500-3000 字符 | > 6000 字符 |
| 外部证据引用数 | 0-4 | 随来源可用性变化 |
| Fallback 占位符 | 每节均有 | 零 |
| 可信度评估 | 逐句表格 | 自然语言段落 |
| 截断免责声明 | "受运行预算限制" | 无 |
| 分析判断标注 | "Model analysis" | "（分析判断）" |

## 7. 未运行的 9 个案例

以下案例从未在 P1.5 管道上运行过，将在 V2 实现后首次运行并记录：

- `policy-ai-governance` (broad_review_or_limitations)
- `gis-architecture-design` (technical_comparison_or_design)
- `materials-method-comparison` (technical_comparison_or_design)
- `data-lakehouse-comparison` (technical_comparison_or_design)
- `clinical-ai-causality` (causal_mechanism_or_evidence_review)
- `battery-degradation-causality` (causal_mechanism_or_evidence_review)
- `recent-geoai-agents` (recent_status)
- `recent-clinical-agents` (recent_status)
- `empty-rag-security` (rag_empty_web_available)
