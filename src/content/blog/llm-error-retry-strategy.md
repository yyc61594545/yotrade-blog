---
title: LLM API 错误重试策略设计
description: 覆盖 429、500、502、timeout 等 LLM API 常见错误，系统讲解指数退避、抖动、熔断器与幂等设计，附 Python 生产可用代码。
keywords:
  - LLM API 错误重试
  - 指数退避重试
  - API rate limit 处理
  - 429 错误处理
  - LLM 生产可靠性
pubDate: '2026-05-23'
updatedDate: '2026-05-23'
canonical: https://blog.yotradeapi.com/blog/llm-error-retry-strategy/
tags:
  - API
  - 工程实践
  - Python
  - 可靠性
category: 应用工程
heroImage: ../../assets/blog-placeholder-4.jpg
---

LLM API 不像内部数据库那么稳定——rate limit、过载、网络抖动随时可能出现。如果你的应用没有正确的重试逻辑，一个偶发的 429 就能让用户体验崩掉。本文从错误类型分类出发，梳理生产可用的重试策略设计，附完整 Python 实现。

## 一、先搞清楚哪些错误值得重试

不是所有错误都应该重试。盲目重试不仅浪费，还可能加重服务端压力，触发更长时间的限流。

| 错误类型 | HTTP 状态 | 是否重试 | 理由 |
|----------|-----------|----------|------|
| Rate limit 超限 | 429 | ✅ 重试（退避） | 临时限制，等待后可恢复 |
| 服务端过载 | 500、529 | ✅ 重试 | 临时过载，通常几秒内恢复 |
| 网关错误 | 502、503、504 | ✅ 重试 | 代理层问题，通常短暂 |
| 网络超时 | timeout | ✅ 重试（需幂等） | 请求可能未到达，也可能在处理中 |
| 认证失败 | 401 | ❌ 不重试 | Key 无效，重试也没用 |
| 参数错误 | 400 | ❌ 不重试 | 请求本身有问题，重试会一直失败 |
| 内容违规 | 400（特定错误码） | ❌ 不重试 | 模型拒绝，不是临时问题 |
| 上下文超长 | 400 | ❌ 不重试（需截断） | 先处理 prompt，再发请求 |

**核心判断原则**：错误是"临时的服务端问题"就重试，是"请求本身有问题"就不重试。

## 二、指数退避：基础算法

最简单的重试是"失败后立刻再试"，但这会在服务端已经过载时继续轰炸，制造惊群效应。正确做法是指数退避：每次重试等待时间翻倍。

```python
import time
import random

def exponential_backoff(attempt: int, base: float = 1.0, cap: float = 60.0) -> float:
    """
    返回第 attempt 次重试应等待的秒数（含抖动）。
    attempt 从 0 开始计数。
    """
    delay = min(base * (2 ** attempt), cap)
    # 加入 ±25% 随机抖动，防止多个客户端同时重试
    jitter = delay * random.uniform(-0.25, 0.25)
    return max(0, delay + jitter)
```

**抖动（Jitter）为什么重要**：如果 100 个客户端同时触发 429，然后都按同样的退避时间等待，下一轮它们会同时发出请求，再次触发 429。加入随机抖动能把这 100 个请求分散到一个时间窗口里，避免"同步重试风暴"。

## 三、生产可用的重试装饰器

下面是一个完整的重试装饰器，覆盖 Anthropic SDK 和 OpenAI SDK 的常见异常：

```python
import time
import random
import functools
import logging
from typing import Callable, Tuple, Type

import anthropic

logger = logging.getLogger(__name__)

# 可重试的异常类型
RETRYABLE_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    anthropic.RateLimitError,
    anthropic.InternalServerError,
    anthropic.APIConnectionError,
    anthropic.APITimeoutError,
)

def with_retry(
    max_attempts: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = RETRYABLE_EXCEPTIONS,
):
    """重试装饰器，使用指数退避+抖动策略。"""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        raise  # 最后一次失败直接抛出
                    
                    # 从响应头读取 Retry-After（如果有）
                    retry_after = None
                    if hasattr(e, 'response') and e.response is not None:
                        retry_after = e.response.headers.get('retry-after')
                    
                    if retry_after:
                        delay = float(retry_after)
                    else:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        delay *= random.uniform(0.75, 1.25)
                    
                    logger.warning(
                        f"API 调用失败（{type(e).__name__}），"
                        f"第 {attempt + 1}/{max_attempts} 次，"
                        f"{delay:.1f}s 后重试"
                    )
                    time.sleep(delay)
                except Exception:
                    raise  # 不可重试的错误直接抛出
            raise last_exception
        return wrapper
    return decorator


# 使用示例
client = anthropic.Anthropic()

@with_retry(max_attempts=5)
def call_claude(prompt: str) -> str:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text
```

### 异步版本

如果你在用 `asyncio`，需要对应的异步实现：

