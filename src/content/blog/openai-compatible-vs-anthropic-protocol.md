---
title: OpenAI 兼容协议 vs Anthropic 原生协议
description: AI API 中转下两套主流协议的差异、转换损耗、tool_call/cache_control 等高级特性的兼容情况，含实战选择建议。
keywords:
- openai 兼容 协议
- anthropic 原生 协议
- api 协议 对比
- openai 协议 anthropic
- 中转 协议
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/openai-compatible-vs-anthropic-protocol/
tags:
- 协议
- OpenAI
- Anthropic
- API 中转
- 技术细节
category: 入门
heroImage: ../../assets/blog-placeholder-4.jpg
---

走中转时第一个要决定的事是用什么协议。OpenAI 兼容协议覆盖广、生态成熟；Anthropic 原生协议保留 Claude 全部能力。本文讲清楚两者差异、转换损耗、什么时候用哪个。

## 一、两种协议的端点

### OpenAI 协议

```
POST /v1/chat/completions
POST /v1/embeddings
POST /v1/responses          (GPT-5 新协议)
POST /v1/audio/speech       (TTS)
POST /v1/audio/transcriptions (STT)
POST /v1/images/generations
```

### Anthropic 协议

```
POST /v1/messages
POST /v1/messages/count_tokens
GET  /v1/models
```

OpenAI 端点更多（覆盖了完整生态），Anthropic 端点更少但每个都做得深。

## 二、消息结构差异

### OpenAI

```json
{
  "model": "claude-sonnet-4-6",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

system 是 messages 数组里的第一个。

### Anthropic

```json
{
  "model": "claude-sonnet-4-6",
  "system": "...",
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "max_tokens": 1024
}
```

system 独立字段、`max_tokens` 必填。

## 三、协议转换的损耗

中转能把 Anthropic 模型用 OpenAI 协议调，但有损：

| 特性 | OpenAI 协议下 | Anthropic 原生 |
| --- | --- | --- |
| prompt caching | 部分（看中转实现） | 完整 |
| extended thinking | 一般丢失 | 完整 |
| tool_use 多轮 | 完整 | 完整 |
| 多 content_block | 简化为字符串 | 完整 |
| 内置工具（web_search 等） | 不支持 | 支持 |
| 1M 上下文 beta | 不一定 | 完整 |

**关键判断**：如果你要用 Claude 独家特性（extended thinking、computer use、内置 web_search），**必须走 Anthropic 原生协议**。

## 四、tool_call 在两套协议下

### OpenAI 风格

```json
{
  "tools": [{
    "type": "function",
    "function": {
      "name": "get_weather",
      "parameters": { "type": "object", "properties": { "city": {"type": "string"} } }
    }
  }],
  "tool_choice": "auto"
}
```

### Anthropic 风格

```json
{
  "tools": [{
    "name": "get_weather",
    "description": "...",
    "input_schema": { "type": "object", "properties": { "city": {"type": "string"} } }
  }],
  "tool_choice": {"type": "auto"}
}
```

字段名不同但结构等价。中转一般能做转换。**但流式 tool_call 的转换是高难度区域**——容易出 bug，建议测试一次再上生产。

## 五、prompt caching 在两套协议下

### Anthropic 原生

显式标记缓存边界：

```json
{
  "system": [{
    "type": "text",
    "text": "long prompt...",
    "cache_control": {"type": "ephemeral"}
  }]
}
```

### OpenAI 兼容

走兼容协议时如果中转支持，会自动透传 `cache_control`：

```python
client.chat.completions.create(
    model="claude-sonnet-4-6",
    messages=[
        {"role": "system", "content": "long prompt"},
        {"role": "user", "content": "..."},
    ],
    extra_body={
        "cache_control": [{"index": 0, "type": "ephemeral"}]
    },
)
```

不是所有中转都正确实现。**最稳的办法**：用原生协议。

## 六、流式响应差异

| 维度 | OpenAI | Anthropic |
| --- | --- | --- |
| 协议 | SSE | SSE |
| 数据格式 | `data: {...}` | `event: ... + data: {...}` |
| 结束信号 | `data: [DONE]` | `event: message_stop` |
| 增量字段 | `choices[].delta` | `content_block_delta` |

写客户端时一定要用 SDK，不要自己解析。

## 七、SDK 选择

| 场景 | SDK |
| --- | --- |
| 调 GPT 系列 | openai-python / openai-node |
| 调 Claude 走 OpenAI 兼容 | openai-python / openai-node |
| 调 Claude 走原生 | anthropic-sdk-python / anthropic-sdk-typescript |
| 多家模型抽象 | LiteLLM / Vercel AI SDK |
| 本地 / 多模型 | LangChain / LlamaIndex |

**最常见的选择**：openai-python，覆盖 90% 场景。需要 Claude 独家特性时再切 anthropic-sdk。

## 八、什么时候必须用 Anthropic 原生

| 需求 | 必须原生？ |
| --- | --- |
| 标准 chat | 不必 |
| function calling | 不必 |
| extended thinking | **是** |
| computer use | **是** |
| 长缓存（1h） | **是** |
| 1M 上下文 beta | **是** |
| MCP server 接入（Anthropic Bedrock） | **是** |

## 九、Claude Code / Cursor / Cline 的协议选择

- **Claude Code**：原生 Anthropic 协议（必须）
- **Cursor**：自定义模型用 OpenAI 兼容
- **Cline**：默认 OpenAI 兼容，可选 Anthropic
- **Aider**：通过 LiteLLM，两者皆可
- **Continue.dev**：明确指定 provider 类型

## 十、协议同时支持的中转

好中转的标志之一：同时支持 OpenAI 兼容与 Anthropic 原生。这样你的不同工具可以走不同协议而共享同一把 Key。

最小验证：

```bash
# OpenAI 兼容
curl https://yotradeapi.com/v1/chat/completions \
  -H "Authorization: Bearer $KEY" \
  -d '{"model":"claude-sonnet-4-6","messages":[{"role":"user","content":"hi"}]}'

# Anthropic 原生
curl https://yotradeapi.com/v1/messages \
  -H "x-api-key: $KEY" -H "anthropic-version: 2023-06-01" \
  -d '{"model":"claude-sonnet-4-6","max_tokens":64,"messages":[{"role":"user","content":"hi"}]}'
```

两个端点都应该返回 200。

## 十一、相关阅读

- [OpenAI SDK base_url 国内配置实战](/blog/openai-sdk-base-url-cn/)
- [Claude Code 镜像国内配置完整指南](/blog/claude-code-mirror-cn-setup/)
- [Cursor API 中转怎么选](/blog/2026-05-15-cursor-api-relay-recommendation-2026/)
- [prompt caching 在国内中转下省成本指南](/blog/prompt-caching-cost-optimization/)
- [流式 SSE 故障排查](/blog/streaming-sse-troubleshooting/)

[YoTradeApi](https://yotradeapi.com) 同时支持 OpenAI 兼容协议（`/v1/chat/completions`）与 Anthropic 原生协议（`/v1/messages`），一把 Key 跑两个协议。
