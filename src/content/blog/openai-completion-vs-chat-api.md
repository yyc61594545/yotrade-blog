---
title: OpenAI Completions 与 Chat API 选型与差异
description: 深度对比 OpenAI Completions API 和 Chat Completions API 的接口设计、适用场景和成本差异，帮助开发者做出正确的 API 选型决策。
keywords:
  - OpenAI Completions API
  - Chat Completions API
  - API 选型
  - OpenAI 接口对比
  - text-davinci 对比 GPT-4
  - openai api 差异
pubDate: '2026-06-30'
updatedDate: '2026-06-30'
canonical: https://blog.yotradeapi.com/blog/openai-completion-vs-chat-api/
tags:
  - OpenAI
  - API
  - 技术对比
  - LLM
category: 技术深度
heroImage: ../../assets/blog-placeholder-3.jpg
---

OpenAI 对外提供的核心文本生成接口其实有两套：**Completions API**（`/v1/completions`）和 **Chat Completions API**（`/v1/chat/completions`）。很多开发者在刚接触 OpenAI 生态时会搞混这两者，或者不清楚什么场景下该用哪个。本文从接口设计、模型支持、适用场景、成本控制几个维度做系统梳理，帮你做出正确的技术选型。

## 一、两套接口的历史背景

Completions API 是 OpenAI 最早对外开放的接口，2020 年随 GPT-3 一起发布。它的设计非常简单：你发一段提示文本（prompt），模型续写后面的内容。这对 GPT-3 时代的任务来说已经够用，因为那时候的主要用途是文本生成、代码补全、文章改写等"单向输出"场景。

Chat Completions API 则是 2023 年 3 月 ChatGPT 接口开放时引入的，起初专为 `gpt-3.5-turbo` 设计。它把输入结构化成一个消息数组（messages），每条消息有 `role`（`system`、`user`、`assistant`）和 `content`，天然支持多轮对话状态。

从 2023 年下半年起，OpenAI 开始将新模型**仅在 Chat 接口上发布**：GPT-4、GPT-4o、o1、o3 等都只支持 `/v1/chat/completions`。Completions API 实际上已处于"维护模式"，仅保留了少数旧模型（如 `gpt-3.5-turbo-instruct`、`davinci-002`、`babbage-002`）的支持。

## 二、接口结构对比

两套接口的请求体结构差异一目了然：

| 字段 | Completions API | Chat Completions API |
|------|----------------|---------------------|
| 输入格式 | `prompt`（字符串或字符串数组） | `messages`（消息对象数组） |
| 角色区分 | 无，全部由 prompt 自行拼接 | `system` / `user` / `assistant` 明确分离 |
| 多轮上下文 | 需手动拼接成长字符串 | 原生数组结构，天然支持历史消息 |
| 停止词 | `stop`（字符串/数组） | `stop`（字符串/数组） |
| 最大 token | `max_tokens` | `max_tokens` / `max_completion_tokens` |

**Completions API 调用示例**：

```python
import openai

response = openai.Completion.create(
    model="gpt-3.5-turbo-instruct",
    prompt="写一首关于秋天的五言绝句：",
    max_tokens=100,
    temperature=0.8
)
print(response.choices[0].text)
```

**Chat Completions API 调用示例**：

```python
import openai

response = openai.ChatCompletion.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "你是一位擅长中国古典诗词的作家。"},
        {"role": "user", "content": "写一首关于秋天的五言绝句。"}
    ],
    max_tokens=100,
    temperature=0.8
)
print(response.choices[0].message.content)
```

从代码来看，Chat 接口多了 `messages` 数组和 `role` 的概念，但带来的好处是结构清晰，System Prompt 与用户输入彻底分离，不再担心用户 prompt 注入污染系统指令。

## 三、模型支持现状

这是选型时最关键的一点：**Completions API 能用的模型非常有限**。

| API 类型 | 可用模型（截至 2026 年） |
|---------|----------------------|
| Completions API | `gpt-3.5-turbo-instruct`、`davinci-002`、`babbage-002` |
| Chat Completions API | `gpt-4o`、`gpt-4o-mini`、`gpt-4-turbo`、`gpt-4`、`o1`、`o3`、`o4-mini`，以及所有未来新模型 |

结论非常清晰：**如果你要用 GPT-4o 及以上的模型，只能走 Chat Completions API**。Completions API 已经无缘最新最强的模型，长期来看是技术死路。

## 四、适用场景分析

尽管两者都能完成文本生成任务，但各有擅长的场景。

**Completions API 仍然适合的场景**：

1. **少量 token 的快速补全任务**：比如代码行补全、关键词扩写，`gpt-3.5-turbo-instruct` 的延迟极低，价格也便宜（$0.0015/1K input tokens），适合对成本敏感、不需要推理能力的批量任务。
2. **格式严格的结构化输出**：老模型的"续写"特性在某些固定模板填充场景下表现稳定，输出格式易控制。
3. **历史系统迁移成本考虑**：有些 2022 年建的老系统大量依赖 Completions 接口，短期改造代价高，维持现状也是合理选择——前提是业务场景不需要推理能力。

**Chat Completions API 几乎适合所有新项目**：

