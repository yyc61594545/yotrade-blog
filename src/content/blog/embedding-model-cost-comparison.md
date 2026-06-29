---
title: Embedding 模型成本对比：API 调用 vs 自托管全算
description: 系统对比 OpenAI、Cohere、Voyage 等主流 Embedding API 与 BGE、E5 自托管方案的完整成本，含百万文档建库与在线查询两个场景的详细测算。
keywords:
  - Embedding 模型成本对比
  - text-embedding API 价格
  - 自托管 Embedding 成本
  - BGE 向量模型成本
  - RAG 向量化成本优化
pubDate: '2026-06-29'
updatedDate: '2026-06-29'
canonical: https://blog.yotradeapi.com/blog/embedding-model-cost-comparison/
tags:
  - Embedding
  - 成本优化
  - RAG
  - 向量模型
category: 成本优化
heroImage: ../../assets/blog-placeholder-5.jpg
---

Embedding 模型的成本往往被低估——开发阶段处理几万条文档感觉不贵，但一旦进入生产环境，百万条文档建库 + 每天数万次在线查询的累积成本，可能比 LLM 本身还高。本文专门算这笔账，帮你在 API 服务和自托管之间找到最优解。

> **说明**：价格数据来自各厂商公开定价页面（截至 2026 年 6 月），实际以官网当前定价为准。成本测算均为近似估算，不同数据分布结果会有差异。

## 一、成本构成要素

在比较之前，先厘清 Embedding 场景的成本有哪些组成：

**离线建库成本**（一次性或低频）：
- 将文档转化为向量的 API 调用费（按 token 计费）
- 向量写入数据库的成本（通常可忽略不计）

**在线查询成本**（持续发生）：
- 每次用户 query 向量化的 API 调用费
- 向量检索的计算成本（向量数据库侧）

**自托管的额外成本**：
- GPU 服务器租金或购买折旧
- 运维人力（部署、监控、扩容）
- 冷启动延迟（Serverless 场景）

## 二、主流 API 服务定价对比

以下为各主要 Embedding API 的公开价格（单位：美元/百万 token，约数）：

| 模型 | 维度 | 每百万 token 价格 | 最大输入长度 | 备注 |
|------|------|------------|------------|------|
| text-embedding-3-small | 1536 | ~$0.02 | 8191 tokens | OpenAI 性价比款 |
| text-embedding-3-large | 3072 | ~$0.13 | 8191 tokens | OpenAI 高精度款 |
| text-embedding-ada-002 | 1536 | ~$0.10 | 8191 tokens | 旧版，性价比差 |
| Cohere Embed v3 (English) | 1024 | ~$0.10 | 512 tokens | 英文优化 |
| Cohere Embed v3 (Multi) | 1024 | ~$0.10 | 512 tokens | 多语言 |
| Voyage-3 | 1024 | ~$0.06 | 32000 tokens | 长文档优 |
| Voyage-3-lite | 512 | ~$0.02 | 32000 tokens | 轻量低成本 |
| Jina Embedding v3 | 1024 | ~$0.018 | 8192 tokens | 价格激进 |

**中文表现说明**：
- 中文文档向量化质量对比，参见 [Embeddings API 国内对比：text-embedding-3-large/voyage/BGE](/blog/embeddings-api-cn-comparison/)
- 本文聚焦成本，不重复质量评测

## 三、百万文档建库的成本测算

**假设条件**：
- 文档总量：100 万条
- 平均每条文档长度：500 中文字符 ≈ 250 英文 token（中文 1 字约 0.7 token）
- 总 token 量：约 2.5 亿 token（250M tokens）

| 方案 | 单价 | 100 万文档建库总成本 |
|------|------|---------------|
| text-embedding-3-small | $0.02/M | **$5** |
| Voyage-3-lite | $0.02/M | **$5** |
| Jina v3 | $0.018/M | **$4.5** |
| Voyage-3 | $0.06/M | **$15** |
| Cohere Embed v3 | $0.10/M | **$25** |
| text-embedding-3-large | $0.13/M | **$32.5** |
| ada-002（旧版） | $0.10/M | **$25** |

**结论**：建库是一次性成本，绝对金额其实不高。即使选最贵的 `text-embedding-3-large`，100 万文档也只花约 $32。建库时选稍贵的高维度模型通常是值得的。

## 四、在线查询的成本测算

在线查询是持续成本，算法不同：

**假设条件**：
- 每天查询次数：10,000 次
- 每次 query 长度：50 字 ≈ 35 token
- 每月查询次数：30 万次
- 每月总 query token：约 1050 万 token（10.5M tokens）

| 方案 | 每月 query 成本 | 年成本 |
|------|------------|------|
| text-embedding-3-small | **$0.21** | **$2.5** |
| Voyage-3-lite | **$0.21** | **$2.5** |
| Jina v3 | **$0.19** | **$2.3** |
| Voyage-3 | **$0.63** | **$7.6** |
| text-embedding-3-large | **$1.37** | **$16.4** |

**结论**：在线查询的成本比建库更需要关注——它是持续支出。但即使日均 1 万次查询，全年成本也不超过 $20（用 small 系模型时）。Embedding 查询不是主要成本瓶颈，关键还是向量数据库和 LLM 生成的费用。

## 五、自托管方案的真实成本

自托管 Embedding 的典型选择（中文效果较好）：

