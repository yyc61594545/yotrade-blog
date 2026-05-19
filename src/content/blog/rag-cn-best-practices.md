---
title: 中文 RAG 工程实战：从分块到 Rerank 完整流程
description: 中文 RAG 系统的工程实战指南，含文档解析、chunk 策略、embedding 选择、向量库、检索、rerank、生成全流程。
keywords:
- 中文 rag
- rag 实战
- rag 分块
- rag rerank
- 向量数据库
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/rag-cn-best-practices/
tags:
- RAG
- 向量检索
- Embedding
- 中文
- 工程实战
category: 工程实战
heroImage: ../../assets/blog-placeholder-4.jpg
---

# 中文 RAG 工程实战：从分块到 Rerank 完整流程

中文 RAG 看起来简单——"嵌入 + 检索 + 拼 prompt"——但工程化做好的不多。常见问题：检索召回低、回答漂移、token 浪费、中文专有名词处理不好。本文给一份完整的中文 RAG 工程实战。

## 一、流程总览

```
原始文档 → 解析 → 分块 → embedding → 向量库
                                          ↓
用户提问 → embedding → 检索 → rerank → 拼 prompt → LLM → 回答
```

每一步都有讲究。我们逐个展开。

## 二、文档解析

中文场景常见格式：PDF、Word、Markdown、网页、Excel。

| 格式 | 推荐工具 |
| --- | --- |
| PDF（文字） | pdfplumber、pypdf |
| PDF（扫描图） | OCR（PaddleOCR、Tesseract） |
| Word | python-docx |
| Markdown | 直接读 |
| HTML | BeautifulSoup、trafilatura |
| Excel | pandas、openpyxl |

**关键纪律**：

- 解析时保留结构（标题、列表、表格）
- 表格转换成 markdown 表格保留对齐
- 代码块明确标记（``` 包围）

## 三、分块（Chunking）

最容易做错的一步。基础三种策略：

### 1. 固定长度

```python
def chunk_fixed(text, size=500, overlap=50):
    chunks = []
    for i in range(0, len(text), size - overlap):
        chunks.append(text[i:i + size])
    return chunks
```

简单但**对中文不友好**——会切断词、句子。

### 2. 按句子切

```python
import re

def split_sentences(text):
    # 中文句末标点
    return [s for s in re.split(r"(?<=[。！？\n])", text) if s.strip()]

def chunk_by_sentence(text, max_size=500):
    sents = split_sentences(text)
    chunks, cur, cur_len = [], [], 0
    for s in sents:
        if cur_len + len(s) > max_size and cur:
            chunks.append("".join(cur))
            cur, cur_len = [], 0
        cur.append(s)
        cur_len += len(s)
    if cur:
        chunks.append("".join(cur))
    return chunks
```

中文场景更合适。

### 3. 语义分块（Semantic）

用 embedding 找语义断点：

```python
import numpy as np

def semantic_chunk(text, threshold=0.7):
    sents = split_sentences(text)
    embs = [embed(s) for s in sents]
    chunks = [[sents[0]]]
    for i in range(1, len(sents)):
        sim = cosine(embs[i-1], embs[i])
        if sim < threshold:
            chunks.append([])
        chunks[-1].append(sents[i])
    return ["".join(c) for c in chunks]
```

效果好但成本高。文档量小时用。

### 推荐配置

| 场景 | size | overlap | 策略 |
| --- | --- | --- | --- |
| 技术文档 | 500–800 字 | 50–100 字 | 按句切 |
| 长篇小说 | 800–1200 字 | 100–200 字 | 按段切 |
| 代码 | 按函数切 | 0 | AST 切 |
| 表格 | 整张表 | 0 | 不切 |

## 四、Embedding 选择

详见 [Embeddings API 国内对比](/blog/embeddings-api-cn-comparison/)。简化版：

- **预算紧 + 文档量大**：text-embedding-3-small
- **召回质量优先**：voyage-3-large 或 text-embedding-3-large
- **自部署 / 数据不能出局**：BGE-M3

通过中转调用：

```python
from openai import OpenAI

