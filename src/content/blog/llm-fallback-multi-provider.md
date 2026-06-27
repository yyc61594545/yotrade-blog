---
title: LLM 多提供商 fallback 路由设计
description: 深入解析如何设计健壮的 LLM 多提供商 fallback 路由，覆盖熔断、重试、权重调度与成本控制，让 AI 应用始终高可用。
keywords:
  - LLM fallback 路由
  - 多提供商 AI 路由
  - LLM 高可用设计
  - AI API 熔断策略
  - 多模型负载均衡
  - LLM 故障转移
pubDate: '2026-06-27'
updatedDate: '2026-06-27'
canonical: https://blog.yotradeapi.com/blog/llm-fallback-multi-provider/
tags:
  - LLM
  - fallback
  - 应用工程
  - 高可用
category: 应用工程
heroImage: ../../assets/blog-placeholder-1.jpg
---

单一 AI 提供商出故障，你的产品就宕了——这是许多开发者踩过的坑。设计好多提供商 fallback 路由，是生产级 LLM 应用不可绕过的一环。本文从实战角度讲清楚：为什么要 fallback、怎么选策略、代码骨架长什么样，以及如何控制成本。

## 一、为什么单提供商是风险点

OpenAI 在 2023–2025 年发生过多次数小时级别的服务降级；Anthropic Claude 的 API 在流量高峰也会限速；Gemini 在部分地区有网络抖动。任何一家都不保证 99.99% SLA。

如果你的产品只接一家提供商，一旦对方故障，影响链条是：

- 用户侧：请求超时、报错
- 业务侧：流水、订单受损
- 运维侧：紧急切换，手动改配置

而多提供商 fallback 的目标，就是**在用户无感知的情况下自动完成这一切换**。

## 二、路由策略全景

常见策略不止一种，按决策维度分类：

| 策略 | 决策依据 | 适用场景 |
|------|----------|----------|
| 主备（Primary/Backup） | 固定优先级 | 对主力模型有强依赖，备用仅保底 |
| 轮询（Round-Robin） | 请求序号 | 多个等价提供商，均摊流量 |
| 权重轮询（Weighted RR） | 静态权重 | 不同提供商速度/成本差异大 |
| 最低延迟（Latency-based） | 实时 RTT 测量 | 对响应时间敏感的交互应用 |
| 成本优先（Cost-first） | token 单价 | 对精度要求中等、预算敏感的场景 |
| 健康感知（Health-aware） | 熔断状态 + 错误率 | 生产级高可用，推荐默认选项 |

实际项目里最常用的是**主备 + 健康感知熔断**的组合：平时用主力（通常是最高精度的），出问题自动切备用（成本可控的）。

## 三、熔断器（Circuit Breaker）是核心

fallback 不等于简单重试。如果主力提供商已经完全宕机，每个请求都先打过去等超时再切换，会引入巨大延迟（每次多 5–30 秒）。

熔断器解决的就是这个问题，它有三个状态：

```
CLOSED ──(错误率 > 阈值)──→ OPEN
  ↑                             │
  └──(半开探测成功)── HALF_OPEN ←┘
```

- **CLOSED（关闭）**：正常通行，统计错误率
- **OPEN（断开）**：直接返回 fallback，不再打主力
- **HALF_OPEN（半开）**：允许少量探测请求，成功则恢复 CLOSED

Python 实现骨架：

```python
import time
import threading
from enum import Enum

class State(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._state = State.CLOSED
        self._failure_count = 0
        self._last_failure_time = None
        self._lock = threading.Lock()

    @property
    def state(self):
        with self._lock:
            if self._state == State.OPEN:
                if time.time() - self._last_failure_time > self.recovery_timeout:
                    self._state = State.HALF_OPEN
            return self._state

    def record_success(self):
        with self._lock:
            self._failure_count = 0
            self._state = State.CLOSED

    def record_failure(self):
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._failure_count >= self.failure_threshold:
                self._state = State.OPEN
```

## 四、多提供商路由器完整设计

将熔断器组合进多提供商路由器：

```python
import asyncio
from dataclasses import dataclass
from typing import Callable, Any

@dataclass
class Provider:
    name: str
    call_fn: Callable          # 实际调用该提供商的异步函数
    weight: float = 1.0        # 权重（用于权重轮询）
    breaker: CircuitBreaker = None

    def __post_init__(self):
        if self.breaker is None:
            self.breaker = CircuitBreaker()

class MultiProviderRouter:
    def __init__(self, providers: list[Provider]):
        self.providers = providers

    def _available_providers(self):
        """返回当前熔断状态允许使用的提供商列表"""
        return [
            p for p in self.providers
            if p.breaker.state in (State.CLOSED, State.HALF_OPEN)
        ]

    async def call(self, prompt: str, **kwargs) -> Any:
        candidates = self._available_providers()
        if not candidates:
            raise RuntimeError("所有提供商均不可用（全部熔断）")

        last_error = None
        for provider in candidates:
            try:
                result = await asyncio.wait_for(
                    provider.call_fn(prompt, **kwargs),
                    timeout=30,
                )
                provider.breaker.record_success()
                return result
            except Exception as e:
                provider.breaker.record_failure()
                last_error = e
                continue  # 自动 fallback 到下一个

        raise RuntimeError(f"所有可用提供商均失败，最后错误: {last_error}")
```

