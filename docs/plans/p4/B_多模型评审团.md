# B 多模型评审团设计

> 文档状态：v1.1 已按 2026-08-14 真实 A/B 教训修订（伪多样性 → 真异构 roster）；
> 三模型真异构与 arbitration 迁移已落地 config/校验，对抗评测与 arbitration 挂载待实施确认。
>
> 优先级：P0（第 1 批，与 A 并行）→ 建议映射 P4.1
>
> 版本：1.1
>
> 日期：2026-08-14
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
3. 同一判断点成员必须来自**不同模型 preset**，且解析后的 **(provider, model) 必须互异**
   （`research_modes.validate_research_model_profiles` 已升级为 provider/model 级校验；
    2026-08-14 A/B 教训：verifier/balanced 曾同指 deepseek-v4-flash-guan 造成伪多样性）。
4. 成员之间**无多轮辩论**——单轮独立评审 + 裁判是收敛点，消息往返成本不可控。

## 3.1 真异构 roster 与三模型任务安排（v1.1，2026-08-14）

模型能力大致递减：**ds_strong（deepseek-v4-flash-0731）> mimo（mimo-v2.5）> qwen_weak（qwen3.7-flash）**，
同一 OpenAI 兼容网关，仅 model 名不同（`config.yaml models.{ds_strong,mimo,qwen_weak}`）。

| 角色 | 分配模型 | 理由 |
|---|---|---|
| verification 成员（2 成员多数票，无裁判） | ds_strong（strict critic）+ mimo（domain pragmatist） | 高频判断点控制成本；强+中组合质量与成本平衡 |
| arbitration 成员（3 成员 + 裁判，仅 deep 档） | ds_strong（strict critic）+ mimo（domain pragmatist）+ qwen_weak（risk sensitive） | 误判代价高开全团；弱模型"宁缺毋滥"恰好做保守否决票 |
| 裁判 referee（分歧叙事，不改变票数） | ds_strong | 最强模型承担综合分歧的最高推理需求 |

成员顺序 = 能力降序，与 `panel.py` 按 index 轮换的 persona（strict critic / domain pragmatist / risk sensitive）对齐：
弱模型拿到 risk-sensitive 角色（保守价值与其能力匹配），强模型拿到 strict-critic 与裁判。

## 3.2 arbitration 挂载（待实施）

- 现有 `arbitration_node`（`graph_v2.py:770-855`）为单 planner 调用 `_arbitration_payload`；
  挂载点：deep 档 `panel_enabled` 时改走 `run_panel`（verdict 白名单换为 `covered/gap/conflict/uncertain`，
  `run_panel` 已支持 `verdict_whitelist` 参数；成员输出 judgments/action_proposals 后仍走既有
  subquestion_id/source/trigger 白名单校验）。
- `panel.py` 需新增 arbitration 版成员 prompt（输入 subquestions + ledger snapshot，输出 judgments + action_proposals）。
- standard 档 arbitration 保持单 planner（评审团仅 deep 档挂载，与校验一致）。

## 3.3 对抗评测集（待实施）

当前 66-claim gold 对两臂不构成区分（单 verifier 也 0 误判），需构造**对抗样本**让单模型必然出错：

| 对抗类型 | 构造方式 | 预期效果 |
|---|---|---|
| overclaim 近 miss | 证据支持"某限制"但声明过度到"保证/绝对" | 单 verifier 误判 supports，评审团（strict critic）拦截 |
| off-domain 擦边 | 相关系统而非目标系统，但措辞接近 | 弱模型保守票降级 |
| 多源弱支持 | 多个相关但不直接证据 | 单模型过信，评审团 majority 折衷 |
| 反直觉真值 | 证据直接矛盾但声明措辞权威 | 强模型 contradicts，弱模型跟从 vs 独立 |

目标：单 verifier 误判率显著 >0（≥20%），评审团下降 ≥10pp 且成本 ≤1.5× 才算真异构有效；
评测跑 `scripts/p4_panel_ab.py --real --repeats 2`，报告落 `reports/evaluation/p4/`。

## 3.4 对抗评测实测结论（2026-08-14，21 claims / 4 cases / 2 repeats，真实三模型）

数据：`evaluation/p4_panel_ab/verification_claims_gold_adv.jsonl`（生成器
`scripts/p4_build_gold_adversarial.py`）；报告
`reports/evaluation/p4/b_panel_ab_adv_real_v2_20260814.md/.json`。

| 指标 | 单 verifier | 评审团（ds_strong + mimo） | 增量 |
|---|---|---|---|
| 误判率（判 supports 而 gold 非 supports） | 0.0%（n=0） | 0.0%（n=0） | — |
| 全量不一致率（不含 uncertain） | **61.9%** | **14.3%** | **-47.6pp** |
| 待核验率（uncertain） | 0.0% | 85.7% | +85.7pp |
| token 成本 | 2169 | 3476 | **×1.603** |
| P95 延迟 | 28.2s | 48.5s | +20s |

