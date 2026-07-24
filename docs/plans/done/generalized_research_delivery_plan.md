# 泛化研究可交付质量收敛方案

> 文档状态：实现及离线合同完成（2026-07-21 已完成 WP1-WP6；WP7 评测框架与 12 题代表集已完成，真实连续三批退出线待验收）。**P1.5 管线已被 V2 answer_first 部分取代为默认管道**（config.yaml pipeline: answer_first）；P1.5 仍可通过 `pipeline: p15` 使用。12 题代表集和评审框架已迁移为 V2 评估基建的复用基础。
>
> 适用范围：P1.5 泛化研究管线及其 Standard/Deep 真实运行
>
> 目标：将“协议完整、能够落盘”的泛化研究管线收敛为“内容正确、证据匹配、结构有效、可以交付”的研究报告生产能力
>
> 基线运行：`6ef2529e34a3`，查询“GIS处理自动化研究目前有哪些瓶颈？”

> 2026-07-21 实施复核：覆盖矩阵已升级为 `dimension x required_action`；运行预算已增加阶段硬保留、实际/扣减 Token 双账本和角色遥测；章节综合已改用可持久化 `SectionEvidencePack`，未核验章节不得参与跨维度综合；WP7 提供 12 题代表集、盲评量表、批次退出判断和连续三批判断。离线全量回归为 `490 passed`。这些结果证明实现合同成立，不替代尚未完成的真实内容盲评。

## 1. 成功定义

本方案不以报告已生成、章节齐全、来源状态为 `success`、引用编号有效或运行未超时作为成功。一次运行只有同时通过以下四层门禁，才允许成为正式研究报告：

1. **问题覆盖**：研究范围、核心维度和用户要求得到实质回答，不以标题、占位段落或缺口声明代替覆盖。
2. **证据正确**：外部事实由直接相关、可定位的正文证据支撑；引用存在不等于引用支持声明。
3. **分析充分**：报告解释机制、影响、边界、比较、案例或实现细节，并区分外部事实、模型分析和建议。
4. **核验完成**：关键声明经过语义核验；严重问题已修订或降级，未完成核验的结果不得作为正式报告交付。

正式交付物分为三种状态：

| 状态 | 含义 | 用户可见行为 |
| --- | --- | --- |
| `deliverable` | 四层门禁全部通过 | 进入正式报告列表，可导出 Markdown/HTML |
| `limited` | 结论有价值，但存在明确且非关键的证据缺口 | 可展示和导出，标题与正文显著标注“有限证据报告” |
| `diagnostic_only` | 规划、证据相关性、核心覆盖或核验失败 | 只进入运行诊断，不作为正式研究报告 |

超时不再自动等价于失败，但超时降级结果必须重新经过相同的交付门禁。系统不得因为成功写出文件而把 `diagnostic_only` 包装成正式报告。

## 2. 当前基线与根因

基线运行在 220 秒内完成并满足 240 秒 SLO，但不具备交付条件：

- Planner 超时后使用通用维度，领域地图退化为“范围、机制、实施、评估”等研究动作，而不是 GIS 自动化的真实问题地图。
- SourcePlan 查询没有稳定携带原始问题和领域锚点，RAG 召回通用 Deep Research、多智能体透明度、社会科学和 Kubernetes 论文。
- Model Analyst 因异常 Token 预留被拒绝，错误证据未经过语义分析和纠偏。
- 覆盖矩阵把有正文、高权威标签的错域证据计为已覆盖，没有检查主题相关性和声明蕴含关系。
- 覆盖循环在整体覆盖率约 0.38 时因迭代预算结束；第四节综合超时，全局综合被截止时间跳过。
- FactCheck 只报告 36.4% 的声明引用覆盖，没有修订正文，但结果仍写入正式报告目录。
- 丰富度评分通过章节长度和关键词命中得到 4.88/5，与 `high_importance_coverage=0`、`passed=false` 和人工观感冲突。

