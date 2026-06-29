---
title: Claude 流式响应事件类型完全指南
description: 完整解析 Claude API 流式响应的所有 SSE 事件类型：message_start/delta/stop、content_block 系列与 error 事件的数据结构与处理模式。
keywords:
  - Claude 流式响应事件
  - Claude SSE 事件类型
  - Anthropic API streaming
  - content_block_delta 事件
  - Claude API 流式处理
pubDate: '2026-06-29'
updatedDate: '2026-06-29'
canonical: https://blog.yotradeapi.com/blog/claude-streaming-event-types/
tags:
  - Claude
  - 流式响应
  - API参考
  - 技术深度
category: 技术深度
heroImage: ../../assets/blog-placeholder-4.jpg
---

Claude 的流式响应基于 SSE（Server-Sent Events）协议，但与 OpenAI 的流式格式有明显差异：Claude 使用了更精细的事件类型体系，将一次对话拆分成多个语义明确的事件。如果你已经熟悉 OpenAI 的流式处理（`delta.content` 拼接），切换到 Claude 时需要理解这套新的事件结构。

> 本文基于 Anthropic Messages API 的流式规范，与 OpenAI 兼容层（如通过 API 中转提供的 `/v1/chat/completions` 端点）的事件格式不同——本文只讲 Anthropic 原生格式。

## 一、事件流总览

一次完整的 Claude 流式响应包含以下事件序列：

```
event: message_start
data: {...}

event: content_block_start
data: {...}

event: ping
data: {...}

event: content_block_delta     ← 重复多次，每次一个 token 片段
data: {...}

event: content_block_stop
data: {...}

event: message_delta
data: {...}

event: message_stop
data: {...}
```

**关键特征**：
- 每个 SSE 事件包含两行：`event: <类型>` 和 `data: <JSON>`
- `content_block_delta` 是实际 token 内容的载体，会重复出现
- `message_start` 和 `message_stop` 分别包含请求级别的元数据
- 如果响应包含 Tool Use（工具调用），会有额外的 `content_block_start` 序列

## 二、各事件类型详解

### message_start

每次响应的第一个事件，包含消息元数据：

```json
{
  "type": "message_start",
  "message": {
    "id": "msg_01XFDUDYJgAACzvnptvVoYEL",
    "type": "message",
    "role": "assistant",
    "content": [],
    "model": "claude-sonnet-4-6-20251001",
    "stop_reason": null,
    "stop_sequence": null,
    "usage": {
      "input_tokens": 25,
      "output_tokens": 1
    }
  }
}
```

**实际用途**：
- 记录 `message.id` 用于日志追踪
- 获取 `input_tokens`（输出 tokens 此时为 1，是预留的）
- `model` 字段确认实际使用的模型版本

### content_block_start

标志着一个内容块的开始。普通文本响应只有一个 content block（index=0）；如果模型调用了工具，每个工具调用也是一个独立的 content block。

**文本块的 content_block_start**：
```json
{
  "type": "content_block_start",
  "index": 0,
  "content_block": {
    "type": "text",
    "text": ""
  }
}
```

**工具调用块的 content_block_start**：
```json
{
  "type": "content_block_start",
  "index": 1,
  "content_block": {
    "type": "tool_use",
    "id": "toolu_01A09q90qw90lq917835lq9",
    "name": "get_weather",
    "input": {}
  }
}
```

**关键点**：`index` 字段标识块序号，在有多个 content block 时用来区分不同块的 delta 归属。

### content_block_delta

流式传输的核心事件，每个事件携带一小片内容增量：

**文本 delta（text_delta）**：
```json
{
  "type": "content_block_delta",
  "index": 0,
  "delta": {
    "type": "text_delta",
    "text": "Hello"
  }
}
```

**工具输入 delta（input_json_delta）**：
```json
{
  "type": "content_block_delta",
  "index": 1,
  "delta": {
    "type": "input_json_delta",
    "partial_json": "{\"location\": \"San Fr"
  }
}
```

