---
title: response_format 参数完全指南：JSON 模式与结构化输出
description: 深入讲解 LLM API 的 response_format 参数，涵盖 JSON mode、structured outputs、schema 校验及主流模型兼容性，帮助开发者稳定获取结构化数据。
keywords:
  - response_format 参数
  - LLM JSON mode
  - 结构化输出 API
  - OpenAI structured outputs
  - JSON schema LLM
pubDate: '2026-05-22'
updatedDate: '2026-05-22'
canonical: https://blog.yotradeapi.com/blog/llm-response-format-cn-guide/
tags:
  - response_format
  - JSON模式
  - 结构化输出
  - API调用
category: 技术深度
heroImage: ../../assets/blog-placeholder-2.jpg
---

在把 LLM 输出接入业务系统时，最让开发者头疼的问题往往不是模型智能，而是**输出格式不稳定**：有时多一句废话，有时 JSON 键名拼错，有时多余的 markdown 代码块包裹导致 `JSON.parse` 直接报错。`response_format` 参数就是为解决这类问题而生的。本文从原理到实战，系统讲解这个参数的用法、各模型的兼容性差异，以及生产环境的最佳实践。

## 一、response_format 是什么

`response_format` 是 OpenAI 兼容 API 中的一个请求参数，用于**约束模型的输出格式**。最早由 OpenAI 在 GPT-3.5/4 时代引入，目前已成为 OpenAI 兼容接口的事实标准，DeepSeek、Qwen、Gemini 等主流模型的兼容端点均有不同程度的支持。

参数接受一个对象，目前有三种取值：

| 取值 | 含义 |
|------|------|
| `{ "type": "text" }` | 默认，普通文本输出 |
| `{ "type": "json_object" }` | JSON 模式：保证输出合法 JSON |
| `{ "type": "json_schema", "json_schema": {...} }` | 结构化输出：按 Schema 严格校验 |

## 二、JSON mode（json_object）

JSON mode 是最简单的约束方式，只保证输出是**合法的 JSON 字符串**，不约束字段结构。

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://api.yotradeapi.com/v1",
    api_key="your-api-key"
)

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {
            "role": "system",
            "content": "你是一个数据提取助手，必须以 JSON 格式返回结果。"
        },
        {
            "role": "user",
            "content": "从以下文本提取姓名和年龄：张伟，28岁，软件工程师"
        }
    ],
    response_format={"type": "json_object"}
)

import json
data = json.loads(response.choices[0].message.content)
print(data)  # {"name": "张伟", "age": 28, "occupation": "软件工程师"}
```

**注意事项**：

1. **必须在 prompt 中提及 JSON**：如果 system prompt 或 user message 不包含"JSON"关键词，部分模型会拒绝或产生异常。OpenAI 官方文档明确要求这一点。
2. **不保证字段完整性**：模型可能自行决定返回哪些字段，字段名可能与预期不同。
3. **不适用于流式输出解析**：流式模式下 JSON 对象在 chunk 边界被切断，需要积攒完整再解析。

## 三、Structured Outputs（json_schema）

Structured Outputs 是 OpenAI 在 2024 年推出的进阶功能，通过提供 JSON Schema 来**精确约束输出的字段、类型和必填项**。

```python
response = client.chat.completions.create(
    model="gpt-4o-2024-08-06",  # 需要支持 structured outputs 的版本
    messages=[
        {"role": "user", "content": "提取以下文章的关键信息：今日头条报道..."}
    ],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "article_extraction",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "author": {"type": "string"},
                    "publish_date": {"type": "string", "format": "date"},
                    "summary": {"type": "string", "maxLength": 200},
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["title", "summary", "tags"],
                "additionalProperties": False
            }
        }
    }
)
```

当 `strict: true` 时，模型**必须**按照 Schema 输出，且不允许额外字段（`additionalProperties: false` 生效）。这是生产环境下接入数据管道最可靠的方式。

## 四、主流模型兼容性对照

不同模型对 `response_format` 的支持程度差异较大，下表整理了常见模型的情况（基于公开文档，实际效果以测试为准）：

| 模型 | json_object | json_schema + strict |
|------|------------|----------------------|
| gpt-4o / gpt-4o-mini | ✅ 稳定 | ✅ 2024-08-06 版本起 |
| gpt-3.5-turbo | ✅ 支持 | ❌ 不支持 |
| claude-3.5-sonnet | ⚠️ 通过兼容层 | ⚠️ 有限支持 |
| deepseek-v3 | ✅ 支持 | ⚠️ 部分支持 |
| qwen-plus / qwen-max | ✅ 支持 | ⚠️ 部分支持 |
| gemini-1.5-pro | ✅ 支持 | ✅ 通过 response_schema |

Claude 系列模型本身通过 tool_use 机制实现更可靠的结构化输出，直接使用 `response_format` 的效果视兼容层实现而定。

## 五、Pydantic 集成：Python 最佳实践

OpenAI Python SDK 支持直接传入 Pydantic 模型，自动生成 Schema 并解析结果，是 Python 项目的推荐做法：

```python
from pydantic import BaseModel
from typing import List, Optional
from openai import OpenAI