**结论**：

1. 对抗集成功区分两臂（单 verifier 61.9% 具体判断错误 vs 评审团 14.3%）——评审团的
   **真实价值是"去过度自信"：把错误的自信判断转为待核验（85.7%），而非把错误变正确**。
2. **成本门 ×1.5 对 2 成员多数票评审团是结构性不可达**（2 次输入调用 vs 1 次，输入 token
   占主导；实测 ×1.60–1.69）。若按"单位正确判断成本"核算，评审团每正确判断成本更低。
3. 成员可靠性修复（2026-08-14）：`panel._extract_json` 接 json-repair 容错截断/围栏 JSON、
   `_invoke_member` 失败重试一次——首轮 A/B 中 mimo 截断 JSON + qwen 空响应导致"有效票<2
   → 全 uncertain"的伪结果已被修复（uncertain 100%→85.7%）。
4. 默认化决策：按既有规则（成本 ≤1.5×）为 `deep_optional`；**建议评审团默认化门禁修订为
   "不一致率显著下降（≥20pp）且成本 ≤2×"**——待用户确认后写入 config 默认。

## 3.5 v1.2 强制表态协议实测（2026-08-14，对抗集修正版 21 claims / 2 repeats）

协议变更：成员**必须表态**——uncertain 必须带 `likely_verdict`（否则视为弃权票，
权重 0）；聚合改为**置信度加权**（uncertain+likely 权重减半），平局/全弃权才判
uncertain（`panel.py _aggregate_checks` v1.2）。

对抗集修正（`scripts/p4_build_gold_adversarial.py` v2）：overclaim 类证据文本改为
只谈主题相关机制、不含矛盾限定词（否则模型判 contradicts 是合理的、gold=insufficient
反而错）。报告 `reports/evaluation/p4/b_panel_ab_adv_real_v5_20260814.md`：

| 指标 | 单 verifier | 评审团（ds_strong+mimo） |
|---|---|---|
| 全量不一致率 | **42.9%**（9/21） | **66.7%**（14/21） |
| 待核验率 | 0% | 0%（强制表态生效） |
| token 成本 | 4195 | 3720（×0.887，反而更低） |
| P95 延迟 | 119.9s | 49.1s |

**结论（诚实记录）**：

1. 强制表态协议按设计生效：两臂 0% 弃权。
2. **评审团不优于单 verifier**：两成员（ds_strong/mimo）对"绝对化声明 vs 温和证据"
   共享 contradicts 解读（单模型 8/13 错判、评审团 13/13 全判 contradicts，还把单模型
   判对的 5 条 insufficient 翻成 contradicts）。**评审团无法纠正成员共享的偏见**——
   加权聚合只在成员意见真正分歧时有价值。
3. gold 语义边界（insufficient vs contradicts）对"绝对化声明"存在人-模型口径差异，
   即使修正证据文本仍残留；该边界本身是评测设计难点。
4. 综合 66-claim（成本 ×1.69）与对抗集（质量不优于单模型）证据：**verification 判断点
   的评审团不具默认化理由**，维持 deep_optional。若要让评审团产生价值，需制造
   "成员意见分歧"的样本（依赖模型间知识/风格差异的模糊案例），或转向 arbitration
   （高频低误判代价判断点）验证。此方向待用户决策。

## 3.6 控制变量实验：表观差异的根因（2026-08-14）

v5 中"单 verifier 42.9% vs 评审团 66.7%"的表观差异**经控制变量实验证明是模型差异，
不是评审团机制**：

- 原 A/B 脚本（`scripts/p4_panel_ab.py`）single 臂默认用 `profile.verifier_model`
  （deepseek-v4-flash-guan），而 panel 臂用 roster 成员（ds_strong=deepseek-v4-flash-0731
  + mimo=mimo-v2.5）——两臂模型不同，混杂。
- 控制实验：`--single-preset ds_strong`（single 臂与 panel 首成员同模型），对抗集
  repeats=2 → **single 66.7% = panel 66.7%**（明细：contradicts 7/7 对，insufficient
  13/13 判 contradicts，uncertain 1/1 判 contradicts）。报告
  `reports/evaluation/p4/b_panel_ab_adv_control_20260814.md`。

**结论**：

1. ds_strong（0731）对"绝对化声明 vs 温和证据"稳定判 contradicts（与 gold 的
   insufficient 口径不同），评审团是成员判断的忠实投影——**没有放大错误，也没有纠偏**。
2. 修复：A/B 脚本已改为默认 single 臂与 panel 首成员同模型（`--single-preset` 可覆盖），
   报告标注 single 臂模型；未来所有 A/B 默认公平对照。
3. gold 语义边界（insufficient vs contradicts）仍是评测设计的灰色地带：绝对化声明
   在模型与标注者之间存在稳定口径差，需在 prompt/gold 中显式给出判定规则才能消除。

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
