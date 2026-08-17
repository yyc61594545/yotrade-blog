---
title: AI Agent 状态机设计与落地
description: 从状态定义、事件流转、超时补偿到人工接管，系统讲清 AI Agent 状态机如何设计，才能真正落到生产环境。
keywords:
  - AI Agent 状态机
  - Agent workflow 设计
  - Agent 事件驱动架构
  - Agent 超时回滚
  - 生产级 Agent 系统
pubDate: '2026-08-17'
updatedDate: '2026-08-17'
canonical: https://blog.yotradeapi.com/blog/agent-state-machine-design/
tags:
  - AI Agent
  - 状态机
  - 工作流
  - 应用工程
category: 应用工程
heroImage: ../../assets/blog-placeholder-4.jpg
---

很多团队做 AI Agent，第一版往往是“能跑起来”的脚本：收一段用户输入，调用模型，遇到工具就执行，最后把答案返回。演示没问题，一进生产就开始失控。常见症状包括：任务卡在半途、重复调用同一工具、失败后不知道该从哪里恢复、人工接手时状态对不上。

这些问题本质上都指向同一个缺口：没有把 Agent 当成一个有明确生命周期的系统来设计。状态机并不等于流程图好看，而是用有限状态、明确事件和合法转移，把“这个 Agent 现在到底在干什么”说清楚。

本文聚焦生产环境里最实用的状态机设计方法，不讲抽象定义，而讲怎样让 Agent 在真实业务里可观测、可恢复、可回滚、可人工接管。

## 一、为什么 Agent 比普通任务流更需要状态机

普通任务流通常有一个特点：输入明确、步骤固定、失败方式有限。AI Agent 正好相反。它既可能走不同工具路径，也可能在中途根据模型输出改写计划，还可能因为上下文、权限、外部 API、工具超时而偏离预期。

如果没有状态机，你最后只能靠日志猜当前进度。这样一来，三个关键动作都会变得很难：

1. 判断某个任务是否卡死，还是只是执行较慢。
2. 决定失败后该重试同一步，还是回滚到上一步。
3. 在人工接管时，把上下文和责任边界交代清楚。

状态机真正提供的价值，是把 Agent 从“一个正在运行的黑盒”变成“一个随时可以被检查和驱动的系统对象”。

## 二、先别急着画图，先定义最小可用状态集合

很多状态机设计一开始就过度细化，结果自己都维护不住。更稳妥的做法是先定义最小可用状态，再逐步细分。

对大多数有工具调用的 Agent，我更推荐从这 8 个状态起步：

| 状态 | 含义 | 典型进入事件 |
| --- | --- | --- |
| `queued` | 已创建，尚未开始 | 新任务入队 |
| `planning` | 正在拆解任务或生成计划 | worker 开始处理 |
| `waiting_tool` | 等待某个工具返回 | 发起外部调用 |
| `executing` | 正在消费工具结果或继续推理 | 工具成功返回 |
| `waiting_human` | 需要人工确认或补充 | 命中审批/权限边界 |
| `retrying` | 某一步正在受控重试 | 发生可恢复错误 |
| `completed` | 正常结束 | 最终结果通过校验 |
| `failed` | 无法继续，需要停止 | 不可恢复错误或超出重试上限 |

这套状态的好处是：既能覆盖常见运行路径，也不会细到每次 token 输出都成一个新状态。状态必须回答的是“控制权现在在谁手里”，而不是“模型刚才想了什么”。

## 三、状态转移必须由事件触发，而不是靠函数嵌套暗示

很多 Agent 代码的问题，不在逻辑本身，而在状态转移被埋在调用栈里。例如 `plan() -> call_tool() -> handle_error() -> retry()` 一串函数执行完，你也很难从外部知道任务经历了什么。

更好的做法是把状态转移统一写成“事件驱动”：

```ts
type AgentState =
  | "queued"
  | "planning"
  | "waiting_tool"
  | "executing"
  | "waiting_human"
  | "retrying"
  | "completed"
  | "failed";

function transition(state: AgentState, event: string): AgentState {
  if (state === "queued" && event === "worker.started") return "planning";
  if (state === "planning" && event === "tool.requested") return "waiting_tool";
  if (state === "waiting_tool" && event === "tool.succeeded") return "executing";
  if (state === "waiting_tool" && event === "tool.failed.retryable") return "retrying";
  if (state === "executing" && event === "human.approval.required") return "waiting_human";
  if (state === "executing" && event === "task.finished") return "completed";
  return "failed";
}
```

这里最关键的不是代码形式，而是 discipline：**状态只能被事件推动，不要让任何业务函数私下改状态**。只有这样，你的日志、监控、回放和人工介入才会一致。

## 四、把“工具等待”和“模型执行”拆开，很多问题会立刻清楚

不少团队一开始只有一个 `running` 状态，结果排障时非常痛苦。因为 `running` 可能代表：

- 模型正在生成计划
- 工具请求已经发出，但第三方 API 还没回
- 工具回来了，但结果还没过校验
- 任务在重试 backoff 中

这些阶段的含义完全不同，处理策略也不同。所以至少要把“模型执行中”和“等待外部世界”拆开。

