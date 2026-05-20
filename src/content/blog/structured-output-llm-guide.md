---
title: LLM 结构化输出完全指南（JSON Schema / Function Call）
description: OpenAI / Claude / Gemini 结构化输出（JSON Schema、Tool Use、Response Format）的完整对比与实战，含 Pydantic / Zod 集成。
keywords:
- llm 结构化输出
- json schema llm
- claude structured output
- openai response format
- pydantic ai
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/structured-output-llm-guide/
tags:
- 结构化输出
- JSON Schema
- Tool Use
- Pydantic
- 工程实战
category: 工程实战
heroImage: ../../assets/blog-placeholder-4.jpg
---

把 LLM 当后端接口用的人都遇到过：模型有时输出多了一句"以下是 JSON：" 之类的废话，JSON 解析失败。本文讲清楚三家旗舰的"结构化输出"机制怎么用。

## 一、三种主要机制

| 机制 | OpenAI | Claude | Gemini |
| --- | --- | --- | --- |
| Response Format json_object | ✓ | ✗ | ✓ |
| Response Format json_schema | ✓ | ✗ | ✓ |
| Tool Use (function call) | ✓ | ✓ | ✓ |
| Prefill + 严格 prompt | 都可 | 都可 | 都可 |

## 二、OpenAI 的 `response_format`

最优雅的方式。GPT-4 / GPT-5 直接支持：

```python
from pydantic import BaseModel

class User(BaseModel):
    name: str
    age: int
    skills: list[str]

resp = client.chat.completions.parse(
    model="gpt-5",
    messages=[{"role": "user", "content": "造一个用户：张三，30 岁，会 Python 和 Go"}],
    response_format=User,
)

user: User = resp.choices[0].message.parsed
print(user.name, user.skills)
```

要点：

- `client.chat.completions.parse`（注意是 parse，不是 create）
- 直接传 Pydantic 模型
- 返回的 `parsed` 已是 Pydantic 对象，省手工 JSON 解析

底层 OpenAI 会把 Pydantic 转 JSON Schema 注入 API。

## 三、Claude 用 Tool Use 实现结构化

Claude 没有 response_format，但 tool_use 等价：

```python
import anthropic, json

client = anthropic.Anthropic(base_url="https://yotradeapi.com", api_key="sk-yo-...")

schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer"},
        "skills": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["name", "age", "skills"],
}

resp = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1000,
    tools=[{
        "name": "save_user",
        "description": "保存用户信息",
        "input_schema": schema,
    }],
    tool_choice={"type": "tool", "name": "save_user"},   # 强制调用这个 tool
    messages=[{"role": "user", "content": "造一个用户：张三，30 岁，会 Python 和 Go"}],
)

for block in resp.content:
    if block.type == "tool_use" and block.name == "save_user":
        user_data = block.input
        print(user_data)
```

`tool_choice={"type": "tool", "name": "..."}` 强制 Claude 调用某个 tool——这是把"输出结构化"的关键技巧。

## 四、Gemini 的 response_schema

```python
client.chat.completions.create(
    model="gemini-2.5-pro",
    messages=[{"role": "user", "content": "造一个用户"}],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "user",
            "schema": schema,
            "strict": True,
        },
    },
)
```

Gemini 通过 OpenAI 兼容协议下支持 `response_format`。

## 五、为什么不要用 "Prompt 里要求 JSON"

```
> 输出严格的 JSON，不要其它内容
```

这种 prompt 在简单场景能用，但**不稳定**：

- 模型可能加 markdown 围栏 ```json
- 偶尔加注释
- 中文标点混进去
- 输出截断

**结构化输出机制比 prompt 更可靠**——模型在生成时会按 schema 约束。

## 六、复杂 schema 例子

```python
class Task(BaseModel):
    title: str
    priority: Literal["low", "medium", "high"]
    due_date: date | None
    assignee: str | None

class Project(BaseModel):
    name: str
    description: str
    tasks: list[Task]
    tags: list[str]

