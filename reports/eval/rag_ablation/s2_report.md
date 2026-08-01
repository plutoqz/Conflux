# R1 S2 — 重排消融（底座 text-embedding-v4 / 512/128，zh_zh）

| 配置 | recall@10 | recall@20 | mrr@10 | ndcg@5 | ndcg@10 |
|---|------|---|---|---|---|
| 无重排（下界） | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| LLM judge（SemanticReranker） | 1.000 | 1.000 | 0.900 | 0.926 | 0.926 |
| Cross-Encoder bge-reranker-v2-m3-free | 1.000 | 1.000 | 0.833 | 0.876 | 0.876 |
| Cross-Encoder jina-reranker-m0 | 1.000 | 1.000 | 0.883 | 0.913 | 0.913 |

时间：2026-08-01 17:14:35