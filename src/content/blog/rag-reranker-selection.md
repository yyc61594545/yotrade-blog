---
title: RAG Reranker 选型与评测：什么时候值得加一层重排
description: 系统梳理主流 Reranker 方案（Cohere Rerank、BGE-Reranker、Voyage Rerank、LLM 重排）的选型标准、延迟成本与评测方法，判断你的 RAG 系统是否真的需要重排。
keywords:
  - RAG Reranker
  - 重排模型选型
  - Cohere Rerank
  - BGE Reranker
  - RAG 检索优化
pubDate: '2026-09-10'
updatedDate: '2026-09-10'
canonical: https://blog.yotradeapi.com/blog/rag-reranker-selection/
tags:
  - RAG
  - Reranker
  - 检索优化
  - 应用工程
category: 应用工程
---

很多 RAG 系统调优到最后，会有人建议"加个 Reranker 试试"，但少有人先问一句：这一层到底解决什么问题、值不值得为它多付一次调用延迟和费用。Reranker 不是免费的精度提升，它是用延迟和成本换召回精度的权衡工具。这篇文章把选型和评测标准讲清楚，帮你判断该不该加、加哪个。

## 一、Reranker 解决的是什么问题

向量检索（含 [Hybrid Search 权重调优实战](/blog/rag-hybrid-search-tuning/) 里讲的融合检索）返回的是"粗排"结果——用向量相似度或关键词匹配快速从几万到几百万文档里捞出 Top 50~100 候选。这一步追求的是召回速度和覆盖率，不追求精排准确率，代价是候选里混杂大量"看起来相关，实际不是最佳答案"的文档。

Reranker 的角色是"精排"：拿粗排的 Top N 候选，用一个更强、但更慢的模型对 query-document 对逐一打分，重新排序后只保留 Top K（通常 K 远小于 N）送进生成阶段。它不负责召回，只负责在已经召回的候选里把顺序排对。

**判断该不该加的第一个标准很简单**：如果你的粗排 Top 5 命中率已经很高（比如 90% 以上正确答案文档排进了前 5），加 Reranker 收益有限；如果 Top 5 命中率一般但 Top 30 命中率不错，说明正确答案"在候选里但排序靠后"，这正是 Reranker 最擅长解决的场景。

## 二、主流 Reranker 方案分类

| 类型 | 代表 | 特点 |
|---|---|---|
| Cross-Encoder API | Cohere Rerank、Voyage Rerank、Jina Reranker | 按调用量计费，效果稳定，接入简单 |
| 开源 Cross-Encoder | BGE-Reranker、bce-reranker | 可自托管，中文效果好，需要自己管理推理服务 |
| LLM 直接打分 | 用 Claude/GPT 对候选逐条打分排序 | 效果上限最高，延迟和成本也最高 |
| ColBERT 类后期交互 | ColBERTv2 及其变体 | 精度和延迟介于向量检索和 Cross-Encoder 之间 |

四类方案的核心权衡都是"精度 vs 延迟 vs 成本"，没有绝对最优解，只有匹配场景的选择。

## 三、选型标准逐项拆解

### 1. 语言覆盖

英文场景 Cohere Rerank、Voyage Rerank 效果都不错；中文场景优先看 BGE-Reranker（尤其是 `bge-reranker-v2-m3` 这类多语言版本）或者国内厂商专门优化过中文的重排模型，纯英文训练的 Cross-Encoder 在中文语料上精度会有明显折损，选型时不要直接假设英文榜单第一的模型中文也第一。

### 2. 延迟预算

Reranker 是同步阻塞在检索和生成之间的一步，延迟会直接叠加到用户等待时间上：

| 方案 | 典型延迟（Top 50 候选） |
|---|---|
| API 型 Cross-Encoder | 200ms~800ms（含网络往返） |
| 自托管 Cross-Encoder（GPU） | 50ms~200ms |
| LLM 打分（逐条调用） | 数秒到数十秒，取决于并发方式 |
| LLM 打分（批量单次调用） | 1~3 秒 |

