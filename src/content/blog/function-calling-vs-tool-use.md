---
title: Function Calling vs Tool Use 差异辨析
description: 深度对比 OpenAI Function Calling 与 Anthropic Tool Use 的 API 结构、并行调用、强制调用等核心差异，帮助开发者写出兼容多模型的 Agent 代码。
keywords:
  - function calling vs tool use
  - OpenAI function calling
  - Anthropic tool use
  - LLM工具调用
  - AI Agent开发
pubDate: '2026-05-20'
updatedDate: '2026-05-20'
canonical: https://blog.yotradeapi.com/blog/function-calling-vs-tool-use/
tags:
  - function-calling
  - tool-use
  - OpenAI
  - Anthropic
  - Agent开发
category: 技术深度
heroImage: ../../assets/blog-placeholder-3.jpg
---

工具调用（Tool Call）是当前 AI Agent 开发的核心能力：让模型决定"何时调用什么函数、传什么参数"，并把结果整合进对话。然而，OpenAI 把这个能力叫做 **Function Calling**，Anthropic 把它叫做 **Tool Use**，两套 API 在细节上有不少差异。

如果你同时使用多家模型，或者打算在 Claude 和 GPT 之间做兼容层，搞清楚这些差异能省去大量调试时间。

---

## 一、概念起源：同一件事，两套叫法

**Function Calling** 由 OpenAI 于 2023 年 6 月在 GPT-3.5/4 上推出，最初的设计思路是让模型"调用"开发者定义的函数，返回结构化 JSON。2024 年初，OpenAI 将其升级为 **Tool Use**（在 API 里字段变成 `tools`），并支持并行调用，但民间仍习惯叫"function calling"。

**Tool Use** 是 Anthropic 的叫法，从 Claude 3 系列开始正式支持，API 字段也是 `tools`。两者底层逻辑相同：

1. 开发者在请求里声明可用工具（名称 + 描述 + JSON Schema 参数）
2. 模型返回"我要调用工具 X，参数是 Y"的信号
3. 开发者执行工具，把结果塞回对话
4. 模型读结果，给出最终回答

叫法不同，流程相同——但 API 字段和边界行为差异明显。

---

## 二、请求体结构对比

### OpenAI（GPT-4o / GPT-4.1）

```json
{
  "model": "gpt-4o",
  "messages": [...],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "获取指定城市的实时天气",
        "parameters": {
          "type": "object",
          "properties": {
            "city": { "type": "string" },
            "unit": { "type": "string", "enum": ["celsius", "fahrenheit"] }
          },
          "required": ["city"]
        }
      }
    }
  ],
  "tool_choice": "auto"
}
```

### Anthropic（Claude 3.5 / Claude 4）

```json
{
  "model": "claude-opus-4-7",
  "messages": [...],
  "tools": [
    {
      "name": "get_weather",
      "description": "获取指定城市的实时天气",
      "input_schema": {
        "type": "object",
        "properties": {
          "city": { "type": "string" },
          "unit": { "type": "string", "enum": ["celsius", "fahrenheit"] }
        },
        "required": ["city"]
      }
    }
  ]
}
```

**关键差异一览：**

| 字段 | OpenAI | Anthropic |
|---|---|---|
| 工具外层包装 | `{"type": "function", "function": {...}}` | 直接 `{name, description, input_schema}` |
| 参数 Schema 字段名 | `parameters` | `input_schema` |
| 强制调用控制 | `tool_choice: "required"` / `{"type":"function","function":{"name":"..."}}` | `tool_choice: {"type":"any"}` / `{"type":"tool","name":"..."}` |
| 禁止工具调用 | `tool_choice: "none"` | `tool_choice: {"type":"auto"}` 里模型自行判断；无强制 none |

---

## 三、响应体结构对比

模型决定调用工具时，两家的响应格式也不同。

### OpenAI 响应（tool call）

```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": null,
      "tool_calls": [
        {
          "id": "call_abc123",
          "type": "function",
          "function": {
            "name": "get_weather",
            "arguments": "{\"city\": \"上海\", \"unit\": \"celsius\"}"
          }
        }
      ]
    },
    "finish_reason": "tool_calls"
  }]
}
```

注意：`arguments` 是**字符串**（JSON 序列化），需要 `json.loads()` 解析。

### Anthropic 响应（tool use）

```json
{
  "content": [
    {
      "type": "tool_use",
      "id": "toolu_01abc",
      "name": "get_weather",
      "input": { "city": "上海", "unit": "celsius" }
    }
  ],
  "stop_reason": "tool_use"
}
```

注意：`input` 已经是**解析好的对象**，不需要再 `json.loads()`。

---

## 四、工具结果的传递方式

这是两套 API 差异最大的地方，写兼容代码时最容易踩坑。

### OpenAI：用 `role: "tool"` 消息

```json
{
  "role": "tool",
  "tool_call_id": "call_abc123",
  "content": "{\"temperature\": 28, \"condition\": \"晴\"}"
}
```

- 需要把 `tool_call_id` 原样返回
- `content` 是字符串（可以是 JSON 字符串）

### Anthropic：在 `user` 消息里嵌套 `tool_result`

```json
{
  "role": "user",
  "content": [
    {
      "type": "tool_result",
      "tool_use_id": "toolu_01abc",
      "content": "温度 28°C，晴天"
    }
  ]
}
```

- 工具结果放在 **user 角色**的内容块里，而非独立角色
- `content` 可以是字符串，也可以是包含文本/图片的内容块数组

---

## 五、并行工具调用

当模型需要同时调用多个工具时（例如同时查天气和日历），两家都支持，但实现细节不同。

### OpenAI 并行调用

响应里 `tool_calls` 是数组，可能同时包含多个调用：

