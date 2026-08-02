# 阶段 R — 组件级评测数据收集 完成摘要

> 日期：2026-07-30
> 状态：框架就绪，部分需真实API运行确认

## R1: RAG 检索消融矩阵

| 项目 | 状态 |
|---|---|
| 实验方案 | `docs/plans/R1检索消融实验方案.md` ✅ |
| 脚本（旧版） | `scripts/eval_rag_ablation.py` — 待按方案重写 |
| 查询集 (zh-zh) | 待构建（基于 `data/documents/`） |
| 查询集 (zh-en) | 待构建（基于 `data/documents/papers/`） |
| 查询集 (en-en) | 待构建（同上英文 PDF） |
| 实验矩阵 | S1: 9 组（chunk×embedding） + S2: 4 组（rerank）= 13 组 |
| 指标工具 | 待引入 `ranx` 替换自写指标函数 |
| 输出 | `reports/eval/rag_ablation/` |

**实验方案概要**：分层消融，S1 在无重排下选最佳 chunk+embedding，S2 在最佳底座上对比 4 种 rerank 方法（无重排/LLM judge/bge-reranker-v2-m3-free/jina-reranker-m0）。详见 `docs/plans/R1检索消融实验方案.md`。

## R2: Web 搜索质量评测

| 项目 | 状态 |
|---|---|
| 脚本 | `scripts/eval_web_search.py` ✅ |
| 查询集 | `data/web_eval_queries.yaml` (18 题时效性查询) ✅ |
| 自动指标 | 命中率、抓取成功率、有效证据率、provider 分布 ✅ |
| 人工标注 | 相关性评分 (1-3) 模板预留，待填入 |

**运行**:
```bash
python scripts/eval_web_search.py --depth standard --k 18
```

## R3: P1 消融实验

| 项目 | 状态 |
|---|---|
| 脚本 | `scripts/eval_ablation.py` ✅ (已修复 single_agent) |
| 配置 | 3 (multi_no_arbitration / multi_arbitration / multi_full) |
| 场景 | 4 (all_success / model_fallback / web_failed / only_model) |
| 矩阵 | 3×4 = 12 组 ✅ |
| 输出 | `reports/eval/ablation.{md,json}` ✅ |

**运行**:
```bash
python scripts/eval_ablation.py
```

## R4: 端到端门禁统计

> **已终止**（2026-08-02 决定不再执行，不再列入待完成/未完成项）

| 项目 | 状态 |
|---|---|
| 脚本 | `scripts/eval_gates.py` ✅ |
| 统计维度 | Run Completion / Confidence / FactCheck / Quality / Delivery |
| V2 验证批 | 4 runs: Completion 100%, Confidence high+med 75% |
| 输出 | `reports/eval/gates/gate_stats.{md,json}` ✅ |

**运行**:
```bash
# V2
python scripts/eval_gates.py --summaries-dir reports/v2-hk-verify --pipeline v2

# P1/P1.5
python scripts/eval_gates.py --summaries-dir reports/workbench/query --pipeline p15
```

## 产出物清单

```
scripts/
  eval_rag_ablation.py          # R1: RAG 检索消融矩阵
  eval_web_search.py            # R2: Web 搜索质量评测
  eval_ablation.py              # R3: P1 消融实验 (已修复)
  eval_gates.py                 # R4: 端到端门禁统计

data/
  p1_retrieval_eval_zh.yaml     # R1: zh-zh 标签 (10 GIS 查询)
  p1_retrieval_eval_en.yaml     # R1: en-en 标签 (10 英文查询)
  web_eval_queries.yaml         # R2: 18 个时效性查询

reports/eval/
  rag_ablation/                 # R1 输出
  web/                          # R2 输出
  ablation.{md,json}            # R3 输出
  gates/                        # R4 输出
```

## 待完成项

1. **R1 完整运行**: 下载 PDF 论文或基于 markdown 文档运行 5 配置 × 2 语言
2. **R2 人工标注**: 为 18 个查询标注 1-3 分相关性

> R4（端到端门禁全量统计）已于 2026-08-02 终止，不再列入待完成/未完成项。
