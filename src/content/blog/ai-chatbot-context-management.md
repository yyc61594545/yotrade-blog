---
title: AI Chatbot 上下文管理与裁剪：工程实践完整指南
description: 深入讲解 AI Chatbot 的上下文管理策略：滑动窗口、摘要压缩、重要性评分裁剪等方法，含 Python 代码示例，帮你在保持对话连贯性的同时控制 Token 成本。
keywords:
  - AI Chatbot 上下文管理
  - LLM 对话历史裁剪
  - Chatbot Token 控制
  - 对话上下文压缩
  - 多轮对话工程实践
  - AI 对话内存管理
pubDate: '2026-06-19'
updatedDate: '2026-06-19'
canonical: https://blog.yotradeapi.com/blog/ai-chatbot-context-management/
tags:
  - Chatbot
  - 应用工程
  - 上下文管理
  - Token优化
category: 应用工程
heroImage: ../../assets/blog-placeholder-5.jpg
---

构建 AI Chatbot 时，有一个问题会在上线后迟早出现：**用户对话越来越长，成本直线上升，而某个时间点之后，模型开始「忘记」早先的对话内容**。

这两个问题本质上都源于同一个约束：LLM 的上下文窗口是有限的。虽然 Claude 支持 200K token 上下文、GPT-4o 支持 128K，但把整个对话历史每次都全量发送既昂贵又低效。

本文从工程角度，系统梳理 AI Chatbot 上下文管理的主要策略：什么时候裁剪、裁剪什么、怎么裁剪，以及各种策略的取舍。

## 一、问题的本质：上下文是有成本的

在深入策略之前，先量化一下上下文累积的成本影响。

假设你的 Chatbot：
- 每轮平均输入 100 tokens（用户消息）
- 每轮平均输出 300 tokens（助手回复）
- 不做任何裁剪，全量发送对话历史

| 第 N 轮 | 发送的历史 tokens | 本轮输入总量 |
|--------|----------------|------------|
| 第 1 轮 | 0 | 100 |
| 第 5 轮 | 4 × 400 = 1,600 | 1,700 |
| 第 10 轮 | 9 × 400 = 3,600 | 3,700 |
| 第 20 轮 | 19 × 400 = 7,600 | 7,700 |
| 第 50 轮 | 49 × 400 = 19,600 | 19,700 |

一个 50 轮的对话，最后一条消息的处理成本是第 1 轮的 197 倍。对于高并发产品，这个差异直接影响月度 API 账单数量级。

## 二、策略一：固定窗口截断（最简单）

最直接的方案：只保留最近 N 轮对话。

```python
from anthropic import Anthropic

client = Anthropic()

def chat_with_window(
    messages: list[dict],
    user_input: str,
    system_prompt: str,
    max_turns: int = 10
) -> tuple[str, list[dict]]:
    
    messages.append({"role": "user", "content": user_input})
    
    # 固定窗口：只保留最近 max_turns 轮（每轮 2 条消息）
    window_messages = messages[-(max_turns * 2):]
    
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system_prompt,
        messages=window_messages
    )
    
    reply = response.content[0].text
    messages.append({"role": "assistant", "content": reply})
    
    return reply, messages
```

**优点**：实现简单，token 成本可预测，延迟稳定。

**缺点**：硬截断会导致模型忘记早期重要信息（比如用户在第 2 轮说的需求，第 20 轮时完全消失）。适合场景：客服对话、单次任务咨询（大多数对话不超过 10 轮）。

## 三、策略二：Token 数量限制（更精细的固定窗口）

固定「轮数」有时不够准确（每轮长短差异很大）。按 token 数量限制更可控：

```python
import anthropic

def count_tokens(messages: list[dict], model: str = "claude-sonnet-4-6") -> int:
    client = anthropic.Anthropic()
    response = client.messages.count_tokens(
        model=model,
        messages=messages
    )
    return response.input_tokens

def trim_to_token_limit(
    messages: list[dict],
    max_tokens: int = 8000,
    model: str = "claude-sonnet-4-6"
) -> list[dict]:
    """从最旧的消息开始丢弃，直到总 token 数在限制内"""
    
    if len(messages) == 0:
        return messages
    
    # 至少保留最新一条用户消息
    if count_tokens(messages, model) <= max_tokens:
        return messages
    
    # 从头部开始移除，成对移除（user + assistant）
    trimmed = list(messages)
    while len(trimmed) > 2 and count_tokens(trimmed, model) > max_tokens:
        trimmed = trimmed[2:]  # 移除最早的一对 user/assistant 消息
    
    return trimmed
```

