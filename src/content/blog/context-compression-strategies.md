---
title: 上下文压缩 5 种策略对比：Token 节省与质量权衡
description: 系统对比摘要压缩、滑动窗口、RAG 检索替换、结构化截断和 KV Cache 共享五种上下文压缩策略，含代码示例与成本对比。
keywords:
  - 上下文压缩策略
  - LLM Token 优化
  - 对话历史压缩
  - RAG 上下文替换
  - 大模型成本节省
pubDate: '2026-06-25'
updatedDate: '2026-06-25'
canonical: https://blog.yotradeapi.com/blog/context-compression-strategies/
tags:
  - 成本优化
  - 上下文管理
  - Token 节省
  - LLM 工程
category: 成本优化
heroImage: ../../assets/blog-placeholder-5.jpg
---

随着对话轮次增加，上下文长度成为 AI 应用成本和性能的双重瓶颈。Token 费用随上下文线性增长，而模型的有效注意力在超长上下文中往往开始分散，反而降低输出质量。上下文压缩（Context Compression）是在"保留必要信息"与"削减无用 Token"之间找平衡点的工程实践。

本文系统对比五种主流压缩策略：**摘要压缩**、**滑动窗口**、**RAG 检索替换**、**结构化截断**、**KV Cache 共享**，从实现复杂度、Token 节省率、质量损失三个维度给出可操作的判断框架。

---

## 一、为什么需要上下文压缩

先量化一下不压缩的代价。以 GPT-4o 为例（近似参考，以官网实时定价为准）：

| 场景 | 上下文长度 | 每次调用成本（估算） | 100 次/日 |
|------|---------|-----------------|---------|
| 短对话（10 轮） | ~2K tokens | ~¥0.02 | ~¥2 |
| 中等对话（50 轮） | ~10K tokens | ~¥0.10 | ~¥10 |
| 长对话（200 轮） | ~40K tokens | ~¥0.40 | ~¥40 |
| 超长对话（500 轮） | ~100K tokens | ~¥1.00 | ~¥100 |

成本随对话轮次**线性叠加**——第 100 轮的调用需要把前 99 轮都塞进去，费用远高于第 1 轮。对于高频、多轮的 AI 产品，不压缩意味着成本随用户行为失控增长。

此外，研究表明超长上下文下 LLM 的注意力存在"Lost in the Middle"现象——模型对位于上下文中间段的信息关注度显著低于开头和结尾，这意味着盲目堆砌历史不一定带来更好的回答质量。

---

## 二、策略一：摘要压缩

**核心思路**：定期将历史对话摘要成一段简短文本，用摘要替换原始历史。

```python
from openai import OpenAI

client = OpenAI(api_key="your_key")

def compress_history_with_summary(
    history: list[dict],
    keep_recent: int = 4,
    summarize_model: str = "gpt-4o-mini",
) -> list[dict]:
    """
    保留最近 keep_recent 轮，将更早的历史摘要为一段文字。
    """
    if len(history) <= keep_recent * 2:
        return history  # 不够长，不压缩
    
    # 待摘要的旧历史
    old_history = history[: -keep_recent * 2]
    recent_history = history[-keep_recent * 2 :]
    
    # 构建摘要请求
    summary_prompt = "请将以下对话历史摘要为 3-5 句话，保留关键决策、用户偏好和重要信息：\n\n"
    for msg in old_history:
        role = "用户" if msg["role"] == "user" else "助手"
        summary_prompt += f"{role}：{msg['content']}\n"
    
    summary_response = client.chat.completions.create(
        model=summarize_model,
        messages=[{"role": "user", "content": summary_prompt}],
        max_tokens=300,
    )
    summary_text = summary_response.choices[0].message.content
    
    # 将摘要作为系统消息插入历史开头
    compressed = [
        {"role": "system", "content": f"[历史摘要] {summary_text}"}
    ] + recent_history
    
    return compressed
```

**适用场景**：通用对话助手、客服机器人，对话内容有较强的叙事连贯性。

**权衡**：
- Token 节省：60–80%（旧历史变成几百字的摘要）
- 质量损失：中等——细节信息会丢失，用户说的具体数字、代码片段通常无法完整保留
- 额外成本：每次压缩需调用一次摘要模型，建议用 mini 版本降低摘要成本

---

## 三、策略二：滑动窗口（最近 N 轮）

**核心思路**：只保留最近 N 轮对话，丢弃更早的历史。

```python
def sliding_window(
    history: list[dict],
    max_rounds: int = 10,
    system_message: str | None = None,
) -> list[dict]:
    """
    保留最近 max_rounds 轮（一轮 = 一问一答）。
    """
    # 过滤出非 system 消息
    non_system = [m for m in history if m["role"] != "system"]
    
    # 每轮 2 条消息（user + assistant）
    keep_count = max_rounds * 2
    windowed = non_system[-keep_count:] if len(non_system) > keep_count else non_system
    
    # 确保第一条是 user 消息（防止孤立的 assistant 消息）
    while windowed and windowed[0]["role"] == "assistant":
        windowed = windowed[1:]
    
    # 重新加入 system 消息
    if system_message:
        return [{"role": "system", "content": system_message}] + windowed
    return windowed
```

