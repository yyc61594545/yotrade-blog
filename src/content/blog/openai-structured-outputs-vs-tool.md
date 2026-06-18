---
title: OpenAI Structured Outputs vs tool_choice 选型指南
description: 深度对比 OpenAI Structured Outputs 与 tool_choice:required 两种强制结构化输出方案，分析适用场景与性能差异，含代码示例。
keywords:
  - OpenAI Structured Outputs
  - tool_choice required
  - 结构化输出选型
  - JSON Schema 强制输出
  - OpenAI 函数调用对比
pubDate: '2026-06-18'
updatedDate: '2026-06-18'
canonical: https://blog.yotradeapi.com/blog/openai-structured-outputs-vs-tool/
tags:
  - OpenAI
  - 结构化输出
  - 技术深度
  - API 设计
category: 技术深度
heroImage: ../../assets/blog-placeholder-1.jpg
---

OpenAI 在 2024 年下半年推出了 Structured Outputs 功能，允许开发者传入 JSON Schema，模型会严格按照 schema 输出合法 JSON。在这之前，强制获得结构化输出的主流方案是 `tool_choice: "required"` + 定义一个"假工具"。现在这两条路都能走，很多开发者在选型时感到困惑：它们有什么本质区别？什么时候用哪个？

本文给出一个清晰的决策框架。

---

## 一、两种方案的工作原理

### 1.1 Structured Outputs

Structured Outputs 通过在 `response_format` 里传入 JSON Schema，让模型在解码阶段直接约束输出 Token 的合法范围，从语法层面保证输出符合 schema。

```python
from openai import OpenAI
from pydantic import BaseModel

client = OpenAI()

class ArticleMeta(BaseModel):
    title: str
    summary: str
    tags: list[str]
    word_count: int

response = client.beta.chat.completions.parse(
    model="gpt-4o-2024-08-06",
    messages=[
        {"role": "user", "content": "分析这篇文章并提取元数据：...（文章内容）"}
    ],
    response_format=ArticleMeta,
)

article = response.choices[0].message.parsed
print(article.title)     # 直接访问，已是 Python 对象
print(article.tags)      # list[str] 类型安全
```

使用 Pydantic 模型时，OpenAI SDK 会自动将其转换为 JSON Schema，并在响应时自动解析回 Python 对象。

### 1.2 tool_choice: required

`tool_choice: "required"` 强制模型必须调用某个工具，通过"假工具"的参数定义来约束输出结构：

```python
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "user", "content": "分析这篇文章并提取元数据：...（文章内容）"}
    ],
    tools=[{
        "type": "function",
        "function": {
            "name": "extract_article_meta",
            "description": "提取文章元数据",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "summary": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "word_count": {"type": "integer"},
                },
                "required": ["title", "summary", "tags", "word_count"],
            }
        }
    }],
    tool_choice={"type": "function", "name": "extract_article_meta"},
)

import json
tool_call = response.choices[0].message.tool_calls[0]
result = json.loads(tool_call.function.arguments)
```

---

## 二、核心差异对比

| 维度 | Structured Outputs | tool_choice: required |
|------|-------------------|----------------------|
| 输出合法性保证 | **语法级别**，100% 合法 JSON | **语义级别**，偶有边缘 case 不合规 |
| Pydantic 集成 | 原生支持（SDK .parse()） | 需手动 json.loads + 验证 |
| 支持的模型 | gpt-4o-2024-08-06 起 | 所有支持 Function Calling 的模型 |
| 流式响应处理 | 需要 stream=True + 额外处理 | 标准流式即可 |
| 多工具并行调用 | 不适用 | 原生支持 |
| 响应结构 | `message.content` 为 null，数据在 `parsed` | 数据在 `tool_calls[0].function.arguments` |
| API 兼容性 | 仅 OpenAI 官方 | 大多数 OpenAI 兼容 API 均支持 |
| 输出 token 开销 | 略低（无工具元数据） | 略高（含工具定义 token） |

---

## 三、Structured Outputs 的技术限制

Structured Outputs 并不是万能的，它有一些需要注意的约束：

### 3.1 JSON Schema 限制

不是所有 JSON Schema 特性都被支持。目前不支持：

- `anyOf`（有限支持，需要特定写法）
- `oneOf`
- `if/then/else`
- 自定义 format（如 `format: "date"`）
- `$ref` 嵌套（不超过一定深度）

```python
# ❌ 不支持的写法
class Result(BaseModel):
    value: int | str  # 对应 anyOf，可能触发限制

# ✅ 推荐写法：明确类型
class Result(BaseModel):
    value: str  # 统一为 str，应用层自行转换
```

### 3.2 必须全字段 required

