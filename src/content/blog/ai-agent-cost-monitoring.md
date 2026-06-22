---
title: AI Agent 单会话成本监控实现：从零构建 Token 追踪系统
description: 完整讲解如何为 AI Agent 构建单会话 token 成本监控系统，包括实时追踪、预算告警、多轮对话计费拆分，附 Python 生产级代码。
keywords:
  - AI Agent 成本监控
  - 单会话 token 追踪
  - Agent 计费系统
  - LLM 成本监控实现
  - AI Agent token 预算
pubDate: '2026-06-22'
updatedDate: '2026-06-22'
canonical: https://blog.yotradeapi.com/blog/ai-agent-cost-monitoring/
tags:
  - AI Agent
  - 成本优化
  - 应用工程
  - Python
category: 应用工程
heroImage: ../../assets/blog-placeholder-1.jpg
---

AI Agent 的成本管理远比单次 API 调用复杂。一个自主 Agent 可能在一次用户请求中发起 3 次、10 次甚至 50 次模型调用（工具调用、重试、子任务拆分等），如果没有会话级别的成本追踪，账单超支往往在月底才被发现。

本文从零构建一套**单会话 token 成本监控系统**，覆盖实时追踪、预算告警、多模型成本聚合，以及如何将成本数据接入可观测性平台。

---

## 一、问题定义：Agent 成本难在哪里

单次 API 调用的成本追踪相对简单——从响应的 `usage` 字段读取 token 数乘以单价即可。但 Agent 场景带来几个新挑战：

**1. 单会话包含多次调用**

用户发起一个"帮我分析这份合同"的请求，Agent 内部可能依次调用：
- 第 1 次：判断任务类型（50 token）
- 第 2 次：调用 OCR 工具解析 PDF（无成本，外部 API）
- 第 3 次：逐段分析合同条款（800 token × 5 段）
- 第 4 次：汇总生成报告（1200 token）
- 合计：约 5250 token，但来自 6 次调用

**2. 多模型混用**

现代 Agent 常见策略：路由层用 Haiku（便宜快速），实际任务用 Sonnet，复杂推理用 Claude Sonnet 扩展思考。不同模型单价差异可达 20 倍，必须按模型分别计价。

**3. 工具调用的隐性成本**

工具定义（Tool Schema）会占用大量输入 token，且每轮对话都会重复携带，这部分成本容易被忽略。

**4. 预算超限需要中止**

Agent 运行中途如果发现本次会话已超预算，需要能够优雅地停止并返回已有结果，而不是继续产生费用。

---

## 二、数据结构设计

首先定义成本追踪的核心数据结构：

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid

# 各模型的每千 token 价格（美元，近似估算，以实际账单为准）
MODEL_PRICING = {
    "claude-haiku-4-5-20251001": {"input": 0.001, "output": 0.005},
    "claude-sonnet-4-5": {"input": 0.003, "output": 0.015},
    "claude-opus-4-8": {"input": 0.015, "output": 0.075},
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "hunyuan-turbo": {"input": 0.002, "output": 0.007},
}


@dataclass
class CallRecord:
    """单次 LLM 调用记录"""
    call_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0   # Prompt Cache 命中的 token（通常折扣价）
    cost_usd: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    purpose: str = ""            # 此次调用的用途标注，如 "route", "analyze", "summarize"
    duration_ms: int = 0


@dataclass
class SessionCostTracker:
    """单会话成本追踪器"""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    budget_usd: float = 0.10     # 默认 $0.10 预算上限
    calls: list[CallRecord] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def total_cost(self) -> float:
        return sum(c.cost_usd for c in self.calls)

    @property
    def total_input_tokens(self) -> int:
        return sum(c.input_tokens for c in self.calls)

    @property
    def total_output_tokens(self) -> int:
        return sum(c.output_tokens for c in self.calls)

    @property
    def remaining_budget(self) -> float:
        return self.budget_usd - self.total_cost

    @property
    def is_over_budget(self) -> bool:
        return self.total_cost >= self.budget_usd

    def cost_by_model(self) -> dict[str, float]:
        result = {}
        for call in self.calls:
            result[call.model] = result.get(call.model, 0.0) + call.cost_usd
        return result

    def summary(self) -> dict:
        return {
            "session_id": self.session_id,
            "total_cost_usd": round(self.total_cost, 6),
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "call_count": len(self.calls),
            "budget_usd": self.budget_usd,
            "remaining_budget_usd": round(self.remaining_budget, 6),
            "cost_by_model": {k: round(v, 6) for k, v in self.cost_by_model().items()},
            "duration_seconds": (datetime.utcnow() - self.started_at).total_seconds(),
        }
