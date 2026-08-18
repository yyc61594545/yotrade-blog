---
title: 用 Event Sourcing 记录 Agent 执行轨迹
description: Agent 的执行过程天然是多步、异步、可失败的。相比只存最终状态，用 Event Sourcing 记录每一步事件，更适合做回放调试、审计追踪、补偿回滚和离线评测。
keywords:
  - Agent Event Sourcing
  - Agent 执行轨迹
  - AI Agent 审计日志
  - Agent 回放调试
  - 事件溯源架构
pubDate: '2026-08-18'
updatedDate: '2026-08-18'
canonical: https://blog.yotradeapi.com/blog/agent-event-sourcing/
tags:
  - AI Agent
  - Event Sourcing
  - 轨迹追踪
  - 审计
  - 架构设计
category: 应用工程
heroImage: ../../assets/blog-placeholder-2.jpg
---

很多 Agent 系统上线后，最先暴露的问题不是“模型不够聪明”，而是“出了问题根本还原不了现场”。日志里也许只留下一个最终错误，数据库里只有一条 `status=failed`，但真正关键的信息都丢了：它到底看到了什么上下文、什么时候调用了哪个工具、哪一步重试了、为什么最后走到了错误分支。

这也是为什么越来越多团队开始把 Agent 执行轨迹从“普通日志”升级为“事件流”。相比只记录当前状态，Event Sourcing 的思路是：**把每一次重要动作都作为不可变事件写下来，再由这些事件推导出当前状态。** 对多步 Agent 来说，这个模型往往比“只存最后一版对象”更贴合现实。

## 一、为什么 Agent 天然适合事件溯源

Agent 的执行并不是一次函数调用，而是一串状态变化：

用户输入 -> 路由判断 -> 检索 -> 模型推理 -> 工具调用 -> 工具结果 -> 二次推理 -> 输出完成

这条链路里，任何一步都可能失败、重试、回退、等待人工确认，甚至并发展开多个子任务。用一张“当前状态表”固然能知道最后结果，但很难回答下面这些生产问题：

- 为什么这次任务比平时多跑了 7 轮？
- 哪一次工具调用开始把成本拉高了？
- 某个错误是模型判断错了，还是外部 API 超时？
- 如果要做事故复盘，能不能把当时的决策过程完整回放？

这类问题的共同点是：**你需要过程，而不只是结论。**

## 二、事件流和最终状态表不是对立关系

一提 Event Sourcing，很多人担心系统会不会过重。其实最稳的做法不是“只有事件流，没有状态表”，而是两者并存：

| 存储层 | 作用 | 典型查询 |
| --- | --- | --- |
| Event Log | 保存完整过程、不可变真相源 | 回放、审计、离线分析 |
| Projection / Read Model | 保存当前派生状态 | 任务列表、当前进度、报表 |

换句话说，事件流负责“留下发生过什么”，投影视图负责“让产品和运营方便读取现在是什么状态”。这和 [LLM 对话轨迹存储与查询设计实践](/blog/llm-conversation-trace-design/) 里“原始轨迹 + 查询模型”的思路是同一类分层，只是 Agent 的粒度更细、动作更多。

## 三、事件最少要记哪些字段

如果你决定用事件流，第一件事不是选 Kafka 还是 Postgres，而是定义事件 schema。对 Agent 来说，最少建议包含：

```json
{
  "event_id": "evt_123",
  "run_id": "run_456",
  "step_id": "step_007",
  "event_type": "tool_call.started",
  "timestamp": "2026-08-18T10:12:03Z",
  "actor": "agent",
  "payload": {"tool": "search_docs", "args": {"query": "..." }},
  "cost_snapshot": {"input_tokens": 320, "output_tokens": 0},
  "parent_event_id": "evt_122"
}
```

这里最重要的不是字段多，而是满足三件事：

1. **可排序**：知道事件发生顺序。
2. **可关联**：知道它属于哪个 run、哪个 step、哪个父事件。
3. **可重建**：拿到这些事件，能大致回放出执行路径。

