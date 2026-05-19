---
title: 2026 向量数据库对比：Chroma/Qdrant/Milvus/pgvector
description: 主流向量数据库横向对比：性能、规模、运维、成本、集成、混合检索能力，给中文 RAG 场景的选型建议。
keywords:
- 向量数据库 对比
- chroma vs qdrant
- milvus pgvector
- vector db 选型
- rag 向量库
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/vector-db-comparison-2026/
tags:
- 向量数据库
- RAG
- 选型
- 工程实战
category: 工程实战
heroImage: ../../assets/blog-placeholder-5.jpg
---

# 2026 向量数据库对比：Chroma/Qdrant/Milvus/pgvector

向量数据库这两年百花齐放。但 RAG 项目里，**绝大多数选错了**——要么用了太重的（Milvus 跑几千文档），要么用了太轻的（Chroma 跑几千万）。本文按场景给清晰选型。

## 一、6 个主流选项

| DB | 类型 | 适合规模 | 部署复杂度 |
| --- | --- | --- | --- |
| Chroma | 嵌入式 / 服务 | < 1M | 极低 |
| Qdrant | 服务 | 1M – 100M | 中 |
| Milvus | 服务 | 10M – 10B | 高 |
| pgvector | Postgres 扩展 | < 10M | 低（如已有 PG） |
| Weaviate | 服务 | 1M – 100M | 中 |
| Pinecone | SaaS | 1M – 1B | 极低（托管） |

## 二、性能（10M 向量，1024 维，top-10 检索）

| DB | 召回率 | QPS | p95 延迟 | 内存 |
| --- | --- | --- | --- | --- |
| Chroma | 高 | 200 | 50ms | 高 |
| Qdrant | 极高 | 2500 | 8ms | 中 |
| Milvus | 极高 | 3000+ | 10ms | 中 |
| pgvector (HNSW) | 高 | 1500 | 12ms | 中 |
| Weaviate | 高 | 1800 | 15ms | 中 |
| Pinecone | 高 | 受限于套餐 | 20ms | 托管 |

**结论**：

- 性能极致：Qdrant / Milvus
- 工程简单：pgvector（如已有 Postgres）
- 入门：Chroma

## 三、Chroma：入门首选

```python
import chromadb

client = chromadb.PersistentClient(path="./chroma_db")
coll = client.get_or_create_collection("docs")
coll.add(
    ids=["1", "2"],
    documents=["text A", "text B"],
    embeddings=[emb_a, emb_b],
    metadatas=[{"src": "doc1"}, {"src": "doc2"}],
)

results = coll.query(query_embeddings=[query_emb], n_results=5)
```

优势：

- 零运维
- API 极简
- 嵌入 + 服务两种模式
- 自动批量

劣势：

- 超 1M 向量明显变慢
- 没有真正高级查询（filter 简单）
- 没有真正水平扩展

**适合**：50 万以内文档 / Demo / 个人项目。

## 四、Qdrant：性能 / 易用平衡

```python
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

client = QdrantClient("http://localhost:6333")
client.create_collection(
    "docs",
    vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
)

client.upsert(
    collection_name="docs",
    points=[PointStruct(id=1, vector=emb, payload={"src": "doc1"})],
)

hits = client.search(collection_name="docs", query_vector=query_emb, limit=5)
```

优势：

- 性能极强
- HNSW + 量化
- 富 filter（嵌套字段、范围查询）
- Docker 部署简单
- HTTP / gRPC

劣势：

- 单机最多到 1 亿规模
- 分布式集群配置复杂

**适合**：百万 - 亿级 / 生产 RAG / 数据敏感（自部署）。

## 五、Milvus：大规模生产

```python
from pymilvus import MilvusClient

client = MilvusClient(uri="http://localhost:19530")
client.create_collection("docs", dimension=1024)
client.insert("docs", data=[{"id": 1, "vector": emb, "src": "doc1"}])
hits = client.search("docs", data=[query_emb], limit=5)
```

优势：

- 真正水平扩展
- 多副本 / 强一致
- 丰富索引（IVF / HNSW / DiskANN）
- 集群管理工具完善

劣势：

- 部署复杂（K8s）
- 1M 以下规模性价比低
- 学习曲线陡