这种方式比固定轮数更精确，但需要调用 token 计数 API（会产生少量额外成本）。

## 四、策略三：摘要压缩（保留语义，节省 Token）

当对话很长时，与其把早期对话全部丢弃，不如先**摘要压缩**：

```python
def summarize_old_messages(
    old_messages: list[dict],
    model: str = "claude-haiku-4-5-20251001"
) -> str:
    """用低成本模型（Haiku）对旧对话生成摘要"""
    
    conversation_text = "\n".join([
        f"{'用户' if m['role'] == 'user' else '助手'}: {m['content']}"
        for m in old_messages
    ])
    
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=model,  # 用 Haiku 降低摘要成本
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": f"""请用 150–200 字总结以下对话的关键信息，重点保留：
1. 用户明确提出的需求和偏好
2. 已确认的决策和结论
3. 还未解决的问题

对话内容：
{conversation_text}

请直接输出摘要，不需要开头的说明语句。"""
        }]
    )
    
    return response.content[0].text


def chat_with_summary_compression(
    messages: list[dict],
    user_input: str,
    system_prompt: str,
    max_tokens_threshold: int = 6000,
    keep_recent_turns: int = 5
) -> tuple[str, list[dict], str]:
    """
    超过阈值时，将旧消息压缩为摘要，保留最近 N 轮完整对话。
    返回 (回复, 更新后的消息列表, 当前摘要)
    """
    
    messages.append({"role": "user", "content": user_input})
    current_summary = ""
    
    # 检查是否需要压缩
    total_tokens = count_tokens(messages)
    
    if total_tokens > max_tokens_threshold and len(messages) > keep_recent_turns * 2:
        # 分割：旧消息 + 最近 N 轮
        cutoff = len(messages) - keep_recent_turns * 2
        old_messages = messages[:cutoff]
        recent_messages = messages[cutoff:]
        
        # 压缩旧消息
        current_summary = summarize_old_messages(old_messages)
        
        # 重建：摘要作为第一条系统消息附加
        augmented_system = f"{system_prompt}\n\n[之前对话摘要]\n{current_summary}"
        
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=augmented_system,
            messages=recent_messages
        )
        
        reply = response.content[0].text
        recent_messages.append({"role": "assistant", "content": reply})
        return reply, recent_messages, current_summary
    
    else:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system_prompt,
            messages=messages
        )
        reply = response.content[0].text
        messages.append({"role": "assistant", "content": reply})
        return reply, messages, current_summary
```

**优点**：能保留重要的早期语义信息，token 成本受控。

**实用技巧**：用便宜的 claude-haiku 来做摘要，摘要成本只有 Claude Sonnet 的约 1/20，整体额外成本可以接受。

## 五、策略四：重要性评分保留

不是所有消息都同等重要。可以给每条消息评分，裁剪时优先保留「重要」消息：

```python
from dataclasses import dataclass, field

@dataclass
class AnnotatedMessage:
    role: str
    content: str
    importance: float = 1.0  # 0.0–1.0
    turn_id: int = 0

def score_message_importance(message: dict, turn_id: int) -> float:
    """简单的重要性启发式评分"""
    content = message.get("content", "")
    score = 1.0
    
    # 越新的消息越重要（时间衰减）
    recency_bonus = turn_id * 0.05
    score += recency_bonus
    
    # 包含关键词的消息更重要
    important_keywords = ["需求", "必须", "一定", "不能", "要求", "目标", "结论"]
    keyword_matches = sum(1 for kw in important_keywords if kw in content)
    score += keyword_matches * 0.2
    
    # 超短消息（可能是无实质信息的闲聊）降权
    if len(content) < 20:
        score *= 0.5
    
    # 用户消息通常比助手消息更重要（承载意图）
    if message["role"] == "user":
        score *= 1.2
    
    return min(score, 5.0)  # 上限 5.0

def trim_by_importance(
    messages: list[dict],
    max_tokens: int = 6000,
    model: str = "claude-sonnet-4-6"
) -> list[dict]:
    """按重要性保留消息，总是保留最新 2 条（当前轮次）"""
    
    if count_tokens(messages, model) <= max_tokens:
        return messages
    
    # 最新 2 条消息（当前轮次的 user + 可能还没有的 assistant）一定保留
    must_keep = messages[-2:] if len(messages) >= 2 else messages
    candidates = messages[:-2] if len(messages) >= 2 else []
    
    # 评分
    scored = [
        (msg, score_message_importance(msg, i))
        for i, msg in enumerate(candidates)
    ]
    # 按重要性降序
    scored.sort(key=lambda x: x[1], reverse=True)
    
    # 贪心选择直到 token 预算耗尽
    selected = []
    for msg, _ in scored:
        test_messages = selected + must_keep
        if count_tokens(test_messages, model) < max_tokens:
            selected.append(msg)
    
    # 恢复时间顺序
    selected_ids = {id(msg) for msg in selected}
    ordered = [msg for msg in candidates if id(msg) in selected_ids]
    
    return ordered + must_keep
```

