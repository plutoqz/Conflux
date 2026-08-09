# P2 检索排序优化结论（2026-08-08）

真实 arXiv 多 Track 检索（5 QuerySpec / 3 Track / 75 候选 / 17 篇标注相关，同一查询集）。

> 当前默认配置（2026-08-08 受控 A/B 后）：无分层评审 + 温度 0.25 + arXiv cat 过滤。
> 分层评审 + 温度 0 已回滚为可选实验参数，证据见下方对照实验。

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
  `success_at_10`。校准后（LLM 评审）：MRR=1.0（首条 R≥2 相关）、success@10 单次有波动、
  nDCG@10≈0.55-0.61、
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


## 2026-08-08 追加：分层评审 + 温度 0 观测（第五次运行）

- 配置：高分(>=0.35)直收、低分(<0.25)直拒、模糊带(0.25-0.35)送审（limit 40）；评审温度 0。
- 结果：recall@10=0.286、precision@5=0.4、nDCG@10=0.413、strong_recall@20=0.5、MRR=1.0。
- 成本：仍 40 次调用 / 41k tokens / 164s——模糊带 46 篇 > limit 40，**未实现降本**。
- 多次运行序列（同标注）：strong_recall@20 = 0.5 / 0.75 / 0.25 / 0.5；recall@10 = 0.43 / 0.43 / 0.43 / 0.29。
- 结论：单次运行波动大于分层/温度带来的差异，**无法据此判定分层+温度的独立效果**；
  分层实现与测试已保留，但默认评估协议需改为多次运行取中位数，或先扩大标注集再评估。
  温度 0 是否优于 0.25、模糊带阈值是否需要收窄，均需对照实验（多次运行平均）确认。


## 2026-08-08 追加：3 次运行中位数基线（分层+温度0，已不是默认）

评估协议升级：`eval_p2_radar.py --merge` 输出多次运行的 median/min/max。
`--merge` 的输入是单次 `eval_p2_radar.py` 生成的评估 JSON（含 `results`），
不是原始 `radar_run.json`。
以下 3 次运行基线来自 RTLola 分类修复前的候选池；
修复后的单次真实运行见下一节。
该配置（分层评审 + 温度0 + arXiv cat 过滤）3 次真实运行中位数：

| 指标 | median | min | max |
|---|---|---|---|
| recall@10 | 0.4286 | 0.1429 | 0.4286 |
| precision@5 | 0.4 | 0.4 | 0.6 |
| precision@10 | 0.6 | 0.2 | 0.6 |
| nDCG@10 | 0.4399 | 0.1952 | 0.4481 |
| MRR | 1.0 | 1.0 | 1.0 |
| first_strong_rank | 9 | 8 | 16 |
| strong_recall@20 | 0.25 | 0.25 | 0.5 |
| success@10 | True（2/3） | — | — |
| strong_success@1 | False（0/3） | — | — |

- 稳定结论：MRR=1.0 表示第一条相关（R≥2）论文稳定排第一；**不代表第一篇是强相关**。
  `first_strong_rank` 三次为 16 / 9 / 8，`strong_success@1` 为 0/3，`success@10` 为 2/3。
- 短板：strong_recall@20 中位数 0.25（4 篇强相关不能稳定全部进入 top-20）。
  XAIeval 三次 rank 50-61，是 LLM 评审低分问题；RTLola 的 arXiv 分类为 `cs.LO`，
  当前修复前未被 agent_verification 查询 categories 覆盖，属于源头召回问题而非评审低分。

## 2026-08-08 收尾：高优先级修正

- 评测口径：新增 `first_strong_rank`、`strong_success_at_1`；`--merge` 输出
  `success_at_10` / `strong_success_at_1` 的 count/total，基线表已改为实际 2/3。
- RTLola 覆盖：`profiles/example_gis_agent.yaml` 的 agent_verification 查询加入
  `cs.LO`；`build_p2_label_candidates.py` 与真实雷达一致传递 QuerySpec categories，
  避免标注候选和运行候选使用不同检索口径。
- 当前 75 篇标注为 codex-agent 初标、evidence=abstract-only，已代审并冻结；
  2026-08-09 完成用户委托终审。计划已取消“至少 100 篇人工标注集”的数量门槛，
  以已终审冻结的标注集为 P2 退出标准。
- 成本：约 41k tokens / 次，波动小。

## 2026-08-08 标注复核 + RTLola 修复后真实运行

### 标注复核

- 复核范围：`labels.jsonl` 全部 75 行 / 56 篇唯一论文，按
  `annotation_rubric.md` 逐条复核 title + abstract。
- 结果：无等级调整；相关（R2+）14 篇、强相关（R3）4 篇；evidence_quality 仍为 1。
- 记录与冻结：`annotation_spotcheck_20260808.md`、`manifest.json`、
  `candidates_spotcheck_20260808.jsonl`。

