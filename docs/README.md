# Conflux 文档索引

本文档说明 `docs/` 下的文档分类和当前入口。长期有效的总体文档保留在 `docs/` 根目录；阶段性计划、报告和复盘按类别归档。

## 总体文档

- [architecture.md](architecture.md)：Conflux ResearchOps 长期架构蓝图、核心边界和演进原则。

项目级产品说明和界面约束仍位于仓库根目录：

- [PRODUCT.md](../PRODUCT.md)：产品定位和设计原则。
- [DESIGN.md](../DESIGN.md)：工作台视觉和交互约束。

## 计划

目录：`docs/plans/`

- [execution_plan_v1.md](plans/execution_plan_v1.md)：第一版执行方案、阶段状态、验收标准和剩余闸门。

计划类文档描述未来或正在执行的工作，包括范围、顺序、验收、回滚和阶段状态。实际完成情况必须由代码、测试和评测产物支持。

## 阶段报告

目录：`docs/reports/`

- [m0_baseline_report.md](reports/m0_baseline_report.md)：M0 阶段的测试、检索、报告和性能基线。

报告类文档记录某个时间点或阶段的事实结果，原则上不承担后续实施计划。

## 复盘

目录：`docs/retrospectives/`

- [p1_execution_retrospective.md](retrospectives/p1_execution_retrospective.md)：P1 三源研究质量闭环的完整执行与技术复盘。

复盘类文档记录实施过程、决策变化、问题、纠正措施、指标结果和可复用经验，不替代执行计划中的正式状态。

## 维护规则

1. 总体架构、长期原则和文档索引保留在 `docs/` 根目录。
2. 执行计划放入 `docs/plans/`，阶段报告放入 `docs/reports/`，复盘放入 `docs/retrospectives/`。
3. 文档移动后必须同步更新 README、项目配置和文档间链接。
4. 同一阶段的计划、报告和复盘分别承担不同职责，避免在多个文件中维护相互冲突的状态。
5. 阶段状态以执行计划为入口，以代码、测试和评测产物为最终事实依据。
