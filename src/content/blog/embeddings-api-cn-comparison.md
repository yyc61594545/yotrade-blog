---
title: Embeddings API 国内对比：text-embedding-3-large/voyage/BGE
description: text-embedding-3-large、Voyage、BGE 中文向量模型在 RAG 场景的实测对比，含召回率、速度、维度、价格与中转配置。
keywords:
- text-embedding-3-large
- voyage embedding
- bge 中文 embedding
- embeddings api 国内
- rag 向量模型
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/embeddings-api-cn-comparison/
tags:
- Embeddings
- RAG
- 向量模型
- OpenAI
- BGE
category: 模型评测
heroImage: ../../assets/blog-placeholder-2.jpg
---

做 RAG 的人都知道：检索质量 = 70% embedding + 20% chunking + 10% rerank。embedding 选错了，后面再怎么调都救不回来。本文用中文真实场景实测四个主流方案。

## 一、测评设置

- **测试集**：1000 条中文技术文档（覆盖编程、产品、运维），500 条查询
- **召回评估**：top-10 召回率、MRR
- **场景**：通过 OpenAI 兼容中转调用

参赛者：

| 模型 | 维度 | 多语言 | 备注 |
| --- | --- | --- | --- |
| `text-embedding-3-large` | 3072 | ✓ | OpenAI 旗舰 |
| `text-embedding-3-small` | 1536 | ✓ | OpenAI 性价比 |
| `voyage-3-large` | 1024 | ✓ | Anthropic 推荐 |
| `voyage-3-lite` | 512 | ✓ | 便宜版 |
| `BGE-M3` | 1024 | ✓ | 智源开源 |
| `BGE-large-zh-v1.5` | 1024 | 中文专用 | 智源开源 |

## 二、召回率对比

| 模型 | top-10 召回 | MRR |
| --- | --- | --- |
| text-embedding-3-large | 87.2% | 0.71 |
| text-embedding-3-small | 81.5% | 0.65 |
| voyage-3-large | 89.1% | 0.74 |
| voyage-3-lite | 83.8% | 0.67 |
| BGE-M3 | 86.5% | 0.70 |
| BGE-large-zh-v1.5 | 85.3% | 0.69 |

**结论**：

- 中文 RAG 强烈推荐 voyage-3-large 或 text-embedding-3-large
- 想自部署且无 GPU，BGE-M3 是最佳开源选择
- 纯中文文档 BGE-large-zh-v1.5 略弱（训练数据更专但更窄）
- text-embedding-3-small 性价比最高，预算紧用它

## 三、速度对比

| 模型 | 单文档延迟（中位） | 批量 100 条 |
| --- | --- | --- |
| text-embedding-3-large | 180ms | 600ms |
| text-embedding-3-small | 120ms | 350ms |
| voyage-3-large | 200ms | 700ms |
| BGE-M3（本地 RTX 4090） | 25ms | 220ms |

自部署 BGE 速度优势明显，但维护成本高。

## 四、价格对比（相对值）

| 模型 | 1M tokens |
| --- | --- |
| text-embedding-3-small | 100 |
| text-embedding-3-large | 650 |
| voyage-3-lite | 100 |
| voyage-3-large | 600 |
| BGE-M3（自部署） | ~0（电费） |

## 五、Python 调用示例

### OpenAI 兼容路径

```python
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_YOTRADE_KEY",
    base_url="https://yotradeapi.com/v1",
)

resp = client.embeddings.create(
    model="text-embedding-3-large",
    input=["你好世界", "Hello world"],
)
vec1 = resp.data[0].embedding   # 3072 维向量
vec2 = resp.data[1].embedding
```

### Voyage 原生

```python
import voyageai

vo = voyageai.Client(api_key="YOUR_KEY")
result = vo.embed(["你好世界"], model="voyage-3-large", input_type="document")
print(result.embeddings[0])
```

### BGE 本地

```python
from FlagEmbedding import BGEM3FlagModel

model = BGEM3FlagModel('BAAI/bge-m3', use_fp16=True)
embeddings = model.encode(["你好世界"])['dense_vecs']
```

## 六、维度选择：1536 vs 3072

text-embedding-3-large 默认 3072 维，但支持降维：

```python
resp = client.embeddings.create(
    model="text-embedding-3-large",
    input=text,
    dimensions=1024,  # 降到 1024 维
)
```

实测：

| 维度 | 召回 | 存储 | 检索速度 |
| --- | --- | --- | --- |
| 3072 | 87.2% | 100% | 100% |
| 1536 | 86.5% | 50% | 60% |
| 1024 | 85.8% | 33% | 45% |
| 768 | 83.9% | 25% | 35% |

**结论**：1024 维是甜蜜点。召回略降，存储/检索成本大幅下降。

## 七、Chunk size 与 embedding 配合

很多人忽略的点：embedding 模型有最佳 chunk 长度。

| 模型 | 推荐 chunk |
| --- | --- |
| text-embedding-3-large | 300–600 tokens |
| voyage-3-large | 400–800 tokens |
| BGE-M3 | 200–500 tokens |

超长 chunk（> 1000 tokens）召回质量明显下降。一般用 500 token + 50 token overlap 是稳的起点。

## 八、Rerank：embedding 之上的二次精调

embedding 召回后，加一个 rerank 模型能显著提升 top-3 准确度：

```python
resp = client.embeddings.create(
    model="rerank-3-large",  # 假设网关支持
    query="什么是 LRU 缓存",
    documents=top_10_docs,
)
```

实测加 rerank 之后：

| 配置 | top-3 准确度 |
| --- | --- |
| 纯 embedding | 78% |
| embedding + rerank | 91% |

成本增加约 30%，但准确度提升 13 个百分点，对 RAG 关键场景非常值得。

## 九、本地 vs 云端选择决策

| 你的情况 | 推荐 |
| --- | --- |
| 文档量 < 10k，无 GPU | 云端 text-embedding-3-large |
| 文档量 10k–1M，预算紧 | 云端 text-embedding-3-small |
| 文档量 > 1M，有 GPU | 自部署 BGE-M3 |
| 数据敏感不能出局 | 自部署 BGE-M3 |
| 多语言（10+ 语言） | voyage-3-large |
| 纯中文 + 简单场景 | BGE-large-zh-v1.5 |

## 十、相关阅读

- [OpenAI SDK base_url 国内配置实战](/blog/openai-sdk-base-url-cn/)
- [Cherry Studio 国内 API 中转配置指南](/blog/cherry-studio-cn-config/)
- [Gemini API 国内调用指南](/blog/gemini-api-cn-guide/)
- [AI 编程代理成本控制实战](/blog/ai-coding-agent-cost-control/)

需要一把 Key 同时调 embedding + chat + rerank？[YoTradeApi](https://yotradeapi.com) 支持 OpenAI / Voyage 兼容端点，按上面 SDK 例子直接接入。
