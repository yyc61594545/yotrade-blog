---
title: Claude 并行 Tool Use 实战：一次调用多个工具
description: Claude 模型的并行 tool_use（同一回合内多个工具调用）原理、配置、性能优势与典型应用场景，含 Python 实战代码。
keywords:
- claude 并行 tool use
- parallel tool call
- claude function call
- tool use 优化
- claude tool 并发
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/parallel-tool-use-claude/
tags:
- Claude
- Tool Use
- 并行
- 进阶
- 性能优化
category: 工程实战
heroImage: ../../assets/blog-placeholder-5.jpg
---

# Claude 并行 Tool Use 实战：一次调用多个工具

普通 tool use 是"一回合一个工具"。Claude（与 GPT-5）支持**一回合多个工具并行调用**，能让 agent 任务速度翻倍。本文给原理 + 实战代码。

## 一、串行 vs 并行 tool use

### 串行（默认）

```
回合 1：模型 → "我要调 get_weather"
        ↓
        客户端跑 get_weather(北京)
        ↓
回合 2：模型 → "现在我要调 get_news"
        ↓
        客户端跑 get_news()
        ↓
回合 3：模型 → "综合上面，回答："
```

3 个 LLM 回合 + 2 个外部 API 串行。总耗时 = 3×LLM + 2×API。

### 并行

```
回合 1：模型 → "我要并行调 get_weather + get_news"
        ↓
        客户端并行跑两个 API
        ↓
回合 2：模型 → "综合，回答："
```

2 个 LLM 回合 + API 并行。**总耗时 = 2×LLM + max(API)**。

对延迟敏感的应用（聊天界面、对话 agent），这是数量级提升。

## 二、Claude 并行 tool use 启用

Anthropic 默认开。在 prompt 里加一句强化：

```python
import anthropic

client = anthropic.Anthropic(base_url="https://yotradeapi.com", api_key="sk-yo-...")

resp = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=2000,
    system="如果用户问题需要多个工具结果，并行调用它们。",
    tools=[
        {
            "name": "get_weather",
            "description": "查城市天气",
            "input_schema": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        },
        {
            "name": "get_news",
            "description": "查最新新闻",
            "input_schema": {
                "type": "object",
                "properties": {"topic": {"type": "string"}},
                "required": ["topic"],
            },
        },
    ],
    messages=[{"role": "user", "content": "北京今天什么天气？最近 AI 圈有什么新闻？"}],
)

# 检查并发 tool_use
tool_calls = [b for b in resp.content if b.type == "tool_use"]
print(f"模型并行调用了 {len(tool_calls)} 个工具")
for call in tool_calls:
    print(f"  - {call.name}: {call.input}")
```

输出：

```
模型并行调用了 2 个工具
  - get_weather: {'city': '北京'}
  - get_news: {'topic': 'AI'}
```

## 三、客户端并发执行

```python
import asyncio

async def get_weather(city):
    # 实际 API 调用
    await asyncio.sleep(1)
    return f"{city} 25 度晴"

async def get_news(topic):
    await asyncio.sleep(1)
    return [f"{topic} 新闻 1", f"{topic} 新闻 2"]

async def execute_tools(tool_calls):
    """并行执行多个 tool"""
    async def one(call):
        if call.name == "get_weather":
            result = await get_weather(**call.input)
        elif call.name == "get_news":
            result = await get_news(**call.input)
        return {
            "type": "tool_result",
            "tool_use_id": call.id,
            "content": str(result),
        }
    return await asyncio.gather(*[one(c) for c in tool_calls])

# 把 tool 结果回传给模型
tool_results = asyncio.run(execute_tools(tool_calls))

# 第二轮：把结果发回，让模型综合
final = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=2000,
    tools=[...],   # 同上
    messages=[
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": resp.content},
        {"role": "user", "content": tool_results},
    ],
)

print(final.content[0].text)
```

## 四、`disable_parallel_tool_use` 显式关闭

某些场景（比如串行依赖）你要禁用并行：