**适用场景**：短记忆任务（代码调试、翻译、单次问答），用户每隔几轮就换新话题。

**权衡**：
- Token 节省：取决于窗口大小，设置合理时可节省 50–70%
- 质量损失：当对话跨越窗口边界时（用户引用 20 轮前的决定），模型会"失忆"
- 实现复杂度：最低，几行代码即可

**推荐参数**：一般任务 10–20 轮，代码调试等上下文依赖强的场景适当加大到 30 轮。

---

## 四、策略三：RAG 检索替换

**核心思路**：不把历史全量放入上下文，而是将历史向量化存储，每轮按当前问题检索最相关的 K 条。

```python
from openai import OpenAI
import numpy as np

client = OpenAI(api_key="your_key")

class VectorMemory:
    def __init__(self, embed_model: str = "text-embedding-3-small"):
        self.embed_model = embed_model
        self.memories: list[dict] = []  # [{text, embedding, role, timestamp}]
    
    def _embed(self, text: str) -> list[float]:
        response = client.embeddings.create(
            model=self.embed_model,
            input=text,
        )
        return response.data[0].embedding
    
    def add(self, role: str, content: str):
        embedding = self._embed(content)
        self.memories.append({
            "role": role,
            "content": content,
            "embedding": embedding,
        })
    
    def retrieve(self, query: str, top_k: int = 5) -> list[dict]:
        if not self.memories:
            return []
        query_emb = np.array(self._embed(query))
        
        scores = []
        for mem in self.memories:
            mem_emb = np.array(mem["embedding"])
            # 余弦相似度
            cos_sim = np.dot(query_emb, mem_emb) / (
                np.linalg.norm(query_emb) * np.linalg.norm(mem_emb) + 1e-8
            )
            scores.append(cos_sim)
        
        # 返回 top_k 最相关的历史
        top_indices = np.argsort(scores)[-top_k:][::-1]
        return [self.memories[i] for i in top_indices]
    
    def build_context(self, query: str, top_k: int = 5) -> list[dict]:
        relevant = self.retrieve(query, top_k)
        # 转换为消息格式，按时间顺序排列
        return [{"role": m["role"], "content": m["content"]} for m in relevant]
```

**适用场景**：长期记忆场景（个人助手、用户偏好记忆），对话历史超过 100 轮。

**权衡**：
- Token 节省：非常高（原来 100 轮历史，每次只取 5 条），可节省 90%+
- 质量损失：依赖检索质量，主题跳跃时检索准确率下降；顺序信息丢失
- 额外成本：Embedding API 调用成本，通常远低于大量 Token 的成本

---

## 五、策略四：结构化截断

**核心思路**：不均匀截断，而是识别内容类型并优先保留高价值内容（代码、表格、决策点），压缩低价值内容（重复确认、礼貌用语）。

```python
import re

def structured_truncation(
    history: list[dict],
    target_tokens: int = 4000,
    tokens_per_char: float = 0.4,  # 中文约 0.4 token/字符
) -> list[dict]:
    """
    结构化截断：保留代码块和高权重消息，压缩低价值轮次。
    """
    def estimate_tokens(text: str) -> int:
        return max(1, int(len(text) * tokens_per_char))
    
    def message_priority(msg: dict) -> int:
        content = msg.get("content", "")
        # 包含代码块的消息优先级高
        if "```" in content:
            return 3
        # 包含列表/表格（结构化信息）优先级中等
        if re.search(r"^\s*[-*|]\s", content, re.MULTILINE):
            return 2
        # 短确认消息（"好的"、"明白了"）优先级低
        if len(content) < 20:
            return 0
        return 1
    
    # 系统消息始终保留
    system_msgs = [m for m in history if m["role"] == "system"]
    other_msgs = [m for m in history if m["role"] != "system"]
    
    # 按优先级从低到高排列，从尾部优先保留
    scored = [(message_priority(m), i, m) for i, m in enumerate(other_msgs)]
    scored.sort(key=lambda x: (x[0], x[1]))  # 优先级低的在前（先被丢弃）
    
    # 从高优先级开始添加，直到达到 token 预算
    used_tokens = sum(estimate_tokens(m.get("content", "")) for m in system_msgs)
    kept_indices = set()
    
    for priority, idx, msg in reversed(scored):
        cost = estimate_tokens(msg.get("content", ""))
        if used_tokens + cost <= target_tokens:
            kept_indices.add(idx)
            used_tokens += cost
    
    # 按原始顺序重组
    kept = [msg for i, msg in enumerate(other_msgs) if i in kept_indices]
    return system_msgs + kept