class ProductInfo(BaseModel):
    name: str
    price: float
    currency: str = "CNY"
    features: List[str]
    in_stock: bool
    discount: Optional[float] = None

client = OpenAI(
    base_url="https://api.yotradeapi.com/v1",
    api_key="your-api-key"
)

completion = client.beta.chat.completions.parse(
    model="gpt-4o",
    messages=[
        {"role": "user", "content": "从以下商品描述提取信息：苹果 iPhone 16，售价 5999 元，支持 A18 芯片，现货供应，无折扣"}
    ],
    response_format=ProductInfo,
)

product = completion.choices[0].message.parsed
print(product.name)    # iPhone 16
print(product.price)   # 5999.0
print(product.in_stock)  # True
```

`client.beta.chat.completions.parse()` 会自动处理 Schema 生成和结果反序列化，`message.parsed` 直接返回类型化的 Pydantic 对象，省去手动 `json.loads` 和字段映射。

## 六、TypeScript / Node.js 使用方式

```typescript
import OpenAI from "openai";
import { zodResponseFormat } from "openai/helpers/zod";
import { z } from "zod";

const client = new OpenAI({
  baseURL: "https://api.yotradeapi.com/v1",
  apiKey: process.env.API_KEY,
});

const UserSchema = z.object({
  id: z.string(),
  name: z.string(),
  email: z.string().email(),
  role: z.enum(["admin", "user", "guest"]),
  createdAt: z.string().datetime(),
});

async function extractUser(text: string) {
  const response = await client.beta.chat.completions.parse({
    model: "gpt-4o",
    messages: [{ role: "user", content: `从以下文本提取用户信息：${text}` }],
    response_format: zodResponseFormat(UserSchema, "user_extraction"),
  });

  const user = response.choices[0].message.parsed;
  if (!user) throw new Error("解析失败");
  return user; // 类型为 z.infer<typeof UserSchema>
}
```

`zodResponseFormat` 会将 Zod schema 转换为 JSON Schema 并包装为正确的 `response_format` 对象，同时负责结果反序列化。

## 七、常见错误与排查

**错误一：`json_object` 模式下返回非 JSON**

原因通常是 prompt 里没有明确提 JSON，或模型版本不支持。解决方案：在 system prompt 中加入"请以合法 JSON 格式返回，不要有其他内容"。

**错误二：`finish_reason` 为 `length` 导致 JSON 不完整**

设置足够的 `max_tokens`，或在业务层检查 `finish_reason`：

```python
choice = response.choices[0]
if choice.finish_reason == "length":
    raise ValueError("输出被截断，JSON 不完整，请增大 max_tokens")
```

**错误三：Schema 中有不支持的关键字**

Structured Outputs 的 `strict` 模式不支持所有 JSON Schema 关键字，`anyOf`、`if/then/else` 等在某些实现中不可用。尽量用 `enum`、`oneOf`（简单场景）代替复杂条件。

**错误四：嵌套对象字段缺失**

`strict: true` 时，所有嵌套对象也需要声明 `additionalProperties: false`，且子对象的必填字段全部在 `required` 中列出。

## 八、何时用 response_format，何时用 tool_use

`response_format` 和 `tool_use` 都能实现结构化输出，但适用场景不同：

| 场景 | 推荐方案 |
|------|----------|
| 一次性数据提取，输出即为最终结果 | `response_format` json_schema |
| 需要模型"调用函数"并可能多轮交互 | `tool_use` |
| Claude 模型，需要最高可靠性 | `tool_use` 定义单个工具 |
| 简单字段约束，快速验证 | `response_format` json_object |
| 流式实时渲染部分字段 | 两者都有挑战，考虑 streaming + 手动解析 |

对于 Claude 模型，官方推荐通过定义只有一个工具的 `tools` 列表并设置 `tool_choice: {"type": "tool", "name": "..."}` 来实现可靠的结构化输出，比 `response_format` 稳定性更高。

## 九、相关阅读

- [结构化输出 LLM 完整指南：JSON Schema 约束与最佳实践](/blog/structured-output-llm-guide/)
- [LLM JSON 模式横向对比：各模型稳定性测试](/blog/llm-json-mode-comparison/)
- [function calling 与 tool use 核心区别详解](/blog/function-calling-vs-tool-use/)
- [Claude tool use 使用最佳实践与常见坑](/blog/claude-tool-use-best-practices/)

如果你需要稳定调用 GPT-4o、Claude、DeepSeek 等模型的结构化输出能力，[YoTradeApi](https://yotradeapi.com) 提供统一的 OpenAI 兼容接口，支持多模型切换与自动重试。
