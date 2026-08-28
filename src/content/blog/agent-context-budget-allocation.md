---
title: Agent 上下文预算分配算法
description: Agent 多轮工具调用场景下，如何把有限的上下文窗口预算在系统提示、工具定义、历史消息、工具结果之间动态分配，含优先级分层与运行时再平衡算法。
keywords:
  - Agent 上下文预算
  - context budget allocation
  - Agent 多轮工具调用
  - 上下文窗口分配算法
  - LLM Agent 工程设计
pubDate: '2026-08-28'
updatedDate: '2026-08-28'
canonical: https://blog.yotradeapi.com/blog/agent-context-budget-allocation/
tags:
  - Agent
  - 上下文工程
  - 应用工程
  - 技术深度
category: 应用工程
heroImage: ../../assets/blog-placeholder-1.jpg
---

[上下文压缩策略](/blog/context-compression-strategies/) 和 [上下文工程实践](/blog/llm-context-engineering/) 讲的是"某一类内容该怎么压缩"，本文讲一个更上层的问题："总预算就这么多，该怎么在系统提示、工具定义、历史消息、工具调用结果这几类内容之间分配"。这是长时间运行的 Agent（多轮工具调用、几十步执行）里绕不开的设计决策——分配算法设计得不好，Agent 跑到第 10 步时可能系统提示都被历史挤占没了空间。

## 一、Agent 场景的预算分配和普通对话不一样

普通聊天机器人的上下文只有两类内容：系统提示 + 对话历史，按 [上下文管理的固定窗口/摘要策略](/blog/ai-chatbot-context-management/) 处理就够了。但 Agent 场景多了两类会持续增长且大小不可控的内容：

- **工具定义（tool schemas）**：工具越多，这部分越大，而且几乎是固定成本，每一轮都要占用
- **工具调用结果**：某些工具返回的数据量完全不可控（比如一次数据库查询可能返回几十条记录），且这类内容通常是"用完即弃"——模型看完做完决策后，原始返回数据的边际价值急剧下降

四类内容的增长模式和保留价值都不同，用同一套压缩策略处理是不合适的，需要分层预算。

## 二、四层预算模型

把总上下文窗口（假设 128K token）按类别设置预算上限和优先级：

| 层级 | 内容 | 预算占比参考 | 优先级 | 特点 |
|------|------|------------|-------|------|
| L0 | 系统提示 + 工具定义 | 固定，不参与压缩 | 最高 | 每轮必须完整保留，否则 Agent 会"忘记规则" |
| L1 | 最近 N 轮工具调用结果 | 40% | 高 | 决策直接依赖的原始数据 |
| L2 | 历史对话摘要 | 20% | 中 | 早期轮次压缩后的语义摘要 |
| L3 | 早期工具调用原始结果 | 剩余空间，优先丢弃 | 低 | 已经被模型"消化"过的旧数据 |

```python
class ContextBudgetAllocator:
    def __init__(self, total_budget: int):
        self.total_budget = total_budget

    def allocate(self, system_prompt_tokens: int, tool_schema_tokens: int) -> dict:
        # L0 是硬性开销，先扣除，剩余的才是可分配空间
        l0_cost = system_prompt_tokens + tool_schema_tokens
        available = self.total_budget - l0_cost

        if available <= 0:
            raise ValueError("系统提示 + 工具定义已超出总预算，需要精简工具集")

        return {
            "l0_fixed": l0_cost,
            "l1_recent_tool_results": int(available * 0.5),
            "l2_history_summary": int(available * 0.25),
            "l3_old_tool_results": available - int(available * 0.5) - int(available * 0.25),
        }
```

L0 优先级最高、不可压缩这个设计是刻意的——工具定义一旦被截断，模型可能编造不存在的参数或调用不存在的工具，这类错误比"忘记某个早期细节"严重得多。宁可少给 L1/L2/L3 空间，也不能动 L0。

## 三、运行时再平衡：预算不是静态分完就不管了

Agent 每执行一轮工具调用，L1（最近工具结果）都会新增内容，如果不做再平衡，L1 会持续膨胀挤占 L2/L3 甚至逼近 L0。再平衡的触发逻辑：

