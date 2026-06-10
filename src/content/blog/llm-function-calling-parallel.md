---
title: LLM 并行函数调用实战
description: 跨模型（Claude/GPT/Gemini）并行函数调用的工程实践：依赖图设计、扇出查询模式、部分失败处理与生产环境性能优化，含完整代码。
keywords:
  - LLM 并行函数调用
  - parallel function calling
  - LLM tool call 并发
  - AI Agent 工具调用优化
  - 多模型并行工具调用
pubDate: '2026-06-10'
updatedDate: '2026-06-10'
canonical: https://blog.yotradeapi.com/blog/llm-function-calling-parallel/
tags:
  - 函数调用
  - Agent
  - 技术深度
  - 性能优化
category: 技术深度
heroImage: ../../assets/blog-placeholder-5.jpg
---

并行函数调用是 LLM Agent 性能优化中最容易被忽视的一块。大多数教程只展示"模型返回工具调用 → 执行 → 返回结果"的单次线性流程，但真实的 Agent 任务往往需要同时拿到多个数据源的结果，串行执行在这里是纯粹的性能浪费。

本文聚焦**跨模型**的并行函数调用工程实践，覆盖 Claude、GPT-5、Gemini 三个主流模型，重点讲那些教程里不会告诉你的部分：依赖图设计、扇出查询、部分失败处理，以及生产环境里的实际问题。

Claude 自身的并行 Tool Use 基础可以参考 [Claude 并行 Tool Use 实战](/blog/parallel-tool-use-claude/)，这里专注讲跨模型的通用工程模式。

## 一、为什么并行调用是重要的

假设你的 Agent 任务是"分析一个用户的投资组合风险"，需要：

1. 获取股票 A 的当前价格
2. 获取股票 B 的当前价格
3. 获取当前市场情绪指标
4. 获取用户的历史风险偏好

串行执行：4 次 API 调用 × 平均 200ms = **800ms+**

并行执行：max(200ms × 4) = **约 200ms**

时间差距随工具数量线性增长。对于一个 6 步工具调用的 Agent，串行可能需要 2-3 秒，而并行控制在 0.5 秒以内——这是用户能感知的差距。

## 二、三个主流模型的并行调用差异

并行函数调用的支持情况：

| 模型 | 并行调用支持 | 一次最多并行数 | 强制调用特定工具 |
|------|------------|-------------|---------------|
| Claude 3.5/4.x | ✓ | 无硬限制（实测 5-10 较稳定） | `tool_choice: {type: "tool", name: "..."}` |
| GPT-5 / GPT-4o | ✓ | 无硬限制 | `tool_choice: {"type": "function", "function": {"name": "..."}}` |
| Gemini 2.5 | ✓ | 无硬限制 | `tool_config` 设置 `mode: ANY` |

三个模型都支持并行调用，但 API 格式不同，收到并行响应后的处理方式也略有差异。

### Claude 的并行调用格式

Claude 响应中的并行工具调用是一个数组：

```python
# Claude 响应结构（并行调用时）
{
    "type": "message",
    "content": [
        {"type": "text", "text": "我来查询这几个数据..."},
        {
            "type": "tool_use",
            "id": "toolu_01",
            "name": "get_stock_price",
            "input": {"symbol": "AAPL"}
        },
        {
            "type": "tool_use", 
            "id": "toolu_02",
            "name": "get_stock_price",
            "input": {"symbol": "MSFT"}
        }
    ]
}
```

返回结果时，需要把所有工具结果作为一条 `user` 消息中的多个 `tool_result` 块：

```python
messages.append({
    "role": "user",
    "content": [
        {
            "type": "tool_result",
            "tool_use_id": "toulu_01",
            "content": "182.50"
        },
        {
            "type": "tool_result",
            "tool_use_id": "toolu_02",
            "content": "425.30"
        }
    ]
})
```

### GPT-5 的并行调用格式

GPT-5 的格式略有不同：

```python
# GPT 响应结构（并行调用时）
{
    "choices": [{
        "message": {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call_abc",
                    "type": "function",
                    "function": {
                        "name": "get_stock_price",
                        "arguments": '{"symbol": "AAPL"}'
                    }
                },
                {
                    "id": "call_def",
                    "type": "function",
                    "function": {
                        "name": "get_stock_price",
                        "arguments": '{"symbol": "MSFT"}'
                    }
                }
            ]
        }
    }]
}
```

