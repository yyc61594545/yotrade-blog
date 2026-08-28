---
title: 客户端令牌桶限速进阶实现
description: 超越单维度令牌桶的进阶限速方案：RPM/TPM 双维度联合限流、多进程分布式令牌桶、根据响应头动态调整速率，附完整可运行代码。
keywords:
  - 令牌桶算法
  - token bucket 实现
  - 分布式限流
  - RPM TPM 双维度限流
  - 客户端限速
pubDate: '2026-08-28'
updatedDate: '2026-08-28'
canonical: https://blog.yotradeapi.com/blog/client-side-rate-limiter/
tags:
  - 工程实战
  - Rate Limit
  - 技术深度
  - API管理
category: 工程实战
heroImage: ../../assets/blog-placeholder-4.jpg
---

[LLM API 限速处理完整指南](/blog/llm-rate-limit-handling/) 里给过一个基础的单维度令牌桶实现，够用于单进程、单一速率维度的场景。但真实场景往往更复杂：LLM API 同时限制 RPM（请求数/分钟）和 TPM（token 数/分钟）两个维度，服务可能是多进程/多实例部署，限速阈值也不是一成不变的。本文只讲这些进阶场景的具体实现，基础版本不再重复。

## 一、为什么单维度令牌桶不够用

大部分 LLM API 的限速是双维度联合生效的——RPM 和 TPM 任何一个触顶都会返回 429。如果客户端只做请求数限流，完全可能在 TPM 维度先被限速：发送 10 个请求，每个请求 5000 token，请求数远没到上限，但 token 总量已经超标。

正确的做法是维护两个独立的令牌桶，请求发出前**同时**申请两个桶的额度，任何一个不够都要等待：

```python
import asyncio
import time

class DualDimensionLimiter:
    """同时限制请求数和 token 数的双维度限流器"""

    def __init__(self, rpm: int, tpm: int):
        self.request_bucket = _TokenBucket(rate=rpm / 60, capacity=rpm)
        self.token_bucket = _TokenBucket(rate=tpm / 60, capacity=tpm)

    async def acquire(self, estimated_tokens: int):
        # 两个桶都要拿到额度才能放行，任何一个不够就整体等待
        while True:
            async with self.request_bucket.lock, self.token_bucket.lock:
                self.request_bucket.refill()
                self.token_bucket.refill()
                if self.request_bucket.tokens >= 1 and self.token_bucket.tokens >= estimated_tokens:
                    self.request_bucket.tokens -= 1
                    self.token_bucket.tokens -= estimated_tokens
                    return
            await asyncio.sleep(0.05)


class _TokenBucket:
    def __init__(self, rate: float, capacity: float):
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last = time.monotonic()
        self.lock = asyncio.Lock()

    def refill(self):
        now = time.monotonic()
        self.tokens = min(self.capacity, self.tokens + (now - self.last) * self.rate)
        self.last = now
```

**关键细节**：`estimated_tokens` 需要在请求发出前就估算出来（可以用 tiktoken 或类似分词器粗略估算 prompt token 数，再加一个预期输出 token 的保守估计），因为实际消耗量要等响应返回才知道，而限流判断必须发生在请求发出之前。

## 二、多进程/多实例场景：内存令牌桶失效

上面的实现是进程内内存态的，多开几个 worker 进程或者水平扩容多个实例后，每个进程各自维护一份令牌桶，加起来的实际请求量会远超预期——这是最容易被忽视的一个坑：单实例测试时限流工作正常，一上多实例限流形同虚设。

分布式场景需要把令牌桶状态放到 Redis 里，用 Lua 脚本保证"读取余量 + 扣减"是原子操作：

```python
import redis
import time

TOKEN_BUCKET_LUA = """
local key = KEYS[1]
local rate = tonumber(ARGV[1])       -- 每秒补充速率
local capacity = tonumber(ARGV[2])   -- 桶容量
local cost = tonumber(ARGV[3])       -- 本次请求消耗
local now = tonumber(ARGV[4])        -- 当前时间戳（秒，浮点）

local bucket = redis.call("HMGET", key, "tokens", "last")
local tokens = tonumber(bucket[1]) or capacity
local last = tonumber(bucket[2]) or now

-- 按时间差补充令牌
tokens = math.min(capacity, tokens + (now - last) * rate)

if tokens >= cost then
    tokens = tokens - cost
    redis.call("HMSET", key, "tokens", tokens, "last", now)
    redis.call("EXPIRE", key, 3600)
    return 1
else
    redis.call("HMSET", key, "tokens", tokens, "last", now)
    redis.call("EXPIRE", key, 3600)
    return 0
end
"""

class DistributedRateLimiter:
    def __init__(self, redis_client: redis.Redis, key: str, rate: float, capacity: float):
        self.redis = redis_client
        self.key = key
        self.rate = rate
        self.capacity = capacity
        self.script = self.redis.register_script(TOKEN_BUCKET_LUA)

    def try_acquire(self, cost: float = 1) -> bool:
        now = time.time()
        result = self.script(
            keys=[self.key],
            args=[self.rate, self.capacity, cost, now]
        )
        return bool(result)

    async def acquire(self, cost: float = 1, poll_interval: float = 0.05):
        while not self.try_acquire(cost):
            await asyncio.sleep(poll_interval)
```