如果缺少 `run_id`、`step_id` 或父子关联，后面做回放时就会退化成一堆散乱日志。

## 四、事件类型要围绕“决策点”和“副作用”设计

不是所有细节都值得写成事件。真正需要落库的，通常是那些会影响结果、成本或审计结论的节点：

| 事件类型 | 为什么值得记录 |
| --- | --- |
| `run.created` / `run.completed` | 标记一次任务的生命周期 |
| `model.requested` / `model.completed` | 还原提示词、输出、token 与耗时 |
| `tool_call.started` / `tool_call.finished` | 追踪外部副作用和失败点 |
| `approval.requested` / `approval.granted` | 审计人工介入 |
| `retry.scheduled` | 解释为什么一条任务会多跑几次 |
| `rollback.executed` | 支撑补偿与事后复盘 |

一个简单标准是：**如果这一步出了问题，你未来会不会后悔当时没记下来？** 如果答案是会，那它大概率就该成为事件。

## 五、Event Sourcing 最大的价值是“可回放”

普通 trace 更像录像，Event Sourcing 更像剧本。录像能看见当时发生了什么，剧本还能让你重新跑一遍状态机，看最后是否还能得到同样结果。

这对 Agent 调试特别重要。比如某次执行因为工具返回脏数据而走偏，你可以：

- 保留原始事件流
- 替换其中某个工具结果事件
- 从那个事件开始重新投影后续状态
- 验证问题到底出在工具层还是策略层

这类“部分重放”能力，是 [AI Agent 可观测性设计](/blog/ai-agent-observability-design/) 和 [AI 流水线的错误追踪方案](/blog/ai-pipeline-error-tracing/) 继续往前走的一步：不只是看见故障链路，而是能基于链路做实验和复盘。

## 六、别忽视副作用：回放不等于重做外部写操作

Event Sourcing 在 Agent 场景里的最大陷阱，是把“回放状态”误解成“重放所有动作”。如果某个事件对应的是写数据库、发邮件、创建 PR、调用付费 API，直接重放就可能造成二次副作用。

所以要把两类动作分开：

- **纯状态事件**：可以安全回放
- **带外部副作用的命令事件**：回放时默认只模拟，不重执行

更稳的实现方式，是把“命令”和“事件”区分开来：命令请求某个动作，执行成功后才写事件；后续回放只消费事件，不再次执行命令。这样你既能保留完整轨迹，又不会因为回放把线上系统再改一遍。这和 [AI Agent 写操作回滚策略：让 Agent 的错误可以被撤销](/blog/ai-agent-rollback-strategy/) 的补偿思路是配套的。

## 七、结论：把 Agent 当状态机，就该给它事件账本

只要你的 Agent 会多步执行、调用工具、等待外部结果、允许重试或人工介入，它本质上就已经不是一个“单请求单响应”系统，而是一个状态机。既然是状态机，单纯保存最终状态就不够；你最终会需要一份能够回放、审计、归因和补偿的事件账本。

Event Sourcing 不一定意味着上复杂中间件。很多团队一开始用 Postgres 顺序表就能做出足够好用的第一版。真正关键的是思路：先把不可变事件沉淀下来，再从事件派生读模型。这样你的 Agent 轨迹就不只是日志，而会成为后续调试、评测、成本分析和安全审计的共同底座。

## 八、相关阅读

- [LLM 对话轨迹存储与查询设计实践](/blog/llm-conversation-trace-design/)
- [AI Agent 可观测性设计](/blog/ai-agent-observability-design/)
- [AI 流水线的错误追踪方案：从日志到根因定位](/blog/ai-pipeline-error-tracing/)
- [AI Agent 写操作回滚策略：让 Agent 的错误可以被撤销](/blog/ai-agent-rollback-strategy/)

如果你的团队需要先把多模型与多工具调用统一接入，再在上层建设自己的轨迹、审计和回放系统，[YoTradeApi](https://yotradeapi.com) 可以作为统一 API 入口，减少底层协议差异带来的接入负担。
