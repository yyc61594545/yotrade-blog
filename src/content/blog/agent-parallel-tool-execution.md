---
title: Agent 并行工具调用的并发控制：从信号量到自适应限流
description: Agent 并行调用多个工具时，如何设计并发控制机制避免打垮下游服务：信号量限流、按下游分组的连接池、自适应并发调整与优先级调度。
keywords:
  - Agent 并发控制
  - 并行工具调用限流
  - 信号量并发
  - 自适应限流
  - Agent 工程实践
pubDate: '2026-08-29'
updatedDate: '2026-08-29'
canonical: https://blog.yotradeapi.com/blog/agent-parallel-tool-execution/
tags:
  - AI Agent
  - 并发控制
  - 工程实践
  - 应用工程
category: 应用工程
heroImage: ../../assets/blog-placeholder-3.jpg
---

[《Claude 并行 Tool Use 实战》](/blog/parallel-tool-use-claude/)和[《LLM 并行函数调用实战》](/blog/llm-function-calling-parallel/)已经讲清楚了并行工具调用"怎么发起、怎么收结果"。但真正上生产之后会发现，**能并行**和**该并行到什么程度**是两个问题——一个 Agent 任务并行发起 20 次工具调用，如果背后打向同一个下游 API，很可能直接把它打限流甚至打挂。本文只聚焦并发控制这一个维度：怎么让并行既快，又不失控。

## 一、为什么"能并行就全部并行"是个陷阱

模型一回合可能返回 10 个、20 个工具调用（比如批量查询一组商品价格）。如果客户端不假思索地用 `asyncio.gather` 全部同时发出去，会遇到几个真实问题：

- **下游服务被打垮**：第三方 API 通常有 QPS 限制，突发的并发峰值容易触发 429，甚至连累到其他正常流量
- **本地资源耗尽**：数据库连接池、HTTP 连接池都有上限，无节制并发会导致连接耗尽、后续请求排队甚至报错
- **单个慢工具拖累全局**：所有工具一起等待，其中一个响应慢的会让整轮任务的尾延迟被拉长，即便其他 9 个都秒回

**并行的本意是"缩短总耗时"，如果因为并发过量导致下游限流重试、连接排队，反而比顺序执行更慢**。并发控制要解决的就是这个"发起并行"和"控制在系统能承受的范围内"之间的落差。

## 二、第一层控制：全局信号量

最基础的做法：用信号量（Semaphore）限制同时在跑的工具调用总数，不管模型一次返回多少个。

```python
import asyncio

class ConcurrencyLimiter:
    def __init__(self, max_concurrent: int = 8):
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def run(self, coro):
        async with self.semaphore:
            return await coro

async def execute_tools_limited(tool_calls, tool_registry, max_concurrent=8):
    limiter = ConcurrencyLimiter(max_concurrent)

    async def run_one(call):
        fn = tool_registry[call["name"]]
        return await limiter.run(fn(**call["input"]))

    return await asyncio.gather(*[run_one(c) for c in tool_calls])
```

即使模型一次返回 30 个调用，实际同时在跑的也只有 `max_concurrent` 个，其余排队等待空位。这一层解决的是"本地资源不被打爆"的问题，但还没区分"打向哪个下游"。

## 三、第二层控制：按下游服务分组限流

全局信号量有个盲点：如果 30 个工具调用分别打向 5 个不同的下游服务，用一个全局并发上限，容易出现"其中一个服务占满了全部并发名额，其他服务饿着"的情况。更合理的做法是**按下游服务分别设置并发上限**：

```python
class PerServiceLimiter:
    def __init__(self, limits: dict[str, int]):
        self.semaphores = {
            service: asyncio.Semaphore(limit)
            for service, limit in limits.items()
        }

    async def run(self, service: str, coro):
        sem = self.semaphores.get(service)
        if sem is None:
            return await coro  # 未配置限流的服务，不限制
        async with sem:
            return await coro

# 按下游服务实际承受能力配置
limiter = PerServiceLimiter({
    "payment_api": 3,       # 支付网关严格限流，留足余量
    "search_index": 10,     # 内部搜索服务，承受力强
    "third_party_geo": 5,   # 第三方地理编码 API，按其官方 QPS 上限设置
})

async def execute_tool(call):
    service = TOOL_TO_SERVICE[call["name"]]
    fn = TOOL_REGISTRY[call["name"]]
    return await limiter.run(service, fn(**call["input"]))
```

这样即使一次任务里混合了多个下游的工具调用，每个下游各自的并发都被单独限制在其能承受的范围内，不会互相挤占。

