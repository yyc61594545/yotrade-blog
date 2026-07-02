---
title: LLM 429 响应中 Retry-After 头的正确处理
description: 详解 LLM API 429 响应里 Retry-After 头的格式差异、常见解析错误、与指数退避的优先级关系，附生产可用的正确处理代码。
keywords:
  - retry-after 头处理
  - llm 429 重试
  - http retry-after 格式
  - api 限速 retry-after
  - 429 响应头解析
pubDate: '2026-07-02'
updatedDate: '2026-07-02'
canonical: https://blog.yotradeapi.com/blog/llm-429-retry-after-header/
tags:
  - Rate Limit
  - API
  - 工程实践
  - 故障排查
category: 技术深度
heroImage: ../../assets/blog-placeholder-2.jpg
---

大部分团队处理 429 时只做了一件事：指数退避 + 抖动。这没错，但漏了一个更直接、更准确的信号——**响应头里的 `Retry-After`**。服务端已经告诉你该等多久了，客户端却还在自己猜，猜错了要么等太久浪费吞吐，要么等太短继续触发限速。本文只讲 `Retry-After` 这一个头怎么正确解析和使用，通用的重试策略架构参考 [LLM API 错误重试策略设计](/blog/llm-error-retry-strategy/)，限速机制的整体讲解参考 [LLM API 限速处理完整指南](/blog/llm-rate-limit-handling/)，这里不重复。

## 一、Retry-After 头的两种格式，很多客户端只处理了一种

`Retry-After` 是标准 HTTP 头（RFC 9110），但它的取值格式有两种，很多手写的解析逻辑只覆盖了其中一种就上线了：

```
# 格式一：整数秒数（最常见）
Retry-After: 30

# 格式二：HTTP-date（相对少见，但规范允许）
Retry-After: Wed, 21 Oct 2026 07:28:00 GMT
```

如果解析逻辑写成 `int(response.headers["Retry-After"])`，遇到格式二会直接抛异常，导致重试逻辑整体失败，甚至比不处理 `Retry-After` 更糟——因为异常可能被上层 catch 成"不可重试"，请求直接失败返回用户。

正确的解析要同时处理两种格式：

```python
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

def parse_retry_after(header_value: str) -> float | None:
    """解析 Retry-After 头，返回需要等待的秒数"""
    if not header_value:
        return None

    header_value = header_value.strip()

    # 格式一：纯数字秒数
    if header_value.isdigit():
        return float(header_value)

    # 格式二：HTTP-date
    try:
        target_time = parsedate_to_datetime(header_value)
        if target_time.tzinfo is None:
            target_time = target_time.replace(tzinfo=timezone.utc)
        delta = (target_time - datetime.now(timezone.utc)).total_seconds()
        return max(delta, 0)
    except (TypeError, ValueError):
        return None
```

## 二、不同厂商的实际行为差异

| 厂商 | 是否返回 Retry-After | 常见取值范围 | 备注 |
| --- | --- | --- | --- |
| Anthropic | 通常返回 | 数秒到数十秒不等 | 与 RPM/TPM 哪个维度触发限速有关，具体以实际响应头为准 |
| OpenAI | 通常返回 | 数秒到数十秒不等 | 部分历史版本 API 在某些错误码下不带这个头，需要有 fallback |
| 部分中转/代理服务 | 视具体实现而定 | 不定 | 中转层如果没有透传原始响应头，客户端会拿不到这个信号，需要单独确认 |

**关键结论**：不能假设这个头一定存在。生产代码必须处理"头缺失"的情况，而不是假设它总会返回，否则一旦某次响应恰好没带这个头，重试逻辑会因为 `None` 值处理不当而崩溃。

## 三、Retry-After 存在时，应该优先于指数退避，而不是叠加

一个常见的设计错误：把 `Retry-After` 的等待时间和指数退避的等待时间**相加**，或者取两者较大值再额外加抖动。这会导致等待时间远超服务端实际需要的恢复时间，白白浪费吞吐。

正确的优先级关系：