使用示例：

```python
router = MultiProviderRouter([
    Provider(name="claude",  call_fn=call_claude,  weight=3.0),
    Provider(name="openai",  call_fn=call_openai,  weight=2.0),
    Provider(name="gemini",  call_fn=call_gemini,  weight=1.0),
])

response = await router.call("请帮我总结以下内容：...")
```

## 五、错误分类：哪些应该 fallback，哪些不该

不是所有错误都值得 fallback。乱 fallback 会浪费 token 并产生不一致输出。

| 错误类型 | HTTP 状态 | 应对 |
|----------|-----------|------|
| 限速（Rate Limit） | 429 | 等待后重试（同一提供商） |
| 服务器错误 | 500/503 | 立即 fallback |
| 网络超时 | timeout | 短暂重试，超次数再 fallback |
| 认证失败 | 401/403 | 告警，不 fallback（配置问题） |
| 内容过滤 | 400（内容原因） | 不 fallback（输入问题） |
| 上下文超长 | 400（token 原因） | 截断后重试，不 fallback |

代码层面，根据异常类型分流：

```python
async def smart_fallback_call(provider, prompt, **kwargs):
    try:
        return await provider.call_fn(prompt, **kwargs)
    except RateLimitError:
        await asyncio.sleep(2)
        return await provider.call_fn(prompt, **kwargs)  # 同提供商重试
    except (ServerError, TimeoutError):
        raise  # 向上传播，触发 fallback
    except AuthError:
        raise RuntimeError("认证配置错误，请检查 API Key")
    except ContentFilterError:
        raise  # 输入问题，不 fallback
```

## 六、成本控制：fallback 不能变成"烧钱黑洞"

多提供商 fallback 如果不设上限，某些场景下成本会失控：

**场景**：主力提供商限速，每次请求先在主力等 2 秒超时，再 fallback 到备用——备用价格是主力的 3 倍，且流量全打过去。

避免方式：

1. **设置每日/每小时 fallback 预算上限**，超出后直接拒绝而非继续 fallback
2. **区分 fallback 等级**：一级备用（中等成本）、二级备用（高成本但高可靠）
3. **记录每次 fallback 触发原因**，用于事后分析和主力提供商的评估

```python
class BudgetAwareRouter(MultiProviderRouter):
    def __init__(self, providers, hourly_fallback_budget_usd=5.0):
        super().__init__(providers)
        self._fallback_cost = 0.0
        self._budget = hourly_fallback_budget_usd
        self._window_start = time.time()

    def _check_budget(self, estimated_cost):
        now = time.time()
        if now - self._window_start > 3600:  # 窗口重置
            self._fallback_cost = 0.0
            self._window_start = now
        if self._fallback_cost + estimated_cost > self._budget:
            raise RuntimeError("fallback 预算已用尽，等待窗口重置")
        self._fallback_cost += estimated_cost
```

## 七、可观测性：没有监控的 fallback 等于盲飞

fallback 路由上线后，必须配套监控，否则你不知道它是否在正常工作。

最小监控集合：

```python
import logging
from prometheus_client import Counter, Histogram

FALLBACK_COUNTER = Counter(
    'llm_fallback_total',
    '触发 fallback 的次数',
    ['from_provider', 'to_provider', 'reason']
)

REQUEST_LATENCY = Histogram(
    'llm_request_latency_seconds',
    '请求延迟',
    ['provider', 'status']
)

# 在 router 里埋点
FALLBACK_COUNTER.labels(
    from_provider=failed_provider.name,
    to_provider=next_provider.name,
    reason=type(last_error).__name__
).inc()
```

告警阈值建议：

- 某提供商 fallback 率 > 20%：发出警告
- 全部提供商同时 OPEN（全熔断）：立即告警
- 单次请求总延迟 > 60 秒（含重试）：记录日志，异步告警

## 八、实战建议：从简单开始

不要第一天就把全部策略都堆上去。按阶段演进：

**阶段一（MVP）**：主备，手动配置，靠运维切换  
**阶段二（自动化）**：加熔断器，自动切换，基础日志  
**阶段三（成熟）**：权重路由 + 成本控制 + Prometheus + 告警  
**阶段四（高级）**：延迟感知路由 + A/B 路由 + 自动成本优化

大多数中小型项目，阶段二就够用了。阶段三是面向规模超过日均百万次调用的场景。

如果你不想自己维护这套基础设施，使用支持多模型路由的 API 中转服务是更省力的选择——中转服务层已内置 fallback 逻辑，你只需要配置优先级即可。相关对比可参考[AI API 中转 vs 自建 VPN 方案](/blog/ai-api-relay-vs-self-vpn/)。

## 相关阅读

- [LLM 错误重试策略：指数退避与限速处理](/blog/llm-error-retry-strategy/)
- [AI 中间件 fallback 设计模式](/blog/ai-agent-fallback-design/)
- [多模型成本路由实战](/blog/multi-model-cost-routing/)
- [AI API 中转 vs 自建 VPN 方案](/blog/ai-api-relay-vs-self-vpn/)
- [AI API 中转稳定性测试](/blog/ai-api-relay-stability-test/)

需要开箱即用的多提供商路由能力，[YoTradeApi](https://yotradeapi.com) 已内置主备切换和熔断逻辑，无需自行维护路由基础设施。