## 四、第三层控制：自适应并发（根据错误率动态调整）

固定的并发上限是静态估算，实际下游的承受能力会随时间波动（比如第三方 API 在高峰期本身就更容易限流）。更进一步的做法是让并发上限根据实时错误率自动升降，类似 TCP 拥塞控制的思路：

```python
class AdaptiveLimiter:
    def __init__(self, initial=8, min_c=2, max_c=20):
        self.current = initial
        self.min_c = min_c
        self.max_c = max_c
        self.semaphore = asyncio.Semaphore(initial)

    def on_success(self):
        # 连续成功，缓慢提升并发上限（加法增长）
        if self.current < self.max_c:
            self.current += 1
            self.semaphore.release()

    def on_rate_limited(self):
        # 遇到 429/限流信号，快速砍半（乘法减少）
        self.current = max(self.min_c, self.current // 2)
        # 实际实现需要重建 semaphore 或用计数器控制，此处为简化示意

    async def run(self, coro):
        async with self.semaphore:
            try:
                result = await coro
                self.on_success()
                return result
            except RateLimitError:
                self.on_rate_limited()
                raise
```

核心思路是**加法增长、乘法回退**（AIMD）：没有限流信号时缓慢提升并发上限，一旦遇到 429 就快速砍半。这样系统能自动逼近下游实际能承受的并发水位，不需要人工反复调参数。生产实现建议用现成的限流库（如 `aiolimiter`），上面代码只是展示思路，`Semaphore` 本身不支持动态调整容量，实际要用计数器 + 条件变量或者第三方库替代。

## 五、优先级：不是所有工具调用都同等重要

并发名额有限时，先执行哪个也是个设计问题。比如一个任务里既有"查用户身份权限"（阻塞后续步骤的关键路径）又有"查历史浏览记录做个性化"（锦上添花），并发吃紧时应该让关键路径优先拿到执行名额：

```python
import heapq

async def execute_with_priority(tool_calls, limiter, priority_map):
    # priority_map: {tool_name: priority}，数字越小优先级越高
    sorted_calls = sorted(tool_calls, key=lambda c: priority_map.get(c["name"], 99))

    async def run_one(call):
        fn = TOOL_REGISTRY[call["name"]]
        return await limiter.run(fn(**call["input"]))

    # 按优先级顺序提交任务，先提交的更早拿到信号量名额
    return await asyncio.gather(*[run_one(c) for c in sorted_calls])
```

这只是简化处理——用"提交顺序"近似模拟优先级，严格意义上的优先级队列需要在信号量释放时按优先级唤醒等待者，复杂场景可以直接用 `asyncio.PriorityQueue` 配合 worker 池实现。

## 六、监控：并发控制生效与否要看得见

上线并发控制后，至少要监控三个指标才能判断参数设置是否合理：

| 指标 | 异常信号 | 处理方向 |
|---|---|---|
| 平均排队等待时间 | 持续偏高 | 并发上限设太低，可以适当调高 |
| 下游 429 / 5xx 比例 | 明显上升 | 并发上限设太高，需要调低或启用自适应限流 |
| 任务总耗时 P99 | 比预期高很多 | 检查是否有单个慢工具或下游成为瓶颈 |

没有监控的并发控制参数本质上是拍脑袋定的数字，跑一段时间后应该用真实数据回过头验证。

## 七、小结：三层控制组合使用

- **全局信号量**：兜底，防止本地资源（连接池、内存）被打爆
- **按下游分组限流**：核心，避免不同下游之间互相挤占并发名额
- **自适应调整**：进阶，让并发水位随下游实际承受能力自动收敛，减少人工调参

大多数场景做到前两层已经足够稳健，只有下游承受能力波动明显、且团队有精力做好监控和回归验证时，才值得投入自适应限流。

## 八、相关阅读

- [Claude 并行 Tool Use 实战：一次调用多个工具](/blog/parallel-tool-use-claude/)
- [LLM 并行函数调用实战](/blog/llm-function-calling-parallel/)
- [Agent 工具调用的超时预算设计](/blog/agent-tool-timeout-budget/)
- [AI Agent 工具集合的设计原则](/blog/ai-agent-tool-design/)

搭建 Agent 并行工具调用链路时，如果模型侧的调用也需要稳定不被限流打断，[YoTradeApi](https://yotradeapi.com) 提供 Claude、GPT-5 等主流模型的高并发中转接口，配合本文的并发控制思路可以让整条链路更稳。
