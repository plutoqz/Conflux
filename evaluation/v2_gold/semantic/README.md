# 查询级语义 Gold（conflux-v2-gold-semantic-v1）

## 目的

解决运行绑定 gold 的复用限制（evidence_id 绑定 run_id、子问题规划每次运行不同）。
本资产按**查询语义**定义期望，任何一次 V2 运行都可用同一套资产评分。

## Schema

- `aspects[]`：语义方面
  - `aspect_id` / `aspect`：标识与人类可读描述
  - `keywords[]`：命中即部分相关（grade 2）
  - `positive_semantics[]`：命中即直接相关（grade 3），并用于 semantic_coverage
  - `expected_policy`：verify / abstain（回答覆盖检查）
- `negative_semantics[]`：全局噪声类别（prompt/指令文本、ingestion 元数据、样板、已知离题内容）
- `answer`：期望 run_status / confidence / factcheck_status

## 匹配器（确定性、可复现）

- 归一化：去标点、压缩空白、casefold（`_normalize_for_match`）。
- 证据分级：negative 命中 → 0；positive 命中 → 3；仅关键词 → 2；否则 0。
- 子问题对齐：aspect 的关键词/positive 在运行子问题文本中的命中数，取最高（≥1 才对齐），
  未对齐的 aspect 记录为 `aspect_gaps`。

## 指标

- 检索：`precision_at_k`、`irrelevant_at_k`、`semantic_coverage`（positive 命中数/总数）、`ndcg_at_k`
- 验证：`verdict_accuracy`（引用 negative 证据应判 insufficient，positive 应判 supports）、
  `negative_evidence_cited_as_support`
- 回答：`run_status/confidence/factcheck` 匹配、`aspect_coverage`、`aspect_gaps`

## 验收标准（2026-08-07 验证通过）

1. 旧运行 81f14e039862 与当前运行 13c3d24470f3 均可评分（指标不再因 id 不匹配而缺失）。
2. 负例识别有效：旧运行 `negative_evidence_cited_as_support=2`、verdict_accuracy 0.78；
   当前运行 `negative_evidence_cited_as_support=0`、verdict_accuracy 1.0。
3. 全量测试 410 通过。

## 局限（不掩盖）

- 简单匹配器召回低于人工标注：旧运行手工 grade 2 的 Hybrid-Code 证据未被 asp-1 关键词命中
  （precision 0.0），不同口径，结果需按匹配器语义解读。
- 子问题对齐可能不完美（如旧运行 asp-6 对齐到 sq-3），未对齐 aspect 显式记为 gap。
- 语义匹配不替代人工语义真值；结论强度限于“可复现近似评估”。

## 相关产物

- 资产：`evaluation/v2_gold/semantic/rag_hallucination.semantic.json`
- 评分：`reports/evaluation/v2_gold/rag_hallucination_semantic.json`
- 代码：`src/conflux/evaluation_gold.py`（`score_run_semantic` / `score_runs_semantic`）
- 测试：`tests/test_v2_gold_evaluation.py`（semantic 三例）