```

**适用场景**：代码助手、技术支持场景，历史中代码片段价值高、闲聊价值低。

**权衡**：
- Token 节省：中等（30–60%），因为高价值内容通常较长
- 质量损失：低——重要信息被优先保留
- 实现复杂度：中等，需要针对业务场景调整优先级规则

---

## 六、策略五：KV Cache 共享（Prompt Cache）

**核心思路**：这不是截断历史，而是利用大模型的 KV Cache 机制，让重复的前缀只计算一次 Token 费用。

适用于有固定长 System Prompt 的场景（如知识库系统提示、角色人设）。

```python
# Claude API 的 Prompt Caching 示例
import anthropic

client_claude = anthropic.Anthropic(api_key="your_key")

# 将固定的大块 System Prompt 标记为可缓存
response = client_claude.messages.create(
    model="claude-opus-4-8",
    max_tokens=1024,
    system=[
        {
            "type": "text",
            "text": "你是一个专业的金融分析师助手...",
        },
        {
            "type": "text",
            "text": "<这里是 10000 字的公司知识库内容>",
            "cache_control": {"type": "ephemeral"},  # 标记为可缓存
        }
    ],
    messages=[{"role": "user", "content": user_question}],
)

# 第一次调用：全量计算，写入 cache
# 后续 5 分钟内的调用：缓存命中，输入 Token 按折扣价计费（约 10% 原价）
```

**OpenAI 的 Prompt Caching** 是自动进行的（对 1024+ Token 的共同前缀自动缓存），无需代码修改，只需确保每次调用的消息前缀保持一致。

**适用场景**：有大量固定 System Prompt（文档知识库、角色设定），高并发场景（多用户共享同一前缀）。

**权衡**：
- Token 节省：对缓存命中的 Token 节省 80–90%（具体折扣因供应商而异）
- 质量损失：零——内容完全不变，只是计费优化
- 实现复杂度：低（Claude 需显式标记，OpenAI 自动处理）

---

## 七、五种策略横向对比

| 策略 | Token 节省率 | 质量损失 | 实现复杂度 | 额外成本 | 最佳场景 |
|------|------------|---------|----------|---------|---------|
| 摘要压缩 | 60–80% | 中 | 低 | 摘要调用费 | 通用对话 |
| 滑动窗口 | 50–70% | 低–中 | 极低 | 无 | 短记忆任务 |
| RAG 检索替换 | 85–95% | 中（依检索） | 高 | Embedding 费 | 长期记忆 |
| 结构化截断 | 30–60% | 低 | 中 | 无 | 代码/技术场景 |
| KV Cache 共享 | 对缓存部分 80–90% | 零 | 极低 | 无 | 固定长前缀 |

---

## 八、组合策略：实战中如何选择

单一策略很少能完美解决所有场景，实践中常用组合：

**组合一（轻量级）**：滑动窗口 + KV Cache 共享
- System Prompt 固定且长 → KV Cache 降低前缀成本
- 历史只保留最近 10 轮 → 滑动窗口控制对话长度
- 适合：快速上线的对话产品，不想引入 Embedding 依赖

**组合二（中等复杂度）**：摘要压缩 + 滑动窗口
- 每 20 轮触发一次摘要，将旧历史压缩成摘要
- 摘要 + 最近 5 轮进入上下文
- 适合：需要一定长程记忆的助手，可接受 5–10% 质量损失

**组合三（高复杂度）**：RAG 检索 + 结构化截断 + KV Cache
- 历史存入向量库，每轮检索相关记忆
- 结构化截断保证代码/决策高优先
- 固定知识库用 KV Cache
- 适合：个人助手、长期项目协作 AI，对记忆质量要求高

更多 Token 成本控制的系统性方法，可参考 [LLM 成本优化清单](/blog/llm-cost-optimization-checklist/) 和 [LLM Prompt Token 精简实战](/blog/llm-prompt-token-trimming-recipes/)。

---

## 九、相关阅读

- [LLM 成本优化清单](/blog/llm-cost-optimization-checklist/)
- [LLM Prompt Token 精简实战](/blog/llm-prompt-token-trimming-recipes/)
- [AI 对话上下文管理实践](/blog/ai-chatbot-context-management/)
- [AI 流水线的错误追踪方案](/blog/ai-pipeline-error-tracing/)
- [Claude 1M 上下文窗口使用指南](/blog/claude-1m-context-guide/)

如果你在压缩上下文的同时还希望统一多模型的 API 调用，[YoTradeApi](https://yotradeapi.com) 提供 OpenAI 兼容接口，支持 GPT-4o、Claude、Gemini 等主流模型，一套代码可以横向测试哪个模型在相同压缩策略下效果最好。
