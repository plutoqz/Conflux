# P2 标注终审记录（2026-08-09）

> 范围：用户委托 Codex 对 `evaluation/p2_radar/labels.jsonl` 做正式终审。
> 状态：终审完成并冻结，无等级调整。

## 审查材料

- 标注：`evaluation/p2_radar/labels.jsonl`（75 行 / 56 篇唯一论文）
- 候选快照：`reports/evaluation/p2_radar/label_run/candidates.jsonl`
- 候选快照 SHA-256：`E801FEDEF54C1508DA202844AC26234EEDC7096F91C568F6B15C4582D92F71A8`
- Rubric：`evaluation/p2_radar/annotation_rubric.md`
- 审查口径：逐条按 title + abstract 对照项目目标（知识图谱增强 GIS Agent 工作流的验证与可复现性）

## 审查方法

1. 将 75 条标注与候选快照按 `(query_id, paper_id)` 对齐，缺失 0 条。
2. 同一论文跨查询的 relevance 一致性检查：56 篇唯一论文无跨查询不一致。
3. 逐条复核 R0-R3，重点核对 R1/R2、R2/R3 边界与已校准样本。

## 终审结果

无等级调整。75 行分布：

| 等级 | 行数 |
|---|---:|
| R0 | 37 |
| R1 | 14 |
| R2 | 19 |
| R3 | 5 |

56 篇唯一论文分布：R0=30、R1=12、R2=10、R3=4。
`evidence_quality` 全部保持 1（abstract-only）。

边界样本复核结论：

- `2608.06366v1`（医疗证据管道）保持 R1：有可迁移的证据链路概念，但迁移路径未在 abstract 中确立。
- `2608.06108v1`（金融 Agent 评估）保持 R1：评估设计有参考价值，但领域绑定强，abstract-only 下不足 R2。
- `2608.06196v1`（Agent skill retrieval + KG）保持 R2：KG 编码与 RQ1 相关，但未直接落到地理数据融合场景，不升 R3。

## 冻结

- 最终标注：`evaluation/p2_radar/labels_final_20260809.jsonl`
- SHA-256：`367CA91C1A6EBCB008C2000ED3F26C330355B4E08680BD08A6DF483AF4DE8663`
- 状态：`final_reviewed_20260809_user_delegated_codex`

## 最终指标（final labels，pointwise cap40，3 次中位数）

| 指标 | median |
|---|---:|
| recall@10 | 0.4286 |
| precision@10 | 0.6 |
| nDCG@10 | 0.5739 |
| MRR | 1.0 |
| strong_recall@20 | 0.5 |
| success@10 | 3/3 |
| strong_success@1 | 2/3 |
| semantic_review_tokens | 43,420 |
| semantic_review_calls | 40 |

合并结果：`reports/evaluation/p2_radar/merge_pp_cap40_3runs_final.json`
