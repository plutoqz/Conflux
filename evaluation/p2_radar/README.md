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


## 2026-08-08 追加：标注校准 + 指标升级 + 源头过滤

### P0 标注校准（R0-R4 rubric）
- rubric: `annotation_rubric.md`。17 篇相关论文复核，6 处调整：
  GST-Bench / Multi-Year Geospatial 3→1（背景相关），Hardware Keystores 2→1，
  TRAJDEBUG / RTLola 2→3（直接对应 RQ2 验证/审计）。
- 校准后：相关(≥R2) 14 篇、强相关(R3) 4 篇（TRAJDEBUG、RTLola、WhenHistoryLies、XAIeval）。

### P1 评测指标升级
- 新增 `ndcg_at_10`（分级标注）、`mrr`（第一推荐位）、`strong_recall_at_20`、
  `success_at_10`。校准后（LLM 评审）：MRR=1.0、success@10=True、nDCG@10≈0.55-0.61、
  recall@10=0.43（理论上限 0.714，达 60%）。

### P2 arXiv cat: 分类过滤
- `search_arxiv` 支持 categories，`_execute_queries` 传入 QuerySpec.categories。
- 一次观测 strong_recall@20 0.5→0.75（XAIeval 66→9），recall@10 持平。

### P3 LLM 评审稳定性观测（重要）
- 三次 LLM 评审运行（同标注、不同批次）strong_recall@20：0.5 / 0.75 / 0.25，
  说明**LLM 单点评审对强相关识别不稳定**；prompt 增加"方法迁移"指导后单次下降，
  无证据收益（已回滚）。
- 纯 embedding 粗排（无 LLM）recall@10 仅 0.14、precision@5 0.4——**LLM 评审整体
  有效（recall 0.43 / precision@5 0.8）**，但强相关稳定召回仍是难点。
- 结论：在更大标注集或多运行平均之前，不宣称 LLM 评审对强相关召回的稳定收益；
  分层评审/温度控制/多次投票是候选改进，未在本轮实施。