这是一条级联失败链：

```text
规划超时
  -> 通用维度替代领域地图
  -> 检索丢失领域锚点
  -> 错域证据进入候选池
  -> 分析调用被预算拒绝
  -> 覆盖启发式误判
  -> 合成扩写错误证据
  -> 核验无时间修订
  -> 不合格结果正式落盘
```

因此，本轮不得只调整 Prompt、增加报告字数或提高搜索次数。必须同时修复领域约束、证据语义门禁、预算调度、核验闭环和交付状态。

## 3. 目标流程

```text
Query Intake
  -> Scope Contract
  -> Domain Discovery
  -> Plan Validation Gate
  -> Anchored Breadth Retrieval
  -> Evidence Relevance and Entailment Gate
  -> Coverage Matrix
  -> Gap-directed Depth Research
  -> Section Evidence Pack
  -> Section Synthesis and Verification
  -> Cross-section Synthesis
  -> Claim-level FactCheck and Revision
  -> Delivery Gate
  -> Formal Report or Diagnostic Artifact
```

流程遵循五条约束：

1. 原问题的研究对象、限定词、时间范围和用户意图必须贯穿规划、检索、证据判断和综合。
2. 检索结果先证明“与该研究对象直接相关”，再判断能否支持某个声明。
3. 覆盖状态由问题动作和有效证据共同决定，不由章节是否存在决定。
4. 时间和 Token 预算优先保障规划、证据判定、最终综合与核验，重复检索和低价值扩写先降级。
5. 任何质量分都不能绕过硬门禁。

## 4. 工作包

### WP1：范围契约与领域锚定

目标是保证规划降级后仍然围绕用户真正询问的对象研究。

实施项：

- 新增 `ScopeContract`，至少记录 `subject`、`task`、`scope_inclusions`、`scope_exclusions`、`time_scope`、`audience`、`required_entities` 和 `ambiguities`。
- 中文概念提取不得把“GIS处理自动化研究目前有”作为单一概念；需产生 `GIS`、`地理处理自动化`、`GeoAI agent` 等可检索锚点。
- Planner 成功时，验证每个维度与 `ScopeContract.subject` 的关联；Planner 超时时，先生成带领域锚点的保守维度，不直接使用脱离研究对象的通用章节。
- 每个 SourcePlan 查询使用结构化组合：`subject anchors + dimension + research action + evidence type/time scope`。
- 补证查询同样携带 ScopeContract，不允许只搜索“局限、失败模式、开放问题”等通用词。

主要代码：

- `src/conflux/research_protocol.py`
- `src/conflux/research_generalization.py`
- `src/conflux/graph_p15.py`

验收：

- 7 个领域、7 类问题原型的所有查询均保留至少一个研究对象锚点。
- Planner 超时夹具仍能生成领域相关维度，不出现纯通用四段模板。
- GIS 基线问题的 RAG 前 10 个候选中，直接相关文档比例不低于 0.8；GeoNatureAgent、GIS Copilot、Autonomous GIS 等已入库直接证据能够被召回。

### WP2：证据相关性、蕴含与来源身份门禁

目标是阻止“标题含 limitations 但研究对象不同”的证据进入覆盖矩阵和正文。

每个 EvidenceItem 增加以下判定：

- `domain_relevance`：证据是否直接讨论 ScopeContract 中的研究对象。
- `claim_entailment`：原文是否支持目标声明，而不是只能用于类比。
- `evidence_role`：`direct_support`、`boundary`、`counterexample`、`analogy` 或 `discovery_only`。
- `source_identity`：题名、作者、年份、来源类型、稳定标识和正文定位是否完整。
- `independence_key`：按论文、标准、官方页面或数据集去重，不把同一论文的不同页计算为独立来源。

确定性门禁：