用 Lua 脚本而不是"先 GET 再 SET"两步操作的原因很直接：两步操作在并发场景下有竞态窗口，多个进程可能同时读到"余量充足"然后都扣减成功，实际消耗量超过桶容量。Lua 脚本在 Redis 里是单线程原子执行的，天然避免这个问题。

## 三、动态调整速率：跟着响应头走

固定的 RPM/TPM 配置有个问题——如果配置得比实际配额保守，白白浪费吞吐；配置得激进，容易触发 429。更好的做法是读取 API 响应头里的实时配额信息，动态调整令牌桶参数：

```python
def update_limiter_from_headers(limiter: DualDimensionLimiter, headers: dict):
    """
    大多数 LLM API 会在响应头返回剩余配额，例如：
    x-ratelimit-remaining-requests / x-ratelimit-remaining-tokens
    x-ratelimit-limit-requests / x-ratelimit-limit-tokens
    """
    remaining_requests = headers.get("x-ratelimit-remaining-requests")
    remaining_tokens = headers.get("x-ratelimit-remaining-tokens")

    if remaining_requests is not None:
        # 用服务端的真实余量校正本地令牌桶，避免本地估算长期漂移
        limiter.request_bucket.tokens = min(
            limiter.request_bucket.tokens,
            float(remaining_requests)
        )
    if remaining_tokens is not None:
        limiter.token_bucket.tokens = min(
            limiter.token_bucket.tokens,
            float(remaining_tokens)
        )
```

这里只做"向下校正"（本地估算值和服务端真实值取较小者），不做向上校正——本地限流器保守一点没坏处，但如果本地余量被错误地调大，可能导致短时间内突发大量请求打到服务端触发限速。

## 四、突发流量整形：capacity 和 rate 怎么配

令牌桶的两个参数含义不同，配置时容易搞混：

- **rate（补充速率）**：决定长期平均吞吐，应该设置为略低于官方限速阈值（建议 90%），留出安全余量
- **capacity（桶容量）**：决定允许的突发峰值，容量越大，短时间内能打出的并发请求越多

如果你的业务流量本身就是均匀的（比如后台批处理），capacity 设置成和 rate 接近即可，几乎不需要突发能力。如果流量是脉冲式的（比如用户点击触发一批请求），适当调大 capacity 能提升响应速度，但要确保突发不会立刻把 TPM 打满导致后续请求排队更久。

```python
# 均匀流量场景：低突发，稳定吞吐
limiter = DualDimensionLimiter(rpm=int(500 * 0.9), tpm=int(150000 * 0.9))

# 脉冲流量场景：允许 3 倍瞬时突发
class BurstyLimiter(DualDimensionLimiter):
    def __init__(self, rpm: int, tpm: int, burst_factor: float = 3.0):
        self.request_bucket = _TokenBucket(rate=rpm / 60, capacity=rpm * burst_factor / 60)
        self.token_bucket = _TokenBucket(rate=tpm / 60, capacity=tpm * burst_factor / 60)
```

## 五、测试限流器：不要等上线才发现配错了

限流器本身的正确性值得单独写测试，重点验证三件事：稳态吞吐是否符合预期、突发是否被正确限制、多维度联合限流是否任一维度触顶都会等待。

```python
import pytest

@pytest.mark.asyncio
async def test_rate_limiter_steady_state():
    limiter = DualDimensionLimiter(rpm=60, tpm=6000)  # 1 req/s, 100 token/s
    start = time.monotonic()
    for _ in range(10):
        await limiter.acquire(estimated_tokens=100)
    elapsed = time.monotonic() - start
    # 10 个请求，稳态下应接近 9 秒（第一个请求立即放行，后续按速率排队）
    assert 8 <= elapsed <= 11

@pytest.mark.asyncio
async def test_token_dimension_blocks_before_request_dimension():
    # 请求数配额充足，但 token 配额很紧，应该被 token 维度卡住
    limiter = DualDimensionLimiter(rpm=6000, tpm=60)  # token: 1/s
    start = time.monotonic()
    await limiter.acquire(estimated_tokens=50)
    await limiter.acquire(estimated_tokens=50)  # 需要等待 token 补充
    elapsed = time.monotonic() - start
    assert elapsed >= 0.4
```

## 六、相关阅读

- [LLM API 限速（Rate Limit）处理完整指南](/blog/llm-rate-limit-handling/)
- [Python 异步并发调用 LLM API](/blog/python-async-llm-client/)
- [AI API 网关请求签名与防重放实现](/blog/llm-api-request-signing-proxy/)
- [自建 LLM 网关的路由实现：从零设计转发逻辑](/blog/llm-gateway-routing-implementation/)

如果不想自己维护这套多维度限流和分布式令牌桶，[YoTradeApi](https://yotradeapi.com) 的中转层已经内置了限速与排队策略，接入后可以直接把这部分复杂度交出去。
