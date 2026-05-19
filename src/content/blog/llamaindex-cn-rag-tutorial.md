---
title: LlamaIndex 中文 RAG 完整教程
description: 用 LlamaIndex 在国内构建 RAG 系统的实战教程，含文档加载、index 构建、查询、Agent、与 LangChain 的对比。
keywords:
- llamaindex 中文
- llamaindex 教程
- llamaindex rag
- llamaindex 国内
- llamaindex 中转
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/llamaindex-cn-rag-tutorial/
tags:
- LlamaIndex
- RAG
- 框架
- 教程
- Python
category: 工程实战
heroImage: ../../assets/blog-placeholder-5.jpg
---

# LlamaIndex 中文 RAG 完整教程

LlamaIndex 与 LangChain 同期出现，**专注做 RAG**。论 chain 能力不如 LangChain 全，但论"文档加载 → index → 查询"这条链路它做得最深。本文给中文 RAG 实战教程。

## 一、安装

```bash
pip install llama-index
pip install llama-index-llms-openai
pip install llama-index-embeddings-openai
pip install llama-index-vector-stores-chroma
```

按需安装其它 reader / vector store 包。

## 二、配置中转

```python
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core import Settings

Settings.llm = OpenAI(
    api_base="https://yotradeapi.com/v1",
    api_key="sk-yo-...",
    model="claude-sonnet-4-6",   # 通过中转走 Claude
)

Settings.embed_model = OpenAIEmbedding(
    api_base="https://yotradeapi.com/v1",
    api_key="sk-yo-...",
    model="text-embedding-3-large",
)
```

全局配置。后续所有 chain 用这个 llm + embedding。

## 三、最简 RAG

```python
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex

# 加载文档
documents = SimpleDirectoryReader("./docs").load_data()

# 建 index（自动 embed）
index = VectorStoreIndex.from_documents(documents)

# 持久化
index.storage_context.persist(persist_dir="./storage")

# 查询
query_engine = index.as_query_engine()
response = query_engine.query("我们的退货政策是什么？")
print(response)
```

10 行 RAG。`SimpleDirectoryReader` 自动识别 PDF / Word / Markdown / Text。

## 四、持久化与重载

```python
from llama_index.core import StorageContext, load_index_from_storage

# 重启后重载，不需要重新 embed
storage_context = StorageContext.from_defaults(persist_dir="./storage")
index = load_index_from_storage(storage_context)
```

避免重复花 embed 钱。

## 五、用 Chroma 替代默认向量库

默认 in-memory + JSON 持久化，**大数据量慢**。换 Chroma：

```python
import chromadb
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import StorageContext, VectorStoreIndex

chroma_client = chromadb.PersistentClient(path="./chroma_db")
chroma_collection = chroma_client.get_or_create_collection("docs")

vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
storage_context = StorageContext.from_defaults(vector_store=vector_store)

index = VectorStoreIndex.from_documents(documents, storage_context=storage_context)
```

10k+ 文档场景**Chroma 性能比默认快 10 倍以上**。

## 六、Chunk 策略

```python
from llama_index.core.node_parser import SentenceSplitter

splitter = SentenceSplitter(
    chunk_size=512,        # 每块约 512 tokens
    chunk_overlap=50,       # overlap 50
    separator="\n\n",       # 段落分隔
)

Settings.node_parser = splitter
```

详见 [中文 RAG 工程实战](/blog/rag-cn-best-practices/)。

## 七、加 Rerank

```python
from llama_index.postprocessor.cohere_rerank import CohereRerank
# 或用 LLM-as-reranker（贵但通用）

rerank = CohereRerank(api_key="...", top_n=3)

query_engine = index.as_query_engine(
    similarity_top_k=10,
    node_postprocessors=[rerank],
)
```

召回 10 → rerank 取 top 3。准确率显著提升。

## 八、Multi-Document Query

```python
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.query_engine import SubQuestionQueryEngine

# 两份文档各自 index
docs_a = VectorStoreIndex.from_documents(load_a())
docs_b = VectorStoreIndex.from_documents(load_b())

tools = [
    QueryEngineTool(
        query_engine=docs_a.as_query_engine(),
        metadata=ToolMetadata(name="docs_a", description="产品文档"),
    ),
    QueryEngineTool(
        query_engine=docs_b.as_query_engine(),
        metadata=ToolMetadata(name="docs_b", description="API 文档"),
    ),
]

query_engine = SubQuestionQueryEngine.from_defaults(query_engine_tools=tools)
response = query_engine.query("产品如何接入 API？")
```

会自动把问题拆成 sub-question 分别查 a / b，再综合。

## 九、Agent + RAG

```python
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.tools import FunctionTool

def get_user_status(user_id: str) -> str:
    """查用户当前订阅状态"""
    return f"user {user_id} is active"

agent = FunctionAgent(
    name="assistant",
    tools=[
        QueryEngineTool(query_engine=docs_a.as_query_engine(), metadata=ToolMetadata(name="kb", description="知识库")),
        FunctionTool.from_defaults(get_user_status),
    ],
    llm=Settings.llm,
)

response = await agent.run("用户 alice 是否能用 X 功能？")
```

Agent 知道何时查文档、何时查用户状态。

## 十、流式

```python
streaming = query_engine.query_stream("...")
for chunk in streaming.response_gen:
    print(chunk, end="")
```

或者用 `as_chat_engine()`：

```python
chat_engine = index.as_chat_engine(
    chat_mode="condense_plus_context",
    streaming=True,
)
response = chat_engine.stream_chat("...")
for token in response.response_gen:
    print(token, end="")
```

## 十一、Metadata 过滤

```python
from llama_index.core.vector_stores import MetadataFilters, ExactMatchFilter

filters = MetadataFilters(filters=[
    ExactMatchFilter(key="category", value="legal"),
    ExactMatchFilter(key="language", value="zh"),
])

query_engine = index.as_query_engine(filters=filters)
```

按 metadata 限制检索范围。**多租户 RAG 必备**。

## 十二、LlamaIndex vs LangChain

| 维度 | LlamaIndex | LangChain |
| --- | --- | --- |
| 专注 | RAG | 通用 chain |
| 文档加载器 | 极多 | 多 |
| Vector store 集成 | 极多 | 多 |
| Agent | 有 | 完整 |
| LCEL 风格 | 部分 | 是 |
| 学习曲线 | 中 | 高 |

**简单决策**：

- 以 RAG 为主 → LlamaIndex
- 复杂 agent + chain → LangChain
- 想自己控制更多 → 裸 SDK

## 十三、生产部署注意

1. **Embedding 一次性算清**：上线前批量 embed，运行时只 query
2. **Vector store 备份**：定期 dump
3. **新文档增量加**：用 `insert_nodes()` 不要重建 index
4. **查询缓存**：相同问题缓存 30 秒
5. **监控 token**：每个 query 都消耗，监控异常
6. **rerank 看场景**：高准确度场景上，速度敏感不上

## 十四、相关阅读

- [中文 RAG 工程实战](/blog/rag-cn-best-practices/)
- [Embeddings API 国内对比](/blog/embeddings-api-cn-comparison/)
- [LangChain 中文实战](/blog/langchain-cn-tutorial/)
- [Cherry Studio 国内 API 中转配置指南](/blog/cherry-studio-cn-config/)
- [OpenAI SDK base_url 国内配置实战](/blog/openai-sdk-base-url-cn/)

LlamaIndex 同时需要 chat + embedding 接口？[YoTradeApi](https://yotradeapi.com/register) 一把 Key 接两个端点，按上面配置接入。
