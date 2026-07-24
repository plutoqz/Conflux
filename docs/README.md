# Conflux 文档索引

本文档说明 `docs/` 下的文档分类和当前入口。长期有效的总体文档保留在 `docs/` 根目录；阶段性计划、报告和复盘按类别归档。

## 总体文档

- [architecture.md](architecture.md)：Conflux ResearchOps 长期架构蓝图、核心边界和演进原则。

项目级产品说明和界面约束仍位于仓库根目录：

- [PRODUCT.md](../PRODUCT.md)：产品定位和设计原则。
- [DESIGN.md](../DESIGN.md)：工作台视觉和交互约束。

## 计划

目录：`docs/plans/`

- [execution_plan_v1.md](plans/execution_plan_v1.md)：**唯一执行主线**。第一版执行方案、阶段状态、验收标准和剩余闸门（M0-M2/P0/P1/P1.5/V2 已完成，P2/M3+ 待启动）。
- [research_query_redesign.md](plans/research_query_redesign.md)：P1.5 → V2 研究查询重构方案与诊断（阶段 A-G 已完成，H-K 待完成）。
- [agent_book_optimization_plan.md](plans/agent_book_optimization_plan.md)：基于《AI Agent 设计原理与工程实践》的 Conflux 候选优化 RFC。**不作为独立执行主线**——通过评审的条目逐项合并进 `execution_plan_v1.md`。

已完成并移至 `docs/plans/done/`：

- [generalized_research_delivery_plan.md](plans/done/generalized_research_delivery_plan.md)：P1.5 泛化研究可交付质量收敛方案（实现及离线合同完成，已被 V2 部分取代）。
- [v2_implementation_summary.md](plans/done/v2_implementation_summary.md)：V2 answer_first 管道实施完成摘要（H-K 待完成项链接到 research_query_redesign.md）。

## 基准

目录：`docs/benchmarks/`

- [p1_deep_research_baseline.md](benchmarks/p1_deep_research_baseline.md)：P1 深度研究基准测试结果。
- [p15_baseline_snapshot.md](benchmarks/p15_baseline_snapshot.md)：P1.5 基线快照（V2 A/B 对比评测对照组）。

基准类文档记录特定时间点的性能快照，用于回归对比。不承担后续实施计划。

## 复盘

目录：`docs/retrospectives/`

- [p1_execution_retrospective.md](retrospectives/p1_execution_retrospective.md)：P1 三源研究质量闭环的完整执行与技术复盘。

复盘类文档记录实施过程、决策变化、问题、纠正措施、指标结果和可复用经验，不替代执行计划中的正式状态。

## 维护规则

1. 总体架构、长期原则和文档索引保留在 `docs/` 根目录。
2. 执行计划放入 `docs/plans/`，完成后移至 `docs/plans/done/`；基准放入 `docs/benchmarks/`；复盘放入 `docs/retrospectives/`。
3. 文档移动后必须同步更新 README、项目配置和文档间链接。
4. 同一阶段的计划、报告和复盘分别承担不同职责，避免在多个文件中维护相互冲突的状态。
5. **阶段状态以执行计划为入口，以代码、测试和评测产物为最终事实依据。**
6. `execution_plan_v1.md` 是唯一执行主线。其他 plans/ 文档通过评审后逐项合并进执行主线，不得形成多个同时维护的执行真相源。
