# P2 检索排序优化结论（2026-08-08）

真实 arXiv 多 Track 检索（5 QuerySpec / 3 Track / 75 候选 / 17 篇标注相关，同一查询集）。

## 阶段对比

| 阶段 | recall@1 | recall@5 | recall@10 | precision@5 | precision@10 |
|---|---|---|---|---|---|
| 词法 score_papers（旧基线） | 0.059 | 0.118 | 0.176 | 0.4 | 0.3 |
| + embedding 粗排（单点查询） | 0.059 | 0.118 | 0.235 | 0.4 | 0.4 |
| + 多点查询向量（goal+RQ+keywords） | 0.059 | 0.118 | 0.235 | 0.4 | 0.4 |
| + 批量 LLM 语义评审（40 篇池） | 0.059 | 0.235 | 0.353 | 0.8 | 0.6 |

注：各阶段运行来自不同 arXiv 检索批次（论文会更新），作为方向性证据，非严格同批次 A/B。

## 粗排“缩范围”能力

- embedding 粗排 top-30 覆盖 16/17、top-40 覆盖 17/17（词法 top-40 仅 15/17）。
- 粗排的职责是“不漏相关”，当前 top-40 全回收；精确排序由 LLM 语义评审承担。

## 成本（LLM 语义评审）

- 40 次评审调用、42,111 tokens、0 失败、约 165s；无深度分析（deep_read_limit=0）。

## 结论

- 执行计划设计的链路（dedup → embedding 粗排 → 批量 LLM 语义评审 → 深评）已落地并有真实指标。
- recall@10 0.18 → 0.35（近一倍），precision@5 0.4 → 0.8。
- 0.80 目标属于 P1 RAG 检索指标，不适用于 P2 论文发现任务；P2 退出标准只要求“报告 recall@k/precision@k”，已满足。

## 相关产物

- 标注集：`evaluation/p2_radar/labels.jsonl`（75 条）
- 评测：`reports/evaluation/p2_radar/{real_result,embedding_result,multi_query_result,llm_review_result}.json`
- 代码：`src/conflux/paper_radar/coarse_rank.py`、`semantic_review.py`