- `domain_relevance < 0.7` 不得作为直接事实证据。
- `claim_entailment < 0.7` 不得将引用绑定到目标声明。
- 类比证据只能支持显式标注的分析推导，不能把通用结论改写成领域事实。
- 抓取正文包含导航、推荐文章列表或明显页面噪声时标记 `body_invalid`。
- 来源元数据为 `unknown` 时可以暂存，但不得被自动提升为高权威证据。

主要代码：

- `src/conflux/evidence.py`
- `src/conflux/rag/reranker.py`
- `src/conflux/quality.py`
- `src/conflux/citation_compiler.py`

验收：

- 四篇基线错域论文全部被标记为 `analogy` 或 `discovery_only`，不得计入 GIS 核心维度覆盖。
- DOI 页面推荐内容串被拒绝为正文证据。
- 同一论文两页只计一个独立来源。
- 人工标注 claim-evidence 集上的相关性 Precision 不低于 0.90，直接支持关系 Precision 不低于 0.90。

### WP3：覆盖矩阵与研究停止条件重构

目标是让覆盖反映“回答了什么”，而不是“产出了多少文本”。

实施项：

- CoverageRow 改为 `dimension x required_action` 二维状态，动作至少包括范围、限制、机制、影响、边界、缓解和开放问题。
- 每个已覆盖单元必须绑定一个有效外部 EvidenceItem 或一个明确标注的 Model analysis；高风险事实不能由 Model-only 覆盖。
- `high_importance_coverage` 只统计已通过证据门禁的实质单元。
- 章节标题、占位文本、缺口声明和重复引用不增加覆盖率。
- 固定迭代次数只作为硬上限，不作为质量停止条件；未达门槛时应进入 `limited/diagnostic_only`，而不是伪装成完整报告。
- 缺口优先级同时考虑重要性、当前证据、用户意图、研究风险和获取成本。

主要代码：

- `src/conflux/research_generalization.py`
- `src/conflux/graph_p15.py`
- `src/conflux/quality.py`

验收：

- 基线报告的高重要性覆盖不得因四个章节存在而得到满分。
- 删除正文、仅保留标题与缺口说明时，维度覆盖分必须低于 2/5。
- Deliverable 报告的高重要性动作覆盖率不低于 0.85，所有核心维度均有至少一条直接外部证据。

### WP4：运行预算与降级策略

目标是在硬时限内优先完成决定报告可信度的步骤。

预算分为不可挪用和弹性两部分：

| 阶段 | Standard 最低保留 | Deep 最低保留 | 策略 |
| --- | ---: | ---: | --- |
| 规划与范围校验 | 30 秒 | 45 秒 | 失败后只允许一次短修复调用 |
| 证据语义判定 | 35 秒 | 60 秒 | 可批量，不能因检索载荷膨胀整体跳过 |
| 章节与全局综合 | 60 秒 | 100 秒 | 先完成核心章节，再完成全局综合 |
| FactCheck 与修订 | 40 秒 | 70 秒 | 不得被前序步骤耗尽 |
| 提交与产物 | 15 秒 | 20 秒 | 仅做确定性编译和写入 |

实施项：

- Token 预算按真实消息负载和角色最大输出计算；修复 `next call reserves 114880 tokens` 一类异常预留。
- 对证据载荷按章节、来源和声明压缩，禁止把整份 90KB RAG 返回重复发送给每个角色。
- 章节综合按优先级执行；剩余时间不足时停止低重要性章节，不牺牲全局综合和 FactCheck。
- 模型超时后不得立即重复同等长度调用；使用短 JSON 修复、模型 fallback 或确定性降级。
- 记录每个阶段的计划预算、实际耗时、输入/输出 Token、排队时间和降级原因。

主要代码：

- `src/conflux/model_factory.py`
- `src/conflux/research_modes.py`
- `src/conflux/graph_p15.py`

验收：