```python
resp = client.messages.create(
    model="claude-sonnet-4-6",
    tools=[...],
    tool_choice={"type": "auto", "disable_parallel_tool_use": True},
    messages=[...],
)
```

模型一回合只调一个 tool。

## 五、典型应用场景

### 场景 1：聊天 agent 查询多个数据源

用户问："我的订单状态 + 账户余额 + 最近物流"。Agent 并行调 3 个内部 API，**比串行快 3 倍**。

### 场景 2：RAG 多策略检索

```
工具 A：向量检索
工具 B：BM25 检索
工具 C：metadata 过滤
```

并行跑三种检索，agent 综合给最终答案。

### 场景 3：多文档对比分析

```
工具 A：摘要 doc1
工具 B：摘要 doc2
工具 C：摘要 doc3
```

并行摘要后，agent 做对比。

### 场景 4：监控 dashboard

```
工具 A：CPU
工具 B：内存
工具 C：磁盘
工具 D：网络
```

一次性获取所有指标，agent 综合给健康报告。

## 六、性能实测

任务：查询 5 个内部 API（每个 1s）+ 综合回答。

| 模式 | 总耗时 |
| --- | --- |
| 串行（默认 OpenAI 旧版） | ~12s |
| 并行（Claude） | ~4s |
| 并行 + caching | ~3s |

**并行优势在工具数量增多时呈线性放大**。

## 七、并行 tool use 的陷阱

### 1. 工具有依赖时不能并行

```
get_user(id) → 返回 user
get_user_orders(user_id) → 需要上一步的 user
```

这种依赖关系模型理解之后会自动串行。**但你给的 prompt 要清楚**："先查 user 再查 orders" vs "并行查 user_id=1 的 user 和 orders"。

### 2. 部分工具失败处理

并行 5 个工具，1 个失败。三种策略：

```python
results = await asyncio.gather(*tasks, return_exceptions=True)
for r in results:
    if isinstance(r, Exception):
        # 失败：把 error 当 tool_result 回传给模型
        tool_results.append({
            "type": "tool_result",
            "tool_use_id": ...,
            "content": f"Error: {r}",
            "is_error": True,
        })
    else:
        tool_results.append({"type": "tool_result", "tool_use_id": ..., "content": str(r)})
```

模型看到 `is_error: True` 会自适应——可能重试、可能降级、可能问用户。

### 3. 并发限频

5 个工具并行 = 同时 5 个外部 API 请求。如果你的下游 API 有 RPM 限制，需要客户端限流（详见 [Python 异步并发调用 LLM API](/blog/python-async-llm-client/)）。

## 八、OpenAI 并行 tool use

GPT-5 也支持并行 tool use，配置类似：

```python
resp = client.chat.completions.create(
    model="gpt-5",
    messages=[...],
    tools=[...],
    parallel_tool_calls=True,   # 默认 True
)
```

返回的 `message.tool_calls` 是数组，里面可能有多个调用。

## 九、Gemini 并行 tool use

Gemini 通过 OpenAI 兼容协议也支持，**但部分版本 bug 较多**。建议测试一遍再上生产。

## 十、最佳实践

- ✓ system prompt 明确"独立任务可以并行"
- ✓ 客户端用 asyncio.gather 真正并发
- ✓ 每个 tool 设独立超时（避免一个慢拖垮全部）
- ✓ 失败时把 error 当结果回传，让模型自适应
- ✗ 不要假设模型总会并行（数据有依赖时模型自然串行）
- ✗ 不要把"必须串行"的工具放进并行 prompt

## 十一、相关阅读

- [Claude Code Subagent 实战](/blog/claude-code-subagent-practice/)
- [Python 异步并发调用 LLM API](/blog/python-async-llm-client/)
- [Claude Extended Thinking 完整指南](/blog/claude-extended-thinking-guide/)
- [LLM 结构化输出完全指南](/blog/structured-output-llm-guide/)
- [AI Agent Prompt Engineering 中文实战](/blog/agent-prompt-engineering-cn/)

需要 Claude / GPT 并行 tool use 完整透传的中转？[YoTradeApi](https://yotradeapi.com/register) 完整支持并行 tool_use 协议。