如果产品对首字延迟敏感（比如实时对话场景），LLM 逐条打分基本不可行，优先考虑 API 型或自托管 Cross-Encoder；如果是异步任务（比如离线报告生成），LLM 重排的精度优势可以充分发挥。

### 3. 成本模型

API 型按"query + document 数量"计费，Top N 候选越多、费用越高；自托管型是固定的推理服务器成本，量大时更划算，量小时闲置浪费。做决策前先测算你的候选数量级和 QPS，具体的向量化成本核算方法可以参考 [Embedding 模型成本对比：API 调用 vs 自托管全算](/blog/embedding-model-cost-comparison/)，Reranker 的成本测算逻辑与之类似，只是把"建库"换成了"每次查询都要跑一遍精排"。

### 4. 是否需要可解释的分数

部分 Reranker API 只返回排序后的顺序，部分会返回归一化的相关性分数（0~1）。如果你的产品需要设置一个"相关性阈值，低于阈值就不召回"的兜底逻辑（避免检索不到答案时硬凑一个不相关的文档去生成），选型时要确认候选模型是否提供可用的分数，而不是只有相对排序。

## 四、评测方法：不要只看 Demo 效果

评测 Reranker 不能靠肉眼扫几条结果，需要一套可复现的黄金测试集，思路和 [RAG 系统评测框架搭建实战](/blog/ai-rag-evaluation-framework/) 里讲的整体框架一致，落到 Reranker 这一层，重点关注两个指标：

- **NDCG@K**：衡量重排后 Top K 结果的排序质量，比单纯的命中率更能反映"最相关的文档有没有排到最前面"
- **重排前后 Top K 命中率提升幅度**：这是最直观的 ROI 指标——如果加了 Reranker 之后 Top 5 命中率只提升了 2~3 个百分点，多数场景下不值得为此多付一次调用延迟和费用

```
评测流程：
1. 准备黄金测试集（query + 标注正确答案文档 ID）
2. 跑一遍纯向量/Hybrid 检索，记录 Top 5 / Top 10 命中率
3. 接入候选 Reranker，对 Top 50 候选重排，记录新的 Top 5 / Top 10 命中率
4. 对比提升幅度，同时记录端到端延迟变化
5. 只有当精度提升幅度明显超过延迟/成本代价时才上线
```

## 五、常见误区

- **候选池给太小**：Reranker 只能从粗排给的候选里选，如果粗排 Top 20 里根本没有正确答案，重排 20 遍也排不出正确结果。先确保粗排召回率足够（通常建议粗排候选数量是最终 Top K 的 5~10 倍），再谈精排。
- **把 Reranker 当万能修复工具**：如果召回质量差的根因是分块策略不合理（参考 [RAG Chunking 策略评测](/blog/rag-chunking-evaluation/)），加 Reranker 只是在错误的候选集里挑最不错的一个，治标不治本。
- **忽略重排对多轮对话上下文的处理**：多轮对话场景下，query 往往需要先做指代消解或改写，直接把用户原始短问句丢给 Reranker 打分，效果会明显低于对完整改写后 query 的打分。

## 六、相关阅读

- [Hybrid Search 权重调优实战：向量检索和关键词检索怎么配比](/blog/rag-hybrid-search-tuning/)
- [RAG 系统评测框架搭建实战](/blog/ai-rag-evaluation-framework/)
- [Embedding 模型成本对比：API 调用 vs 自托管全算](/blog/embedding-model-cost-comparison/)
- [国内 Embedding API 对比：价格、维度与检索效果](/blog/embeddings-api-cn-comparison/)

如果你的 RAG 系统需要同时调用 Embedding、Reranker 和生成模型，[YoTradeApi](https://yotradeapi.com) 支持一个 API Key 统一接入多家模型，省去分别对接、分别付费的麻烦。