- Standard 240 秒内为 FactCheck 保留至少 35 秒实际可用窗口。
- Planner、Analyst 或单章节超时均有独立真实/录制回归，最终状态与质量一致。
- 不再出现预算充足但因单次保守预留大于全局上限而跳过 Analyst 的情况。

### WP5：证据包驱动的章节综合

目标是让每节围绕问题和证据写作，而不是围绕模板词扩写。

每个 `SectionEvidencePack` 必须包含：

- 需要回答的具体问题和研究动作。
- 允许使用的直接证据、边界证据和反例。
- 已验证声明及其逐条引用。
- 必须区分的概念、范围和时间口径。
- 已有缓解方案、适用条件和仍未闭合的缺口。
- 禁止写入的无证据强事实。

综合顺序：

1. 先生成一句直接结论。
2. 展开形成机制和实际影响。
3. 给出定量结果、代表案例或实现细节。
4. 比较不同条件下的差异与取舍。
5. 说明已有缓解、边界和开放问题。
6. 章节核验通过后，才能参与跨维度综合。

主报告不得暴露 `dim-*`、`assess_impact` 等内部协议字段；技术性覆盖缺口进入简洁的人类可读说明，完整状态保留在审计报告。

验收：

- 直接回答必须列出主要结论和必要范围，不能重复问题。
- 跨维度综合必须至少表达两种真实关系，如依赖、权衡、共同根因或替代，不能只说“这些维度相关”。
- 参考文献必须显示题名、作者/机构、年份、来源类型和定位，不再以裸文件名加 `unknown` 作为正式条目。
- 置信度附录以报告关键声明为行，不得以截断原文片段代替声明。

### WP6：FactCheck 修订闭环与交付门禁

FactCheck 从“报告问题”改为“决定是否交付并实际修改输出”。

检查项：

- 声明是否属于外部事实、分析推导、建议或开放问题。
- 引用是否直接支持声明，来源是否相关、独立且可定位。
- 数字、日期、比较、因果和“首个/最佳/普遍”等强措辞是否得到充分证据。
- 高重要性维度是否缺失，是否存在错域证据、冲突或时间口径不一致。
- 直接回答是否与正文和证据一致。

修订策略：

- `citation_missing`：补证或将事实改为清晰的分析判断。
- `citation_mismatch`：替换证据、收窄声明或删除。
- `missing_dimension`：定向补证并只重写受影响章节。
- `overclaim`：降低措辞并披露边界。
- `critical_conflict`：保留分歧，不生成单一确定结论。

交付硬门禁：

- FactCheck 不得为 `failed` 或 `not_run`。
- 关键外部声明有效引用覆盖率不低于 0.90。
- 关键声明 citation entailment Precision 不低于 0.90。
- 无效引用和失败来源泄漏均为 0。
- 核心维度不得存在 `evidence_scarce`；若用户要求的是证据综述，可输出明确的“证据不足”结论，但必须证明检索范围充分。
- 严重问题未修订时状态必须为 `diagnostic_only`。

主要代码：

- `src/conflux/graph_p15.py`
- `src/conflux/quality.py`
- `src/conflux/report.py`
- `src/conflux/workbench/jobs.py`

### WP7：评测体系与真实盲评

现有机械评分保留用于格式、安全和协议诊断，不再作为内容质量的主要证明。

评测分三层：

1. **确定性门禁**：引用可解析、来源状态、覆盖矩阵、预算、Prompt Injection、报告状态和产物一致性。
2. **语义标注集**：领域相关性、claim-evidence 蕴含、维度覆盖和强措辞正确性。
3. **匿名盲评**：与 P1、可信人工参考或外部 Deep Research 报告成对比较。

真实代表集首轮采用 12 个问题，不批量跑满全部离线矩阵：

| 组合 | 数量 |
| --- | ---: |
| 宽泛综述/局限问题 | 3 |
| 技术比较/方案设计 | 3 |
| 因果机制/证据综述 | 2 |
| 近期状态问题 | 2 |
| RAG 空库但 Web 可用 | 2 |