```json
"tool_calls": [
  {"id": "call_1", "function": {"name": "get_weather", "arguments": "..."}},
  {"id": "call_2", "function": {"name": "get_calendar", "arguments": "..."}}
]
```

回传时需要提供**每个 `tool_call_id` 对应的 tool 消息**，数量必须匹配。

### Anthropic 并行调用

`content` 数组里包含多个 `tool_use` 块：

```json
"content": [
  {"type": "text", "text": "我需要同时查询天气和日历"},
  {"type": "tool_use", "id": "toolu_1", "name": "get_weather", "input": {...}},
  {"type": "tool_use", "id": "toolu_2", "name": "get_calendar", "input": {...}}
]
```

注意：Claude 可能在 tool_use 块前面附加一段 `text` 解释，OpenAI 的 `content` 在工具调用时通常为 `null`。

**Anthropic 并行结果回传：**

```json
{
  "role": "user",
  "content": [
    {"type": "tool_result", "tool_use_id": "toolu_1", "content": "28°C 晴"},
    {"type": "tool_result", "tool_use_id": "toolu_2", "content": "今天无会议"}
  ]
}
```

---

## 六、强制调用与禁止调用

某些场景需要强制让模型调用（或不调用）工具，两家的控制字段不一样：

| 场景 | OpenAI | Anthropic |
|---|---|---|
| 让模型自己决定 | `tool_choice: "auto"` | `tool_choice: {"type": "auto"}` |
| 强制调用某个工具 | `tool_choice: {"type":"function","function":{"name":"X"}}` | `tool_choice: {"type":"tool","name":"X"}` |
| 强制调用至少一个工具 | `tool_choice: "required"` | `tool_choice: {"type":"any"}` |
| 禁止调用任何工具 | `tool_choice: "none"` | 不传 tools，或者 Anthropic 暂无等效选项 |

Anthropic 目前没有 `tool_choice: none` 的等效选项——如果传了 tools 但想让模型忽略，只能在 prompt 里说明，或者干脆不传 `tools` 字段。

---

## 七、Streaming 下的差异

Streaming 场景更复杂，差异也更大。

**OpenAI Streaming**：工具调用通过 `delta.tool_calls` 字段逐块推送，`arguments` 是增量字符串，需要自己拼接后再解析。

**Anthropic Streaming**：通过特定事件类型区分：
- `content_block_start`（`type: tool_use`）标志工具调用开始
- `content_block_delta`（`type: input_json_delta`）推送增量 JSON
- `content_block_stop` 标志结束

Anthropic 的事件结构更明确，但需要维护状态机跟踪多个内容块。

---

## 八、兼容层设计思路

如果你的 Agent 需要同时支持 OpenAI 和 Anthropic，可以在中间加一个适配层：

```python
def normalize_tool_definition(tool: dict, provider: str) -> dict:
    """把统一格式的工具定义转换为各 provider 的格式"""
    if provider == "openai":
        return {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"]
            }
        }
    elif provider == "anthropic":
        return {
            "name": tool["name"],
            "description": tool["description"],
            "input_schema": tool["input_schema"]
        }

def extract_tool_calls(response, provider: str) -> list[dict]:
    """从响应中提取工具调用，统一格式"""
    calls = []
    if provider == "openai":
        for tc in response.choices[0].message.tool_calls or []:
            calls.append({
                "id": tc.id,
                "name": tc.function.name,
                "input": json.loads(tc.function.arguments)
            })
    elif provider == "anthropic":
        for block in response.content:
            if block.type == "tool_use":
                calls.append({
                    "id": block.id,
                    "name": block.name,
                    "input": block.input  # 已经是 dict，不需要 json.loads
                })
    return calls
```

这样上层 Agent 逻辑只处理统一的 `{"id", "name", "input"}` 格式，切换 provider 只需换适配层。

---

## 九、实际开发中最常踩的坑

**1. `arguments` vs `input` 的类型问题**：OpenAI 的 `arguments` 是字符串，Anthropic 的 `input` 是对象。跨 provider 复用代码时最容易在这里崩。

**2. 工具结果的角色问题**：OpenAI 用 `role: "tool"`，Anthropic 用 `role: "user"` + `type: "tool_result"`。直接把 OpenAI 的消息格式发给 Anthropic 会报错。

**3. 并行调用后 assistant 消息的处理**：Anthropic 要求在 user 的 tool_result 消息之前，必须把完整的 assistant 消息（含所有 tool_use 块）先放进对话历史，否则会提示 `tool_use_id` 找不到。

**4. 文本 + 工具混合内容**：Claude 经常在 tool_use 之前先输出一段文字，`content` 是数组而非单个对象。OpenAI 的 `content` 在工具调用时是 `null`，需要分别处理。

**5. JSON Schema 的支持范围**：两家对 JSON Schema 的支持程度有细微差异。Anthropic 明确说明支持 JSON Schema draft 2020-12 的子集，`enum`、`anyOf` 等在实际使用中偶有边界行为差异，复杂 Schema 建议实测。

---

## 十、相关阅读

- [Claude Tool Use 最佳实践](/blog/claude-tool-use-best-practices/)
- [OpenAI Responses API 完整指南](/blog/openai-responses-api-guide/)
- [Claude 并行工具调用实战](/blog/parallel-tool-use-claude/)
- [OpenAI 兼容协议 vs Anthropic 原生协议对比](/blog/openai-compatible-vs-anthropic-protocol/)
- [结构化输出（Structured Output）使用指南](/blog/structured-output-llm-guide/)

需要在国内稳定调用 Claude 和 GPT 全系模型，[YoTradeApi](https://yotradeapi.com) 提供统一的 OpenAI 兼容接口，一个 key 覆盖多家模型，无需处理网络和计费问题。
