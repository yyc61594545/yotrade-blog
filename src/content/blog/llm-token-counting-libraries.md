---
title: 各家 LLM token 计数库对比与选型
description: tiktoken、anthropic-tokenizer、google-generativeai、transformers 四大 token 计数库横向对比：精度、速度、中文支持与工程集成指南。
keywords:
  - llm token 计数库
  - tiktoken 对比
  - anthropic token 计数
  - llm token 计算工具
  - transformers tokenizer 对比
pubDate: '2026-06-23'
updatedDate: '2026-06-23'
canonical: https://blog.yotradeapi.com/blog/llm-token-counting-libraries/
tags:
  - Token
  - 技术深度
  - Python
  - LLM工具
  - 性能优化
category: 技术深度
heroImage: ../../assets/blog-placeholder-4.jpg
---

在生产环境中调用 LLM API，有两个地方必须精确计算 token 数：**提示词裁剪**（防止超出上下文长度）和**成本预估**（账单控制）。但不同模型用不同的分词器，选错工具会导致计数偏差，轻则截断提示词，重则预算计算严重偏移。

关于 token 计算的基础知识，可参考 [LLM Token 计算完整指南](/blog/token-counting-cn-guide/)；本文聚焦**库的选型和工程集成**，不重复基础知识。

## 一、主流 token 计数方案概览

| 库 / 方法 | 对应模型 | 语言 | 精度 | 速度 |
|-----------|---------|------|------|------|
| `tiktoken` | GPT-3.5 / 4 / 4o 系列 | Python | 官方精确 | 极快（Rust 核心） |
| Anthropic `count_tokens` API | Claude 全系列 | 任何（HTTP） | 官方精确 | 有网络延迟 |
| `anthropic-tokenizer`（非官方） | Claude（近似） | Python/JS | 近似（偏差 1–3%） | 快 |
| `google.generativeai.count_tokens` | Gemini 系列 | Python | 官方精确 | 有网络延迟 |
| HuggingFace `transformers` | 开源模型 | Python | 官方精确 | 中等（纯 Python） |
| 字符数估算（÷ N） | 粗估所有模型 | 任何 | 低（±20%） | 极快 |

## 二、tiktoken 深度解析

`tiktoken` 是 OpenAI 官方发布的 Python 分词库，底层用 Rust 实现，是计数 GPT 系列 token 的**唯一精确方案**。

### 安装与基础用法

```python
pip install tiktoken
```

```python
import tiktoken

def count_tokens_openai(text: str, model: str = "gpt-4o") -> int:
    enc = tiktoken.encoding_for_model(model)
    return len(enc.encode(text))

# 计算对话的 token 数（包含特殊格式 token）
def count_chat_tokens(messages: list[dict], model: str = "gpt-4o") -> int:
    enc = tiktoken.encoding_for_model(model)
    # 每条消息有固定的 overhead token
    tokens_per_message = 3   # gpt-4o 的值
    tokens_per_name = 1
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(enc.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3  # 回复 primer
    return num_tokens
```

### 模型与编码器的对应关系

```python
# 查看模型使用的编码器
enc = tiktoken.encoding_for_model("gpt-4o")
print(enc.name)  # "o200k_base"

# 各模型的编码器（参考，以 tiktoken 最新版本为准）
# gpt-4o, gpt-4o-mini → o200k_base
# gpt-4, gpt-3.5-turbo → cl100k_base
# text-davinci-003 → p50k_base（已弃用模型）
```

### 性能基准

tiktoken 的 Rust 核心让它非常快。实测参考（约估，以实际机器为准）：

- 100 token 的文本：< 0.1ms
- 1000 token 的文本：< 0.5ms
- 10000 token 的文本：< 3ms

适合在每次 API 调用前做实时计数，不需要缓存。

## 三、Claude token 计数：官方 API vs 近似估算

### 方案 A：Anthropic 官方 count_tokens API（推荐）

Anthropic 提供了专用的 token 计数 API，不触发实际推理，成本低廉（按公开文档，计数调用按输入 token 的极低比例计费，或免费，具体以官网为准）：

```python
from anthropic import Anthropic

client = Anthropic(
    base_url="https://api.yotradeapi.com/v1",  # 通过中转访问
    api_key="your-key"
)

def count_claude_tokens(messages: list[dict], model: str = "claude-3-5-sonnet-20241022") -> int:
    response = client.messages.count_tokens(
        model=model,
        messages=messages,
    )
    return response.input_tokens

# 使用示例
messages = [{"role": "user", "content": "你好，请解释一下量子纠缠"}]
token_count = count_claude_tokens(messages)
print(f"Token count: {token_count}")
```

**优点**：100% 精确，与实际计费完全一致
**缺点**：有网络 RTT（约 100–300ms），高频场景有性能开销

### 方案 B：本地近似计数（高频场景）

对于需要极低延迟的场景（如实时截断、流式输入的动态计数），可以用近似方案：

```python
# 粗略估算（仅作参考，偏差 ±10-15%）
def estimate_claude_tokens(text: str) -> int:
    # Claude 对中文的 token 化：大约每 1.5 个汉字 = 1 token（近似估算）
    # 英文：大约 4 字符 = 1 token（近似估算）
    chinese_chars = sum(1 for c in text if '一' <= c <= '鿿')
    other_chars = len(text) - chinese_chars
    return int(chinese_chars / 1.5 + other_chars / 4)
```

**实际建议**：在不需要精确计费的场景（如提示词预裁剪）用近似，在需要精确成本追踪的场景用官方 API。

