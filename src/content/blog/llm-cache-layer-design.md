---
title: LLM 应用缓存层设计：从语义缓存到 Prompt 缓存的完整方案
description: 系统讲解 LLM 应用的缓存层架构，涵盖语义缓存、Prompt Caching、结果缓存三大策略，帮助降低 API 成本 60% 以上。
keywords:
  - LLM 缓存层设计
  - 语义缓存
  - Prompt Caching
  - LLM API 成本优化
  - AI 应用缓存架构
pubDate: '2026-06-24'
updatedDate: '2026-06-24'
canonical: https://blog.yotradeapi.com/blog/llm-cache-layer-design/
tags:
  - LLM
  - 缓存
  - 应用工程
  - 成本优化
  - 架构设计
category: 应用工程
heroImage: ../../assets/blog-placeholder-3.jpg
---

LLM API 调用成本高、延迟长是每个生产级 AI 应用都绕不开的问题。缓存是最直接的解法——但 LLM 请求的多样性让"缓存"二字远比传统 HTTP 缓存复杂得多。本文系统梳理三大缓存策略，帮你在实际项目中找到合适的落地路径。

## 一、为什么 LLM 应用特别需要缓存

传统 Web 应用里，缓存命中率取决于请求的重复度。LLM 应用有几个独特性：

- **Token 计费模式**：每次调用按输入 + 输出 token 数计费，相同 prompt 重复调用等于重复花钱
- **延迟敏感**：GPT-4o / Claude 3.5 的 P50 延迟普遍在 1–3 秒，缓存命中可降至毫秒级
- **用户问题高度重叠**：客服、问答类产品中，80% 的问题往往集中在 20% 的话题上（典型长尾分布）
- **System Prompt 反复发送**：大量 token 花在每次都一样的 system prompt 上

根据不同产品类型，合理的缓存策略可以将 API 费用降低 40%–70%。

## 二、三大缓存层

LLM 应用缓存可以分三个层次，从浅到深依次是：

| 层次 | 技术方案 | 适用场景 | 命中率范围 |
|------|---------|---------|-----------|
| 精确匹配缓存 | Redis KV / 哈希 | 完全相同的请求 | 5%–20% |
| 语义缓存 | 向量相似度 | 同义问法 | 30%–60% |
| Prompt Caching | API 原生支持 | 长 System Prompt | 80%+ |

三层可以叠加使用，下面逐层展开。

## 三、精确匹配缓存：最简单的起点

对于完全相同的输入（包括 system prompt + user message），用 MD5/SHA256 哈希作 key，将结果存入 Redis。

```python
import hashlib, json, redis

client = redis.Redis()

def cache_key(messages: list, model: str) -> str:
    payload = json.dumps({"model": model, "messages": messages}, sort_keys=True)
    return "llm:" + hashlib.sha256(payload.encode()).hexdigest()

def llm_call_with_exact_cache(messages, model="gpt-4o"):
    key = cache_key(messages, model)
    cached = client.get(key)
    if cached:
        return json.loads(cached)
    
    response = openai_client.chat.completions.create(
        model=model, messages=messages
    )
    result = response.choices[0].message.content
    client.setex(key, 3600, json.dumps(result))  # 1h TTL
    return result
```

**适合场景**：
- 代码生成器里固定模板的调用（如"帮我写单元测试"）
- 数据提取任务（相同文档 + 相同 prompt）
- 定时批量任务中的重复数据行

**局限**：用户措辞稍有变化就无法命中，实际命中率通常低于 20%。

## 四、语义缓存：同义问法的破局之道

语义缓存的核心思路：把历史问答的 embedding 存入向量数据库，新请求进来先做相似度检索，相似度超过阈值就复用旧答案。

```python
from openai import OpenAI
import numpy as np

openai = OpenAI()

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

class SemanticCache:
    def __init__(self, threshold=0.92):
        self.threshold = threshold
        self.store = []  # 生产中换成 Pinecone / Qdrant / pgvector
    
    def embed(self, text: str) -> list:
        resp = openai.embeddings.create(
            model="text-embedding-3-small", input=text
        )
        return resp.data[0].embedding
    
    def lookup(self, query: str):
        q_emb = self.embed(query)
        for item in self.store:
            sim = cosine_similarity(q_emb, item["embedding"])
            if sim >= self.threshold:
                return item["answer"]
        return None
    
    def save(self, query: str, answer: str):
        self.store.append({
            "embedding": self.embed(query),
            "answer": answer,
            "query": query
        })
```

**阈值选择建议**：
- `0.95+`：只命中几乎一字不差的问法，误命中率极低
- `0.90–0.95`：同义表达基本都命中，偶有语义漂移
- `< 0.90`：命中率高但误判多，慎用

