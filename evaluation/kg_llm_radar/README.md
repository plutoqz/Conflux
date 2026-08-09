# KG/LLM 跨领域测试（2026-08-09）

## 目的

在 GIS Agent 画像之外，用知识图谱 + 大语言模型融合领域验证当前默认配置
是否仍能输出高质量论文雷达结果，避免把单画像结论当成通用结论。

## 测试设置

- 画像：`profiles/kg_llm_integration.yaml`
- 候选池：本地知识库 `data/documents/papers/papers/*#summary.md` 共 136 篇，
  其中约 103 篇标题命中 KG/RAG/LLM 相关关键词。
- 知识库验证：Chroma 对
  `knowledge graph large language model GraphRAG` 和
  `retrieval augmented generation evaluation metrics` 均可返回相关论文块。
- 配置：pointwise、非分层、温度 0.25、评审池 Top-40。
- 运行：`reports/evaluation/kg_llm_radar/run_20260809/radar_run.json`

## 结果

- 候选：136 → 粗排 Top-100。
- 评审：40 次调用，50,762 tokens，0 失败。
- Top-25 结果全部为 KG/RAG/LLM/Agent 相关论文，例如：
  DO-RAG、GraphRAG Consumer Hardware、AgREE、ConRAG、
  Ontology-grounded KG Construction、MemGraphRAG。

## 初标指标（provisional）

- 初标：`labels_provisional_20260809.jsonl`，136 篇按 title + abstract 标注，
  分布为 R3=45、R2=22、R1=44、R0=25；相关（R2+）67 篇，强相关 45 篇。
- 单次运行结果：

| 指标 | 值 |
|---|---|
| recall@10 | 0.1493 |
| precision@10 | 1.0 |
| nDCG@10 | 0.7838 |
| MRR | 1.0 |
| first_strong_rank | 1 |
| strong_success@1 | True |
| strong_recall@20 | 0.3333 |
| success@10 | True |

注意：这是 Codex 代审初标，不是人工金标准；单次运行，未做多次中位数。
随机按论文 ID 划分 hold-out 对检索排序不成立，本轮不做 paper-level hold-out；
跨领域验证采用“GIS 调参域 / KG 独立测试域”的方式。

## 2026-08-09 Cap 网格

KG Cap 网格结果见 `evaluation/recall_cap_grid_20260809.md`：
listwise 扩池未提升 strong_recall@20；pointwise cap100 单次运行质量最高但成本
约 2.4 倍。当前建议：成本敏感用 listwise cap60，质量优先用 pointwise cap100
并补多次运行确认。

## 2026-08-09 标注复核 + 多次运行中位数

### 标注复核

- 复核范围：`labels_provisional_20260809.jsonl` 全部 136 行，按 5 个 KG/LLM
  研究问题逐条复核 title + abstract，记录见
  `annotation_review_20260809.md`。
- 调整 2 处：`2310.11555v1`、`2601.03587v1` 由 R3 降为 R2（均为无 LLM 参与的
  KG 应用，仅方法可迁移）。
- 复核后分布：R3=43、R2=24、R1=44、R0=25；相关（R2+）67 篇、强相关 43 篇。
- 冻结文件：`labels_reviewed_20260809.jsonl`，仍为 Codex 代审，用户终审待做。

### 多次运行中位数（同一 136 候选快照，复核后标注）

对默认 `pointwise cap40` 与成本推荐 `listwise cap60` 各运行 3 次真实
LLM 评审，用 `eval_p2_radar.py --merge` 合并：