Structured Outputs 要求 schema 里所有字段必须是 required，不支持 optional 字段。用 Pydantic 时：

```python
from typing import Optional

# ❌ 会触发 schema 验证错误
class Meta(BaseModel):
    title: str
    subtitle: Optional[str] = None  # optional 字段

# ✅ 用 Union with None 并显式声明
class Meta(BaseModel):
    title: str
    subtitle: str | None  # 告诉模型可以输出 null
```

### 3.3 首个 token 延迟

因为语法约束在解码层生效，首个 token 的延迟（TTFT）会比普通请求略高，在 P99 延迟敏感的场景需要压测确认。

---

## 四、tool_choice 的使用场景

`tool_choice: required` 在以下场景里仍然是更合适的选择：

### 4.1 需要并行调用多工具

```python
# 同一个请求里让模型并行调用多个工具
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "查询北京今天的天气和明天的航班"}],
    tools=[get_weather_tool, search_flights_tool],
    tool_choice="required",  # 要求至少调用一个工具
)

# 模型可能同时返回两个 tool_calls
for tool_call in response.choices[0].message.tool_calls:
    print(f"工具: {tool_call.function.name}")
    print(f"参数: {tool_call.function.arguments}")
```

Structured Outputs 不支持多工具并行，这是 tool_choice 的独家能力。

### 4.2 与其他 OpenAI 兼容 API 对接

如果你的代码需要同时兼容 OpenAI 和其他厂商（如百川、智谱、Moonshot），`response_format` 的 JSON Schema 支持程度差异较大，而 Function Calling 的标准化程度更高。

```python
# 这段代码可以兼容多个 OpenAI 兼容厂商
def extract_with_tool(client, model, text):
    return client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": text}],
        tools=[extraction_tool],
        tool_choice={"type": "function", "name": "extract"},
    )
```

### 4.3 需要模型"选择性"调用

如果你有多个工具，但不确定每次都需要哪个，用 `tool_choice: "auto"` 让模型自己决定，而不是强制指定。Structured Outputs 没有这个灵活性——要么全量输出，要么什么都不输出。

---

## 五、决策树

```
你需要结构化输出吗？
├── 是 → 你的模型是 gpt-4o-2024-08-06 或更新版本吗？
│         ├── 是 → 你需要并行调用多个工具吗？
│         │         ├── 是 → tool_choice: required
│         │         └── 否 → 你的代码是否需要兼容非 OpenAI 厂商？
│         │                    ├── 是 → tool_choice: required
│         │                    └── 否 → ✅ Structured Outputs（推荐）
│         └── 否 → tool_choice: required
└── 否 → 正常请求
```

简而言之：**如果只用 OpenAI 官方 API + 不需要多工具并行，优先用 Structured Outputs**；其他情况用 `tool_choice: required`。

---

## 六、生产代码示例

### 完整的 Structured Outputs 模式

```python
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import Literal

client = OpenAI()

class ReviewAnalysis(BaseModel):
    sentiment: Literal["positive", "negative", "neutral"]
    score: float = Field(ge=0, le=10, description="评分 0-10")
    key_points: list[str] = Field(min_length=1, max_length=5)
    language: str

def analyze_review(review_text: str) -> ReviewAnalysis:
    response = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=[
            {"role": "system", "content": "你是一个评论分析助手"},
            {"role": "user", "content": f"分析以下用户评论：\n{review_text}"},
        ],
        response_format=ReviewAnalysis,
    )

    # 检查 refusal
    if response.choices[0].message.refusal:
        raise ValueError(f"模型拒绝回答: {response.choices[0].message.refusal}")

    return response.choices[0].message.parsed

# 使用
result = analyze_review("这个产品非常好用，快递也很快，下次还会购买！")
print(f"情感: {result.sentiment}, 评分: {result.score}")
print(f"关键点: {result.key_points}")
```

注意 `response.choices[0].message.refusal`——当模型认为请求违反内容策略时，会走 refusal 而非输出 JSON，生产代码必须处理这个 case。

---

## 七、相关阅读

- [Function Calling vs Tool Use 详细对比](/blog/function-calling-vs-tool-use/)
- [LLM JSON 模式横向对比](/blog/llm-json-mode-comparison/)
- [LLM 函数调用并行执行实战](/blog/llm-function-calling-parallel/)
- [结构化输出 LLM 完全指南](/blog/structured-output-llm-guide/)
- [LLM 摘要质量横评：六大模型实测](/blog/llm-summarization-quality/)

调用 OpenAI API 时若遇到网络问题，[YoTradeApi](https://yotradeapi.com) 提供稳定的中转接入，完整支持 Structured Outputs 与 Function Calling，OpenAI SDK 无缝切换。
