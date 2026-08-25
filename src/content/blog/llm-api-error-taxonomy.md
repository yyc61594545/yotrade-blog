---
title: 多模型 API 错误码分类与统一处理
description: OpenAI、Anthropic、Gemini 错误码体系并不统一，本文给出一套跨厂商的统一错误分类模型与归一化代码实现，减少多模型切换时的错误处理债务。
keywords:
  - 多模型错误处理
  - openai anthropic 错误码对比
  - api 错误统一处理
  - 错误码归一化
  - 多模型网关设计
pubDate: '2026-08-25'
updatedDate: '2026-08-25'
canonical: https://blog.yotradeapi.com/blog/llm-api-error-taxonomy/
tags:
  - 技术深度
  - 错误处理
  - 多模型网关
  - 工程实战
category: 技术深度
heroImage: ../../assets/blog-placeholder-5.jpg
---

同时接入 OpenAI、Anthropic、Gemini 三家 API 的团队都会遇到同一个问题：三家的错误码体系互不相同，同样是"限流"，OpenAI 用 `429` + `rate_limit_exceeded`，Anthropic 用 `429` + `rate_limit_error`，字段名和嵌套结构还都不一样。如果业务代码里散落着 `if provider == "openai": ...elif provider == "anthropic": ...` 这样的分支，每接入一个新模型就要重写一遍错误处理逻辑。本文给出一套统一错误分类模型，把"排查具体错误"的问题（见[《AI API 中转常见错误码排查手册》](/blog/ai-api-relay-error-codes/)）往前推一步，变成"设计层面怎么归一化"。

## 一、三家错误码体系对比

| 场景 | OpenAI | Anthropic | Gemini |
| --- | --- | --- | --- |
| 认证失败 | 401 `invalid_api_key` | 401 `authentication_error` | 401 `UNAUTHENTICATED` |
| 限流 | 429 `rate_limit_exceeded` | 429 `rate_limit_error` | 429 `RESOURCE_EXHAUSTED` |
| 请求格式错误 | 400 `invalid_request_error` | 400 `invalid_request_error` | 400 `INVALID_ARGUMENT` |
| 内容被拒 | 400 `content_policy_violation` | 400 `invalid_request_error`（附 `content_filter` 提示） | 400 `PROHIBITED_CONTENT` |
| 上游过载 | 503 `server_error` | 529 `overloaded_error` | 503 `UNAVAILABLE` |
| 上下文超长 | 400 `context_length_exceeded` | 400 `invalid_request_error`（信息里说明） | 400 `INVALID_ARGUMENT`（信息里说明） |

三个明显的坑：

1. **Anthropic 的 529 是私有状态码**，很多 HTTP 客户端库和网关中间件对非标准状态码处理不一致，需要单独兼容
2. **Gemini 和部分 Anthropic 错误共用同一个粗粒度 code**（如 `invalid_request_error`、`INVALID_ARGUMENT`），真正的错误原因要解析 `message` 文本，无法只靠状态码/错误类型区分
3. **内容过滤的表现形式完全不同**：OpenAI 是独立错误类型，Anthropic 藏在通用错误的 message 里，Gemini 又是独立类型——如果业务需要区分"内容违规"和"其他 400"，三家要写三套解析逻辑

## 二、统一分类模型：按处理策略分类，而不是按厂商语义分类

关键设计原则是：**分类维度应该对应"业务该怎么处理"，而不是照抄厂商的分类**。厂商分类是为了描述错误原因，但业务只关心"要不要重试、要不要降级、要不要告警"。建议归一化为五类：

| 内部分类 | 包含场景 | 处理策略 |
| --- | --- | --- |
| `AUTH_ERROR` | 401/403 全部 | 不重试，立即告警（key 失效是高优先级事故） |
| `RATE_LIMITED` | 429 全部 | 指数退避重试，读 `Retry-After` 头 |
| `TRANSIENT_UPSTREAM` | 5xx、529、超时、连接重置 | 重试 + 可切备用模型 |
| `INVALID_REQUEST` | 400 中的格式错误、参数错误 | 不重试，记录请求体用于排查 |
| `CONTENT_REJECTED` | 内容过滤、政策拒绝 | 不重试，走业务侧的内容处理分支（不是系统故障） |

`INVALID_REQUEST` 和 `CONTENT_REJECTED` 分开是因为处理路径完全不同：前者是代码 bug 或参数错误，需要开发介入；后者是正常业务场景（用户输入触发了内容策略），应该给终端用户友好提示，而不是当成系统错误上报。

## 三、归一化代码实现

以 Python 为例，核心是一个 `normalize_error` 函数，把三家的原始异常/响应转成统一的内部错误对象：