| 指标 | pointwise cap40 median（min/max） | listwise cap60 median（min/max） |
|---|---|---|
| recall@10 | 0.1493（0.1493 / 0.1493） | 0.1493（0.1493 / 0.1493） |
| precision@10 | 1.0（1.0 / 1.0） | 1.0（1.0 / 1.0） |
| nDCG@10 | 0.9581（0.9117 / 0.9603） | 0.9217（0.9173 / 0.9225） |
| MRR | 1.0 | 1.0 |
| first_strong_rank | 1（1 / 1） | 1（1 / 1） |
| strong_recall@20 | 0.3256（0.3256 / 0.3488） | 0.3488（0.3256 / 0.3721） |
| success@10 | 3/3 | 3/3 |
| strong_success@1 | 3/3 | 3/3 |
| semantic_review_tokens | 48,228（48,153 / 49,081） | 40,664（38,042 / 41,941） |
| semantic_review_calls | 40 | 8 |

结论：多次运行下 `listwise cap60` 的 strong_recall@20 中位数不劣于
`pointwise cap40`（0.3488 vs 0.3256），且调用数降至 1/5、token 省约 15%；
`pointwise cap40` 的 nDCG 更高（0.9581 vs 0.9217）。两个配置都稳定把
第一条强相关论文排到首位（strong_success@1=3/3），但 top-10 仅覆盖约 1/7
相关论文（10/67），相关论文进入 top-20 的绝对量仍是主要短板。

产物：
- `reports/evaluation/kg_llm_radar/multi_pp_cap40_{1,2,3}/radar_run.json`
- `reports/evaluation/kg_llm_radar/multi_lw_cap60_{1,2,3}/radar_run.json`
- `reports/evaluation/kg_llm_radar/merge_pp_cap40_3runs_reviewed.json`
- `reports/evaluation/kg_llm_radar/merge_lw_cap60_3runs_reviewed.json`

### 无 LLM 评审基线（2026-08-09）

同一候选快照、reviewed 标签下补算纯 embedding 粗排（确定性、单次代表）：

| 指标 | 无 LLM 粗排 | pointwise cap40 median | listwise cap60 median |
|---|---|---|---|
| recall@10 | 0.1493 | 0.1493 | 0.1493 |
| precision@10 | 1.0 | 1.0 | 1.0 |
| nDCG@10 | 0.9621 | 0.9581 | 0.9217 |
| strong_recall@20 | 0.3488 | 0.3256 | 0.3488 |
| semantic_review_tokens | 0 | 48,228 | 40,664 |
| semantic_review_calls | 0 | 40 | 8 |

结论：KG 高密度本地池上，无 LLM 粗排已接近全相关（top-10 全相关、66/67 相关
论文进入 top-100），LLM 评审未带来质量收益，仅增加约 40k tokens 成本。
“LLM 评审有效”目前是 GIS/arXiv 稀疏检索场景的结论，不能推广到所有领域。

### 分领域向量库模拟（2026-08-09）

将 136 篇 KG 论文与 29 个跨域文档（GIS/ESRI、NIST/密码学、AI 治理、RAG/LLM wiki）
混入同一池做无 LLM 粗排：

- Top-25 全部为 KG 论文，跨域文档最早出现在第 100 名；
- 纯 KG 池 Top-20 与混合池 Top-20 排序完全一致。

结论：无 LLM 评审下粗排抗跨域噪声能力足够，按领域拆库收益小且增加路由风险；
更优先的方向是“论文 vs 通用资料”来源分层、metadata 过滤，以及补全当前
`conflux_docs`（仅 97 条论文分块）的索引覆盖。

### listwise 评审失败缺口

`multi_lw_cap60_1` 有 2 篇 top-60 论文因批次解析失败（fell_back）未完成语义
评审，但实现未标记 `needs_review`，论文直接保留粗排分进入 links，违反
`unreviewed` 合同；两篇分别落在 rank 8（R3）与 rank 37（R2），对当轮指标影响
很小，listwise 结论需在修复后重新确认。

## 限制

- 本测试仍是跨领域冒烟；标注已由 Codex 复核冻结，但仍待用户终审。
- 候选池来自本地知识库而非实时 arXiv，arXiv 当前网络不可达。
- 下一步应在该领域建立标注集并划分 hold-out 后，再比较跨领域指标。 