```

---

## 三、核心追踪逻辑

将 LLM 调用封装在一个带成本记录的 wrapper 中：

```python
import time
from openai import OpenAI
from contextlib import contextmanager


def calculate_cost(model: str, input_tokens: int, output_tokens: int,
                   cache_read_tokens: int = 0) -> float:
    pricing = MODEL_PRICING.get(model, {"input": 0.003, "output": 0.015})
    # Cache 命中的 token 按 10% 折扣计算（以实际提供商策略为准）
    cache_discount = 0.1
    input_cost = (input_tokens - cache_read_tokens) * pricing["input"] / 1000
    cache_cost = cache_read_tokens * pricing["input"] * cache_discount / 1000
    output_cost = output_tokens * pricing["output"] / 1000
    return input_cost + cache_cost + output_cost


class TrackedLLMClient:
    """带成本追踪的 LLM 客户端"""

    def __init__(self, client: OpenAI, tracker: SessionCostTracker):
        self.client = client
        self.tracker = tracker

    def chat(self, model: str, messages: list, purpose: str = "",
             max_tokens: int = 1000, **kwargs):
        # 预算检查
        if self.tracker.is_over_budget:
            raise BudgetExceededError(
                f"会话已超预算 ${self.tracker.budget_usd:.4f}，"
                f"已消费 ${self.tracker.total_cost:.4f}"
            )

        start = time.time()
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            **kwargs
        )
        duration_ms = int((time.time() - start) * 1000)

        usage = response.usage
        cache_read = getattr(usage, "prompt_tokens_details", None)
        cache_read_tokens = getattr(cache_read, "cached_tokens", 0) if cache_read else 0

        cost = calculate_cost(
            model=model,
            input_tokens=usage.prompt_tokens,
            output_tokens=usage.completion_tokens,
            cache_read_tokens=cache_read_tokens
        )

        record = CallRecord(
            model=model,
            input_tokens=usage.prompt_tokens,
            output_tokens=usage.completion_tokens,
            cache_read_tokens=cache_read_tokens,
            cost_usd=cost,
            purpose=purpose,
            duration_ms=duration_ms
        )
        self.tracker.calls.append(record)

        # 超预算告警（不中止，但记录警告）
        if self.tracker.total_cost > self.tracker.budget_usd * 0.8:
            print(f"⚠️  [Session {self.tracker.session_id[:8]}] "
                  f"已用 {self.tracker.total_cost/self.tracker.budget_usd:.0%} 预算")

        return response


class BudgetExceededError(Exception):
    pass
```

---

## 四、在 Agent 循环中集成

下面是一个简化的 Tool-use Agent，展示如何在实际 Agent 循环中使用成本追踪：

```python
import json

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "搜索互联网获取最新信息",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"]
            }
        }
    }
]