**注意**：`partial_json` 是不完整的 JSON 字符串片段，必须累积所有片段后才能解析。不要在每个 delta 上尝试 `json.loads()`。

### content_block_stop

标志一个 content block 结束：

```json
{
  "type": "content_block_stop",
  "index": 0
}
```

收到此事件后，可以认为对应 index 的 content block 内容已完整。

### message_delta

在最后一个 `content_block_stop` 之后、`message_stop` 之前出现，包含停止原因和最终 token 用量：

```json
{
  "type": "message_delta",
  "delta": {
    "stop_reason": "end_turn",
    "stop_sequence": null
  },
  "usage": {
    "output_tokens": 15
  }
}
```

**stop_reason 可能的值**：

| 值 | 含义 |
|----|------|
| `end_turn` | 模型正常结束输出 |
| `max_tokens` | 达到 max_tokens 限制被截断 |
| `stop_sequence` | 命中了自定义停止序列 |
| `tool_use` | 模型请求调用工具，等待工具结果 |

**重要**：`output_tokens` 的最终准确值在这里，而不是 `message_start` 里的值。计费应以此为准。

### message_stop

响应结束的信号：

```json
{
  "type": "message_stop"
}
```

收到此事件后，整个流式传输结束。

### ping

Anthropic 发送的心跳事件，防止连接超时：

```json
{
  "type": "ping"
}
```

正常忽略即可，不携带业务数据。

### error

流式传输中发生错误时的事件：

```json
{
  "type": "error",
  "error": {
    "type": "overloaded_error",
    "message": "Overloaded"
  }
}
```

常见错误类型：`api_error`、`overloaded_error`、`invalid_request_error`。

## 三、Python 完整处理示例

```python
import anthropic
import json

client = anthropic.Anthropic()

def stream_claude(prompt: str):
    content_blocks = {}   # index -> accumulated text
    tool_inputs = {}      # index -> accumulated partial_json
    final_usage = {}
    stop_reason = None

    with client.messages.stream(
        model="claude-sonnet-4-6-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    ) as stream:
        for event in stream:
            etype = event.type

            if etype == "message_start":
                print(f"消息 ID: {event.message.id}")
                print(f"输入 tokens: {event.message.usage.input_tokens}")

            elif etype == "content_block_start":
                idx = event.index
                block = event.content_block
                if block.type == "text":
                    content_blocks[idx] = ""
                elif block.type == "tool_use":
                    tool_inputs[idx] = {
                        "name": block.name,
                        "id": block.id,
                        "partial": ""
                    }

            elif etype == "content_block_delta":
                idx = event.index
                delta = event.delta
                if delta.type == "text_delta":
                    content_blocks[idx] += delta.text
                    print(delta.text, end="", flush=True)  # 实时打印
                elif delta.type == "input_json_delta":
                    tool_inputs[idx]["partial"] += delta.partial_json

            elif etype == "content_block_stop":
                idx = event.index
                if idx in tool_inputs:
                    # 工具调用完整 JSON 可以在这里解析
                    tool = tool_inputs[idx]
                    try:
                        tool["input"] = json.loads(tool["partial"])
                    except json.JSONDecodeError:
                        print(f"警告: 工具 {tool['name']} 的输入 JSON 解析失败")

            elif etype == "message_delta":
                stop_reason = event.delta.stop_reason
                final_usage = {"output_tokens": event.usage.output_tokens}

            elif etype == "message_stop":
                print()  # 换行
                print(f"停止原因: {stop_reason}")
                print(f"输出 tokens: {final_usage.get('output_tokens', 0)}")

            elif etype == "error":
                print(f"错误: {event.error.type} - {event.error.message}")
                raise Exception(event.error.message)

    return content_blocks, tool_inputs

stream_claude("用 3 句话介绍量子计算")
```

## 四、原生 SSE 处理（不使用 SDK）

如果直接调用 HTTP 接口（比如在 Go 或 Rust 项目中），需要手动解析 SSE：