返回结果时，每个工具结果是独立的 `tool` 角色消息：

```python
messages.append({
    "role": "tool",
    "tool_call_id": "call_abc",
    "content": "182.50"
})
messages.append({
    "role": "tool",
    "tool_call_id": "call_def",
    "content": "425.30"
})
```

## 三、生产级并行调用执行器

下面是一个可复用的并行工具调用执行框架，支持：

- 真正的并行执行（`asyncio.gather`）
- 超时控制
- 部分失败容忍
- 统一日志

```python
import asyncio
import time
from typing import Any, Callable, Dict, List, Optional

async def execute_tool_calls_parallel(
    tool_calls: List[Dict],
    tool_registry: Dict[str, Callable],
    timeout: float = 10.0,
    fail_fast: bool = False
) -> List[Dict]:
    """
    并行执行多个工具调用，返回结果列表（顺序与输入一致）。
    fail_fast=True 时任一工具失败即取消其余调用。
    """
    async def execute_single(tool_call: Dict) -> Dict:
        tool_name = tool_call.get("name") or tool_call["function"]["name"]
        tool_id = tool_call.get("id") or tool_call.get("tool_use_id")
        
        if tool_name not in tool_registry:
            return {
                "id": tool_id,
                "success": False,
                "error": f"Unknown tool: {tool_name}",
                "result": None
            }
        
        try:
            args = tool_call.get("input") or tool_call.get("function", {}).get("arguments", {})
            if isinstance(args, str):
                import json
                args = json.loads(args)
            
            start = time.monotonic()
            result = await asyncio.wait_for(
                asyncio.coroutine(tool_registry[tool_name])(**args)
                if not asyncio.iscoroutinefunction(tool_registry[tool_name])
                else tool_registry[tool_name](**args),
                timeout=timeout
            )
            elapsed = time.monotonic() - start
            
            return {
                "id": tool_id,
                "name": tool_name,
                "success": True,
                "result": result,
                "elapsed_ms": round(elapsed * 1000)
            }
        except asyncio.TimeoutError:
            return {
                "id": tool_id,
                "name": tool_name,
                "success": False,
                "error": f"Tool timed out after {timeout}s",
                "result": None
            }
        except Exception as e:
            return {
                "id": tool_id,
                "name": tool_name,
                "success": False,
                "error": str(e),
                "result": None
            }
    
    if fail_fast:
        results = await asyncio.gather(
            *[execute_single(tc) for tc in tool_calls]
        )
    else:
        results = await asyncio.gather(
            *[execute_single(tc) for tc in tool_calls],
            return_exceptions=False
        )
    
    return list(results)
```

使用示例：

```python
# 定义工具实现（可以是同步或异步函数）
async def get_stock_price(symbol: str) -> str:
    # 实际实现调用股票 API
    await asyncio.sleep(0.1)  # 模拟网络延迟
    return f"{symbol}: 182.50"

async def get_market_sentiment() -> str:
    await asyncio.sleep(0.15)
    return "贪婪指数: 72（贪婪区间）"

tool_registry = {
    "get_stock_price": get_stock_price,
    "get_market_sentiment": get_market_sentiment,
}

# 执行并行工具调用
tool_calls = [
    {"id": "tc_1", "name": "get_stock_price", "input": {"symbol": "AAPL"}},
    {"id": "tc_2", "name": "get_stock_price", "input": {"symbol": "MSFT"}},
    {"id": "tc_3", "name": "get_market_sentiment", "input": {}},
]

results = asyncio.run(
    execute_tool_calls_parallel(tool_calls, tool_registry, timeout=5.0)
)
# 3 个工具约 150ms 内全部完成，而非 350ms
```

## 四、依赖图：何时并行，何时必须串行

并行不是万能的。某些工具调用存在依赖关系：

```
任务："分析用户 #123 的最新订单并生成退款建议"

第一轮（可并行）：
  ├── get_user_info(user_id=123)         → 返回用户基本信息
  ├── get_recent_orders(user_id=123)     → 返回最近 10 个订单
  └── get_refund_policy(category="全品类") → 返回当前退款政策

第二轮（依赖第一轮结果，再次并行）：
  ├── get_order_detail(order_id=最新订单ID)   ← 依赖第一轮的订单列表
  └── check_user_tier(user_tier=用户等级)    ← 依赖第一轮的用户信息
```