一个简单判断标准是：**当前这一步是否能仅靠本进程继续推进**。如果答案是否定的，就不该继续留在 `executing`，而应该进入等待类状态。

这样拆开以后，你能更容易回答两个生产问题：

| 问题 | 没拆状态时 | 拆开后 |
| --- | --- | --- |
| 任务为什么慢 | 只能说“还在跑” | 能区分是模型慢还是工具慢 |
| 任务能否重试 | 很难判断 | 可以只重试等待阶段的外部依赖 |

这和[AI Agent 可观测性设计](/blog/ai-agent-observability-design/)里强调的观测粒度是一致的：你不需要追踪一切，但要追踪那些会改变控制策略的阶段。

## 五、超时、重试、回滚，不是附加逻辑，而是状态机的一部分

很多 Agent 项目把超时和重试写成外围装饰器，这对简单调用没问题，但对多步任务常常不够。因为一旦某一步已经产生副作用，重试就不再只是“再来一次”。

更稳妥的思路是把异常路径也编码进状态机：

| 事件 | 推荐状态变化 | 说明 |
| --- | --- | --- |
| 工具超时 | `waiting_tool -> retrying` | 标记本次等待失败，进入受控重试 |
| 工具重试成功 | `retrying -> executing` | 继续消费结果 |
| 工具重试耗尽 | `retrying -> failed` | 停止并保留诊断上下文 |
| 已产生副作用但后续失败 | `executing -> failed` 或补偿子流 | 可能需要 rollback |
| 需要人工确认后继续 | `waiting_human -> executing` | 人工输入本身也是事件 |

一旦这么建模，重试、补偿和回滚就不再是到处打补丁，而是主流程的一部分。相关策略可以结合[AI Agent 错误恢复机制设计：让 Agent 在失败中自我修复](/blog/ai-agent-error-recovery/)和[AI Agent 写操作回滚策略：让 Agent 的错误可以被撤销](/blog/ai-agent-rollback-strategy/)一起看。

## 六、人工接管要设计成正式状态，不要靠临时备注

现实里的 Agent 很少能 100% 自动跑完。权限审批、模糊指令、金额确认、高风险操作、外部依赖异常，这些都可能要求人介入。如果你没有 `waiting_human` 这类正式状态，最终就会出现两种坏味道：

1. 系统看起来还在跑，实际已经没人知道下一步该做什么。
2. 人工处理完以后，任务历史里没有留下清晰证据。

把人工接管设计成正式状态，至少要落三样东西：

- 为什么进入人工等待
- 当前已经完成到哪一步
- 人工输入回来后，允许从哪个状态继续

一个实用的数据结构可以是：

```json
{
  "state": "waiting_human",
  "pendingAction": "approve_email_send",
  "resumeFrom": "executing",
  "contextSnapshot": {
    "draftId": "d_123",
    "recipientCount": 28
  }
}
```

这样做的价值不只是便于产品展示，更关键的是让人工输入也成为系统事件，而不是散落在聊天消息里的口头补丁。

## 七、状态机落地时，最容易被忽略的是幂等和版本化

当 Agent 开始跨服务、跨队列、跨 worker 跑起来后，状态机的另一类风险就出现了：重复事件和旧事件覆盖新状态。

典型场景包括：

- 同一个工具回调因为网络重试被投递两次
- 两个 worker 同时尝试推进同一任务
- 人工审批回来时，任务已经因为超时被判失败

这时如果你的状态记录没有版本号或幂等键，就会出现“状态倒流”。所以在持久化层至少要有两项保护：

1. 状态更新带版本号或乐观锁。
2. 关键事件带 `event_id`，重复消费时直接忽略。

可以把规则记成一句话：**状态机不是单机内存对象，而是分布式系统里的共享事实**。一旦意识到这一点，很多“偶发现象”其实都能提前规避。

## 八、一个够用的落地路径：先做小状态机，再补诊断能力

如果你现在的 Agent 还只是“脚本 + prompt + 工具调用”，不需要一上来就做巨大编排平台。更实用的顺序通常是：

1. 定义最小状态集合。
2. 把所有状态变化统一成事件。
3. 为每个终态补齐原因和上下文快照。
4. 再增加重试、回滚、人工接管这些异常路径。

很多时候，团队不是不会设计复杂状态机，而是还没把“状态是产品能力”这件事想清楚。真正成熟的 Agent 系统，核心竞争力往往不在于模型多聪明，而在于出了问题以后，系统是否仍然可解释、可恢复、可继续推进。

## 九、相关阅读

- [AI Agent 错误恢复机制设计：让 Agent 在失败中自我修复](/blog/ai-agent-error-recovery/)
- [AI Agent 写操作回滚策略：让 Agent 的错误可以被撤销](/blog/ai-agent-rollback-strategy/)
- [AI Agent 可观测性设计](/blog/ai-agent-observability-design/)
- [AI Agent 任务分解模式](/blog/ai-agent-task-decomposition/)

如果你要把多模型、多工具的 Agent 流程接进统一服务层，[YoTradeApi](https://yotradeapi.com) 提供兼容式 API 接入方式，便于把状态流转、模型切换和调用治理放到同一套工程体系里。