```
如果响应带 Retry-After → 直接用这个值作为等待时间（可以加小幅抖动避免雷群，但不要再叠加指数退避的计算结果）
如果响应不带 Retry-After → 退化到指数退避 + 抖动的通用策略
```

```python
import random
import time

def wait_before_retry(attempt: int, retry_after_header: str | None) -> float:
    parsed = parse_retry_after(retry_after_header) if retry_after_header else None

    if parsed is not None:
        # 服务端给了明确信号，直接用，只加小幅抖动防止雷群效应
        jitter = random.uniform(0, min(parsed * 0.1, 2))
        return parsed + jitter

    # 没有 Retry-After，退化到指数退避
    base = min(2 ** attempt, 60)
    return base + random.uniform(0, base * 0.3)
```

## 四、一个容易被忽略的边界：Retry-After: 0 或负数

极少数情况下会遇到 `Retry-After: 0`，或者因为客户端时钟偏移导致 HTTP-date 格式解析出负数。这种情况**不代表可以立即重试**，通常意味着：

- 限速窗口刚好在这一刻重置，但下一个请求仍可能撞上刚重置的窗口边界
- 客户端本地时钟与服务端存在偏差，HTTP-date 格式解析出的差值不可靠

处理方式：设置一个最小等待下限（比如 1 秒），不要完全信任解析出的 0 或负值直接触发零延迟重试：

```python
def wait_before_retry(attempt: int, retry_after_header: str | None) -> float:
    parsed = parse_retry_after(retry_after_header) if retry_after_header else None

    if parsed is not None:
        parsed = max(parsed, 1.0)  # 最小等待下限，防止 0/负数导致的立即重试风暴
        jitter = random.uniform(0, min(parsed * 0.1, 2))
        return parsed + jitter

    base = min(2 ** attempt, 60)
    return base + random.uniform(0, base * 0.3)
```

## 五、并发场景下的额外考量：不要只在单个请求维度处理

如果你的应用是并发发起多个请求（比如批量处理任务），单个请求收到 `Retry-After: 20` 之后，**同一批次里其他还没发出的请求也应该感知这个信号**，而不是各自独立地重试、各自撞上同一个限速窗口。

一个简化的共享等待机制：

```python
import threading
import time

class RetryAfterGate:
    """跨请求共享 Retry-After 信号，避免并发请求各自撞限速"""

    def __init__(self):
        self._lock = threading.Lock()
        self._resume_at = 0.0

    def report_retry_after(self, seconds: float):
        with self._lock:
            self._resume_at = max(self._resume_at, time.monotonic() + seconds)

    def wait_if_needed(self):
        with self._lock:
            resume_at = self._resume_at
        remaining = resume_at - time.monotonic()
        if remaining > 0:
            time.sleep(remaining)
```

这样，批量任务里第一个撞上 429 的请求上报等待时间后，其余还未发出的请求会先检查这个共享 gate，避免大家在同一个限速窗口里反复试错。

## 六、验证清单

上线前建议逐条确认：

1. Retry-After 解析是否同时处理整数秒和 HTTP-date 两种格式
2. Retry-After 缺失时是否有 fallback 到指数退避，而不是抛异常
3. Retry-After 存在时是否作为优先信号使用，而不是和指数退避叠加
4. 是否设置了最小等待下限，防止 0/负数导致的重试风暴
5. 并发场景下是否有跨请求共享的等待机制，避免同批请求反复撞同一个限速窗口
6. 如果经过中转/代理服务，是否确认过对方透传了原始 Retry-After 头

## 七、相关阅读

- [LLM API 错误重试策略设计](/blog/llm-error-retry-strategy/)
- [LLM API 限速（Rate Limit）处理完整指南](/blog/llm-rate-limit-handling/)
- [Streaming SSE 故障排查](/blog/streaming-sse-troubleshooting/)
- [Python 异步 LLM 客户端设计](/blog/python-async-llm-client/)

如果你的应用经常在多个模型/多个 Key 之间切换来规避限速，[YoTradeApi](https://yotradeapi.com) 提供统一中转和账号级限速管理，减少手写多套 Retry-After 处理逻辑的维护成本。
