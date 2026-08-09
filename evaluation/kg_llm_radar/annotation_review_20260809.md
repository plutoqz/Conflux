# KG/LLM 标注复核记录（2026-08-09）

复核范围：`labels_provisional_20260809.jsonl` 全部 136 行，按
`profiles/kg_llm_integration.yaml` 的 5 个研究问题（KG 为 LLM 提供可验证/
可追溯/可更新知识、LLM 支持 KG 构建/补全/对齐/质量控制、GraphRAG 提升
复杂问答与多跳推理、KG+LLM 降低幻觉并改善可解释性、智能体系统利用 KG
支持记忆/规划/工具调用）逐条复核 title + abstract。

## 复核结果

- R3（直接相关）45 -> 43：2 篇降为 R2。
- R2（方法相关）22 -> 24。
- R1/R0 不变：R1=44、R0=25。
- 相关（R2+）仍为 67 篇；强相关（R3）由 45 调整为 43 篇。
- evidence_quality 全部保持 1（abstract-only）。

## 等级调整

| paper_id | 标题 | 调整 | 理由 |
|---|---|---|---|
| `2310.11555v1` | Integrating 3D City Data through Knowledge Graphs | R3 -> R2 | CityGML 到 KG 的映射与查询，无 LLM 参与；对 KG-LLM 研究问题仅为方法可迁移 |
| `2601.03587v1` | Deontic Knowledge Graphs for Privacy Compliance in Multimodal Disaster Data Sharing | R3 -> R2 | 基于 KG 的合规决策与 provenance，无 LLM 参与；可追溯方法可借鉴，但不直接回答 KG-LLM 研究问题 |

## 边界判断

- `2605.17669v1`（Cultural Heritage KG Extension）保留 R3：使用 LLM/VLM
  自动扩展 KG 并带 grounding 验证管线，直接对应 KG 自动构建与质量控制。
- `2605.01582v1`（KG-First, LLM-Fallback）、`2605.20170v1`（KoRe）保留 R2：
  方法直接对应 KG 检索/知识注入，但领域或实现路径未达到 R3 直接复用程度。

## 冻结信息

- 复核后标注：`labels_reviewed_20260809.jsonl`
- 标注哈希：`213DD5FE7D07978B2E3D753FE83D6D8F04371CD94FD2F8808A8E5F1F2D2DB185`
- 候选来源：`candidates_local_20260809.jsonl`
- 候选哈希：`447D6B4655F0EF749A58E5F39C344F036C3A663A337B877DA0E46B3B5E92B6B1`

本轮由 Codex 代审完成；正式验收时仍建议对 R2/R3 边界样本做用户终审。
