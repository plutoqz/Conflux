# P2 论文相关性标注 Rubric（R0–R4）

评审背景：项目 = 知识图谱增强 GIS Agent 工作流的验证与可复现性。
研究问题：
- RQ1: How can knowledge-grounded agents improve geospatial data fusion workflows?
- RQ2: How should agent systems verify, repair, and audit geospatial processing steps?
- RQ3: What evidence is needed to make GIS agent experiments reproducible?

## 等级定义

| 等级 | 名称 | 判定标准 | 示例 |
|---|---|---|---|
| R0 | 无关 | 领域与方法均无联系 | 物理、量子、牙科、视频生成 |
| R1 | 背景相关 | 共享领域（GIS/空间/Agent/KG）或话题，但无可借鉴方法，也不回答研究问题 | 视频空间感知基准（非 GIS）、领域综述 |
| R2 | 方法相关 | 方法/机制可迁移到本项目的 agent 验证、知识融合或可复现评估 | 通用 Agent 工具使用评估、RAG 变体对比 |
| R3 | 直接相关 | 直接回答某个研究问题，或方法/数据可直接复用 | Agent 轨迹错误追踪（RQ2）、评估方法挑战（RQ3） |
| R4 | 核心引用 | 可作为项目论文核心引用/基准 | 与 RQ 直接对应的 SOTA 方法或基准 |

## 判定原则

1. 领域共享（GIS/空间）≠ 直接相关：视频空间感知不是 GIS 数据处理。
2. 方法可迁移（Agent 验证/工具评估）≥ 直接相关，只要迁移路径明确。
3. 标注对象是"论文对项目的价值"，不是"论文质量"。
4. 无法从 abstract 判断方法细节时，上限为 R2（不臆断直接可用）。

## 复核范围（2026-08-08）

- 原"强相关（=3）"4 篇逐篇复核，必要时下调。
- 原"相关（=2）"13 篇复核是否保持。
- 校准后 relevance>=3 视为强相关（strong-recall 口径）。