def run_agent_with_cost_tracking(user_query: str, budget_usd: float = 0.05) -> dict:
    tracker = SessionCostTracker(budget_usd=budget_usd)
    client_raw = OpenAI(api_key="YOUR_KEY", base_url="https://api.yotradeapi.com/v1")
    llm = TrackedLLMClient(client_raw, tracker)

    messages = [
        {"role": "system", "content": "你是一个有用的助手，使用工具完成用户任务。"},
        {"role": "user", "content": user_query}
    ]

    max_iterations = 10
    for i in range(max_iterations):
        try:
            response = llm.chat(
                model="claude-sonnet-4-5",
                messages=messages,
                purpose=f"agent_loop_iter_{i}",
                max_tokens=800,
                tools=TOOLS,
                tool_choice="auto"
            )
        except BudgetExceededError as e:
            return {
                "status": "budget_exceeded",
                "error": str(e),
                "partial_result": messages[-1].get("content", ""),
                "cost_summary": tracker.summary()
            }

        msg = response.choices[0].message

        # 没有工具调用，任务完成
        if not msg.tool_calls:
            return {
                "status": "success",
                "result": msg.content,
                "cost_summary": tracker.summary()
            }

        # 处理工具调用（此处模拟工具执行）
        messages.append(msg.model_dump())
        for tool_call in msg.tool_calls:
            tool_result = execute_tool(tool_call.function.name,
                                       json.loads(tool_call.function.arguments))
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(tool_result, ensure_ascii=False)
            })

    return {
        "status": "max_iterations_reached",
        "cost_summary": tracker.summary()
    }


def execute_tool(name: str, args: dict) -> dict:
    # 实际项目中替换为真实工具调用
    return {"result": f"模拟执行 {name}({args})"}
```

---

## 五、成本数据上报与可观测性

生产环境中，成本数据需要接入监控平台：

```python
import logging
import json
from datetime import datetime

logger = logging.getLogger("agent.cost")

def report_session_cost(tracker: SessionCostTracker, outcome: str = "success"):
    """结构化日志上报，可接入 Datadog/Prometheus/自建 ELK"""
    summary = tracker.summary()
    summary["outcome"] = outcome
    summary["timestamp"] = datetime.utcnow().isoformat()

    # 结构化日志，方便 ELK / Loki 解析
    logger.info(json.dumps(summary, ensure_ascii=False))

    # 也可以推送到 Prometheus pushgateway、InfluxDB 等
    # push_to_metrics(summary)
```

**告警规则示例（Prometheus AlertManager）**：

```yaml
# 单会话成本超过 $0.50 触发告警
- alert: HighAgentSessionCost
  expr: agent_session_cost_usd > 0.50
  for: 0m
  labels:
    severity: warning
  annotations:
    summary: "Agent 会话成本过高：{{ $value }}$"

# 每小时 API 总成本超过 $50 触发告警
- alert: HourlyAPIBudgetExceeded
  expr: sum(rate(agent_session_cost_usd[1h])) > 50
  for: 5m
  labels:
    severity: critical
```

---

## 六、工具调用 Token 的成本细节

工具定义（Schema）会在每次调用时计入输入 token，这部分成本容易被忽略：

```python
import tiktoken

def estimate_tool_schema_tokens(tools: list) -> int:
    """估算工具 Schema 占用的 token 数"""
    enc = tiktoken.get_encoding("cl100k_base")
    schema_text = json.dumps(tools, ensure_ascii=False)
    return len(enc.encode(schema_text))

# 如果你有 10 个工具，每个工具 Schema 约 100 token
# 每次调用都会多 1000 input token
# 按 claude-sonnet-4-5 的价格：1000/1000 * $0.003 = $0.003/次
# 100 次调用/天 × $0.003 = $0.3/天，不可忽视
tools_token_cost = estimate_tool_schema_tokens(TOOLS)
print(f"工具 Schema 占用约 {tools_token_cost} tokens/次调用")
```

**优化建议**：
- 只在需要时注入相关工具，而不是每次都携带全部工具
- 对于只用文本输出的调用（如路由、摘要），完全移除 `tools` 参数

---

## 七、相关阅读

- [AI Agent 错误恢复与重试策略](/blog/ai-agent-error-recovery/)
- [LLM 输出截断省钱实战：max_tokens 精细化控制指南](/blog/llm-output-truncation-savings/)
- [LLM 成本优化完整检查清单](/blog/llm-cost-optimization-checklist/)
- [AI 编程 Agent 月均成本真实测算](/blog/ai-coding-monthly-cost-real/)

想统一管理多个 Agent 的 API 账单并自动获得用量折扣，[YoTradeApi](https://yotradeapi.com) 提供完善的用量统计面板，支持 Claude、GPT、混元等主流模型，一个平台搞定所有账单。