1. **多轮对话产品**：聊天机器人、客服助手、AI 助理，messages 数组让历史消息管理变得简单。
2. **需要区分系统指令和用户输入的场景**：System Prompt 独立字段让角色注入防护更可靠。
3. **使用 Function Calling / Tool Use**：工具调用功能只在 Chat 接口可用。
4. **需要 JSON Mode 或 Structured Outputs**：同样只有 Chat 接口支持。
5. **Vision（图像理解）任务**：GPT-4o 的视觉能力只能通过 Chat 接口传入 `image_url`。

## 五、多轮对话的实现差异

这是两套接口使用体验差距最大的地方。

**Completions 方式管理多轮上下文**，你需要手动把历史拼进 prompt 字符串：

```python
# 手动维护对话历史
history = "用户：你好，帮我分析一下这段代码。\n助手：好的，请把代码发给我。\n用户：def add(a,b): return a+b\n助手："
response = openai.Completion.create(
    model="gpt-3.5-turbo-instruct",
    prompt=history,
    max_tokens=200
)
```

这种方式的问题显而易见：格式完全靠自己约定，容易出现角色混淆；随着轮次增多，prompt 越来越长，token 消耗难以控制；而且没有官方的 token 优化机制（如提示词缓存）。

**Chat 方式管理多轮上下文**，只需维护一个 messages 列表：

```python
messages = [
    {"role": "system", "content": "你是一位专业的代码审查助手。"}
]

def chat_round(user_input: str) -> str:
    messages.append({"role": "user", "content": user_input})
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=messages
    )
    reply = response.choices[0].message.content
    messages.append({"role": "assistant", "content": reply})
    return reply

chat_round("帮我分析一下这段代码")
chat_round("def add(a,b): return a+b")
```

结构更清晰，且 OpenAI 官方的 Prompt Caching 功能（对 system prompt 和长上下文缓存，可省 50% token 费用）只在 Chat 接口上生效。

## 六、成本差异与优化建议

纯按 token 单价来看，`gpt-3.5-turbo-instruct`（Completions API）确实比 `gpt-4o-mini`（Chat API）便宜一些。但从**总体拥有成本**来看，Chat API 往往更划算：

- Chat API 支持 **Prompt Caching**，system prompt 重复时可缓存，成本降低 50%
- Chat API 支持 **Batch API**，非实时任务打包处理可节省 50%（详见 [LLM Batch API 实际节省分析](/blog/llm-batch-api-real-savings/)）
- Chat API 的 `max_completion_tokens` 可以更精确控制推理 token，避免浪费

**实际选型建议**：

- 新项目一律用 Chat Completions API，不要纠结
- 只有当你的场景是**极低延迟的简单文本补全**且**不需要推理**，才考虑 `gpt-3.5-turbo-instruct`
- 用国内中转 API（如 YoTradeApi）时，两套接口都完整支持，接入成本一样低

## 七、与其他 LLM 接口的兼容性

Chat Completions API 的 messages 格式已经成为行业标准。几乎所有主流 LLM 提供商（Anthropic Claude、Google Gemini、Mistral、DeepSeek）都提供了与 OpenAI Chat API 兼容的接口，可以通过切换 `base_url` 无缝替换。

这种兼容性在 Completions API 上是不存在的——大多数新模型厂商根本不实现那套旧接口。这也是从长期架构健壮性考虑应该选 Chat API 的理由。

关于 OpenAI 兼容接口与原生 Anthropic 协议的选择，可以参考 [OpenAI Compatible 与 Anthropic 原生协议对比](/blog/openai-compatible-vs-anthropic-protocol/)。

## 八、迁移指南：从 Completions 切到 Chat API

如果你有老系统需要从 Completions API 迁移到 Chat API，核心改动如下：

```python
# 旧代码（Completions）
response = openai.Completion.create(
    model="text-davinci-003",  # 已废弃
    prompt=f"System: 你是助手\nUser: {user_input}\nAssistant:",
    max_tokens=200,
    stop=["User:"]
)
result = response.choices[0].text.strip()

# 新代码（Chat Completions）
response = openai.ChatCompletion.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "你是助手"},
        {"role": "user", "content": user_input}
    ],
    max_tokens=200
)
result = response.choices[0].message.content
```

主要改动：
1. `prompt` → `messages` 数组
2. `choices[0].text` → `choices[0].message.content`
3. 手动拼接的 `System:` / `User:` → 用 role 字段替代
4. `stop=["User:"]` 通常不再需要

## 九、相关阅读

- [LLM System Prompt 与 User Prompt 的本质区别](/blog/llm-system-prompt-vs-user-prompt/)
- [OpenAI SDK base_url 中转配置指南](/blog/openai-sdk-base-url-cn/)
- [LLM Batch API 实际节省分析](/blog/llm-batch-api-real-savings/)
- [OpenAI Compatible 与 Anthropic 原生协议对比](/blog/openai-compatible-vs-anthropic-protocol/)

如果你需要低延迟、低成本地调用 OpenAI 全系列模型（包括 Chat 和 Completions 接口），[YoTradeApi](https://yotradeapi.com) 提供稳定中转，按量计费，无需信用卡即可开始。
