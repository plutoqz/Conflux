# rag-hallucination-verification Gold（候选，已复核）

- 标注对象：真实 B4 运行 `81f14e039862`（2026-08-06，旧代码基线）。
- 复核：2026-08-07，18 条 retrieval grade + 18 条 verification verdict 逐条确认（reviewer: codex-agent-on-behalf-of-user）。
- 状态：manual_reviewed，但**仅对绑定运行有效**。

## 复用限制（重要）

1. evidence_id 绑定运行前缀（`81f14e039862:ev-XXXX`），跨运行无法匹配。
2. 子问题规划每次运行不同（2026-08-07 当前代码运行 `13c3d24470f3` 的 sq 列表与旧运行不一致）。
3. 因此本 gold 只能评估 `81f14e039862` 该次运行；评估新运行需重新标注，或升级为
   “查询级语义标注”（不绑定运行 id，按子问题语义匹配证据）。

## 已用当前代码验证的结论

- 离线验证（复用 81f14e039862 ledger）：prompt 文本记录 `ev-0002` 在当前代码下不再进入
  citation map 与生成上下文（旧代码基线中它被引用并判 supports）。
- 当前代码真实运行 `13c3d24470f3`：15 条声明仅引用 3 个合理证据，`off_domain_evidence_in_report=0`，
  检索噪声（ingestion 元数据、离题内容）未被声明引用；factcheck=passed。
- 语义离题但文本合格的记录（如旧运行的 `ev-0022`）仍可通过规则准入，属检索/验证器能力限制，
  非规则可覆盖的准入问题。

## 相关产物

- 旧代码评分：`reports/evaluation/v2_gold/rag_hallucination_candidate.json`（verdict_accuracy 0.7222）
- 当前代码运行：`reports/v2_real_gold_current/13c3d24470f3.*`
- 评分命令示例见 `scripts/eval_v2_gold.py` 头注释。