resp = client.chat.completions.parse(
    model="gpt-5",
    messages=[{"role": "user", "content": "从这段话提取项目：'公司官网重做。重要任务：5月底前发布。Alice 设计，Bob 开发'"}],
    response_format=Project,
)
```

嵌套对象 + 可选字段 + 枚举都支持。

## 七、Streaming + 结构化

OpenAI 支持流式结构化：

```python
with client.chat.completions.stream(
    model="gpt-5",
    messages=[...],
    response_format=Project,
) as stream:
    for event in stream:
        if event.type == "content.delta":
            print(event.parsed)  # 累积的部分对象
```

每个 chunk 给一个"逐步构建"的对象，UI 可以实时渲染。Claude 当前不支持流式结构化（tool_use 流式可解析但更复杂）。

## 八、常见错误模式

### 错误 1：schema 太松

```python
{"type": "object"}   # 没指定 properties
```

模型可能输出任意 JSON，没真正"结构化"。

### 错误 2：required 字段没加

```python
{
    "type": "object",
    "properties": {"name": {"type": "string"}}
    # 缺 "required": ["name"]
}
```

模型可能省略字段。

### 错误 3：用 free-text 字段没约束

```python
{"description": {"type": "string"}}   # 100% 自由
```

可以用 `maxLength`、`pattern`、`enum` 进一步约束。

### 错误 4：strict=false

OpenAI 的 strict 模式：

```python
"strict": True
```

不开 strict，模型偶尔会"协议外发挥"。

## 九、Tool Use vs Response Format

什么时候用哪个：

| 场景 | 推荐 |
| --- | --- |
| 只要一个固定结构 | response_format |
| 模型可能调用多个 tool | tool_use |
| Claude 模型 | tool_use（强制单 tool） |
| 需要"先思考再输出" | response_format 不适合，用 tool_use + reasoning |
| 嵌套深 | response_format |

## 十、与 Pydantic / Zod / TypeBox 集成

| 语言 | 库 |
| --- | --- |
| Python | Pydantic v2 |
| TypeScript | Zod、TypeBox |
| Rust | serde + schemars |
| Go | jsonschema |

OpenAI Python SDK 直接吃 Pydantic，TypeScript 直接吃 Zod：

```ts
import { z } from "zod";
import { zodResponseFormat } from "openai/helpers/zod";

const User = z.object({
  name: z.string(),
  age: z.number().int(),
});

const completion = await client.chat.completions.parse({
  model: "gpt-5",
  messages: [...],
  response_format: zodResponseFormat(User, "user"),
});
```

## 十一、中转兼容性

`response_format` 在 OpenAI 兼容路径下需要中转**完整透传**。测试：

```bash
curl https://yotradeapi.com/v1/chat/completions \
  -H "Authorization: Bearer $KEY" \
  -d '{
    "model": "gpt-5",
    "messages": [{"role":"user","content":"x"}],
    "response_format": {
      "type": "json_schema",
      "json_schema": {"name":"x","schema":{"type":"object"},"strict":true}
    }
  }'
```

返回 200 + JSON 合法即可。

## 十二、何时不用结构化输出

- 输出本身就是自由文本（文章、故事）
- 极简场景（单字符回答用 prompt 够）
- 模型不支持（一些小模型）

## 十三、相关阅读

- [OpenAI SDK base_url 国内配置实战](/blog/openai-sdk-base-url-cn/)
- [AI Agent Prompt Engineering 中文实战](/blog/agent-prompt-engineering-cn/)
- [OpenAI 兼容协议 vs Anthropic 原生协议](/blog/openai-compatible-vs-anthropic-protocol/)
- [Python 异步并发调用 LLM API](/blog/python-async-llm-client/)
- [LangChain 中文实战](/blog/langchain-cn-tutorial/)

需要支持 response_format 与 tool_use 完整透传的中转？[YoTradeApi](https://yotradeapi.com) 同时支持两种结构化机制。
