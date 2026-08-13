# B 多模型评审团设计

> 文档状态：设计完成，待实施确认
>
> 优先级：P0（第 1 批，与 A 并行）→ 建议映射 P4.1
>
> 版本：1.0
>
> 日期：2026-08-13
>
> 上位：[../P4智能体能力与工程化扩展计划.md](../P4智能体能力与工程化扩展计划.md)

## 0. 目标

在**纯模型判断点**引入多模型 ensemble 评审：各模型独立给出看法、裁判汇总、**异议作为一等公民保留**，对抗单模型训练偏好、世界知识差异与同一上下文的思维僵化。确定性裁决优先原则不变（见 ADR-01）。

## 1. 现状与复用

| 已有基建 | 复用方式 |
|---|---|
| verification 节点（`graph_v2.py verification_node`）：单 verifier + 确定性规则 rules-v1 | 评审团挂载点；确定性规则裁决不可被模型推翻的约束延续 |
| arbitration 节点（单 planner） | 第二个评审点 |
| 检索盲区独立分析（quick 档关闭） | "不看检索结果先判断"的多视角先例 |
| M5 评测 harness（四策略 + 盲评 + R3 replay） | A/B 对照载体 |
| `research_modes.py` 深度分档（55k/75k/320k） | 预算挂载点 |
| 冻结标注集（P2 75 篇 + KG 136 篇终审） | A/B 判据来源 |

## 2. 判断点选择：哪里开团，哪里不开

| 判断点 | 开团 | 理由 |
|---|---|---|
| verification（声明核验） | ✅ | 分歧集中、有冻结标注集可量化误判 |
| arbitration（覆盖仲裁） | ✅ | 决定是否补检索，误判代价高 |
| 周期审计摘要判断、验收标准判断 | ✅ | 高价值、低频、成本可控 |
| decompose / generate / synthesize | ❌ | 生成类，成本 ×N 而收益薄；生成多样性用温度/多证据解决 |
| 一切确定性节点 | ❌ | 永远不开 |

## 3. 评审团协议（`PanelReview`）

```text
输入：不可变 input_snapshot（声明列表 + 证据快照）——成员互不可见彼此输出
成员：members[] = { model_preset, persona, verdict, rationale }
      persona 差异化：严格批判者 / 领域务实者 / 风险敏感者
裁判：referee 汇总 → { consensus, dissent[], final_verdict, confidence }
分歧规则：
  - 全一致            → 维持原置信度
  - 多数 vs 少数      → 置信降一级 + 异议原文进 Evidence sidecar
  - 均分 / 不可调和   → 判"待核验"，保留全部成员意见
```

硬约束：

1. 模型**永远不能推翻确定性规则裁决**（延续 P3 既有约束）。
2. 成员输出必须 JSON 契约 + 白名单校验（复用现有 `_invoke_json` 模式）。
3. 同一判断点成员必须来自**不同模型 preset**（config 校验），防止"同一模型多采样"的伪多样性。
4. 成员之间**无多轮辩论**——单轮独立评审 + 裁判是收敛点，消息往返成本不可控。

## 4. 分档与成本

| 档位 | 成员 | 裁判 | 增量成本（相对单 verifier） |
|---|---|---|---|
| quick | 1（现状） | 无 | 0 |
| standard | 2（verifier + 异构） | 无（多数票） | +1 call/判断点 |
| deep | 3 + 1 | 有 | +3 call/判断点 |

- `panel_budget` 纳入 `BudgetState` 预扣；成员 `max_tokens` 减半。
- quick 档**强制关闭**（保住便宜路径，对应 §6 成本约束）。

## 5. 配置

```yaml
research:
  panel:
    enabled_by_depth: {quick: false, standard: true, deep: true}
    roster:
      verification: [verifier, balanced]   # 不同 preset，config 校验
      arbitration:  [planner, flash]
    referee: balanced
    quorum: majority
```

## 6. 先 A/B 后默认（评测先行）

- 载体：M5 盲评 harness + 冻结的 P2/KG 标注集；同证据快照下"单 verifier vs 评审团"对照。
- 指标：误判率（本应 insufficient 被判 supports）、待核验率、成本（token ×N）、延迟（并行后 P95）。
- **默认化条件**：误判率下降或持平 **且** 成本增量 ≤1.5×；否则保持单模型，评审团仅作为 deep 可选能力保留。
- 证据落 `reports/evaluation/p4/b_panel_ab_*.md`。

## 7. 验收（B1–B5）

| 编号 | 验收项 | 通过标准 |
|---|---|---|
| B1 | A/B 报告 | 产出对照报告，结论落 `config.yaml` |
| B2 | 异议可追溯 | sidecar 保留成员原文与最终裁决的分歧关系 |
| B3 | 预算不破 | deep 档压测，`panel_budget` 硬上限不超 |
| B4 | 通用性 | 模型全部 config 指定，不硬编码厂商/型号 |
| B5 | 确定性回归 | 评审团不改变任何确定性裁决（回归测试） |

## 8. 风险与取舍

| 风险 | 对策 |
|---|---|
| 裁判本身有偏 | 裁判角色按 run 哈希轮换，身份记入 sidecar |
| 提示词同质性（不同模型说一样的话） | persona 差异化提示词 + 异构模型 roster |
| 成本失控 | 只开判断点；standard 档多数票无裁判；quick 强制关 |
| 思维僵化 | 保持每成员独立全新 SystemMessage + 结构化输入，不共享聊天历史 |