```python
import httpx
import json

def raw_stream(api_key: str, prompt: str):
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": "claude-sonnet-4-6-20251001",
        "max_tokens": 1024,
        "stream": True,
        "messages": [{"role": "user", "content": prompt}],
    }

    with httpx.stream("POST",
                      "https://api.anthropic.com/v1/messages",
                      headers=headers, json=body, timeout=60) as resp:
        event_type = None
        for line in resp.iter_lines():
            if line.startswith("event:"):
                event_type = line[len("event:"):].strip()
            elif line.startswith("data:"):
                data_str = line[len("data:"):].strip()
                if data_str == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                    # 根据 event_type 处理 data
                    handle_event(event_type, data)
                except json.JSONDecodeError:
                    pass
```

**注意**：Claude 不发送 OpenAI 风格的 `[DONE]` 标记，流结束信号是 `message_stop` 事件。如果你看到 `[DONE]`，说明你走的是 OpenAI 兼容接口层。

## 五、使用 API 中转时的注意事项

通过 API 中转服务调用 Claude 时，通常有两种接口模式：

**模式 A：OpenAI 兼容接口**（`/v1/chat/completions`）
- 流式事件格式是 OpenAI 的 `delta.content` 格式
- 结束标记是 `data: [DONE]`
- 没有 `content_block_start/stop` 这些事件

**模式 B：Anthropic 原生接口**（`/v1/messages`）
- 事件格式与本文一致
- 中转服务需要支持此模式，才能使用工具调用等高级功能

如果你需要使用 Claude 的工具调用、流式 Tool Use、extended thinking 等特性，确认中转服务是否支持 Anthropic 原生接口。

## 六、处理工具调用的完整流程

当 `stop_reason` 为 `tool_use` 时，需要执行工具并继续对话：

```python
def handle_tool_use(tool_name: str, tool_id: str, tool_input: dict):
    """执行工具，返回结果"""
    if tool_name == "get_weather":
        # 实际调用天气 API
        return {"temperature": 22, "condition": "晴天"}
    return {"error": "未知工具"}

# 继续对话（把工具结果附上）
def continue_with_tool_result(original_messages, tool_id, tool_result):
    messages = original_messages + [
        {"role": "assistant", "content": [
            {
                "type": "tool_use",
                "id": tool_id,
                "name": "get_weather",
                "input": {"location": "北京"}
            }
        ]},
        {"role": "user", "content": [
            {
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": json.dumps(tool_result)
            }
        ]}
    ]
    # 用更新后的 messages 再次调用 stream
    return messages
```

## 七、常见问题与排查

**问题 1：content_block_delta 顺序乱**
SSE 是有序的 TCP 流，理论上不会乱序。如果出现，检查中间代理是否对响应做了缓冲处理。关闭代理的响应缓存（在 Nginx 上加 `proxy_buffering off`）。

**问题 2：工具调用的 partial_json 无法解析**
累积所有 `input_json_delta` 之后再解析，不要在中途解析。同时检查是否有 delta 被丢弃（网络中断导致部分事件未收到）。

**问题 3：output_tokens 计费与预期不符**
以 `message_delta` 中的 `usage.output_tokens` 为准，这是最终值。`message_start` 中的值只是占位符（通常为 1）。

更多 SSE 层面的排查方法，参见 [AI API 流式输出（SSE）故障排查与最佳实践](/blog/streaming-sse-troubleshooting/)。

## 八、相关阅读

- [AI API 流式输出（SSE）故障排查与最佳实践](/blog/streaming-sse-troubleshooting/)
- [LLM 流式响应 UI 模式设计](/blog/llm-streaming-ui-patterns/)
- [LLM 流式响应背压处理实战指南](/blog/llm-streaming-backpressure/)
- [LLM 会议纪要生成能力评测](/blog/llm-meeting-minutes-summarization/)

需要在国内稳定调用 Claude API？[YoTradeApi](https://yotradeapi.com) 支持 Anthropic 原生接口和 OpenAI 兼容接口，按量计费，无需海外信用卡。