语义缓存的缺点是 embedding 本身也有延迟和费用。`text-embedding-3-small` 约 $0.02/1M token，换来的收益通常值得。

## 五、Prompt Caching：API 原生的成本杀手

目前 Claude（Anthropic）和 GPT-4o（OpenAI）都支持 Prompt Caching，本质是在模型提供商端缓存 KV 计算结果。

**Claude 的 Prompt Caching**（官方支持最完善）：

```python
import anthropic

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-opus-4-8",
    max_tokens=1024,
    system=[
        {
            "type": "text",
            "text": "你是一个专业的代码审查助手。" + long_context,  # 几千 token 的背景
            "cache_control": {"type": "ephemeral"}  # 标记为可缓存
        }
    ],
    messages=[{"role": "user", "content": user_question}]
)
```

缓存命中时，`cache_read_input_tokens` 的计费是正常输入 token 的 **10%**（claude-opus-4-8）。对于频繁调用同一个长 system prompt 的场景，节省极其显著。

详细的 ROI 分析可以参考 [Claude Prompt Caching 使用与收益分析](/blog/claude-prompt-caching-roi-analysis/)。

**触发条件**：
- Claude：system prompt 超过 1024 token 才有意义，缓存 TTL 5 分钟（活跃调用时自动续期）
- GPT-4o：prefix 超过 1024 token 自动启用，无需显式标记

## 六、三层组合的最佳实践

在实际项目中，三层缓存通常按下面的顺序组合：

```
请求进来
  ↓
[L1] 精确匹配缓存（Redis）
  命中 → 返回，< 1ms
  未命中 ↓
[L2] 语义缓存（向量数据库）
  命中（相似度 ≥ 0.92）→ 返回，< 50ms
  未命中 ↓
[L3] LLM API 调用（含 Prompt Caching）
  → 写回 L1 + L2 缓存
  → 返回结果，1–5s
```

这个架构在客服问答类产品中，实测综合命中率可以到 55%–65%。

## 七、缓存失效策略

缓存最难的部分是失效。LLM 应用常见的失效触发：

- **知识库更新**：RAG 系统里文档变更后，相关 query 的缓存需要作废
- **Prompt 迭代**：system prompt 改了，所有缓存应清空（用 prompt 版本号作 key 的一部分）
- **时效性内容**：涉及"今天""最新"等时态词的问题不应缓存，或 TTL 设为几分钟

```python
def cache_key_v2(messages, model, prompt_version):
    """加入 prompt 版本号，Prompt 更新后自动 miss"""
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "prompt_v": prompt_version
    }, sort_keys=True)
    return "llm:v2:" + hashlib.sha256(payload.encode()).hexdigest()
```

时效性过滤可以用简单的关键词检测：

```python
TEMPORAL_KEYWORDS = ["今天", "现在", "最新", "刚才", "当前", "这周"]

def is_temporal_query(text: str) -> bool:
    return any(kw in text for kw in TEMPORAL_KEYWORDS)
```

## 八、监控与调优

上线后需要持续观察几个指标：

- **缓存命中率**（分层）：精确命中 / 语义命中 / miss 各占多少
- **语义误命中率**：命中后用户是否追问"这个答案不对"——是的话阈值需要调高
- **实际节省金额**：折算成 token 差价，衡量缓存 ROI

一个简单的埋点模板：

```python
import time

def tracked_llm_call(query, ...):
    start = time.time()
    
    # L1 检查
    if exact := exact_cache.get(query):
        metrics.record("cache_hit", layer="l1", latency=time.time()-start)
        return exact
    
    # L2 检查
    if semantic := semantic_cache.lookup(query):
        metrics.record("cache_hit", layer="l2", latency=time.time()-start)
        return semantic
    
    # 真实调用
    result = llm_api_call(query)
    metrics.record("cache_miss", latency=time.time()-start)
    exact_cache.set(query, result)
    semantic_cache.save(query, result)
    return result
```

## 九、相关阅读

- [Claude Prompt Caching ROI 分析](/blog/claude-prompt-caching-roi-analysis/)
- [AI Agent 成本监控实践](/blog/ai-agent-cost-monitoring/)
- [AI API 预算上限设计方案](/blog/ai-api-budget-cap-design/)
- [AI 编程每月实际花费](/blog/ai-coding-monthly-cost-real/)
- [Prompt 版本管理最佳实践](/blog/ai-prompt-versioning/)

如果你在寻找稳定、低成本的 LLM API 接入方案，[YoTradeApi](https://yotradeapi.com) 提供国内直连、按量计费的 Claude / GPT-4o / Gemini 中转服务，配合缓存层可以将综合成本压到更低。
