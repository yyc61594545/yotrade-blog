---
title: Agent 多步写操作的 Saga 补偿机制设计
description: 讲解如何用 Saga 模式为多步 Agent 写操作设计补偿链，涵盖编排式与协同式两种实现、补偿幂等性与部分失败处理。
keywords:
  - Agent Saga 模式
  - 补偿事务设计
  - 多步写操作回滚
  - 分布式事务 Agent
  - Saga 编排与协同
pubDate: '2026-08-19'
updatedDate: '2026-08-19'
canonical: https://blog.yotradeapi.com/blog/agent-saga-compensation/
tags:
  - AI Agent
  - Saga 模式
  - 分布式事务
  - 应用工程
category: 应用工程
heroImage: ../../assets/blog-placeholder-3.jpg
---

Agent 执行"订机票 + 订酒店 + 发确认邮件"这类多步写操作时,如果第三步失败,前两步已经产生的副作用怎么办?单个写操作的撤销,[之前的文章](/blog/ai-agent-rollback-strategy/)已经讲过快照与补偿事务的基本思路。本文聚焦更复杂的场景:**当写操作跨多个步骤、多个外部系统时,怎么用 Saga 模式把这一串操作管理成一个"要么全部生效、要么被完整补偿"的整体**。

## 一、为什么多步写操作不能简单套用单步回滚

单个写操作的回滚,本质是"记住旧状态,出错就恢复"。但多步场景有三个新问题:

- **每一步操作的系统不同**,没有统一的数据库事务可以包裹。订机票是航司 API,订酒店是另一个供应商 API,发邮件是邮件服务商,不可能用一个 `ROLLBACK` 语句处理三个外部系统。
- **步骤之间可能已经产生真实世界的后果**。机票订了就是订了,航司不会因为你的数据库事务失败而自动作废,你必须显式调用它的"取消订单"接口。
- **失败发生的时间点不确定**。可能是第三步彻底失败,也可能是第三步"超时不确定是否成功",这两种情况需要的补偿逻辑不一样。

这正是分布式系统里 Saga 模式要解决的问题:**用一串"正向操作 + 对应补偿操作"的组合,替代做不到的分布式事务。**

## 二、Saga 的核心结构

一个 Saga 由一系列步骤组成,每个步骤都有两个动作:

| 步骤 | 正向操作 | 补偿操作 |
|------|---------|---------|
| 1 | 订机票 | 取消机票订单 |
| 2 | 订酒店 | 取消酒店订单 |
| 3 | 发确认邮件 | 发取消通知邮件(或不补偿,视业务而定) |

关键规则:**补偿操作按正向操作的相反顺序执行**。如果第三步失败,只需要补偿第二步、第一步;已经成功的步骤才需要补偿,还没执行的步骤天然不需要。

```python
class SagaStep:
    def __init__(self, name, action, compensate):
        self.name = name
        self.action = action
        self.compensate = compensate

async def run_saga(steps: list[SagaStep], ctx: dict):
    completed = []
    try:
        for step in steps:
            result = await step.action(ctx)
            completed.append((step, result))
        return {"status": "success", "ctx": ctx}
    except Exception as e:
        # 按相反顺序补偿已完成的步骤
        for step, result in reversed(completed):
            try:
                await step.compensate(ctx, result)
            except Exception as comp_err:
                # 补偿本身失败,必须记录并转人工,不能静默吞掉
                log_compensation_failure(step.name, comp_err)
        return {"status": "compensated", "failed_at": step.name, "error": str(e)}
```

这段代码是最小骨架,生产场景里还需要处理下一节的两个难点。

## 三、编排式 vs 协同式:两种 Saga 落地方式

**编排式(Orchestration)**:有一个中心协调者(通常就是 Agent 本身的执行循环)显式调用每一步、决定失败后按什么顺序补偿。上面的代码就是编排式的写法。优点是流程集中、易于追踪和调试;缺点是协调者本身是单点,需要有可靠的持久化(参考[事件溯源](/blog/agent-event-sourcing/)的思路)防止协调者自己崩溃后 Saga 状态丢失。