```python
import asyncio
import anthropic

async_client = anthropic.AsyncAnthropic()

async def call_claude_async(prompt: str, max_attempts: int = 5) -> str:
    for attempt in range(max_attempts):
        try:
            response = await async_client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except (anthropic.RateLimitError, anthropic.InternalServerError,
                anthropic.APIConnectionError) as e:
            if attempt == max_attempts - 1:
                raise
            delay = min(1.0 * (2 ** attempt), 60.0) * random.uniform(0.75, 1.25)
            logger.warning(f"重试 {attempt + 1}/{max_attempts}，等待 {delay:.1f}s")
            await asyncio.sleep(delay)
```

## 四、读 Retry-After 响应头

Anthropic API 在 429 响应里通常会附带 `retry-after` 响应头，告诉你应该等多久。优先使用这个值，而不是自己算退避时间——它代表服务端的实际恢复预期。

```python
except anthropic.RateLimitError as e:
    if hasattr(e, 'response') and e.response:
        retry_after = e.response.headers.get('retry-after')
        if retry_after:
            wait_time = float(retry_after) + 0.5  # 多等半秒 buffer
        else:
            wait_time = exponential_backoff(attempt)
    time.sleep(wait_time)
```

## 五、超时错误的幂等性问题

Timeout 错误是最棘手的情况：请求可能没到达服务端，也可能已经在处理、只是响应没返回。如果你直接重试，可能触发两次计费或两次操作。

**处理原则**：
- **只读操作**（查询、摘要、分类）：可以安全重试
- **有副作用操作**（写入数据库、发送邮件、扣费）：需要先用幂等 key 去查是否已有结果

```python
import uuid

def generate_idempotency_key(user_id: str, request_content: str) -> str:
    """基于用户 + 内容生成幂等 key，相同输入始终得到相同 key。"""
    import hashlib
    content = f"{user_id}:{request_content}"
    return hashlib.sha256(content.encode()).hexdigest()[:32]

# 在重试前先检查是否有缓存结果
def call_with_idempotency(user_id: str, prompt: str) -> str:
    key = generate_idempotency_key(user_id, prompt)
    
    # 先查缓存
    cached = cache.get(key)
    if cached:
        return cached
    
    # 调用 API
    result = call_claude(prompt)
    
    # 写缓存（TTL 设长一点，避免短时间内重复触发）
    cache.set(key, result, ttl=3600)
    return result
```

## 六、熔断器模式

指数退避解决的是"偶发失败"，熔断器（Circuit Breaker）解决的是"持续故障"。当服务端已经明显挂了，继续重试只会徒耗资源和时间——熔断器会在连续失败 N 次后直接短路，跳过真正的 API 调用。

```python
import time
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"      # 正常，允许调用
    OPEN = "open"          # 熔断，直接失败
    HALF_OPEN = "half_open"  # 试探，允许一次调用

class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    def call(self, func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker OPEN，跳过 API 调用")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

# 使用
breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30)

def safe_call(prompt: str) -> str:
    return breaker.call(call_claude, prompt)
```

熔断器适合有监控告警的生产服务。当熔断器打开时，触发告警，运维可以及时介入。

## 七、日志与可观测性

重试逻辑如果是黑盒，出问题时很难排查。建议在每次重试时记录结构化日志：

```python
import structlog

log = structlog.get_logger()

log.warning(
    "api_retry",
    attempt=attempt,
    max_attempts=max_attempts,
    error_type=type(e).__name__,
    error_message=str(e)[:200],
    wait_seconds=round(delay, 2),
    model=model,
    request_id=request_id,
)
```

关键指标：
- **重试率**：重试次数 / 总请求次数，正常应低于 5%
- **最终失败率**：所有重试都耗尽后仍失败的比例
- **P95 延迟影响**：重试会推高尾延迟，需要单独监控

## 八、常见的错误配置

**错误 1：max_attempts 设太大**

设到 10 次时，最坏情况等待时间是 `1 + 2 + 4 + 8 + 16 + 32 + 60 + 60 + 60 = 243 秒`。对于面向用户的实时接口，这基本等于超时失败。生产里面向用户的接口建议不超过 3–4 次，批处理任务可以设高一点。

**错误 2：重试所有异常**

把 `except Exception` 改成 `except RETRYABLE_EXCEPTIONS`，否则 400 参数错误会傻傻地重试 5 次。

**错误 3：不记录重试日志**

无日志的重试等于黑盒。哪次请求触发了几次重试、等待了多久，这些信息在排查费用异常和稳定性问题时非常关键。

## 九、相关阅读

- [LLM Rate Limit 处理策略详解](/blog/llm-rate-limit-handling/)
- [LLM 延迟优化实战](/blog/llm-latency-optimization/)
- [AI API 中转错误码全解析](/blog/ai-api-relay-error-codes/)
- [Streaming SSE 常见问题排查](/blog/streaming-sse-troubleshooting/)
- [Claude System Prompt 工程实战](/blog/claude-system-prompt-engineering/)

想要更稳定的 LLM API 体验？[YoTradeApi](https://yotradeapi.com) 在中转层内置了自动重试与负载均衡，帮你屏蔽上游抖动，让应用层只需处理真正的业务错误。
