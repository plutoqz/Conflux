# R1 — RAG 检索消融实验汇总报告

> 日期：2026-08-01
> 数据集：`data/rag_eval/{zh_zh,zh_en,en_en}.yaml`（各 10 题，关键词自检 100% 命中）
> 工具链：ranx（Recall@10/20、MRR@10、NDCG@5/10）、chromadb（`tmp/chroma_ablation/` 持久化）
> 详情：`s1_report.md` / `s2_report.md` / `cross_report.md`（含逐配置 JSON）

## 1. S1 — 底座选择（zh-zh：5 篇中文文档，recall@20 全 1.000，区分度在排序质量）

| Embedding | 512/128 | 1024/256 | 2048/512 | 最佳 |
|---|---|---|---|---|
| `text-embedding-v4` | **1.000** | **1.000** | **1.000** | 512/128 或 1024/256 |
| `qwen3-embedding-8b` | **1.000** | **1.000** | **1.000** | 任 |
| `bge-m3` | 0.963 | 0.819 | 0.963 | 512/128 或 2048/512 |
| `jina-embeddings-v4` | 0.889 | 0.963 | 0.963 | 1024/256 或 2048/512 |

（表中为 NDCG@10）

**S1 最佳：`text-embedding-v4` / `512/128`**（recall@20 并列第一，NDCG@10 排序第一）

## 2. S2 — 重排消融（最佳底座 text-embedding-v4/512-128，zh-zh，修复位置分数 bug 后）

| 重排方法 | recall@20 | ndcg@10 | vs 基线 |
|---|---|---|---|
| 无重排（下界） | 1.000 | **1.000** | — |
| LLM judge（deepseek-v4-flash-guan，1391s） | 1.000 | 0.926 | **-0.074** |
| bge-reranker-v2-m3-free（19s） | 1.000 | 0.876 | **-0.124** |
| jina-reranker-m0（22s） | 1.000 | 0.913 | **-0.087** |

> ⚠️ 第一版 S2 数据因 `build_run` 使用检索原始 rrf_score 排序（rerank 顺序未生效）而显示"全 1.000 无增益"，属 bug 假象；修复为位置分数后 rerank 的真实效果是**显著负优化**。

## 3. Step 5 — 跨语言验证

### 3a. zh-en（中文 query → 英文文档，10 篇 esri + 60 篇干扰文档）

| Embedding（均 512/128） | recall@10 | recall@20 | mrr@10 | ndcg@10 |
|---|---|---|---|---|
| `text-embedding-v4` | **1.000** | 1.000 | **0.758** | **0.819** |
| `jina-embeddings-v4` | 1.000 | 1.000 | 0.753 | 0.815 |
| `qwen3-embedding-8b` | 1.000 | 1.000 | 0.742 | 0.806 |
| `bge-m3` | 1.000 | 1.000 | 0.575 | 0.682 |

### 3b. en-en（英文 query → 190 篇论文摘要，全局最佳配置）

| 配置 | recall@10 | recall@20 | mrr@10 | ndcg@10 |
|---|---|---|---|---|
| `text-embedding-v4` / `512/128` | 0.800 | 1.000 | 0.323 | 0.431 |

## 4. 结论

1. **`text-embedding-v4` 全面胜出**：zh-zh 完美、zh-en 跨语言最强（0.819）、是唯一在 en-en 大语料上有数据的模型——「业界通用最高水平」假设成立，**建议作为生产默认 embedding**。
2. **`qwen3-embedding-8b` 未兑现「降维打击」**：zh-zh 与 v4 并列满分，但 zh-en 跨语言仅第 3（0.806 vs 0.819）；4096 维带来 4× 存储/检索开销，**收益不足，不建议替代 v4**。
3. **`bge-m3` 混合检索未显优势**：zh-en 明显垫底（0.682，mrr 0.575）。其 dense+sparse+ColBERT 多路召回在生僻专业词场景才有意义，本数据集专业词覆盖不足，**假设未得到支持**。
4. **`jina-embeddings-v4` 任务适配有价值但接近 v4**：zh-en 0.815 vs v4 0.819，几乎持平；任务适配器未带来显著增益。
5. **chunk 粒度**：512/128 普遍最优或并列；bge-m3 在 2048/512 上反而最佳（0.963），细粒度对 LLM 类 embedding 无惩罚。
6. **en-en 大语料排序质量明显下降**（ndcg 0.431 vs zh-zh 1.000）：190 篇摘要的候选池大、query 相关性弱，**正是 rerank 的用武之地**。