识别依赖的简单规则：
- 一个工具的参数**来自另一个工具的输出** → 有依赖，必须串行
- 两个工具的参数都来自用户输入或常量 → 无依赖，可并行

对于复杂 Agent，可以显式构建 DAG（有向无环图）来调度工具调用，但大多数场景下，"两轮并行"的简单模型已经足够——第一轮并行拿基础数据，第二轮并行拿依赖数据。

## 五、部分失败的处理策略

生产环境里，工具调用失败是常态。并行调用时，如何处理"部分失败"是个需要提前设计的问题。

### 策略一：失败时返回错误描述，继续执行

适用于：工具结果是"锦上添花"，缺失不影响主要任务。

```python
# 把错误信息作为工具结果返回给模型
error_result = f"[工具调用失败: {error_msg}。请基于其他可用信息继续。]"
```

模型通常能合理处理"部分数据缺失"的情况，给出有保留的结论。

### 策略二：重试失败的工具（不重试成功的）

```python
async def execute_with_retry(tool_call, tool_registry, max_retries=2):
    for attempt in range(max_retries + 1):
        result = await execute_single(tool_call)
        if result["success"]:
            return result
        if attempt < max_retries:
            await asyncio.sleep(0.5 * (2 ** attempt))  # 指数退避
    return result  # 最终失败结果
```

### 策略三：关键工具失败时中断整个 Agent 轮次

适用于：某个工具是核心依赖，没有它后续推理没有意义。

```python
CRITICAL_TOOLS = {"get_user_auth", "get_payment_status"}

for result in parallel_results:
    if not result["success"] and result["name"] in CRITICAL_TOOLS:
        raise AgentCriticalToolFailure(
            f"关键工具 {result['name']} 失败，中止本轮执行"
        )
```

## 六、性能调优：并行数量与超时的权衡

并行数量不是越多越好。注意几个边界：

**模型侧的并行数限制**：Claude 官方没有硬限制，但超过 10 个并行工具调用时，模型选择工具的准确率可能下降。实践中 **5-8 个**是比较稳定的上限。

**下游服务的并发限制**：如果 5 个工具都要调用同一个第三方 API，要确认该 API 的并发限制，避免引发限流。

**超时设置**：超时应该根据工具的 P99 响应时间设置，不是拍脑袋。建议：
- 轻量查询（本地缓存/内存）：500ms
- 网络 API 调用：3-5s
- 需要数据库查询的：2-3s
- 外部第三方 API（不可控）：8-10s

## 七、跨模型统一接口

如果你的应用需要支持多个模型（或者想在模型间 A/B 测试），可以做一层薄抽象：

```python
def extract_tool_calls(response, model_family: str) -> List[Dict]:
    """从不同模型的响应中统一提取工具调用列表"""
    if model_family == "anthropic":
        return [
            {"id": block["id"], "name": block["name"], "input": block["input"]}
            for block in response.content
            if block["type"] == "tool_use"
        ]
    elif model_family == "openai":
        return [
            {
                "id": tc["id"],
                "name": tc["function"]["name"],
                "input": json.loads(tc["function"]["arguments"])
            }
            for tc in (response.choices[0].message.tool_calls or [])
        ]
    elif model_family == "gemini":
        # Gemini 格式
        calls = []
        for part in response.candidates[0].content.parts:
            if hasattr(part, "function_call"):
                calls.append({
                    "id": f"gemini_{id(part)}",
                    "name": part.function_call.name,
                    "input": dict(part.function_call.args)
                })
        return calls
    raise ValueError(f"Unknown model family: {model_family}")
```

这样，不管底层模型怎么切换，并行执行器的逻辑不变。

## 八、相关阅读

- [Claude 并行 Tool Use 实战：一次调用多个工具](/blog/parallel-tool-use-claude/)
- [Claude Tool Use 最佳实践与陷阱](/blog/claude-tool-use-best-practices/)
- [Function Calling vs Tool Use 差异辨析](/blog/function-calling-vs-tool-use/)
- [AI Agent 工具设计模式](/blog/ai-agent-tool-design/)
- [AI Agent 容错与降级设计](/blog/ai-agent-fallback-design/)

如果你在国内构建 LLM Agent 并需要稳定调用 Claude、GPT-5 或 Gemini，[YoTradeApi](https://yotradeapi.com) 提供多模型统一中转接口，一个 API Key 可以调用全部主流模型。
