---
title: Agent 任务回放与确定性调试
description: Agent 生产事故很难复现，本文讲如何用捕获的执行轨迹搭建回放调试环境，处理 LLM 采样、工具调用、时间等非确定性因素。
keywords:
  - agent 调试
  - 任务回放
  - 确定性调试
  - llm 非确定性
  - agent 事故复现
pubDate: '2026-08-25'
updatedDate: '2026-08-25'
canonical: https://blog.yotradeapi.com/blog/agent-replay-debugging/
tags:
  - 应用工程
  - Agent
  - 调试
  - 可观测性
category: 应用工程
heroImage: ../../assets/blog-placeholder-1.jpg
---

"这个 Agent 昨天半夜跑崩了，日志里能看到最后一步失败，但没法在本地复现。"这是几乎所有做 Agent 生产化的团队都会遇到的问题。传统服务的 bug 大多能靠固定输入复现，但 Agent 每次执行都要经过 LLM 采样、外部工具调用、当前时间等多个非确定性环节，同一个 bug 可能十次里只炸一次。本文讲怎么搭建一套回放调试环境，把"线上偶发"变成"本地必现"。

回放的前提是有完整的执行轨迹可用，如果你还没有捕获轨迹的机制，先看[《用 Event Sourcing 记录 Agent 执行轨迹》](/blog/agent-event-sourcing/)——本文假设轨迹数据已经就绪，只讲怎么把它变成一个可调试的回放会话。

## 一、Agent 执行里的三类非确定性来源

要做确定性回放，得先知道哪些环节会引入随机性：

| 来源 | 具体表现 | 回放策略 |
| --- | --- | --- |
| LLM 采样 | temperature > 0 时同一 prompt 输出不同 | 回放时直接注入原始响应，不重新调用模型 |
| 外部工具调用 | API 返回随时间变化（价格、天气、搜索结果） | 回放时用捕获的响应做 mock，不打真实请求 |
| 时间与随机数 | `now()`、UUID 生成、随机重试间隔 | 回放时冻结时钟，用捕获的值替换 |
| 并发调度顺序 | 多个工具并行调用时完成顺序不固定 | 回放时按捕获的实际完成顺序重放，而非重新竞速 |

核心思路是：**回放不是"重新执行一遍逻辑"，而是"用真实历史数据重放当时的输入输出"**。区别在于,回放时 LLM 调用、工具调用都不应该真的发生网络请求,而是从轨迹记录里读取当时的返回值直接注入。

## 二、回放引擎的最小实现

以捕获的事件序列为输入，核心是给每一个"非确定性调用点"包一层可切换的适配器：

```python
class ReplayContext:
    def __init__(self, trace_events):
        # trace_events: 按发生顺序排列的历史事件列表
        self.events = iter(trace_events)
        self.mode = "replay"  # or "live"

    def call_llm(self, prompt, **kwargs):
        if self.mode == "replay":
            event = next(self.events)
            assert event["type"] == "llm_call", f"轨迹错位：期望 llm_call，实际 {event['type']}"
            return event["response"]
        return real_llm_call(prompt, **kwargs)

    def call_tool(self, tool_name, args):
        if self.mode == "replay":
            event = next(self.events)
            assert event["type"] == "tool_call" and event["tool"] == tool_name, \
                f"轨迹错位：期望 {tool_name}，实际 {event.get('tool')}"
            return event["result"]
        return real_tool_call(tool_name, args)

    def now(self):
        if self.mode == "replay":
            event = next(self.events)
            assert event["type"] == "clock_read"
            return event["timestamp"]
        return real_now()
```

`assert` 校验轨迹错位这一步很关键：如果 Agent 的代码逻辑在两次运行之间发生了变化（比如加了一次新的工具调用），回放会立刻在断言处报错，而不是悄悄用错误的历史数据继续跑下去、产出一个看起来正常但完全错误的回放结果。

## 三、把回放和断点调试结合起来

回放引擎最大的价值不是"看一遍历史"，而是可以在任意一步暂停，用调试器单步检查 Agent 当时的内部状态：

```python
def replay_with_breakpoint(trace_events, break_at_step):
    ctx = ReplayContext(trace_events)
    for i, step in enumerate(agent_run_generator(ctx)):
        if i == break_at_step:
            import pdb; pdb.set_trace()  # 在这一步暂停，检查变量
        yield step
```

对于复杂的多步 Agent，建议先用轨迹里记录的"决策点"（比如"选择了哪个工具"、"判断任务是否完成"）做一次粗筛，定位到大概在第几步开始偏离预期，再对准那一步下断点，不要每次都从第一步开始单步跟踪。

## 四、Diff 回放：对比两条轨迹的分叉点

比"回放单条轨迹"更有效的调试手段是**对比两条轨迹**：一条是线上失败的真实轨迹，一条是同样输入下本地修复代码后的新轨迹，找出两者从哪一步开始分叉：

```python
def diff_traces(trace_a, trace_b):
    for i, (step_a, step_b) in enumerate(zip(trace_a, trace_b)):
        if step_a["type"] != step_b["type"] or step_a.get("tool") != step_b.get("tool"):
            return {"diverged_at": i, "expected": step_a, "actual": step_b}
    return None
```

这在验证修复是否生效时特别有用：改完代码后重放同一个输入，如果新轨迹从某一步开始和旧的失败轨迹分叉，且分叉点正是你预期修复的那个决策点，就是修复生效的直接证据，比"跑几次看着不报错了"可靠得多。

## 五、回放数据的取舍：不是所有轨迹都要能重放

完整保留所有非确定性调用的原始输入输出，存储成本会随对话长度快速增长。实际落地时的取舍建议：

- **默认只保留失败任务的完整轨迹**，成功任务只保留摘要（步骤数、耗时、最终状态），需要时再从摘要采样补录
- **工具调用的返回体如果很大**（比如整页网页内容），可以只存哈希 + 引用地址，回放时按需拉取，而不是把大对象整个塞进事件记录
- **保留期限按事故排查的实际需要设置**，多数团队 7–30 天足够,更长的保留期收益递减但存储成本线性增长

存储层面更完整的字段设计和索引策略可以参考[《LLM 对话轨迹存储与查询设计实践》](/blog/llm-conversation-trace-design/)。

## 六、和错误追踪体系的分工

回放调试和错误追踪（tracing/logging）解决的是不同阶段的问题：追踪负责"第一时间发现哪里错了"，回放负责"深入复现并验证修复"。两者共用同一份轨迹数据是最高效的架构,不需要为回放单独搭一套采集管线。错误追踪的分层设计可参考[《AI 流水线的错误追踪方案》](/blog/ai-pipeline-error-tracing/)。

## 七、相关阅读

- [用 Event Sourcing 记录 Agent 执行轨迹](/blog/agent-event-sourcing/)
- [AI 流水线的错误追踪方案：从日志到根因定位](/blog/ai-pipeline-error-tracing/)
- [LLM 对话轨迹存储与查询设计实践](/blog/llm-conversation-trace-design/)

排查 Agent 生产问题时,如果调用链路经过中转服务，还要确认中转层是否保留了足够的请求/响应元数据供回放使用——[YoTradeApi](https://yotradeapi.com) 的请求日志包含完整的请求体和响应体，方便直接接入自建的回放系统。
