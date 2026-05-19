---
title: LLM API 限速（Rate Limit）处理完整指南
description: OpenAI / Anthropic / Gemini 限速机制详解、客户端重试策略、令牌桶、跨账号分发、监控告警的工程化处理方法。
keywords:
- llm 限速
- openai rate limit
- anthropic 限速
- 429 处理
- token tpm rpm
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/llm-rate-limit-handling/
tags:
- Rate Limit
- 故障排查
- 工程实战
- API
category: 故障排查
heroImage: ../../assets/blog-placeholder-3.jpg
---

# LLM API 限速（Rate Limit）处理完整指南

429 是 LLM 应用上线后最早遇到的问题。本文讲清楚三家旗舰的限速机制、客户端处理策略、什么时候需要换中转。

## 一、三家限速维度

| 厂商 | RPM | TPM | TPD | Concurrent |
| --- | --- | --- | --- | --- |
| OpenAI | ✓ | ✓ | ✓ | ✓ |
| Anthropic | ✓ | ✓ | ✗ | ✗（一般） |
| Gemini | ✓ | ✓ | ✓ | ✓ |

- **RPM**：requests per minute
- **TPM**：tokens per minute
- **TPD**：tokens per day
- **Concurrent**：同时并发请求数

走中转后，限速由**中转的配置**决定，不一定等于上游官方。

## 二、看到 429 之后

### Step 1：看 response header

```
HTTP/1.1 429 Too Many Requests
Retry-After: 5
X-RateLimit-Limit-Requests: 60
X-RateLimit-Remaining-Requests: 0
X-RateLimit-Reset-Requests: 5s
```

- `Retry-After`：建议等几秒
- `X-RateLimit-*`：当前配额状态

### Step 2：按 Retry-After 等

```python
if response.status_code == 429:
    wait = int(response.headers.get("Retry-After", 5))
    time.sleep(wait)
    # retry
```

如果服务器给了明确的 Retry-After，**严格按它等**。比自己猜更高效。

### Step 3：没有 Retry-After 时用指数退避

```python
def call_with_retry(fn, max_retries=5):
    for attempt in range(max_retries):
        try:
            return fn()
        except RateLimitError as e:
            wait = min(60, 2 ** attempt + random.random())
            time.sleep(wait)
    raise RuntimeError("exceeded retries")
```

加随机抖动避免多个客户端**同步退避**（雪崩）。

## 三、客户端令牌桶限流

主动控制比被动重试好。在客户端实现令牌桶：

```python
import asyncio, time

class RateLimiter:
    def __init__(self, rate, capacity):
        self.rate = rate          # tokens / second
        self.capacity = capacity
        self.tokens = capacity
        self.last = time.monotonic()
        self.lock = asyncio.Lock()

    async def acquire(self, cost=1):
        while True:
            async with self.lock:
                now = time.monotonic()
                self.tokens = min(self.capacity, self.tokens + (now - self.last) * self.rate)
                self.last = now
                if self.tokens >= cost:
                    self.tokens -= cost
                    return
            await asyncio.sleep(0.05)

# 用法
rl = RateLimiter(rate=5, capacity=10)   # 平均 5 req/s, burst 10
async def call():
    await rl.acquire()
    return await client.chat.completions.create(...)
```

详见 [Python 异步并发调用 LLM API](/blog/python-async-llm-client/)。

## 四、TPM 限速怎么处理

RPM 容易理解，**TPM 是按输出 token 算的**——你发请求前不知道输出多少。处理思路：

```python
async def call(prompt):
    # 预估：输入 + max_tokens
    estimated = count_tokens(prompt) + 1000
    await tpm_limiter.acquire(cost=estimated)
    return await client.chat.completions.create(
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )
```

用 max_tokens 上限当 TPM 预算。**保守估算 + 实际不到的部分浪费**——但避免被 429。

## 五、跨账号分发

单账号 RPM 不够？开多账号：

