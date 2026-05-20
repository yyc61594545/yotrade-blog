---
title: OpenAI Agents SDK 国内接入与实战
description: OpenAI 官方 Agents SDK 在国内通过中转的接入方法，含工具定义、handoff、guardrail、tracing 的完整实战代码。
keywords:
- openai agents sdk
- openai agent 国内
- agents sdk 教程
- openai agent handoff
- openai agent 中转
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/openai-agents-sdk-cn/
tags:
- OpenAI
- Agents SDK
- 国内
- Agent
- 工程实战
category: 工程实战
heroImage: ../../assets/blog-placeholder-3.jpg
---

OpenAI 在 2025 年发布了官方 Agents SDK，把"多 agent 协作 + handoff + guardrail + tracing" 这些功能标准化。本文给国内通过中转接入的完整流程。

## 一、Agents SDK 是什么

可以理解为"GPT 版的 LangGraph"，但更轻：

- Agent：带有 instructions + tools 的 LLM 调用单元
- Handoff：一个 agent 把任务转给另一个 agent
- Guardrails：输入 / 输出的安全检查
- Tracing：自动记录每一步

适合中等复杂度的 agent 系统。

## 二、安装

```bash
pip install openai-agents
```

## 三、最小 agent

```python
from agents import Agent, Runner
from openai import AsyncOpenAI
from agents import set_default_openai_client

# 走中转
client = AsyncOpenAI(
    api_key="sk-yo-...",
    base_url="https://yotradeapi.com/v1",
)
set_default_openai_client(client)

agent = Agent(
    name="assistant",
    instructions="你是简洁的中文助手。",
    model="gpt-5",
)

result = await Runner.run(agent, "解释 LRU 缓存")
print(result.final_output)
```

简单到不能再简单。

## 四、加 Tool

```python
from agents import function_tool

@function_tool
def get_weather(city: str) -> str:
    """获取城市天气
    
    Args:
        city: 城市名
    """
    return f"{city} 25 度晴"

@function_tool
def calculator(expr: str) -> float:
    """计算表达式"""
    return eval(expr)

agent = Agent(
    name="assistant",
    instructions="你能用工具回答问题。",
    model="gpt-5",
    tools=[get_weather, calculator],
)

result = await Runner.run(agent, "北京天气怎么样？再算 137*256")
print(result.final_output)
```

`@function_tool` 自动从函数签名 + docstring 生成 schema。

## 五、Handoff（多 agent 协作）

```python
faq_agent = Agent(
    name="faq",
    instructions="回答常见问题。回答完毕。",
    model="gpt-5-mini",
)

booking_agent = Agent(
    name="booking",
    instructions="处理订票。需要：日期、人数、目的地。",
    model="gpt-5",
    tools=[create_booking],
)

triage_agent = Agent(
    name="triage",
    instructions="判断用户意图，转交给对应 agent。",
    model="gpt-5-mini",
    handoffs=[faq_agent, booking_agent],
)

result = await Runner.run(triage_agent, "我想订下周三北京到上海的机票")
# triage_agent 自动把请求 handoff 给 booking_agent
```

`handoffs=[...]` 让 triage 知道有哪些 agent 可以转。Handoff 是"完整把任务交出去"，不是函数调用。

## 六、Guardrails

输入安全检查：

```python
from agents import input_guardrail, GuardrailFunctionOutput

@input_guardrail
async def safety_check(ctx, agent, input):
    if "rm -rf" in input.lower():
        return GuardrailFunctionOutput(
            tripwire_triggered=True,
            output_info={"reason": "dangerous command"},
        )
    return GuardrailFunctionOutput(tripwire_triggered=False)

agent = Agent(
    name="assistant",
    instructions="...",
    input_guardrails=[safety_check],
)
```

输出安全检查也类似。**比手工 if/else 风险捕获更清晰**。

## 七、Tracing（自动追踪）

默认所有 agent 运行都被追踪：

```python
from agents.tracing import trace

with trace("user-flow-123"):
    result = await Runner.run(agent, "...")
```

trace 数据可以发送到 OpenAI 后台看 dashboard。**走中转时不一定能上传**——看中转是否透传 `traces` 端点。

关掉 tracing（如果中转不支持）：

```python
from agents import set_tracing_disabled
set_tracing_disabled(True)
```

## 八、上下文与状态

Agents SDK 用 `RunContextWrapper` 传上下文：

