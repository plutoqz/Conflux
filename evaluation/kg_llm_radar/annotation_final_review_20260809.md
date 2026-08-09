# KG/LLM 标注终审记录（2026-08-09）

> 范围：用户委托 Codex 对 `evaluation/kg_llm_radar/labels_reviewed_20260809.jsonl` 做正式终审。
> 状态：终审完成并冻结，5 处等级调整。

## 审查材料

- 标注：`evaluation/kg_llm_radar/labels_reviewed_20260809.jsonl`（136 行 / 136 篇）
- 候选快照：`evaluation/kg_llm_radar/candidates_local_20260809.jsonl`
- 候选快照 SHA-256：`447D6B4655F0EF749A58E5F39C344F036C3A663A337B877DA0E46B3B5E92B6B1`
- 画像：`profiles/kg_llm_integration.yaml`（5 个 KG/LLM 研究问题）
- 审查口径：逐条按 title + abstract 对照 5 个研究问题

## 审查方法

1. 136 条标注与候选快照按 `paper_id` 对齐，缺失 0 条。
2. 逐条复核 R0-R3，重点核对 R0/R1、R1/R2、R2/R3 边界。
3. 对疑似低估/高估样本读取完整摘要后裁定。

## 终审调整

| paper_id | 标题 | 调整 | 理由 |
|---|---|---|---|
| `2504.06766v2` | FamilyTool: A Multi-hop Personalized Tool Use Benchmark | R1 -> R2 | KG-grounded 多跳工具使用基准 + KG 增强评估管线，直接支持研究问题 5 与评估复用 |
| `2605.04003v1` | Physics-Grounded Multi-Agent Architecture | R0 -> R2 | MAKA 使用 KG 检索、critic 验证与 provenance，直接支持可验证/可追溯知识与 Agent 决策支持 |
| `2605.10120v1` | MicroWorld | R0 -> R2 | 构建 111K 节点 KG 并用图增强检索提升 MLLM 推理，直接支持图检索增强与幻觉缓解 |
| `2605.26256v1` | POLAR | R0 -> R2 | 以多模态 KG 组织长期记忆支持 Agent 多跳推理，直接支持研究问题 5 |
| `2605.27845v1` | Snippet-Driven Supply Chain Discovery | R0 -> R2 | LLM 驱动的供应链 KG 构建并保留 provenance，直接支持研究问题 2 |

`2404.07456v1`（WESE）经完整摘要复核保持 R2：其探索阶段明确使用知识图谱策略存储并提取任务知识，不是无 KG 的纯 Agent 方法。

## 终审后分布

| 等级 | 数量 |
|---|---:|
| R3 | 43 |
| R2 | 29 |
| R1 | 43 |
| R0 | 21 |

相关（R2+）= 72，强相关（R3）= 43。
`evidence_quality` 全部保持 1（abstract-only）。

## 冻结

- 最终标注：`evaluation/kg_llm_radar/labels_final_20260809.jsonl`
- SHA-256：`28794CD650E2CB5F8B86C355C8FBA5B3EA9C132DE35385A1881B443705D95925`
- 状态：`final_reviewed_20260809_user_delegated_codex`

## 最终指标（final labels，3 次中位数）

| 指标 | pointwise cap40 | listwise cap60 |
|---|---:|---:|
| recall@10 | 0.1389 | 0.1389 |
| precision@10 | 1.0 | 1.0 |
| nDCG@10 | 0.9581 | 0.8196 |
| MRR | 1.0 | 1.0 |
| strong_recall@20 | 0.3256 | 0.3256 |
| success@10 | 3/3 | 3/3 |
| strong_success@1 | 3/3 | 2/3 |
| semantic_review_tokens | 48,228 | 41,975 |
| semantic_review_calls | 40 | 8 |

结论：final 标注下 `pointwise cap40` 在 nDCG 与 strong_success@1 上仍明显优于
`listwise cap60`，strong_recall@20 持平；Conflux 默认保持 pointwise cap40 是更优配置。

合并结果：
- `reports/evaluation/kg_llm_radar/merge_pp_cap40_3runs_final.json`
- `reports/evaluation/kg_llm_radar/merge_lw_cap60_3runs_final.json`