**适合**：千万 - 数十亿规模 / 团队有 SRE / 数据是核心资产。

## 六、pgvector：已有 Postgres 的最佳选择

```sql
CREATE EXTENSION vector;

CREATE TABLE docs (
  id SERIAL PRIMARY KEY,
  content TEXT,
  src TEXT,
  embedding vector(1024)
);

CREATE INDEX ON docs USING hnsw (embedding vector_cosine_ops);

-- 检索
SELECT id, content, src, embedding <=> '[...]' AS distance
FROM docs
WHERE src = 'doc1'
ORDER BY distance
LIMIT 5;
```

优势：

- 一个 DB 搞定向量 + 关系数据
- 事务支持
- 完整 SQL（JOIN、聚合）
- 备份 / HA 复用现有 PG 设施

劣势：

- HNSW 性能不如专用
- 不擅长百万级以上
- 索引建得慢

**适合**：项目已有 Postgres / 数据量 < 10M / 不想多维护一个组件。

## 七、Weaviate：GraphQL + Multi-tenancy

```python
import weaviate

client = weaviate.Client("http://localhost:8080")
client.schema.create_class({
    "class": "Doc",
    "vectorizer": "none",
})
client.data_object.create({"content": "...", "src": "doc1"}, "Doc", vector=emb)

result = client.query.get("Doc", ["content", "src"]) \
    .with_near_vector({"vector": query_emb}) \
    .with_limit(5) \
    .do()
```

优势：

- GraphQL 查询
- 内置 multi-tenancy
- 模块化（可接 OpenAI 自动 embed）

劣势：

- 复杂度比 Qdrant 高
- 中文社区资料少

**适合**：多租户 SaaS / 重度依赖 GraphQL 的团队。

## 八、Pinecone：完全托管

```python
from pinecone import Pinecone

pc = Pinecone(api_key="...")
index = pc.Index("docs")
index.upsert(vectors=[{"id": "1", "values": emb, "metadata": {"src": "doc1"}}])
results = index.query(vector=query_emb, top_k=5)
```

优势：

- 零运维
- 全球部署
- 高可用

劣势：

- 国内访问看网络
- 数据出境
- 按存储 + QPS 计费，量大很贵

**适合**：海外项目 / 不想自己运维 / 预算充足。

## 九、混合检索（BM25 + Vector）

中文 RAG **强烈推荐混合检索**：

| DB | 混合检索内置支持 |
| --- | --- |
| Qdrant | ✓（hybrid search） |
| Milvus | ✓ |
| Weaviate | ✓ |
| Chroma | ✗（自己拼） |
| pgvector | 部分（用 tsvector 自拼） |

详见 [中文 RAG 工程实战](/blog/rag-cn-best-practices/)。

## 十、决策表

| 你的情况 | 选 |
| --- | --- |
| Demo / < 100k 文档 | Chroma |
| < 1M 文档 + 已有 PG | pgvector |
| < 1M 文档 + 重检索性能 | Qdrant |
| 1M – 10M 文档 | Qdrant |
| 10M+ 文档 + 团队有 SRE | Milvus |
| 海外 + 不想运维 | Pinecone |
| 多租户 SaaS | Weaviate / Qdrant |
| 实时增量更新频繁 | Qdrant / pgvector |
| 数据敏感不能出局 | Qdrant 自部署 / pgvector |

## 十一、迁移成本

各家 API 不通用。从一个迁到另一个需要：

1. 重新导出所有 embedding（或重新算）
2. 重写 ingest 代码
3. 重写 query 代码
4. 调 chunk / index 参数
5. 跑回归测试

**第一次选错代价大**。建议：从 Chroma / pgvector 起步，量大再迁。

## 十二、相关阅读

- [中文 RAG 工程实战](/blog/rag-cn-best-practices/)
- [Embeddings API 国内对比](/blog/embeddings-api-cn-comparison/)
- [LlamaIndex 中文 RAG 完整教程](/blog/llamaindex-cn-rag-tutorial/)
- [LangChain 中文实战](/blog/langchain-cn-tutorial/)

向量库选好后，embedding 接 [YoTradeApi](https://yotradeapi.com/register) 中转，一把 Key 跑 text-embedding-3-large / voyage / 国产 embedding。
