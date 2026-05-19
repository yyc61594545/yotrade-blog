---
title: Python 异步并发调用 LLM API 实战
description: Python asyncio 高并发调用 LLM API 的完整模式：连接池、限流、超时、重试、监控，含 100/min 任务的真实代码。
keywords:
- python async llm
- asyncio openai
- llm 并发
- python ai api
- llm 限流
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/python-async-llm-client/
tags:
- Python
- asyncio
- 并发
- API 中转
- 工程实战
category: 工程实战
heroImage: ../../assets/blog-placeholder-3.jpg
---

# Python 异步并发调用 LLM API 实战

把 LLM 当后端服务用的人都遇到过这个问题：1000 条数据要跑分类/摘要/翻译，串行跑 4 小时，并发跑容易被 429 ban。本文给一份生产可用的异步并发模式，覆盖连接池、限流、重试、监控。

## 一、基础：异步调用 OpenAI SDK

```python
import asyncio
from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key="sk-yo-...",
    base_url="https://yotradeapi.com/v1",
    timeout=60.0,
    max_retries=2,
)

async def one(text):
    resp = await client.chat.completions.create(
        model="claude-haiku-4-5",
        messages=[{"role": "user", "content": text}],
        max_tokens=200,
    )
    return resp.choices[0].message.content

async def main():
    texts = ["分类这段：..." for _ in range(100)]
    tasks = [one(t) for t in texts]
    results = await asyncio.gather(*tasks)
    print(len(results))

asyncio.run(main())
```

但这样 100 个任务**一次性并发**，会立刻被中转 429。

## 二、并发控制：Semaphore

```python
import asyncio
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key="sk-yo-...", base_url="https://yotradeapi.com/v1")
sem = asyncio.Semaphore(10)   # 同时最多 10 个

async def one(text):
    async with sem:
        resp = await client.chat.completions.create(
            model="claude-haiku-4-5",
            messages=[{"role": "user", "content": text}],
            max_tokens=200,
        )
        return resp.choices[0].message.content
```

简单但够用。`10` 这个数根据中转的 RPM/TPM 决定。

## 三、令牌桶限流

Semaphore 是 "同时并发数"，没考虑 "每秒/每分速率"。更精确：

```python
import asyncio, time

class RateLimiter:
    def __init__(self, rate: float, capacity: int):
        self.rate = rate          # tokens / second
        self.capacity = capacity
        self.tokens = capacity
        self.last = time.monotonic()
        self.lock = asyncio.Lock()

    async def acquire(self, cost: int = 1):
        async with self.lock:
            now = time.monotonic()
            self.tokens = min(self.capacity, self.tokens + (now - self.last) * self.rate)
            self.last = now
            if self.tokens >= cost:
                self.tokens -= cost
                return
            wait = (cost - self.tokens) / self.rate
        await asyncio.sleep(wait)
        await self.acquire(cost)

rl = RateLimiter(rate=5, capacity=10)   # 平均 5 req/s, burst 10

async def one(text):
    await rl.acquire()
    resp = await client.chat.completions.create(...)
    return resp
```

## 四、重试与指数退避

```python
import asyncio, random
from openai import RateLimitError, APIConnectionError, APIError

async def call_with_retry(text, max_retries=5):
    for attempt in range(max_retries):
        try:
            resp = await client.chat.completions.create(
                model="claude-haiku-4-5",
                messages=[{"role": "user", "content": text}],
                max_tokens=200,
            )
            return resp.choices[0].message.content
        except RateLimitError as e:
            wait = 2 ** attempt + random.random()
            print(f"429 wait {wait:.1f}s (attempt {attempt+1})")
            await asyncio.sleep(wait)
        except APIConnectionError as e:
            wait = 2 ** attempt
            await asyncio.sleep(wait)
        except APIError as e:
            if 500 <= e.status_code < 600:
                wait = 2 ** attempt
                await asyncio.sleep(wait)
            else:
                raise
    raise RuntimeError(f"Failed after {max_retries} attempts")
```

要点：

- 429 + 5xx 重试，其它错误直接抛
- 指数退避 + 抖动（random）避免雪崩
- 单任务重试上限避免无限循环

## 五、完整生产模板