client = OpenAI(base_url="https://yotradeapi.com/v1", api_key="sk-yo-...")
resp = client.embeddings.create(model="text-embedding-3-large", input=chunks)
embs = [d.embedding for d in resp.data]
```

## 五、向量库

| 选择 | 适用 |
| --- | --- |
| Chroma | 本地小项目，零运维 |
| Qdrant | 中等规模，开源稳定 |
| Milvus | 大规模 |
| Pinecone | SaaS，零运维 |
| Postgres + pgvector | 已有 pg 设施 |
| Redis Vector | 已有 redis |

中文 RAG 不需要花哨的库。**500k 条以下用 Chroma，500k–10M 用 Qdrant，再大用 Milvus**。

```python
import chromadb
client = chromadb.PersistentClient(path="./data")
coll = client.get_or_create_collection("docs")
coll.add(
    ids=[str(i) for i in range(len(chunks))],
    documents=chunks,
    embeddings=embs,
    metadatas=[{"source": "doc1.pdf", "page": p} for p in pages],
)
```

## 六、检索

不要只用纯向量检索：

```python
# 混合：向量 + BM25
from rank_bm25 import BM25Okapi

# 准备
bm25 = BM25Okapi([list(c) for c in chunks])

def hybrid_search(query, top_k=10):
    # 向量检索
    q_emb = client.embeddings.create(model=EMB_MODEL, input=[query]).data[0].embedding
    vec_results = coll.query(query_embeddings=[q_emb], n_results=top_k)
    # BM25 检索
    bm25_scores = bm25.get_scores(list(query))
    bm25_top = np.argsort(bm25_scores)[-top_k:][::-1]
    # 合并去重
    combined = list(set(vec_results['ids'][0] + [str(i) for i in bm25_top]))
    return combined
```

中文场景**混合检索的召回比纯向量高 8–15 个百分点**。

## 七、Rerank

检索回来 top-20，rerank 重排取 top-5：

```python
resp = client.chat.completions.create(
    model="rerank-3-large",  # 看中转支持
    extra_body={
        "query": query,
        "documents": [doc for doc in retrieved_docs],
        "top_k": 5,
    },
)
```

实测 rerank 后 top-3 准确率提升 10–15 个百分点。代价：每次提问多调一次 API，成本 +20–30%。

## 八、拼 prompt

```python
def build_prompt(query, top_docs):
    return f"""根据下面的资料回答问题。
如果资料中没有答案，明确说"资料中没有相关信息"，不要编造。

# 资料
{chr(10).join(f"[{i+1}] {d}" for i, d in enumerate(top_docs))}

# 问题
{query}

# 要求
- 引用资料编号 [1] [2] 等
- 简洁，不超过 300 字
"""
```

**关键**：

- 明确"不知道就说不知道"，**减少幻觉**
- 引用编号让答案可追溯
- 给出输出长度上限

## 九、整体调用

```python
def rag_answer(query):
    # 1. 检索 top 20
    ids = hybrid_search(query, top_k=20)
    docs = [chunks[int(i)] for i in ids]

    # 2. rerank top 5
    reranked = rerank(query, docs, top_k=5)

    # 3. 生成
    resp = client.chat.completions.create(
        model="claude-sonnet-4-6",
        messages=[
            {"role": "system", "content": "你是严谨的助理。"},
            {"role": "user", "content": build_prompt(query, reranked)},
        ],
    )
    return resp.choices[0].message.content
```

## 十、评估

不评估的 RAG 都在裸奔。最小评估：

```python
test_set = [
    {"q": "公司的 RAG 接入文档在哪？", "expected": "docs/rag-onboarding.md"},
    {"q": "支付回调失败怎么排查？", "expected_keywords": ["webhook", "重试"]},
]

for case in test_set:
    answer = rag_answer(case["q"])
    if "expected" in case:
        passed = case["expected"] in answer
    else:
        passed = all(k in answer for k in case["expected_keywords"])
    print(f"{'PASS' if passed else 'FAIL'}: {case['q']}")
```

每周跑一次回归测试，效果倒退能立刻发现。

## 十一、常见踩坑

| 问题 | 处理 |
| --- | --- |
| 召回率低 | 加 BM25 混合、调小 chunk |
| 答案漂移 | system prompt 强约束、加 rerank |
| 中文专有名词识别差 | 自训 embedding 或换模型 |
| 表格数据丢失 | 用专门的 table 解析 |
| 同义词检索不到 | 加 query 扩展（LLM 重写 query） |

## 十二、相关阅读

- [Embeddings API 国内对比](/blog/embeddings-api-cn-comparison/)
- [Cherry Studio 国内 API 中转配置指南](/blog/cherry-studio-cn-config/)
- [Gemini API 国内调用指南](/blog/gemini-api-cn-guide/)
- [Python 异步并发调用 LLM API 实战](/blog/python-async-llm-client/)

构建 RAG 需要 embedding + chat + rerank 三种接口？[YoTradeApi](https://yotradeapi.com/register) 一把 Key 全覆盖，按上面流程接入。
