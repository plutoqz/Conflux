# 召回 Cap 网格实验（2026-08-09）

目的：验证“扩大 LLM 评审池是否提升 strong_recall”，并记录
recall / precision / nDCG / token 的帕累托关系。

## GIS（99 候选快照，pointwise cap40 为 3 次中位数基线）

| 配置 | recall@10 | precision@5 | nDCG@10 | strong_recall@20 | strong_success@1 | tokens | calls |
|---|---|---|---|---|---|---|---|
| pointwise cap40（median） | 0.4286 | 0.8 | 0.5739 | 0.5 | 2/3 | 43,420 | 40 |
| listwise cap60（单次） | 0.3571 | 0.4 | 0.4563 | 0.5 | 0/1 | 42,852 | 8 |
| listwise cap80（median） | 0.3571 | 0.6 | 0.4476 | 0.75 | 1/3 | 51,815 | 10 |
| pointwise cap80（单次） | 0.4286 | 0.6 | 0.4476 | 0.5 | 0/1 | 73,409 | 73 |
| listwise cap100（单次） | 0.2143 | 0.6 | 0.2987 | 0.5 | 0/1 | 56,373 | 10 |

GIS 结论：cap80 listwise 把 strong_recall@20 中位数从 0.5 提到 0.75，
但 nDCG、precision@5 和 recall@10 下降；pointwise cap80 没有提升 strong_recall。
cap100 整体恶化，不建议。

## KG（136 本地候选，provisional 初标，单次运行）

| 配置 | recall@10 | precision@10 | nDCG@10 | strong_recall@20 | strong_recall@40 | tokens | calls |
|---|---|---|---|---|---|---|---|
| pointwise cap40 | 0.1493 | 1.0 | 0.7838 | 0.3333 | 0.5778 | 50,762 | 40 |
| listwise cap60 | 0.1493 | 1.0 | 0.8810 | 0.3111 | 0.5778 | 38,170 | 8 |
| listwise cap80 | 0.1493 | 1.0 | 0.8731 | 0.2889 | 0.5778 | 51,800 | 10 |
| listwise cap100 | 0.1493 | 1.0 | 0.8424 | 0.3111 | 0.5111 | 64,306 | 13 |
| pointwise cap100 | 0.1493 | 1.0 | 0.9184 | 0.3778 | 0.6000 | 122,671 | 100 |
| listwise cap120 | 0.1493 | 1.0 | 0.8210 | 0.2889 | 0.5778 | 78,871 | 15 |

KG 结论：单纯扩评审池（listwise）没有提升 strong_recall@20；
pointwise cap100 单次运行质量最高（nDCG 0.9184、strong_recall@20 0.3778），
但 token 成本约 2.4 倍。listwise cap60 是当前成本/质量折中较好的点。

## 总体判断

- 不存在单一全局最优 Cap；GIS 和 KG 的分数分布与 LLM 排序行为不同。
- 扩池能提高“进入评审池的强相关数量”，但能否进 Top-20 仍取决于 LLM 排序。
- 推荐按领域配置：
  - GIS：默认保持 pointwise cap40；若优先 strong recall，可切 listwise cap80。
  - KG：成本敏感用 listwise cap60；质量优先用 pointwise cap100，并需 3 次运行确认。
- 所有 KG 指标基于 provisional 初标和单次运行，正式结论前需补多次运行与人工复核。

## 2026-08-09 多次运行修正（reviewed labels）

KG 领域补做标注复核与多次运行：136 篇初标经 Codex 复核（2 处 R3→R2），
`pointwise cap40` 与 `listwise cap60` 各 3 次真实评审中位数：

| 配置 | recall@10 | precision@10 | nDCG@10 | strong_recall@20 | strong_success@1 | tokens | calls |
|---|---|---|---|---|---|---|---|
| 无 LLM 粗排（确定性） | 0.1493 | 1.0 | 0.9621 | 0.3488 | 3/3* | 0 | 0 |
| pointwise cap40（median） | 0.1493 | 1.0 | 0.9581 | 0.3256 | 3/3 | 48,228 | 40 |
| listwise cap60（median） | 0.1493 | 1.0 | 0.9217 | 0.3488 | 3/3 | 40,664 | 8 |

修正后结论：多次运行下 `listwise cap60` 的 strong_recall@20 中位数不劣于
`pointwise cap40`（0.3488 vs 0.3256），调用数降至 1/5、token 省约 15%；
`pointwise cap40` 的 nDCG 更高。KG 领域成本敏感默认可考虑 listwise cap60，
质量优先保持 pointwise cap40/100 并做多次确认。正式结论仍需用户终审标注与
hold-out 验证。

*无 LLM 粗排为确定性运行，strong_success@1=3/3 按该次排序等价于 3 次中位数口径。

补充：无 LLM 粗排在 KG 高密度本地池上 nDCG 与 strong_recall 均不低于 LLM 评审，
说明 LLM 评审收益是 GIS/arXiv 稀疏场景结论。另做了分领域向量库模拟（136 KG 论文
+ 29 跨域文档），Top-25 无跨域文档、跨域文档最早第 100 名，按领域拆库在当前
embedding 粗排下收益很小；更优先的是“论文 vs 通用资料”来源分层与索引覆盖补全。