```python
"""
batch_llm.py - 生产可用的批量 LLM 调用

特性：
  - Semaphore + RateLimiter 双重限流
  - 429/5xx 自动重试
  - 失败任务单独记录
  - 进度展示
"""
import asyncio, json, time, random, logging
from dataclasses import dataclass
from typing import Any
from openai import AsyncOpenAI, RateLimitError, APIConnectionError, APIError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("batch")

client = AsyncOpenAI(
    api_key="sk-yo-...",
    base_url="https://yotradeapi.com/v1",
    timeout=60.0,
    max_retries=0,   # 自己实现重试
)

# 并发上限 8，RPS 5（保守）
sem = asyncio.Semaphore(8)

class RateLimiter:
    def __init__(self, rate, capacity):
        self.rate, self.capacity = rate, capacity
        self.tokens = capacity
        self.last = time.monotonic()
        self.lock = asyncio.Lock()
    async def acquire(self):
        async with self.lock:
            now = time.monotonic()
            self.tokens = min(self.capacity, self.tokens + (now - self.last) * self.rate)
            self.last = now
            if self.tokens >= 1:
                self.tokens -= 1
                return 0
            return (1 - self.tokens) / self.rate
        await asyncio.sleep(0)

rl = RateLimiter(5, 10)

@dataclass
class Result:
    id: int
    ok: bool
    output: Any = None
    error: str = ""
    elapsed: float = 0

async def call_one(idx: int, text: str) -> Result:
    t0 = time.monotonic()
    for attempt in range(5):
        wait = await rl.acquire()
        if wait > 0:
            await asyncio.sleep(wait)
            continue
        async with sem:
            try:
                resp = await client.chat.completions.create(
                    model="claude-haiku-4-5",
                    messages=[{"role": "user", "content": text}],
                    max_tokens=200,
                )
                return Result(idx, True, resp.choices[0].message.content,
                              elapsed=time.monotonic() - t0)
            except RateLimitError:
                await asyncio.sleep(2 ** attempt + random.random())
            except APIConnectionError:
                await asyncio.sleep(2 ** attempt)
            except APIError as e:
                if 500 <= getattr(e, "status_code", 0) < 600:
                    await asyncio.sleep(2 ** attempt)
                else:
                    return Result(idx, False, error=f"api_{e.status_code}: {e}",
                                  elapsed=time.monotonic() - t0)
    return Result(idx, False, error="max_retries", elapsed=time.monotonic() - t0)

async def main(inputs: list[str]):
    tasks = [call_one(i, t) for i, t in enumerate(inputs)]
    results = []
    for fut in asyncio.as_completed(tasks):
        r = await fut
        results.append(r)
        ok_n = sum(1 for x in results if x.ok)
        log.info(f"progress: {len(results)}/{len(tasks)} ok={ok_n}")
    return results

if __name__ == "__main__":
    inputs = [f"分类这段：example {i}" for i in range(100)]
    t0 = time.monotonic()
    results = asyncio.run(main(inputs))
    log.info(f"total: {time.monotonic() - t0:.1f}s")
    with open("results.jsonl", "w") as f:
        for r in results:
            f.write(json.dumps(r.__dict__, ensure_ascii=False) + "\n")
```

## 六、监控与可观测性

加上 prometheus / openmetrics：

```python
from prometheus_client import Counter, Histogram, start_http_server

req_total = Counter("llm_req_total", "Total requests", ["status"])
req_latency = Histogram("llm_req_latency_seconds", "Request latency")

async def call_one(...):
    with req_latency.time():
        try:
            ...
            req_total.labels(status="ok").inc()
        except Exception:
            req_total.labels(status="error").inc()
            raise

start_http_server(9090)
```

跑起来后用 grafana 看 QPS / 错误率 / p95 延迟，非常清晰。

## 七、避坑提醒

1. **不要用 `requests`**：它是同步的，再多 thread 也不如 asyncio + httpx/aiohttp
2. **不要把单次 timeout 设太短**：流式响应 + 长 prompt 容易超时
3. **不要忽略 token 维度限流**：除了 RPM 还有 TPM。Haiku 一个请求几百 token，Opus 可能几万
4. **不要每次都 new client**：复用 client 避免连接池重建
5. **不要存全部结果到内存**：超过 10k 条直接流式写文件

## 八、相关阅读

- [OpenAI SDK base_url 国内配置实战](/blog/openai-sdk-base-url-cn/)
- [AI API 中转稳定性测试方法](/blog/ai-api-relay-stability-test/)
- [AI API 中转常见错误码排查手册](/blog/ai-api-relay-error-codes/)
- [流式 SSE 故障排查](/blog/streaming-sse-troubleshooting/)

需要带 RPM/TPM 监控、独立 Key 限频的中转？[YoTradeApi](https://yotradeapi.com) 后台可见每个 Key 的实时用量与限频状态。
