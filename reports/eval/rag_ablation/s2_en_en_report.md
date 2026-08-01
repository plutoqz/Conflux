# R1 S2 — 重排消融（底座 text-embedding-v4 / 512/128，en_en）

| 配置 | recall@10 | recall@20 | mrr@10 | ndcg@5 | ndcg@10 |
|---|------|---|---|---|---|
| 无重排（下界） | 0.800 | 1.000 | 0.323 | 0.343 | 0.431 |
| LLM judge（SemanticReranker） | 0.700 | 1.000 | 0.161 | 0.225 | 0.287 |
| Cross-Encoder bge-reranker-v2-m3-free | 0.700 | 1.000 | 0.267 | 0.376 | 0.376 |
| Cross-Encoder jina-reranker-m0 | 0.800 | 1.000 | 0.338 | 0.313 | 0.444 |

时间：2026-08-01 16:49:36