**注意**：这种方法会打乱消息的时间顺序，需要确保 LLM 能处理非连续的对话历史，建议在每段保留消息前加时间戳或轮次标注。

## 六、各策略对比与选型建议

| 策略 | 实现复杂度 | Token 节省 | 语义保留度 | 适合场景 |
|------|-----------|-----------|-----------|---------|
| 固定轮数窗口 | 极低 | 高 | 低（丢弃早期内容） | 简单客服、FAQ Bot |
| Token 数量限制 | 低 | 高 | 低 | 精确成本控制 |
| 摘要压缩 | 中 | 中高 | 中高 | 长对话助手、任务助理 |
| 重要性评分 | 中高 | 中 | 高 | 复杂需求类 Chatbot |

### 推荐组合

**生产环境最佳实践**：

```
保留最近 5 轮（完整）+ 更早部分摘要压缩
```

这个组合兼顾了实现复杂度和效果，是大多数 Chatbot 产品的合理起点。

## 七、上下文管理的边界情况

### 多模态消息的处理

图片 token 消耗远高于文字（一张图通常 1,000–2,000 tokens）。策略：超过 3 轮后，把历史轮次的图片替换为图片摘要描述。

```python
def compress_image_messages(messages: list[dict]) -> list[dict]:
    """将非最新轮次的图片替换为文字描述"""
    compressed = []
    latest_user_idx = max(
        (i for i, m in enumerate(messages) if m["role"] == "user"),
        default=-1
    )
    
    for i, msg in enumerate(messages):
        if i == latest_user_idx or msg["role"] == "assistant":
            compressed.append(msg)
        elif msg["role"] == "user" and isinstance(msg.get("content"), list):
            # 把图片内容替换为占位描述
            new_content = []
            for block in msg["content"]:
                if isinstance(block, dict) and block.get("type") == "image":
                    new_content.append({
                        "type": "text",
                        "text": "[此轮包含一张图片，内容已省略]"
                    })
                else:
                    new_content.append(block)
            compressed.append({"role": "user", "content": new_content})
        else:
            compressed.append(msg)
    
    return compressed
```

### 系统提示词与对话历史的权重平衡

一个容易被忽视的细节：当系统提示词很长（如含有大量 FAQ 的知识库），而对话历史也很长时，两者会互相挤压有效上下文空间。建议：

- 把系统提示词标记为 Prompt Caching（降低其 token 计费成本）
- 对话历史的 token 预算独立于系统提示词预算管理
- 必要时考虑用 RAG 替代超长系统提示词

关于 Prompt Caching 的成本分析，可以参考[Claude Prompt Caching ROI 分析](/blog/claude-prompt-caching-roi-analysis/)。

## 八、相关阅读

- [LLM Prompt Token 精简实践与代码示例](/blog/llm-prompt-token-trimming-recipes/)
- [Claude Prompt Caching ROI 分析：什么场景值得开启缓存](/blog/claude-prompt-caching-roi-analysis/)
- [LLM 多轮对话设计与实现](/blog/llm-multi-turn-conversation/)
- [AI Agent 记忆系统设计：短期与长期记忆的工程选择](/blog/ai-agent-memory-design/)
- [从零构建 AI 聊天机器人](/blog/ai-chatbot-from-scratch/)

需要在自己的 Chatbot 产品中稳定接入 Claude 或 GPT-4o？[YoTradeApi](https://yotradeapi.com) 提供国内直连的 API 中转，支持流式输出和高并发，适合 Chatbot 类产品的生产环境部署。
