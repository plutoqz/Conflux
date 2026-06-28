# 多智能体 RAG 与三源仲裁工程说明

## Retrieval-Augmented Multi-Agent Systems

Retrieval-Augmented Multi-Agent Systems 是把检索增强生成（RAG）与多智能体协作结合起来的系统形态。系统通常把一个复杂调研问题拆成若干子任务，交给 RAG Agent、Web Agent、Model Agent、FactCheck Agent 等角色并行执行，再由编排器合并结果。

核心流程包括：

- 问题分解：将用户目标拆成事实核查、背景解释、最新信息检索、风险分析等子问题。
- 并行检索：RAG Agent 查询本地知识库，Web Agent 查询互联网，Model Agent 给出模型世界知识和推理补充。
- 证据合并：将各来源输出拆成可追溯声明，构建临时 Evidence Graph。
- 冲突仲裁：对相同、单源、冲突和失败来源分别标注状态。
- FactCheck：检查关键声明是否能追溯到有效来源。
- 报告生成：主报告保持简洁，证据图、原始输出和运行摘要放入附录。

## 三源仲裁

三源仲裁指对 RAG、Web、Model 三类来源进行分层判断。只有状态为 success 的来源可以参与共识投票；failed 或 fallback 来源只能作为失败说明，不能支持事实结论。

仲裁层级：

- 多源真实共识：至少两个 success 来源支持同一关键声明。
- 单源声明：只有一个 success 来源支持，应降低置信度并明确标注。
- 工具失败后的推断：工具失败后由模型补写的内容必须标为 fallback，不得伪装成 Web 或 RAG 结果。
- 冲突声明：不同 success 来源给出相反结论时，应标为 contested，并触发 FactCheck 或人工升级。

## 工程风险

主要风险包括检索偏差、来源过时、Web 搜索超时、模型幻觉、Agent 间重复或矛盾、证据图过大、报告过长和成本不可控。

风险控制建议：

- 为每个来源记录 success、failed、fallback 状态。
- 使用相关性闸门过滤不匹配的 RAG 命中。
- 在证据图中记录 source_detail、authority_score、supporting、contradicting、derived_from 和 uncertainty。
- FactCheck 不只检查文本自洽，还应检查关键声明是否能追溯到 success 来源。
- 报告把最终结论、信息来源、不确定性、FactCheck、证据摘要和运行摘要作为固定小节。

## 落地建议

Phase 1 应先跑通 API-first 的最短路径：远程 LLM、远程 embedding、本地 Chroma RAG、Web 搜索和 Markdown/HTML 报告导出。

Phase 2 应实现 RAG Agent、Web Agent、Model Agent 并行，FactCheck Agent 验证，Evidence Graph，冲突升级协议，L4 深化研究，以及基于 SLO 的运行摘要。

在真实工程中，建议使用环境变量保存 API key，不把凭据写入仓库；使用 pytest、pip check、密钥扫描、真实端到端查询和报告验收器组成回归门禁。
