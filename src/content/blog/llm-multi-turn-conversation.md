---
title: LLM 多轮对话状态管理
description: 系统讲解 LLM 多轮对话中的状态管理策略，涵盖上下文截断、摘要压缩、外部记忆存储与工程实现。
keywords:
  - LLM 多轮对话
  - 对话状态管理
  - 上下文窗口管理
  - Claude 多轮对话
  - 对话历史截断
pubDate: '2026-06-11'
updatedDate: '2026-06-11'
canonical: https://blog.yotradeapi.com/blog/llm-multi-turn-conversation/
tags:
  - LLM
  - 应用工程
  - 对话系统
  - 技术深度
category: 应用工程
heroImage: ../../assets/blog-placeholder-4.jpg
---

构建多轮对话应用是 LLM 工程中最容易踩坑的领域之一。表面上只是"把历史消息放进 messages 数组"，但在生产环境跑上几周后，你会遇到：上下文超出窗口限制、费用因历史消息急速攀升、对话偏离主题越来越远、用户换了个话题但模型还在"纠结"之前的内容……

这些问题都指向同一个根本：**状态管理**。

本文系统梳理多轮对话状态管理的核心策略，给出可直接落地的工程方案。

## 一、多轮对话的状态本质

LLM 本身是**无状态的**。每次 API 调用都是一次独立推理，"记住之前说了什么"完全依赖你传入的 `messages` 数组。

这意味着"对话状态"实际上是你的应用层在维护，而不是模型端。这个认知很重要——它意味着状态设计的自由度和责任都在应用侧。

一次典型的多轮对话 API 调用结构：

```python
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    system="你是一个有帮助的助手。",
    messages=[
        {"role": "user", "content": "我想做一个 Todo 应用"},
        {"role": "assistant", "content": "好的，你用什么语言开发？"},
        {"role": "user", "content": "Python，用 FastAPI"},
        {"role": "assistant", "content": "..."},
        {"role": "user", "content": "帮我设计数据库表结构"},  # 当前轮
    ]
)
```

随着对话进行，`messages` 数组越来越长，问题随之出现。

## 二、核心矛盾：窗口有限 vs 对话无限

以 Claude Sonnet 4.6 为例，上下文窗口为 200K tokens，看起来很大，但：

- 一次对话 20 轮，每轮平均 500 tokens（用户）+ 800 tokens（助手）= 26,000 tokens
- 100 轮对话 ≈ 130,000 tokens，已接近窗口上限
- 费用：输入 token 按量计费，历史消息越长越贵

更关键的是，**窗口大小不等于有效注意力范围**。过长的历史消息会降低模型对近期内容的关注度，出现"遗忘"现象。

所以即使窗口够大，也不意味着无限堆消息是最优解。

## 三、四种状态管理策略

### 策略一：滑动窗口截断

最简单的方案：保留最近 N 轮对话，超出则丢弃最早的部分。

```python
def trim_messages(messages: list, max_turns: int = 20) -> list:
    """保留最近 max_turns 轮（每轮含 user + assistant 共 2 条消息）"""
    if len(messages) <= max_turns * 2:
        return messages
    # 始终保留第一条（通常是重要的用户意图）
    return [messages[0]] + messages[-(max_turns * 2 - 1):]
```

**优点**：实现简单，效果可预期
**缺点**：被截断的历史信息完全丢失，对需要引用早期内容的对话不友好

**适用场景**：客服问答、任务导向型对话（用户通常不会引用很久之前的内容）

### 策略二：Token 预算控制

比轮次截断更精准：按 token 数量而非轮数控制历史长度。

```python
import tiktoken  # 或使用 anthropic 的 token 计数接口

def trim_to_token_budget(messages: list, budget: int = 50000) -> list:
    """从最旧的消息开始删除，直到 token 数在预算内"""
    # 估算 token（实际应用中用精确计数）
    def count_tokens(msgs):
        return sum(len(m["content"].split()) * 1.3 for m in msgs)  # 粗估
    
    result = messages[:]
    while count_tokens(result) > budget and len(result) > 2:
        # 保留最新的用户消息，删除最旧的 user+assistant 对
        result.pop(0)
        if result and result[0]["role"] == "assistant":
            result.pop(0)
    return result
```

**适用场景**：对费用敏感、且对话长度不可预测的场景

### 策略三：摘要压缩（推荐）

不是简单丢弃，而是**把旧对话总结成摘要**，摘要保留在 system prompt 中，原始消息删除。

```python
async def summarize_old_turns(client, messages: list, keep_recent: int = 10) -> tuple:
    """
    将 messages 中超出 keep_recent 轮的部分压缩成摘要
    返回：(摘要文本, 保留的近期消息)
    """
    if len(messages) <= keep_recent * 2:
        return "", messages
    
    to_summarize = messages[:-keep_recent * 2]
    recent = messages[-keep_recent * 2:]
    
    summary_prompt = f"""请将以下对话历史压缩成 200 字以内的要点摘要，
保留关键决策、用户偏好和重要上下文：

{format_messages(to_summarize)}"""
    
    resp = await client.messages.create(
        model="claude-haiku-4-5-20251001",  # 用便宜模型做摘要
        max_tokens=300,
        messages=[{"role": "user", "content": summary_prompt}]
    )
    return resp.content[0].text, recent


async def build_messages_with_summary(client, full_history: list) -> tuple:
    summary, recent = await summarize_old_turns(client, full_history)
    system_addon = f"\n\n[早期对话摘要]\n{summary}" if summary else ""
    return system_addon, recent
```