至少覆盖 GIS/GeoAI、软件工程、医学或生命科学、政策治理、材料或能源、数据系统六个领域。每个问题保留原始产物、provider/model、耗时、Token、费用、失败和降级记录。

盲评核心维度：

- 事实正确性与引用匹配。
- 研究范围和重要维度覆盖。
- 机制深度与因果严谨性。
- 定量证据、案例和实现细节。
- 比较综合、边界条件和洞察增量。
- 结构、可读性和对用户决策的价值。

退出线：

- 12 个代表问题中至少 10 个达到 `deliverable`，其余最多为 `limited`，不得出现错域证据进入正式报告。
- 人工/匿名盲评中位数不低于 4/5，任一核心维度不得低于 3/5。
- 相对 P1 同题基线，广度、深度、证据正确性、综合洞察四项至少三项显著胜出，且无一项显著退化。
- Standard 不得系统性遗漏重要维度；Deep 的首要产出质量中位数不低于 4/5。
- 三次连续真实批次达到退出线后，才将 P1.5 标记为真实内容质量验收完成。

## 5. 实施顺序

| 阶段 | 工作 | 依赖 | 完成标志 |
| --- | --- | --- | --- |
| A | WP1 范围契约和查询锚定 | 无 | 基线错域召回显著下降 |
| B | WP2 证据语义门禁 | A | 错域证据不能进入覆盖和正文 |
| C | WP3 覆盖矩阵重构 | B | 覆盖分与人工判断一致 |
| D | WP4 预算与降级修复 | A-C | 核验得到真实保留窗口 |
| E | WP5 章节综合 | B-D | 章节由证据包驱动且可读 |
| F | WP6 FactCheck 与交付门禁 | C-E | 不合格产物不进入正式报告 |
| G | WP7 真实代表评测 | A-F | 连续三批达到退出线 |

每个阶段先补失败测试，再修改实现；A-F 未完成前不以增加真实 API 调用次数寻找偶然成功。完成 F 后先运行 3 个最小代表问题，确认结构性故障关闭，再扩展到 12 个问题。

## 6. 测试与产物

新增或扩展测试：

- `tests/test_p1_5_scope_contract.py`
- `tests/test_p1_5_evidence_semantics.py`
- `tests/test_p1_5_delivery_gate.py`
- `tests/test_p1_5_budget_reserve.py`
- `tests/test_p1_5_report_quality.py`
- `tests/test_real_query_regressions.py`

新增评测数据：

- 直接相关、相邻相关和错域证据三分类夹具。
- claim-evidence 支持、限制、反驳、类比和无关五分类夹具。
- Planner/Analyst/Section/FactCheck 分阶段超时录制。
- 基线 GIS 问题的直接证据黄金集合和不应入选集合。
- 12 个真实代表问题及盲评 Rubric。

每次真实评测输出：

- 正式报告或诊断产物。
- ScopeContract、DomainMap、SourcePlan、CoverageMatrix 和 SectionEvidencePack。
- 声明到证据的蕴含判定及人工抽查结果。
- 交付门禁逐项结果。
- 阶段耗时、Token、费用和降级记录。
- 与 P1/参考报告的匿名盲评结果。

## 7. 发布、回滚与状态管理

- 新流程通过 `research.generalization.delivery_gate` 功能开关启用。
- 开发期默认同时生成新旧质量判定，正式报告只服从新交付门禁。
- 新门禁误杀时可以回退到 P1 管线，但不得关闭门禁后继续把已知不合格 P1.5 结果标为正式报告。
- Workbench 分开展示“正式报告”“有限证据报告”和“运行诊断”，旧报告不自动改写状态。
- P1.5 状态在真实退出线达成前继续保持“实现及离线合同完成、真实内容质量未验收”。
- 本方案不启动 P2、M3 或跨运行 Evidence Ledger，不修改永久知识库审批边界。