### RTLola 修复后单次真实运行（分层 + 温度0 + 含 cs.LO）

用复核后的同一标注集重新运行一次真实 LLM 评审：

| 指标 | 本次单次运行 |
|---|---|
| recall@10 | 0.3571 |
| precision@5 | 0.4 |
| precision@10 | 0.5 |
| nDCG@10 | 0.4021 |
| MRR | 1.0 |
| first_strong_rank | 8 |
| strong_recall@20 | 0.5 |
| success@10 | True |
| strong_success@1 | False |

- RTLola 已召回并排第 8；TRAJDEBUG 第 19、WhenHistoryLies 第 24、
  XAIeval 第 48，strong_recall@20=2/4。
- 14 篇相关论文全部进入本次候选池（linked_relevant_count=14/14），
  源头覆盖问题已消除。
- XAIeval 仍被 LLM 评审低分，WhenHistoryLies 也未稳定进入 top-20；
  strong_recall 短板从“分类过滤排除”转为“LLM 排序仍待优化”。
- 本次为单次运行，未构成新的中位数基线；成本约 41k tokens / 40 次调用 / 141s。

## 2026-08-08 受控对照实验（3+3，同一 99 候选快照）

同一份冻结候选快照 `candidates_ab_20260808.jsonl` 上，分别运行：

- 旧配置：无分层 + 温度 0.25（3 次）
- 当前候选配置：分层 + 温度 0（3 次）

| 指标 | 旧配置 median（min/max） | 分层+温度0 median（min/max） |
|---|---|---|
| recall@10 | 0.4286（0.4286 / 0.5） | 0.2857（0.2857 / 0.3571） |
| precision@5 | 0.8（0.8 / 0.8） | 0.4（0.4 / 0.4） |
| precision@10 | 0.6（0.6 / 0.7） | 0.4（0.4 / 0.5） |
| nDCG@10 | 0.5739（0.5617 / 0.6319） | 0.3722（0.3377 / 0.4617） |
| MRR | 1.0（0.5 / 1.0） | 1.0（1.0 / 1.0） |
| first_strong_rank | 1（1 / 2） | 7（6 / 8） |
| strong_recall@20 | 0.5（0.5 / 0.75） | 0.5（0.5 / 0.75） |
| success@10 | 3/3 | 3/3 |
| strong_success@1 | 2/3 | 0/3 |
| semantic_review_tokens | 43,420（42,975 / 43,691） | 41,428（41,343 / 42,181） |

结论：在强相关召回持平的情况下，旧配置在 recall、precision、nDCG、
first_strong_rank 和 strong_success@1 上均优于或持平分层 + 温度 0；
分层 + 温度 0 只省约 2k tokens/次，未带来质量收益。因此默认配置回滚为
无分层 + 温度 0.25，分层逻辑保留为 `layered_review` 可选参数。

## 2026-08-08 降本/强相关实验（listwise 与 few-shot，各 3 次）

在同一 99 候选快照上，继续对比 pointwise 基线、listwise（每 8 篇一次调用）
和 few-shot pointwise（注入 RTLola / WhenHistoryLies 已校准示例）：

| 指标 | pointwise median | listwise median | few-shot median |
|---|---|---|---|
| recall@10 | 0.4286 | 0.4286 | 0.2857 |
| precision@5 | 0.8 | 0.6 | 0.6 |
| precision@10 | 0.6 | 0.6 | 0.4 |
| nDCG@10 | 0.5739 | 0.4902 | 0.4654 |
| first_strong_rank | 1 | 3 | 1 |
| strong_recall@20 | 0.5 | 0.5 | 0.5 |
| success@10 | 3/3 | 3/3 | 3/3 |
| strong_success@1 | 2/3 | 0/3 | 2/3 |
| tokens/次 | 43,420 | 29,754 | 60,368 |
| 调用数/次 | 40 | 5 | 40 |

结论：listwise 将调用数降到 5 次、token 降至约 30k，但 nDCG、precision@5
和 first_strong_rank 均下降，strong_recall 未提升；few-shot 增加了 token 成本，
recall/precision/nDCG 下降，strong_recall 仍为 0.5。两者当前均不采纳为默认，
保留为实验参数（`--review-mode listwise`、`--few-shot`）。

## 2026-08-09 Cap 网格

GIS Cap 网格结果见 `evaluation/recall_cap_grid_20260809.md`：
cap80 listwise 提升 strong_recall@20 中位数至 0.75，但 nDCG/precision 下降；
cap100 恶化。默认仍为 pointwise cap40。

## 2026-08-09 追加：无 LLM 评审对照与分领域库模拟

### 无 LLM 评审基线