| 模型 | 维度 | 中文质量 | 推理需求 |
|------|------|---------|---------|
| BGE-large-zh | 1024 | ★★★★★ | CPU 可跑，GPU 快 |
| BGE-m3 | 1024 | ★★★★★ | 内存占用大 |
| E5-large-v2 | 1024 | ★★★★☆ | CPU 可跑 |
| paraphrase-multilingual-mpnet | 768 | ★★★☆☆ | 轻量 |

**GPU 服务器成本估算（按国内云厂商租用）**：

| 规格 | 适用场景 | 月租（估算，近似）|
|------|---------|------------|
| CPU 实例（16 核 32G） | 低并发，时延 100–500ms | 约 ¥200–500/月 |
| T4 GPU 实例 | 中等并发，时延 10–50ms | 约 ¥800–1500/月 |
| A10 GPU 实例 | 高并发生产场景 | 约 ¥2000–4000/月 |

**自托管 Break-even 分析**：

假设使用 `text-embedding-3-small`（$0.02/M token），自托管 BGE-large-zh：

每月节省 API 费用 = 月 token 量 × $0.02/M

| 月 token 量 | API 费 | T4 自托管月租（估算）| 自托管划算？ |
|------------|--------|--------------|----------|
| 1 亿 token | $2 | ¥1000（~$140） | 不划算 |
| 10 亿 token | $20 | ¥1000（~$140） | 不划算 |
| 100 亿 token | $200 | ¥1000（~$140） | 划算 |
| 1000 亿 token | $2000 | ¥3000（~$420）×多卡 | 很划算 |

**核心结论**：月 token 量低于 100 亿时，自托管的服务器成本往往超过 API 费用。自托管的价值体现在：

1. **月 token 量极大**（10B+）时的纯成本节省
2. **数据隐私要求**：文档不能出境、不能经过第三方
3. **极低延迟要求**：本地推理 <10ms，API 调用通常 50–200ms
4. **无网络依赖**：离线环境或内网隔离场景

## 六、混合方案：按场景分流

实际生产中，最优解往往是混合策略：

```
文档建库（离线批处理）→ 使用 API（成本低、一次性）
在线查询（高频）       → 本地小模型（低延迟、无网络调用）
重要文档召回（低频）   → 高质量 API 模型（精度优先）
```

**Python 示例：根据查询频率自动路由**：

```python
import anthropic  # 或其他 SDK
from sentence_transformers import SentenceTransformer

# 本地轻量模型，用于高频在线查询
local_model = SentenceTransformer('BAAI/bge-small-zh-v1.5')  # 约 90MB

def get_embedding(text: str, mode: str = "online"):
    if mode == "online":
        # 高频查询：用本地小模型，延迟 <5ms
        return local_model.encode(text).tolist()
    else:
        # 建库/重要文档：用 API 高质量模型
        import openai
        resp = openai.embeddings.create(
            model="text-embedding-3-large",
            input=text
        )
        return resp.data[0].embedding

# 在线查询
query_vec = get_embedding(user_query, mode="online")

# 离线建库
doc_vec = get_embedding(document_text, mode="batch")
```

**注意**：混合方案要求在线 query 的嵌入空间与文档嵌入空间一致——不能用 BGE 做查询、用 OpenAI 做建库，两者向量空间不兼容。建库和查询必须使用同一模型。

## 七、向量维度与存储成本

维度选择也影响存储成本，容易被忽视：

| 维度 | 每条向量大小（float32）| 100 万向量存储 |
|------|--------------------|-------------|
| 512 | 2 KB | 2 GB |
| 768 | 3 KB | 3 GB |
| 1024 | 4 KB | 4 GB |
| 1536 | 6 KB | 6 GB |
| 3072 | 12 KB | 12 GB |

对于 100 万文档，1536 维需要约 6GB 内存或存储——大多数向量数据库会把向量加载到内存以保证检索速度，因此高维度意味着更高的内存成本。`text-embedding-3-small` 支持通过 `dimensions` 参数降维（最低 256），可以用来降低存储成本。

## 八、国内 API 中转的成本影响

如果通过 API 中转服务调用 OpenAI Embedding，通常有 1.2–1.5 倍的溢价（渠道成本）。即便如此，`text-embedding-3-small` 通过中转调用，月成本仍然极低（10B token 以内很难超过 $50）。如果主要考虑的是数据不出境，用本地模型（BGE 系列）更合适。

## 九、选型建议汇总

| 场景 | 推荐方案 | 理由 |
|------|---------|------|
| 初期验证 / 文档量 <100 万 | `text-embedding-3-small` API | 简单、成本极低 |
| 中文内容 + 数据合规要求 | BGE-large-zh 自托管 | 中文质量好，无数据出境 |
| 长文档（>2000 字） | `voyage-3` API | 最大 32k token 窗口 |
| 高并发在线查询 + 低延迟 | 本地小模型（BGE-small） | 无网络往返，<5ms |
| 多语言企业文档 | Cohere Embed v3 Multi | 多语言优化 |
| 预算极度受限 | Jina v3 | 价格最低，质量可接受 |

## 十、相关阅读

- [Embeddings API 国内对比：text-embedding-3-large/voyage/BGE](/blog/embeddings-api-cn-comparison/)
- [向量数据库选型对比 2026](/blog/vector-db-comparison-2026/)
- [RAG 国内最佳实践：从分块到召回](/blog/rag-cn-best-practices/)
- [LLM 批量 API 真实省钱效果测算](/blog/llm-batch-api-real-savings/)

想低成本调用 OpenAI Embedding API？[YoTradeApi](https://yotradeapi.com) 支持 text-embedding-3-small/large，人民币按量充值，国内直连无需翻墙。