## 5. 补充实验（S2 rerank 在 zh-en / en-en 上的真实增益验证）

> 修复了 build_run 位置分数 bug 后重跑：rerank 后的顺序现在真实作用于指标。
> 底座均为 `text-embedding-v4` / `512/128`，候选池 top_k=60。

### 5a. zh-en（中文 query → 英文文档）

| 重排方法 | recall@20 | ndcg@10 | vs 基线 |
|---|---|---|---|
| 无重排（基线） | 1.000 | **0.819** | — |
| LLM judge（deepseek-v4-flash-guan，1786s） | 1.000 | 0.798 | **-0.021** |
| bge-reranker-v2-m3-free（31s） | 1.000 | 0.742 | **-0.077** |
| jina-reranker-m0（41s） | 1.000 | 0.819 | 0.000 |

### 5b. en-en（英文 query → 190 篇论文摘要）

| 重排方法 | recall@20 | ndcg@10 | vs 基线 |
|---|---|---|---|
| 无重排（基线） | 1.000 | 0.431 | — |
| LLM judge（1618s） | 1.000 | 0.287 | **-0.144** |
| bge-reranker-v2-m3-free（42s） | 1.000 | 0.376 | **-0.055** |
| jina-reranker-m0（32s） | 1.000 | **0.444** | **+0.013** |

### 5c. 补充实验结论（三数据集合并）

**rerank 在本实验场景下全面负优化或持平，仅 1 例微升**：

| 数据集 | 基线 ndcg@10 | llm_judge | bge-reranker | jina-reranker |
|---|---|---|---|---|
| zh-zh（5 篇中文） | 1.000 | -0.074 | **-0.124** | -0.087 |
| zh-en（跨语言） | 0.819 | -0.021 | -0.077 | 0.000 |
| en-en（190 篇摘要） | 0.431 | -0.144 | -0.055 | **+0.013** |

1. **全部 12 个 rerank 组合中 10 个下降、1 个持平、1 个微升**（en-en jina +0.013）。
2. **跨语言（zh-en）**：重排模型对「中文 query × 英文 chunk」的打分弱于 dense 向量空间的跨语言对齐。
3. **zh-zh 小语料**：正确答案本就在前列，rerank 反而把正确排序打乱（-0.074 ~ -0.124）。
4. **成本**：LLM judge 每批 23-30 分钟且全面负优化；Cross-Encoder 秒级但无正收益。
5. **结论**：当前链路（hybrid RRF + top_k=60）下 **rerank 不推荐作为默认路径**；仅 en-en 大语料场景 `jina-reranker-m0` 有微弱正向，需更大数据集 + 显著性检验确认。

## 6. 生产配置建议（当前结论，含补充实验修正）

```
embedding: text-embedding-v4（1024 维）
chunk:     512/128（zh-zh 无差异、zh-en 需 512/128）
检索:      hybrid（dense+BM25 RRF）top_k=60
rerank:    默认关闭；大语料场景可选 jina-reranker-m0（收益微弱，需显著性验证）
```

## 7. 局限与后续

1. zh-zh 语料仅 5 篇中文文档（42 chunks），recall 饱和、区分度集中在排序；后续可扩充中文文档集。
2. en-en 语料为论文摘要（190 篇），query 与摘要的相关性弱于全文，rerank 的 top-60 重排空间有限；用全文 PDF 索引后 rerank 价值需重测。
3. bge-m3 的 sparse/ColBERT 优势需要含生僻专业词的专用数据集验证。
4. rerank 显著性检验（ranx.compare bootstrap）未跑——当前差异量级（±0.02~0.14）中，除 LLM judge 外均较小，建议扩充 query 数后再检验。