```python
class RuntimeRebalancer:
    def __init__(self, allocator: ContextBudgetAllocator, budgets: dict):
        self.allocator = allocator
        self.budgets = budgets

    def on_new_tool_result(self, l1_messages: list, l2_summary: str, l3_messages: list,
                            new_result_tokens: int, count_tokens_fn) -> tuple:
        """
        每次新增工具结果后调用，返回再平衡后的 (l1, l2, l3)。
        核心策略：L1 超预算时，把最老的部分"降级"到 L2（压缩进摘要）或 L3（保留原文但标记低优先级）。
        """
        l1_tokens = sum(count_tokens_fn(m) for m in l1_messages) + new_result_tokens

        if l1_tokens <= self.budgets["l1_recent_tool_results"]:
            return l1_messages, l2_summary, l3_messages

        # L1 超预算：把最老的工具结果移出去
        overflow = l1_tokens - self.budgets["l1_recent_tool_results"]
        demoted = []
        while overflow > 0 and l1_messages:
            oldest = l1_messages.pop(0)
            demoted.append(oldest)
            overflow -= count_tokens_fn(oldest)

        # 被移出的内容不是直接丢弃，而是尝试摘要进 L2，摘要预算不够再降到 L3
        new_summary_fragment = summarize(demoted)
        candidate_l2 = l2_summary + new_summary_fragment
        if count_tokens_fn(candidate_l2) <= self.budgets["l2_history_summary"]:
            l2_summary = candidate_l2
        else:
            l3_messages.extend(demoted)  # 摘要空间也不够，原文降级保留在 L3

        return l1_messages, l2_summary, l3_messages
```

这个"降级"而非"直接丢弃"的设计很关键——工具调用结果里可能包含后续步骤仍然需要引用的关键数据（比如第 2 步查到的订单 ID，第 8 步还要用）。直接截断丢弃会导致 Agent 在后续步骤"失忆"，先摘要、摘要空间不够再保留原文到低优先级层，是更安全的降级路径。

## 四、L3 预算耗尽时的最终防线

L3 是"剩余空间，优先丢弃"的层级，当总预算实在不够时（比如工具集特别大导致 L0 本身就吃掉大量空间），L3 需要一个明确的丢弃策略而不是让程序直接报错：

```python
def enforce_l3_limit(l3_messages: list, l3_budget: int, count_tokens_fn) -> list:
    """L3 超预算时，按 FIFO 丢弃最老的内容，直到符合预算"""
    while sum(count_tokens_fn(m) for m in l3_messages) > l3_budget and l3_messages:
        l3_messages.pop(0)
    return l3_messages
```

丢弃前建议记一条审计日志（哪一轮的哪个工具结果被丢弃），排查"Agent 为什么突然说不知道某个信息"这类问题时，这条日志能省很多排查时间。

## 五、和固定窗口/摘要策略的组合关系

四层预算模型不是替代 [上下文压缩策略](/blog/context-compression-strategies/) 里讲的具体压缩手段，而是一层"调度器"——决定每一类内容能用多少空间，具体怎么把内容塞进这个空间（摘要用什么算法、截断保留哪部分）仍然复用已有的压缩技术：

- L2 的摘要生成，直接复用 [上下文工程](/blog/llm-context-engineering/) 里的递进摘要策略
- L1/L3 的结构化截断（比如只保留 JSON 结果里的关键字段），复用结构化截断策略
- 如果模型支持 Prompt Caching，L0（几乎不变）是最适合缓存的部分，可以参考 [Gemini Context Caching 指南](/blog/gemini-context-caching-guide/) 里的缓存设计思路做进一步优化

## 六、实践建议

- **先测量再分配**：不要凭感觉设置 40/25/剩余 这样的比例，先跑一批真实 Agent 轨迹，统计各层实际的 token 消耗分布，再反过来定预算比例
- **L0 要主动做工具集精简**，而不是指望预算分配算法解决——如果 Agent 平时只用得上 5 个工具却注册了 30 个，先精简工具集比调预算比例收益更大
- **给关键降级动作加日志**，方便事后排查"信息丢失"类问题
- **单元测试覆盖边界场景**：总预算不足以容纳 L0、单条工具结果本身就超过整个 L1 预算这类极端情况必须有明确处理路径，不能让程序直接抛未捕获异常

## 七、相关阅读

- [上下文压缩策略五种方案对比](/blog/context-compression-strategies/)
- [LLM 上下文工程实践](/blog/llm-context-engineering/)
- [AI Chatbot 上下文管理策略](/blog/ai-chatbot-context-management/)
- [Agent 工具调用超时预算设计](/blog/agent-tool-timeout-budget/)
- [Agent 记忆保留策略](/blog/agent-memory-retention-policy/)

如果你的 Agent 需要频繁切换模型对比不同上下文窗口大小下的表现，[YoTradeApi](https://yotradeapi.com) 提供统一接口调用 Claude、GPT-5、Gemini 等多种长上下文模型，方便做这类预算分配算法的横向验证。