**协同式(Choreography)**:没有中心协调者,每个步骤完成后发布一个事件,下一步监听事件后自行触发,补偿也是靠事件链反向传播。优点是去中心化、扩展性好;缺点是流程分散在多处订阅者里,出问题时不容易一眼看出"现在到底卡在哪一步"。

对大多数 Agent 系统而言,**编排式更合适**——因为 Agent 的执行循环本来就是一个中心化的调用者,天然适合承担协调者角色,不需要为了去中心化引入额外的消息系统复杂度。协同式更适合本来就是事件驱动架构、多个独立服务协作的场景。

## 四、两个绕不开的难点

### 难点一:补偿操作必须幂等

补偿本身也可能失败或被重复触发——比如"取消酒店订单"这个请求超时了,上层重试了一次,如果酒店系统没有做幂等处理,可能会因为"订单已取消"报错,或者更糟,产生额外的异常状态。设计补偿操作时,要确保:

- 补偿动作可以安全地被调用多次(用订单 ID 做幂等键,而不是"取消当前最新订单"这种依赖上下文状态的写法)
- 补偿失败要有独立的重试队列和告警,不能因为补偿失败就让整个 Saga 卡死——该记录的记录,该转人工的转人工

### 难点二:不确定态(unknown state)的处理

最麻烦的情况不是"这步明确失败了",而是"这步超时了,不知道到底成功没成功"。比如订酒店请求发出去了,但因为网络问题没收到响应——酒店可能订上了,也可能没有。这种情况直接触发补偿是危险的:如果实际订上了,补偿"取消一个不存在的订单"可能报错;如果没订上,不补偿又会有遗留状态风险。

推荐做法是给每个正向操作补一个**状态查询接口**,遇到超时先查询实际状态再决定是否补偿,而不是盲目假设失败:

```python
async def safe_action_with_uncertainty(step, ctx):
    try:
        return await asyncio.wait_for(step.action(ctx), timeout=10)
    except asyncio.TimeoutError:
        actual_state = await step.query_state(ctx)  # 查询外部系统真实状态
        if actual_state == "confirmed":
            return {"state": "confirmed", "recovered_via_query": True}
        else:
            raise  # 确认没有生效,才走正常的失败补偿路径
```

如果外部系统压根不提供状态查询接口,退而求其次的做法是把这一步标记为"需要人工核实",而不是自动做出可能错误的补偿决定——错误的补偿有时比不补偿代价更高。

## 五、Saga 与 Agent 状态机、审计日志的配合

Saga 补偿链不是孤立设计的,它通常要和另外两块基础设施配合:

- 每个 Saga 步骤的状态转移(pending / running / completed / compensating / compensated),本质就是[Agent 状态机](/blog/agent-state-machine-design/)里讨论的有限状态机模型的一个具体应用
- 每一步的正向操作和补偿操作,都应该作为不可变事件记录下来,这样即使协调者进程崩溃重启,也能从事件流重建"哪些步骤已完成、哪些需要补偿",这正是 Event Sourcing 在 Saga 场景里的价值所在

把这三者放在一起看:状态机定义"合法的状态转移是什么",事件溯源保证"状态可以被可靠重建",Saga 补偿链定义"失败时具体怎么撤销"——三者组合起来,才是一个多步写操作 Agent 在生产环境里站得住脚的完整方案。

## 六、相关阅读

- [AI Agent 写操作回滚策略：让 Agent 的错误可以被撤销](/blog/ai-agent-rollback-strategy/)
- [用 Event Sourcing 记录 Agent 执行轨迹](/blog/agent-event-sourcing/)
- [AI Agent 状态机设计与落地](/blog/agent-state-machine-design/)
- [AI Agent 错误恢复机制设计：让 Agent 在失败中自我修复](/blog/ai-agent-error-recovery/)

多步写操作的 Agent 一旦接入真实外部系统,补偿链设计得越细致,线上事故的恢复成本就越低,搭配稳定的模型 API 调用底座能减少因请求本身失败而触发不必要补偿的情况,[YoTradeApi](https://yotradeapi.com) 提供高可用的中转服务,帮助降低这类基础设施层面的不确定性。