```python
class KeyPool:
    def __init__(self, keys):
        self.clients = [
            OpenAI(api_key=k, base_url="https://yotradeapi.com/v1")
            for k in keys
        ]
        self.idx = 0

    def get(self):
        c = self.clients[self.idx]
        self.idx = (self.idx + 1) % len(self.clients)
        return c

pool = KeyPool([key1, key2, key3])

resp = pool.get().chat.completions.create(...)
```

简单 round-robin。3 个 key = 3 倍 RPM。

**注意**：

- 同一个 key 用在多个客户端，总 RPM 还是上限
- 跨账号的限制由账号 owner 各自承担成本
- 不要把同一个用户的请求拆给多个 key（会丢上下文）

## 六、当限速来自模型本身

OpenAI / Anthropic 都有**全球限速**——不是你的 key 限制，是模型本身在某些时段超负荷。这种 429 表现：

- `Retry-After` 可能 1 秒
- `X-RateLimit-Remaining-Requests` 仍非零
- error message 含 "model overloaded"

处理：**fallback 模型**

```python
async def call_with_fallback(prompt):
    try:
        return await call(prompt, "gpt-5")
    except RateLimitError:
        # 主模型限速，降级
        return await call(prompt, "claude-sonnet-4-6")
```

[LiteLLM Proxy](/blog/litellm-cn-gateway-self-host/) 内置 fallback 链。

## 七、中转层限速

走中转时，限速可能来自：

1. **中转设置的全局 limit**（保护自己上游不爆）
2. **你 key 的 limit**（中转后台配置）
3. **上游 API limit**

排查顺序：

- 看中转后台 key 的 RPM/TPM 配额
- 调高（如果中转允许）
- 仍 429 → 上游问题，等几分钟或 fallback

## 八、监控限速

Prometheus 指标：

```python
from prometheus_client import Counter, Histogram

rate_limit_hits = Counter("llm_rate_limit_total", "429 errors", ["model"])
retry_count = Histogram("llm_retry_count", "retries needed")

try:
    resp = call(...)
except RateLimitError:
    rate_limit_hits.labels(model="claude-sonnet-4-6").inc()
```

异常上升 → 告警。

## 九、长 prompt 的特殊处理

长 prompt（> 50k tokens）即使 RPM 没满也容易 TPM 满。三招：

1. **缩短上下文**：精简 system prompt、用 RAG 替代全文档
2. **缓存**：开 prompt caching（cache 命中不算 input token 全额）
3. **拆任务**：长任务拆成多个小请求

## 十、生产 checklist

- [ ] 客户端有 retry + 指数退避
- [ ] 看 Retry-After 头
- [ ] 加随机抖动
- [ ] 令牌桶主动限流
- [ ] max_retries 有上限（不要无限循环）
- [ ] 监控 429 比例
- [ ] 准备 fallback 模型 / 备用中转
- [ ] 中转后台 key 配额合理
- [ ] 长 prompt 用 caching

## 十一、Anti-pattern

- ❌ 立刻无限重试（雪崩）
- ❌ 退避到 1 秒以下（机器学不会"礼貌"）
- ❌ 把所有用户共享一把 key（无法定位是谁触发限速）
- ❌ 忽视 TPM（只看 RPM）
- ❌ 不监控就上线

## 十二、相关阅读

- [AI API 中转常见错误码排查手册](/blog/ai-api-relay-error-codes/)
- [Python 异步并发调用 LLM API](/blog/python-async-llm-client/)
- [AI API 中转稳定性测试方法](/blog/ai-api-relay-stability-test/)
- [LiteLLM 自部署 LLM 网关](/blog/litellm-cn-gateway-self-host/)
- [AI 编程代理成本控制实战](/blog/ai-coding-agent-cost-control/)

需要 RPM/TPM 可配置 + 限速友好（带 Retry-After）的中转？[YoTradeApi](https://yotradeapi.com/register) 后台每个 Key 独立设限速 + 实时显示当前用量。