```python
@dataclass
class UserContext:
    user_id: str
    locale: str

agent = Agent[UserContext](
    name="...",
    instructions=lambda ctx, agent: f"用户 {ctx.context.user_id}，语言 {ctx.context.locale}。",
)

result = await Runner.run(
    agent,
    "你好",
    context=UserContext(user_id="alice", locale="zh"),
)
```

类型安全的 context 注入。

## 九、流式

```python
result = Runner.run_streamed(agent, "...")
async for event in result.stream_events():
    if event.type == "raw_response_event":
        # 模型 token
        pass
    elif event.type == "agent_updated_stream_event":
        # agent 切换（handoff）
        print(f"now on agent: {event.new_agent.name}")
    elif event.type == "run_item_stream_event":
        # tool 调用等
        pass
```

UI 可以实时显示"正在处理...""转交给 booking agent..."。

## 十、Agents SDK vs LangGraph vs Anthropic Agent SDK

| 维度 | OpenAI Agents | LangGraph | Anthropic Agent SDK |
| --- | --- | --- | --- |
| 抽象 | Agent + Handoff | Graph + State | Agent + Tool |
| 学习曲线 | 中 | 高 | 中 |
| 灵活度 | 中 | 极高 | 高 |
| 默认走的协议 | OpenAI Responses | 任意 | Anthropic Messages |
| 适合 | 中等复杂 | 高复杂 | Anthropic 用户 |
| 国内中转适配 | 看协议透传 | 通用 | 看协议透传 |

**选型建议**：

- 已用 OpenAI 生态 → Agents SDK
- 已用 Anthropic 生态 → Anthropic Agent SDK
- 跨厂商、复杂 graph → LangGraph

## 十一、中转配置注意

Agents SDK 调用底层用 Responses API。中转必须支持：

- `/v1/responses`
- tool_call 在 Responses 流的解析
- handoff 是客户端逻辑（不影响中转）

测试：

```bash
curl https://yotradeapi.com/v1/responses \
  -H "Authorization: Bearer $KEY" \
  -d '{"model":"gpt-5","input":"hi"}'
```

返回 200 + `output_text` 字段即正常。

## 十二、实战例子：客服 Agent

```python
@function_tool
async def lookup_order(order_id: str) -> dict:
    """查订单"""
    return await db.fetch_order(order_id)

@function_tool
async def issue_refund(order_id: str, amount: float, reason: str) -> str:
    """退款"""
    return await payment.refund(order_id, amount, reason)

faq_agent = Agent(
    name="faq",
    instructions="""回答关于运费 / 退货政策 / 配送时间的问题。
你只有 FAQ 内容（在 system context 里）。
不能查具体订单。""",
    model="gpt-5-mini",
)

order_agent = Agent(
    name="order",
    instructions="""查询订单和处理退款。
- 退款 < $50：直接处理
- 退款 ≥ $50：转交给 human""",
    model="gpt-5",
    tools=[lookup_order, issue_refund],
)

triage = Agent(
    name="triage",
    instructions="""判断用户意图：
- 政策问题 → faq
- 订单查询 / 退款 → order""",
    model="gpt-5-mini",
    handoffs=[faq_agent, order_agent],
)

result = await Runner.run(triage, "我想退订单 #12345 的款")
```

跑起来三 agent 自动协作，按职责分工。

## 十三、最佳实践

- **每个 agent 职责单一**：太宽 agent 决策质量下降
- **handoff 比 tool 更适合"完整移交"**：tool 适合"返回数据"
- **guardrail 早做不晚做**：上线前补，事后补痛
- **tracing 至少在开发阶段开**：调 agent 没 trace 等于盲飞
- **测试用 mock tool**：不要每次真调外部 API

## 十四、相关阅读

- [LangChain 中文实战](/blog/langchain-cn-tutorial/)
- [Claude Code Subagent 实战](/blog/claude-code-subagent-practice/)
- [OpenAI Responses API 完整指南](/blog/openai-responses-api-guide/)
- [Claude 并行 Tool Use 实战](/blog/parallel-tool-use-claude/)
- [LLM 结构化输出完全指南](/blog/structured-output-llm-guide/)
- [AI Agent 评估方法](/blog/llm-agent-evaluation-methods/)

需要 Responses API + tool_call + handoff 完整透传的中转？[YoTradeApi](https://yotradeapi.com) 完整支持 Agents SDK 所有特性。
