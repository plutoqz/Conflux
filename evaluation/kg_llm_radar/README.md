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

## 限制

- 本测试仍是跨领域冒烟，初标待用户终审。
- 候选池来自本地知识库而非实时 arXiv，arXiv 当前网络不可达。
- 下一步应在该领域建立标注集并划分 hold-out 后，再比较跨领域指标。 