## 四、Gemini token 计数

Google 提供了同步和异步两种计数方式：

```python
import google.generativeai as genai

genai.configure(api_key="your-key")
model = genai.GenerativeModel("gemini-2.0-flash")

# 方法一：直接对文本计数
result = model.count_tokens("What is the meaning of life?")
print(result.total_tokens)

# 方法二：对完整对话计数
response = model.count_tokens([
    {"role": "user", "parts": ["你好"]},
    {"role": "model", "parts": ["你好！有什么可以帮你的吗？"]},
    {"role": "user", "parts": ["解释量子纠缠"]},
])
print(response.total_tokens)
```

**注意**：Gemini 计数 API 目前（截至 2026 年中）是免费的，但未来可能会变化，以官方文档为准。

## 五、HuggingFace Transformers：开源模型场景

使用本地部署或 API 调用开源模型时，需要用对应模型的 tokenizer：

```python
from transformers import AutoTokenizer

# 对应模型加载对应 tokenizer
tokenizer = AutoTokenizer.from_pretrained("deepseek-ai/DeepSeek-R1")

def count_tokens_hf(text: str, tokenizer) -> int:
    return len(tokenizer.encode(text))

# 批量计数（性能更好）
texts = ["文本一", "文本二", "文本三"]
encoded = tokenizer(texts, add_special_tokens=True)
counts = [len(ids) for ids in encoded["input_ids"]]
```

**性能注意**：纯 Python 实现的 tokenizer 比 tiktoken 慢 10–100 倍，不适合高频实时计数。如果 HuggingFace 提供了 Fast Tokenizer 版本（基于 Rust/tokenizers 库），性能会大幅提升。

## 六、统一封装：多模型 token 计数器

实际项目中往往需要支持多个模型，建议封装一个统一接口：

```python
from typing import Literal
import tiktoken
from anthropic import Anthropic

class TokenCounter:
    def __init__(self, anthropic_base_url: str = None, anthropic_api_key: str = None):
        self._tiktoken_cache: dict = {}
        self._anthropic_client = None
        if anthropic_base_url and anthropic_api_key:
            self._anthropic_client = Anthropic(
                base_url=anthropic_base_url,
                api_key=anthropic_api_key,
            )

    def count(self, text: str, model: str) -> int:
        if model.startswith(("gpt-", "o1", "o3", "o4")):
            return self._count_openai(text, model)
        elif model.startswith("claude-"):
            return self._count_claude_approx(text)  # 快速近似
        elif model.startswith("gemini-"):
            return self._count_gemini_approx(text)
        else:
            return self._count_generic(text)

    def count_messages(self, messages: list[dict], model: str) -> int:
        if model.startswith(("gpt-", "o1", "o3", "o4")):
            enc = self._get_tiktoken(model)
            total = sum(len(enc.encode(m.get("content", ""))) for m in messages)
            total += len(messages) * 3 + 3  # overhead
            return total
        elif model.startswith("claude-") and self._anthropic_client:
            r = self._anthropic_client.messages.count_tokens(
                model=model, messages=messages
            )
            return r.input_tokens
        else:
            return sum(self.count(m.get("content", ""), model) for m in messages)

    def _get_tiktoken(self, model: str):
        if model not in self._tiktoken_cache:
            self._tiktoken_cache[model] = tiktoken.encoding_for_model(model)
        return self._tiktoken_cache[model]

    def _count_openai(self, text: str, model: str) -> int:
        return len(self._get_tiktoken(model).encode(text))

    def _count_claude_approx(self, text: str) -> int:
        chinese = sum(1 for c in text if '一' <= c <= '鿿')
        return int(chinese / 1.5 + (len(text) - chinese) / 4)

    def _count_gemini_approx(self, text: str) -> int:
        # Gemini 的分词与 GPT-4 类似，用 cl100k_base 近似
        try:
            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except Exception:
            return len(text) // 4

    def _count_generic(self, text: str) -> int:
        return len(text) // 4  # 极粗略估算
```

## 七、选型决策树

```
需要计数哪个模型？
├── GPT-4o / GPT-4 / GPT-3.5 → tiktoken（官方精确，极快）
├── Claude 系列
│   ├── 需要精确计费 / 审计 → Anthropic count_tokens API
│   └── 需要低延迟 / 高频 → 本地近似估算（接受 ±10% 偏差）
├── Gemini 系列
│   ├── 偶发计数 → google.generativeai.count_tokens（免费）
│   └── 高频 → cl100k_base tiktoken 近似（偏差 5-15%）
└── 开源模型（DeepSeek / Llama / Qwen 等）
    ├── 精确计数 → transformers AutoTokenizer（慢但准）
    └── 近似 → 4 字符/token 估算（英文），1.5 汉字/token（中文）
```

## 八、相关阅读

- [LLM Token 计算完整指南：tiktoken / Anthropic / 中文](/blog/token-counting-cn-guide/)
- [LLM Prompt Token 裁剪实战技巧](/blog/llm-prompt-token-trimming-recipes/)
- [Claude Extended Thinking Token Budget 详解](/blog/claude-extended-thinking-token-budget/)
- [AI Agent 成本监控实战：从 Token 到账单的全链路追踪](/blog/ai-agent-cost-monitoring/)
- [LLM 视觉 Token 成本计算](/blog/llm-vision-token-cost/)

统一接入多个 LLM 模型、简化 token 成本管理，[YoTradeApi](https://yotradeapi.com) 支持 GPT、Claude、Gemini、DeepSeek 全系模型，单一 API Key 搞定多模型调用。
