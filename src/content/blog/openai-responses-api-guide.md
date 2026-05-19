---
title: OpenAI Responses API 完整使用指南
description: OpenAI Responses API 与 Chat Completions 的差异、何时使用、SDK 调用、stateful 会话、tool_call 与中转兼容性。
keywords:
- openai responses api
- gpt-5 responses
- responses api 用法
- openai 新协议
- stateful conversation
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/openai-responses-api-guide/
tags:
- OpenAI
- Responses API
- GPT-5
- 协议
- 入门
category: 工具配置
heroImage: ../../assets/blog-placeholder-2.jpg
---

# OpenAI Responses API 完整使用指南

OpenAI 在 2024 年末推出了 Responses API，作为 Chat Completions 的下一代。GPT-5 时代它已经成为推荐接口。本文讲清楚它和老接口的差异、什么时候用、中转下要注意什么。

## 一、Responses API vs Chat Completions

| 维度 | Chat Completions | Responses API |
| --- | --- | --- |
| 端点 | `/v1/chat/completions` | `/v1/responses` |
| 状态 | 无状态 | 可选 stateful |
| 工具 | tools 数组 | tools + 内置工具 |
| 多轮 | 客户端拼 messages | server 可保存 |
| 推理 | 不暴露 | 暴露 reasoning |
| Background | 不支持 | 支持 background mode |

## 二、最小调用

```python
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_YOTRADE_KEY",
    base_url="https://yotradeapi.com/v1",
)

resp = client.responses.create(
    model="gpt-5",
    input="用一句话解释 LRU 缓存。",
)
print(resp.output_text)
```

`input` 可以是字符串或消息数组，与 Chat Completions 兼容性高但不完全一样。

## 三、多轮对话（stateful）

老接口需要每次发完整 messages 数组。Responses API 可以让服务端保存：

```python
# 第一轮
r1 = client.responses.create(
    model="gpt-5",
    input="什么是 LRU 缓存？",
    store=True,   # 让服务端保存
)

# 第二轮：只发增量，引用上一轮 id
r2 = client.responses.create(
    model="gpt-5",
    input="给我一个 Python 实现。",
    previous_response_id=r1.id,
)
```

省去客户端管 messages 历史的麻烦。**但要注意**：

- `store=True` 会让 OpenAI/中转保留对话内容
- 国内合规场景可能要 `store=False`
- 走中转时 `previous_response_id` 必须由同一个中转生成才能解析

## 四、走中转的关键参数

```python
client.responses.create(
    model="gpt-5",
    input="...",
    store=False,   # 中转下推荐关闭，避免协议歧义
    reasoning={"effort": "medium"},   # low / medium / high
)
```

`reasoning.effort` 类似 Claude 的 thinking budget，控制推理深度。

## 五、内置工具

Responses API 内置了几个工具：

| 工具 | 用途 |
| --- | --- |
| `web_search` | 联网搜索 |
| `file_search` | 检索上传文档 |
| `computer_use` | 控制虚拟桌面 |
| `code_interpreter` | 跑 Python 沙箱 |

```python
resp = client.responses.create(
    model="gpt-5",
    input="今天 AI 圈有什么新闻？",
    tools=[{"type": "web_search"}],
)
```

**国内中转下**：内置工具大多不可用——它们依赖 OpenAI 服务端基础设施。中转一般只透传"模型本身"，不能透传"OpenAI 后台服务"。

## 六、自定义函数（function call）

```python
tools = [{
    "type": "function",
    "name": "get_weather",
    "description": "获取天气",
    "parameters": {
        "type": "object",
        "properties": {"city": {"type": "string"}},
        "required": ["city"],
    },
}]

resp = client.responses.create(
    model="gpt-5",
    input="北京今天天气怎么样？",
    tools=tools,
)

for item in resp.output:
    if item.type == "function_call":
        print(item.name, item.arguments)
```

注意：Responses API 的工具结构比 Chat Completions 平了一层（没有 `function` 包装）。

## 七、流式输出

```python
stream = client.responses.create(
    model="gpt-5",
    input="数到 10",
    stream=True,
)

for event in stream:
    if event.type == "response.output_text.delta":
        print(event.delta, end="", flush=True)
```

事件类型比 Chat Completions 多：

- `response.created`
- `response.output_text.delta`
- `response.output_text.done`
- `response.function_call.delta`
- `response.completed`

## 八、Background Mode

```python
resp = client.responses.create(
    model="gpt-5",
    input="跑一个长任务...",
    background=True,
)

# 异步轮询
while True:
    status = client.responses.retrieve(resp.id)
    if status.status == "completed":
        print(status.output_text)
        break
    time.sleep(2)
```

**走中转时 background mode 多半不支持**——需要中转维护任务队列与状态机。如需要，直连 OpenAI。

## 九、Codex CLI 用的就是 Responses API

```toml
[model_providers.yotrade]
wire_api = "responses"
```

如果中转不支持 Responses API，Codex CLI 会直接报错"Unknown endpoint /responses"。

## 十、什么时候用 Responses API

| 场景 | 推荐 |
| --- | --- |
| 新项目、GPT-5 | Responses |
| 老项目兼容 | Chat Completions |
| Codex CLI | Responses（必须） |
| Cursor / Cline | Chat Completions（默认） |
| 简单脚本 | Chat Completions（更轻） |
| Agent 长任务 | Responses（stateful 优势） |

短期内 Chat Completions 仍是事实标准——大多数 SDK、工具默认走它。Responses API 是"OpenAI 推荐的未来"。

## 十一、中转兼容性矩阵

| 中转 | Chat Completions | Responses API |
| --- | --- | --- |
| 多数中转 | ✓ | 看支持情况 |
| YoTradeApi 类完整中转 | ✓ | ✓ |

接入前用 curl 测一下：

```bash
curl -i https://yotradeapi.com/v1/responses \
  -H "Authorization: Bearer $KEY" \
  -d '{"model":"gpt-5","input":"hi"}'
```

返回 200 + `output_text` 字段才算通。

## 十二、相关阅读

- [OpenAI SDK base_url 国内配置实战](/blog/openai-sdk-base-url-cn/)
- [Codex CLI 国内配置](/blog/codex-cli-cn-setup/)
- [OpenAI 兼容协议 vs Anthropic 原生协议](/blog/openai-compatible-vs-anthropic-protocol/)
- [GPT-5 与 Claude Opus 4.7 编程能力对比](/blog/gpt-5-vs-claude-opus-4-7-coding/)

需要 Responses API 兼容的中转？[YoTradeApi](https://yotradeapi.com/register) 支持 `/v1/responses` 端点，Codex CLI 等工具可以直接接入。