调用时将摘要附加到 system prompt：

```python
summary_addon, trimmed_messages = await build_messages_with_summary(client, conversation_history)

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    system=base_system + summary_addon,
    messages=trimmed_messages
)
```

**优点**：信息损失最小，历史重要内容以压缩形式保留
**缺点**：额外引入一次（廉价）API 调用；摘要质量影响后续对话

**适用场景**：长期陪伴助手、复杂项目协作、用户可能引用早期内容的场景

### 策略四：外部记忆存储

对于需要跨会话持久化的场景（用户第二天继续上次的对话），单靠 `messages` 数组不够——需要外部存储。

```python
from dataclasses import dataclass
import json

@dataclass
class ConversationMemory:
    user_id: str
    preferences: dict      # 用户偏好（语言、风格等）
    key_facts: list        # 关键事实（用户说过的重要信息）
    ongoing_tasks: list    # 未完成任务
    last_summary: str      # 上次会话摘要

class MemoryManager:
    def __init__(self, storage_backend):  # Redis / PostgreSQL / etc.
        self.storage = storage_backend
    
    def load(self, user_id: str) -> ConversationMemory:
        data = self.storage.get(f"memory:{user_id}")
        if not data:
            return ConversationMemory(user_id, {}, [], [], "")
        return ConversationMemory(**json.loads(data))
    
    def save(self, memory: ConversationMemory):
        self.storage.set(
            f"memory:{memory.user_id}",
            json.dumps(memory.__dict__),
            ex=30 * 24 * 3600  # 30 天过期
        )
    
    def build_system_context(self, memory: ConversationMemory) -> str:
        parts = []
        if memory.last_summary:
            parts.append(f"[上次对话摘要] {memory.last_summary}")
        if memory.preferences:
            parts.append(f"[用户偏好] {json.dumps(memory.preferences, ensure_ascii=False)}")
        if memory.key_facts:
            parts.append(f"[已知事实] {'; '.join(memory.key_facts)}")
        return "\n".join(parts)
```

这套方案让"记忆"从对话窗口中解耦，可以独立维护和更新。

## 四、实际场景中的组合策略

生产环境中，上述策略通常组合使用：

```
新对话开始
  ↓
加载用户长期记忆（策略四）
  ↓
构建 system prompt（基础 + 长期记忆摘要）
  ↓
对话进行中（每轮追加 messages）
  ↓
消息数超过阈值？
  ├── 是 → 执行摘要压缩（策略三），更新 system prompt
  └── 否 → 继续
  ↓
会话结束
  ↓
生成会话摘要 → 写回长期记忆（策略四）
```

| 层级 | 机制 | 时效 |
|---|---|---|
| 当前轮 | 最近 N 轮消息原文 | 本次会话内 |
| 会话内压缩 | 摘要写入 system prompt | 本次会话内 |
| 跨会话记忆 | 持久化存储 | 长期 |

## 五、与 Prompt Caching 联动

如果你的 system prompt 很长（含大量长期记忆），可以配合 prompt caching 降低费用：

```python
messages_create_params = {
    "model": "claude-sonnet-4-6",
    "max_tokens": 1024,
    "system": [
        {
            "type": "text",
            "text": long_system_prompt,
            "cache_control": {"type": "ephemeral"}  # 缓存，5 分钟内重复调用省钱
        }
    ],
    "messages": trimmed_messages
}
```

对于高频对话（用户每隔几分钟发一条），system prompt 缓存命中率极高，可以把输入费用降低 80%+。

## 六、监控与调试建议

状态管理是个持续优化的过程，需要监控指标：

- **平均历史长度**（token）：观察截断策略是否生效
- **摘要触发频率**：摘要太频繁说明对话平均长度超预期
- **用户引用历史的比例**：如果用户经常说"你之前说的那个方案"，说明截断丢失了重要信息
- **模型输出质量**：对比有/无历史摘要的回答一致性

一个简单的日志记录方案：

```python
import logging

def log_conversation_state(user_id: str, messages_count: int, 
                           total_tokens: int, summary_used: bool):
    logging.info(json.dumps({
        "event": "conversation_state",
        "user_id": user_id,
        "turns": messages_count // 2,
        "total_tokens": total_tokens,
        "summary_used": summary_used
    }))
```

## 七、相关阅读

- [LLM Context Engineering 上下文工程实践](/blog/llm-context-engineering/)
- [Claude 1M 上下文窗口实战使用指南](/blog/claude-1m-context-guide/)
- [AI Agent 记忆与状态设计模式](/blog/ai-agent-memory-design/)
- [Claude Message Batches 50% 折扣实战](/blog/claude-message-batches-savings/)
- [Claude Agent SDK 中文入门指南](/blog/claude-agent-sdk-cn/)

构建多轮对话应用时，[YoTradeApi](https://yotradeapi.com) 提供稳定的 Claude API 中转，支持完整的多轮 messages 格式与 prompt caching，助你低成本实现高质量对话体验。
