---
title: 多 Agent 共享限流配额的协调：谁先用、谁该等
description: 多个 AI Agent 并行跑在同一个 API Key 下时如何协调限流配额，涵盖集中式令牌桶、按优先级分配、退避排队三种模式及适用场景。
keywords:
  - 多 Agent 限流协调
  - 共享 API 配额
  - Agent 并发限流
  - 分布式令牌桶
  - AI Agent 编排
pubDate: '2026-08-31'
updatedDate: '2026-08-31'
canonical: https://blog.yotradeapi.com/blog/agent-rate-limit-coordination/
tags:
  - 应用工程
  - Rate Limit
  - Multi-Agent
  - 工程实践
category: 应用工程
heroImage: ../../assets/blog-placeholder-1.jpg
---

单个 Agent 调用 API 时，限流是个相对简单的问题：按 [RPM/TPM 双维度令牌桶](/blog/client-side-rate-limiter/)控制发送节奏，遇到 429 按[标准重试策略](/blog/llm-rate-limit-handling/)退避即可。

但当你的系统里跑着多个 Agent——可能是 [Codex 拆出来的多个并行子任务](/blog/codex-multi-agent-boundaries/)，也可能是多个产品功能各自的 Agent 实例——而它们共用同一个 API Key、同一份限流配额时，问题就变了：**每个 Agent 都以为自己独占限额，实际上大家在抢同一个池子**。这篇文章讲怎么协调这种"多个消费者、一个配额池"的场景。

## 一、问题的本质：局部视角看不到全局占用

如果每个 Agent 各自维护一个本地令牌桶（比如各自按"总限额 ÷ Agent 数量"算出自己的份额），会遇到两类失衡：

- **忙闲不均**：某个 Agent 这一刻没什么任务，它的那份配额被闲置；另一个 Agent 任务堆积，配额却不够用，而两者其实共享同一个上限，理论上应该互相借用
- **总量失控**：如果各 Agent 只按自己的估算发请求，没有一个地方统计"全局这一刻已经发了多少"，很容易在瞬间叠加起来超过账号的真实上限，触发 429 甚至短时封禁

本质原因是：限流配额是账号级别的全局资源，但每个 Agent 的决策是局部的。要协调，就必须有一个地方能看到全局状态。

## 二、模式一：集中式令牌桶（推荐默认选择）

最直接的解法是不让每个 Agent 自己维护令牌桶，而是把令牌桶做成一个所有 Agent 都要请求的中心服务（可以是一个轻量 HTTP 服务，也可以直接用 Redis 做原子操作）。

流程很简单：Agent 发起 API 调用前，先向中心令牌桶请求"许可"；拿到许可才真正发请求；没拿到就等待或进入排队。

用 Redis 实现的核心逻辑，可以直接复用[《LLM 用户级配额管理实现》](/blog/llm-quota-management-design/)里讲的 Redis 原子扣减模式，把"用户级"换成"Agent 级"或"全局级"即可：

```python
import redis
import time

r = redis.Redis()

def acquire_token(bucket_key="global_rpm", capacity=500, refill_per_sec=8.3):
    now = time.time()
    lua_script = """
    local key = KEYS[1]
    local capacity = tonumber(ARGV[1])
    local refill_rate = tonumber(ARGV[2])
    local now = tonumber(ARGV[3])

    local bucket = redis.call('HMGET', key, 'tokens', 'ts')
    local tokens = tonumber(bucket[1]) or capacity
    local last_ts = tonumber(bucket[2]) or now

    local elapsed = now - last_ts
    tokens = math.min(capacity, tokens + elapsed * refill_rate)

    if tokens >= 1 then
        tokens = tokens - 1
        redis.call('HMSET', key, 'tokens', tokens, 'ts', now)
        return 1
    else
        redis.call('HMSET', key, 'tokens', tokens, 'ts', now)
        return 0
    end
    """
    return r.eval(lua_script, 1, bucket_key, capacity, refill_per_sec, now)
```

所有 Agent 进程调用同一个 Redis 实例、同一个 `bucket_key`，天然实现了跨进程、跨机器的全局协调，不需要 Agent 之间互相通信。这是多数场景下最省心的方案。

## 三、模式二：按优先级预分配配额

集中式令牌桶解决了"总量不超限"，但没解决"谁更该被优先满足"。如果系统里有些 Agent 服务的是付费用户、有些是内部批处理任务，全局令牌桶会让它们平等竞争，高优先级任务可能被低优先级任务抢占配额。

这种场景需要在令牌桶之上加一层优先级分配，常见做法是把总配额按比例切成几个子池：

| Agent 类型 | 配额占比 | 说明 |
|---|---|---|
| 用户实时交互 Agent | 60% | 直接影响用户体验，优先保证 |
| 内部批处理 Agent | 25% | 可以容忍延迟，配额不够时排队等待 |
| 监控/巡检 Agent | 15% | 最低优先级，配额紧张时可以跳过本轮 |

实现上，可以给每个子池单独开一个 Redis key，按各自的容量和补充速率独立限流；同时留一个"溢出借用"规则——如果高优先级池子暂时用不完，允许低优先级池子临时借用，避免资源浪费。这比简单粗暴地按 Agent 数量平均分配更贴近真实业务需求。

## 四、模式三：排队 + 退避，而不是直接拒绝

无论用哪种分配模式，总有配额耗尽的时刻。这时候关键设计决策是：**拿不到令牌的 Agent 该怎么办**。

不建议的做法是让 Agent 直接放弃任务或报错退出——尤其是对于批处理、非实时的任务，更合理的处理是进入等待队列：

- 用一个轻量队列（Redis List 或消息队列）暂存"待发送"的请求
- Agent 侧不再自己算退避时间，而是监听队列，令牌桶补充后按 FIFO 或优先级顺序取出执行
- 给队列设置最大长度和超时时间，避免任务无限堆积——超时的任务应该有明确的失败反馈，而不是静默丢弃

这个排队层如果做得足够通用，还能顺带解决"多个 Agent 各自实现自己的 429 重试逻辑，行为不一致"的问题——把重试和退避收敛到队列这一层统一处理，比分散在每个 Agent 里各写一套要好维护得多。

## 五、监控：协调是否生效，得有数据支撑

协调机制上线后，至少要监控这几个指标，才能判断设计是否合理：

- **配额利用率**：全局配额有没有被充分使用，长期低于 50% 说明分配可能过于保守
- **等待队列长度和等待时长分布**：如果高优先级任务经常要等很久，说明优先级分配比例需要调整
- **429 发生率**：协调机制生效后，理论上应该趋近于 0，如果还频繁出现，说明中心令牌桶的容量估算和账号真实限额有偏差

## 六、相关阅读

- [客户端令牌桶限速进阶实现](/blog/client-side-rate-limiter/)
- [LLM API 限速（Rate Limit）处理完整指南](/blog/llm-rate-limit-handling/)
- [LLM 用户级配额管理实现](/blog/llm-quota-management-design/)
- [Codex 多 Agent 任务拆分边界](/blog/codex-multi-agent-boundaries/)

多 Agent 场景下配额协调得再好，也绕不开一个前提——账号本身的限额是否够用。如果多个 Agent 长期在同一个账号下抢配额，也可以考虑通过 [YoTradeApi](https://yotradeapi.com) 申请更高的限额或拆分多个 Key 分摊压力，从源头减少协调层的调度压力。
