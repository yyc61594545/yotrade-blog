---
title: LLM Token 计算完整指南：tiktoken / Anthropic / 中文
description: OpenAI / Anthropic / Gemini 三家模型 token 计算方法对比，中文 token 化特性、客户端预算、tiktoken 实战、Anthropic count_tokens API。
keywords:
- llm token 计算
- tiktoken 教程
- claude token 计算
- 中文 token 数
- token 预算
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/token-counting-cn-guide/
tags:
- Token
- 计算
- 中文
- 成本
- 工程实战
category: 工程实战
heroImage: ../../assets/blog-placeholder-3.jpg
---

# LLM Token 计算完整指南：tiktoken / Anthropic / 中文

写 LLM 应用早晚要算 token：估算成本、控制上下文、走 caching 边界。但每家 tokenizer 不同，中文又特别诡异。本文给完整解析与实战代码。

## 一、什么是 token

简单说：模型不直接看字符，**看 token**——子词单元。一个 token 可能是：

- 一个字符（英文标点）
- 一段词根（"running"="run"+"ning"）
- 一个常见词（"hello"）
- 一个汉字（中文）

LLM 的"上下文长度 200k tokens"= 200k 个这种单元。

## 二、英文 vs 中文 token 比例

| 文本 | 字符 | token 数（OpenAI） |
| --- | --- | --- |
| `Hello world` | 11 | 2 |
| `你好世界` | 4 | 4–6 |
| 1000 字英文段落 | 1000 | ~200 |
| 1000 字中文段落 | 1000 | ~600 |

**中文每个字大约 1–1.5 个 token**，英文一个 token 平均 3–4 个字符。**中文输入成本约是英文的 3 倍**。

## 三、OpenAI 用 tiktoken

```python
# pip install tiktoken
import tiktoken

enc = tiktoken.encoding_for_model("gpt-5")
tokens = enc.encode("你好世界 Hello world")
print(len(tokens))   # 7
print(tokens)        # [...]
```

GPT-4 / GPT-5 都用 `o200k_base` 编码。早期模型用 `cl100k_base`。

### 估算 message 数

不是简单拼字符串。Chat Completion 有 overhead：

```python
def count_tokens(messages, model="gpt-5"):
    enc = tiktoken.encoding_for_model(model)
    total = 0
    for m in messages:
        # 每个 message 约 +3-4 token overhead
        total += 4
        for k, v in m.items():
            total += len(enc.encode(str(v)))
            if k == "name":
                total -= 1
    total += 2   # priming reply
    return total
```

实际值看 response.usage 准。客户端 tiktoken 是**估算**，可能差 5–10%。

## 四、Anthropic 用专属 tokenizer

Claude **没有公开本地 tokenizer**。两种方法：

### 方法 A：用 API 算

```python
import anthropic

client = anthropic.Anthropic(base_url="https://yotradeapi.com", api_key="sk-yo-...")

resp = client.messages.count_tokens(
    model="claude-sonnet-4-6",
    messages=[{"role": "user", "content": "你好世界"}],
)
print(resp.input_tokens)
```

需要中转支持 `/v1/messages/count_tokens` 端点。

### 方法 B：用 tiktoken 做粗估

```python
# 不精确但能用，差 10-20%
enc = tiktoken.get_encoding("cl100k_base")
estimated = len(enc.encode(text)) * 1.1   # Claude 略多
```

适合预估，**精确数字看 response.usage**。

## 五、Gemini

```python
# google-generativeai
import google.generativeai as genai

model = genai.GenerativeModel("gemini-2.5-pro")
print(model.count_tokens("你好世界"))
```

通过 OpenAI 兼容路径调用时，看 response.usage。

## 六、Tokens vs 字符 vs 字数

写工具函数前注意：

| 概念 | 含义 |
| --- | --- |
| token | 模型单元（计费） |
| character | Unicode 字符 |
| 字 / 字符（中文） | 一个汉字 = 一个 char |
| 词（中文） | "你好" = 1 词 = 2 字 |