```python
from dataclasses import dataclass
from enum import Enum

class ErrorCategory(Enum):
    AUTH_ERROR = "auth_error"
    RATE_LIMITED = "rate_limited"
    TRANSIENT_UPSTREAM = "transient_upstream"
    INVALID_REQUEST = "invalid_request"
    CONTENT_REJECTED = "content_rejected"

@dataclass
class NormalizedError:
    category: ErrorCategory
    provider: str
    raw_code: str
    retryable: bool
    retry_after: float | None = None

def normalize_error(provider: str, status_code: int, body: dict) -> NormalizedError:
    if provider == "openai":
        err = body.get("error", {})
        code = err.get("code") or err.get("type", "")
        if status_code == 401:
            return NormalizedError(ErrorCategory.AUTH_ERROR, provider, code, False)
        if status_code == 429:
            return NormalizedError(ErrorCategory.RATE_LIMITED, provider, code, True)
        if code == "content_policy_violation":
            return NormalizedError(ErrorCategory.CONTENT_REJECTED, provider, code, False)
        if status_code >= 500:
            return NormalizedError(ErrorCategory.TRANSIENT_UPSTREAM, provider, code, True)
        return NormalizedError(ErrorCategory.INVALID_REQUEST, provider, code, False)

    if provider == "anthropic":
        err = body.get("error", {})
        code = err.get("type", "")
        message = err.get("message", "")
        if status_code == 401:
            return NormalizedError(ErrorCategory.AUTH_ERROR, provider, code, False)
        if status_code == 429:
            return NormalizedError(ErrorCategory.RATE_LIMITED, provider, code, True)
        if status_code in (500, 529):
            return NormalizedError(ErrorCategory.TRANSIENT_UPSTREAM, provider, code, True)
        if "content" in message.lower() and "policy" in message.lower():
            return NormalizedError(ErrorCategory.CONTENT_REJECTED, provider, code, False)
        return NormalizedError(ErrorCategory.INVALID_REQUEST, provider, code, False)

    if provider == "gemini":
        err = body.get("error", {})
        code = err.get("status", "")
        if code == "UNAUTHENTICATED":
            return NormalizedError(ErrorCategory.AUTH_ERROR, provider, code, False)
        if code == "RESOURCE_EXHAUSTED":
            return NormalizedError(ErrorCategory.RATE_LIMITED, provider, code, True)
        if code == "PROHIBITED_CONTENT":
            return NormalizedError(ErrorCategory.CONTENT_REJECTED, provider, code, False)
        if code == "UNAVAILABLE":
            return NormalizedError(ErrorCategory.TRANSIENT_UPSTREAM, provider, code, True)
        return NormalizedError(ErrorCategory.INVALID_REQUEST, provider, code, False)

    raise ValueError(f"unknown provider: {provider}")
```

业务代码只需要面向 `NormalizedError.category` 做分支，新增第四个模型厂商时只需要在 `normalize_error` 里加一个分支，其余代码零改动。

## 四、Anthropic 529 的特殊兼容

529 不是标准 HTTP 状态码，部分反向代理、API 网关（包括一些云厂商的 API Gateway 产品）默认不认识这个状态码，可能会被转换成 502 或直接丢弃 body。如果你的请求经过了多层网关，建议：

- 在最靠近 Anthropic 的那一层做归一化，尽早把 529 转换成内部错误对象，避免它在链路里被中间件篡改
- 如果用的是中转服务，确认其是否原样透传了 529，还是包装成了统一的错误格式——两种做法都合理，但要确认并写进你的错误处理测试用例里

## 五、重试策略与分类的配合

分类之后，重试策略应该按 `retryable` 字段统一处理，而不是每个 provider 各写一套：

```python
import time
import random

def call_with_retry(fn, max_retries=3):
    for attempt in range(max_retries):
        try:
            return fn()
        except NormalizedError as e:
            if not e.retryable or attempt == max_retries - 1:
                raise
            base = e.retry_after or (2 ** attempt)
            time.sleep(base + random.uniform(0, base * 0.3))
    raise RuntimeError("unreachable")
```

指数退避加抖动的具体设计思路，[《AI Agent 错误恢复机制设计》](/blog/ai-agent-error-recovery/)里有更完整的讨论,这里不重复展开。

## 六、相关阅读

- [AI API 中转常见错误码排查手册](/blog/ai-api-relay-error-codes/)
- [AI Agent 错误恢复机制设计：让 Agent 在失败中自我修复](/blog/ai-agent-error-recovery/)
- [AI Agent 降级与容错策略：生产级可靠性设计](/blog/ai-agent-fallback-design/)

如果你的多模型调用走的是中转服务，错误码归一化这一层其实可以直接交给中转层做——[YoTradeApi](https://yotradeapi.com) 对上游错误做了统一格式封装，省去业务代码里维护多套 provider 分支的麻烦。