## 8. 优先级与预期结果

最高优先级是 WP1、WP2、WP4 和 WP6。它们分别关闭本次事故的四个决定性漏洞：检索丢失研究对象、错域证据被接受、核验预算被耗尽、不合格结果正式交付。

执行完成后，Conflux 应具备以下可观察行为：

1. 泛化规划成功时形成领域特定的问题地图；规划失败时仍保持研究对象不丢失。
2. 通用 AI 或其他领域论文不能因为包含“limitations”而支撑 GIS、医学或政策领域事实。
3. 每个主要结论都能回溯到直接相关正文，分析类比得到明确标注。
4. 覆盖不足会触发补证、有限报告或诊断状态，不会由章节长度掩盖。
5. 最终报告直接回答问题，包含机制、证据、影响、边界、缓解和开放问题，并具有可用的参考文献元数据。
6. FactCheck 有时间、有权限也有责任改变正文和交付状态。
7. “可交付”由真实语义质量和盲评证明，不再由结构完整或未超时推定。

## 9. 本轮收尾执行记录（2026-07-21）

本轮在 A-F 实现合同与 WP7 评估框架基础上，继续关闭真实运行暴露的剩余结构性问题：

- 证据冲突仲裁输入限制为最多 10 个冲突、20 条压缩证据，优先保留冲突直接引用的证据；仲裁获得独立的最小调用窗口，不再因整表载荷造成 Token 拒绝。
- Analyst 新发现维度必须与 `ScopeContract` 的 subject、required entities 或 inclusions 存在真实词汇锚定；模型自报高重要性或 inclusion reason 不得绕过领域门禁，合并后重新执行 `anchor_domain_map()`。
- Planner 的运行时保留在全部角色模型初始化完成后计算，补偿初始化消耗，避免配置为 25 秒但真实只获得 3-16 秒。
- Planner 输出上限收紧为 2400 tokens，prompt 只保留 `scope_contract`、`query_archetype`、`domain_map` 和 `model_prior`，去除与上述结构重复的 `research_strategy`、`claims` 载荷；同时要求 JSON 小于 6000 字符、每个维度最多两个研究问题，以降低完整 25 秒窗口内仍超时的概率。
- Web 查询规划拒绝 `current model` 一类丢失主题的部分翻译；`model/模型` 不再单独触发学术检索，避免政策问题被路由到医学或统计学同名文献。
- WP7 CLI 会自动创建输出父目录；前三个真实样例已固化到 `reports/evaluation/minimal-representative-batch.json`。

真实复测 `cd0ba36a3b9e` 在 174.5 秒内完成并被正确标记为 `diagnostic_only`。该轮验证了错域证据未进入正式报告、仲裁不再发生 Token 预算拒绝，但也暴露出检索英译退化为 `current model`、Planner 初始化后窗口仍不足等问题。

后续真实复测 `9778c773fb28` 在 162.2 秒内完成并仍被正确标记为 `diagnostic_only`。Planner 已获得完整约 25 秒窗口，`current model` 错误查询完全消失，Web 错域结果由错误的 `success` 降为 `low_relevance`，FactCheck 语义核验也正常完成；但 Planner 仍超时、Analyst 在约 35 秒超时，且政策题没有取得可通过门禁的外部证据（`gate_eligible_external_evidence=0`），因此没有生成正式报告。针对 Planner 的最后一项负载精简已完成，尚待新真实运行验证。

最终离线状态为 `491 passed`，`python -m compileall -q src tests` 和 `git diff --check` 均通过。

发布状态仍保持“实现及离线合同完成、真实内容质量未验收”。`minimal-representative-batch.json` 只有 3 个样例且均为 `diagnostic_only`，不能替代 12 题完整批次、盲评和连续三批退出线；最终代码还需要在后续真实批次中验证 Planner 负载精简的时延收益，以及领域特定查询规划对真实召回的改善。