不同语言换算不一样：

| 语言 | 1k tokens ≈ |
| --- | --- |
| 英文 | 750 字 |
| 中文 | 600–700 字 |
| 代码 | 500 行 |
| JSON | 300 行 |

## 七、估算成本

```python
def estimate_cost(input_tokens, output_tokens, model="claude-sonnet-4-6"):
    PRICING = {
        "claude-opus-4-7": {"input": 15.0, "output": 75.0},  # per 1M tokens
        "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
        "claude-haiku-4-5": {"input": 0.8, "output": 4.0},
        "gpt-5": {"input": 10.0, "output": 50.0},
        "gemini-2.5-pro": {"input": 1.25, "output": 5.0},
        "gemini-2.5-flash": {"input": 0.075, "output": 0.30},
    }
    p = PRICING[model]
    return (input_tokens / 1_000_000) * p["input"] + (output_tokens / 1_000_000) * p["output"]

# 用法
print(estimate_cost(5000, 800, "claude-sonnet-4-6"))   # → $0.027
```

UI 里实时展示当前对话累计花费，用户体验好。

## 八、token-aware 上下文裁剪

```python
def trim_messages_to_budget(messages, model, budget=180_000):
    """从最早消息删，保留 system + 最近 N 条"""
    enc = tiktoken.encoding_for_model(model)
    
    def cost(msgs):
        return sum(len(enc.encode(str(m["content"]))) for m in msgs)
    
    system = [m for m in messages if m["role"] == "system"]
    history = [m for m in messages if m["role"] != "system"]
    
    while history and cost(system + history) > budget:
        history.pop(0)   # 删最早
    
    return system + history
```

200k 上下文模型留 20k 安全冗余给输出。

## 九、Caching 边界（Anthropic）

Anthropic 缓存有最小长度：

- Sonnet / Opus: 1024 tokens
- Haiku: 2048 tokens

低于这个长度 `cache_control` 无效。校验：

```python
if count_tokens(system_prompt) < 1024:
    # 这段太短，不要加 cache_control
```

## 十、Tool schema 也算 token

很多人忘了：

```python
tools=[{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "...",
        "parameters": {...}
    }
}]
```

整个 tools 数组**算进 input tokens**。10 个工具能占 5–10k token。**只注册必要的 tool**。

## 十一、Vision token

图片也算 token：

| 模型 | 1024×1024 图片 |
| --- | --- |
| GPT-5 | ~1100 token |
| Claude Sonnet | ~1500 token |
| Gemini Pro | ~250 token |

详见 [LLM Vision API 对比](/blog/llm-vision-api-comparison/)。

## 十二、实战：token budget tracker

```python
class TokenBudget:
    def __init__(self, daily_limit=1_000_000):
        self.daily_limit = daily_limit
        self.used_today = 0

    def check(self, estimated):
        if self.used_today + estimated > self.daily_limit:
            raise BudgetExceeded()

    def record(self, actual):
        self.used_today += actual

# 用法
budget = TokenBudget(daily_limit=1_000_000)
budget.check(estimate_tokens(prompt) + 1000)
resp = client.chat.completions.create(...)
budget.record(resp.usage.total_tokens)
```

加 redis 持久化 + cron 每天清零，能给个人 / 团队加保护。

## 十三、相关阅读

- [prompt caching 在国内中转下省成本指南](/blog/prompt-caching-cost-optimization/)
- [AI 编程代理成本控制实战](/blog/ai-coding-agent-cost-control/)
- [2026 LLM 价格对比与选型决策](/blog/llm-pricing-comparison-2026/)
- [LLM API 限速处理](/blog/llm-rate-limit-handling/)
- [中文 RAG 工程实战](/blog/rag-cn-best-practices/)

需要查询每条请求精确 token 数的中转？[YoTradeApi](https://yotradeapi.com) 后台展示每条请求的 input / output / cached / total tokens，方便复盘。