- GIS（`no_llm_result.json`，73 候选 / 14 相关，校准后标签）：
  recall@10=0.1429、precision@5=0.4、precision@10=0.2、nDCG@10=0.1952、
  strong_recall@20=0.25，0 tokens。
- GIS（17 相关口径，`embedding_result.json` / `multi_query_result.json`）：
  embedding 粗排 recall@10=0.2353、precision@5=0.4；多点查询同值。
- LLM 评审后（校准后口径）：recall@10=0.43、precision@5=0.8。
- 结论：**LLM 评审收益是 GIS/arXiv 稀疏检索场景的真实结论**。

- KG（本地 136 候选 / 67 相关，reviewed 标签，纯 embedding 粗排单次确定性运行）：
  recall@10=0.1493、precision@10=1.0、nDCG@10=0.9621、strong_recall@20=0.3488、
  0 tokens、66/67 相关论文进入 top-100。
- KG LLM 评审 3 次中位数：pointwise cap40 nDCG@10=0.9581、strong_recall@20=0.3256、
  48,228 tokens；listwise cap60 nDCG@10=0.9217、strong_recall@20=0.3488、40,664 tokens。
- 结论：**KG 高密度本地池上，无 LLM 粗排已接近全相关，LLM 评审未带来质量收益，
  仅增加约 40k tokens 成本**。默认全开 LLM 评审可按领域细分：高密度本地池
  可考虑粗排直出或降低评审预算。

### 分领域向量库模拟（2026-08-09）

混合池 = 136 篇 KG 论文 + 29 个明显跨域文档（GIS/ESRI、NIST/密码学、AI 治理、
RAG/LLM wiki），对 KG 画像查询做无 LLM embedding 粗排：

- 混合池 Top-25 全部为 KG 论文，0 个跨域文档进入。
- 跨域文档最早出现在第 100 名（RAG 相关长文档）；GIS、密码学、AI 治理文档全部更靠后。
- 纯 KG 池 Top-20 与混合池 Top-20 排序完全一致。

结论：无 LLM 评审场景下，当前 embedding 粗排的抗跨域噪声能力足够，
**按领域拆库的边际收益很小，且引入路由错误丢召回与跨领域查询变弱的成本**。
更值得做的是“论文 vs 通用资料”来源分层与 metadata 过滤；当前
`conflux_docs` 仅 97 条论文分块，ESRI/NIST/wiki 等资料尚未完整索引，
索引覆盖不足是分库讨论之前更优先的问题。

### listwise 评审失败缺口（KG 第 1 轮）

- `multi_lw_cap60_1` 的 8 个 listwise 批次中有 2 个批次解析失败（fell_back），
  2 篇 top-60 论文未完成语义评审。
- 实现上 `review is None` 时既不更新分数也不标记 `needs_review`，论文直接保留
  粗排分进入 links，违反“评审失败必须 unreviewed”合同。
- 两篇分别落在 rank 8（R3）与 rank 37（R2），对当轮指标影响很小，但 listwise
  结论需在修复该语义缺口后重新确认。

### listwise 缺口修复与重跑（2026-08-09）

缺口已修复：`semantic_review.py` 对缺失/失败的 listwise 论文生成
`reviewed=False` 记录，雷达层将其标记为 `needs_review`，并补了部分/整批失败
回归测试。修复后 `listwise cap60` 3 次中位数：

| 指标 | pointwise cap40 median | listwise cap60 median（修复后） |
|---|---|---|
| nDCG@10 | 0.9581 | 0.8196（0.7418 / 0.838） |
| strong_recall@20 | 0.3256 | 0.3256（0.2558 / 0.3488） |
| strong_success@1 | 3/3 | 2/3 |
| semantic_review_tokens | 48,228 | 41,975 |
| semantic_review_calls | 40 | 8 |

结论变化：修复后 listwise 不再优于 pointwise，且三轮仍有 1-2 个批次解析失败并
正确标记 `needs_review`；默认保持 `pointwise cap40`，listwise 需先提升解析
稳定性再重新评估。

## 2026-08-09 标注终审与配置确认

用户委托 Codex 对 75 行 P2 标注做正式终审，无等级调整，冻结为
`evaluation/p2_radar/labels_final_20260809.jsonl`，详见
`evaluation/p2_radar/annotation_final_review_20260809.md`。

final labels 下默认 `pointwise cap40` 3 次中位数：

| 指标 | median |
|---|---:|
| recall@10 | 0.4286 |
| precision@10 | 0.6 |
| nDCG@10 | 0.5739 |
| strong_recall@20 | 0.5 |
| strong_success@1 | 2/3 |
| semantic_review_tokens | 43,420 |

配置确认：`run_paper_radar` 默认 `review_mode=pointwise`、
`semantic_review_limit=40`、非分层；Workbench `research_radar` 默认回落
`balanced`（温度 0.25），与实验结论所用配置一致。
