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

## 限制

- 本测试是跨领域冒烟，尚未建立 KG 领域人工标注集，因此不给出
  recall/nDCG 等正式指标。
- 候选池来自本地知识库而非实时 arXiv，arXiv 当前网络不可达。
- 下一步应在该领域建立标注集并划分 hold-out 后，再比较跨领域指标。 
