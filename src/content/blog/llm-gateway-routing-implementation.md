---
title: 自建 LLM 网关的路由实现：从零设计转发逻辑
description: 从工程实现角度拆解自建 LLM 网关的路由层设计，包括路由规则匹配、健康检查、故障转移与负载均衡的具体代码思路。
keywords:
  - LLM 网关路由
  - API 网关路由实现
  - 故障转移设计
  - 负载均衡算法
  - 自建 API 网关
pubDate: '2026-08-24'
updatedDate: '2026-08-24'
canonical: https://blog.yotradeapi.com/blog/llm-gateway-routing-implementation/
tags:
  - LLM 网关
  - 系统设计
  - 工程实战
  - API管理
category: 工程实战
heroImage: ../../assets/blog-placeholder-1.jpg
---

如果团队规模不大，用 [LiteLLM 自部署一个网关](/blog/litellm-cn-gateway-self-host/) 通常是更省事的选择。但当业务有特殊需求——比如自定义计费规则、和内部权限系统深度集成、或者需要针对特定协议做转换——自己动手写路由层就成了绕不开的选项。本文不讲"该不该自建"，只聚焦一件事：**路由层具体怎么实现**。

## 一、路由层要解决的核心问题

一个 LLM 网关的路由层，本质上是在做一件事：**根据请求特征，决定把它发到哪个上游，以及上游不可用时怎么办**。拆开来看，需要处理四类问题：

1. **匹配**：请求应该走哪条路由规则（按模型名、按 API Key、按路径前缀）
2. **选择**：如果一条规则对应多个上游，选哪一个（负载均衡）
3. **健康**：怎么知道某个上游是不是出问题了
4. **降级**：上游失败后，是重试、切换备用上游，还是直接返回错误

这四类问题在实现上是分层的，混在一起写会导致代码难以维护。

## 二、路由规则匹配：配置驱动而不是硬编码

新手最容易犯的错误是把路由逻辑写成一堆 `if-else`。更可维护的做法是用配置文件描述规则，路由引擎只负责匹配和执行：

```yaml
routes:
  - match:
      model: "claude-*"
    upstreams:
      - name: anthropic-primary
        weight: 70
      - name: anthropic-backup
        weight: 30
    fallback: openai-compatible-claude

  - match:
      model: "gpt-*"
      header:
        x-team: "growth"
    upstreams:
      - name: openai-direct
    fallback: null
```

匹配逻辑的实现要点：

- **规则按优先级排序**：更具体的规则（带 header 条件的）应该排在更泛化的规则（只匹配 model 前缀的）前面
- **单次遍历，短路返回**：第一条命中的规则立即生效，不要遍历完所有规则再决策
- **未匹配到规则要有默认行为**：明确返回 404 还是走兜底上游，不要让请求静默丢失

```python
def match_route(request, routes):
    for route in routes:  # 已按优先级排序
        if route.matches(request):
            return route
    return default_route  # 显式兜底，而不是 None
```

## 三、负载均衡：三种策略的取舍

| 策略 | 实现复杂度 | 适用场景 |
|------|----------|---------|
| 加权轮询（Weighted Round Robin） | 低 | 上游成本/配额已知，按比例分流 |
| 最少连接数（Least Connections） | 中 | 上游响应时间差异大，避免慢上游堆积请求 |
| 一致性哈希（Consistent Hashing） | 高 | 需要同一用户/会话固定命中同一上游（比如有状态缓存） |

对大多数 LLM 网关来说，**加权轮询 + 健康检查剔除**已经够用，没必要一开始就上一致性哈希。加权轮询的核心实现思路：

```python
class WeightedRouter:
    def __init__(self, upstreams):
        # upstreams: [{"name": "a", "weight": 70}, {"name": "b", "weight": 30}]
        self.pool = []
        for u in upstreams:
            self.pool.extend([u["name"]] * u["weight"])

    def pick(self):
        healthy = [u for u in self.pool if is_healthy(u)]
        if not healthy:
            raise NoHealthyUpstreamError()
        return random.choice(healthy)
```

这里有个容易漏掉的细节：**权重池要在健康检查更新后动态过滤**，而不是初始化时算一次就固定不变，否则某个上游挂了之后，请求依然会按原比例打过去。

## 四、健康检查：主动探测 + 被动熔断结合

单靠一种健康检查方式都不够可靠：

- **主动探测**：定时发送轻量请求（比如极短 prompt）到上游，检查延迟和返回码。优点是能提前发现问题，缺点是探测本身有成本，频率不能太高
- **被动熔断**：统计真实请求的失败率，超过阈值自动标记为不健康。优点是零额外成本，缺点是发现问题时已经有真实请求受影响了

推荐组合：被动熔断做**快速反应**（毫秒级发现异常),主动探测做**恢复确认**（熔断后定时用探测请求判断是否可以恢复流量）。

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=30):
        self.failures = 0
        self.state = "closed"  # closed / open / half_open
        self.opened_at = None
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

    def record_failure(self):
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.state = "open"
            self.opened_at = time.time()

    def record_success(self):
        self.failures = 0
        self.state = "closed"

    def allow_request(self):
        if self.state == "open":
            if time.time() - self.opened_at > self.recovery_timeout:
                self.state = "half_open"  # 放一部分流量试探
                return True
            return False
        return True
```

这是标准的熔断器（Circuit Breaker）模式：closed（正常）→ open（熔断，直接拒绝或切换备用）→ half_open（放少量流量试探）→ 恢复 closed 或重新 open。

## 五、故障转移：重试策略要和幂等性绑定

故障转移看似简单——上游 A 失败就切 B——但实际实现中有个关键前提经常被忽略：**只有幂等的请求才能安全重试或转移**。

对 LLM 网关而言：

- 非流式请求：如果上游返回了明确的错误码（超时、5xx），转移到备用上游通常是安全的
- 流式请求：如果已经开始向客户端吐了部分 token，中途上游失败，**不能**无缝切换到另一个上游重新生成——因为已发送的内容对不上新上游的输出，正确做法是直接中断并返回错误，让客户端决定是否重试整个请求
- 幂等性设计可以参考 [LLM API 幂等性设计](/blog/llm-api-idempotency-design/)，网关层的重试逻辑应该和这套设计保持一致

```python
async def route_with_fallback(request, primary, fallback):
    try:
        if request.stream:
            # 流式请求已开始发送后不做透明转移
            async for chunk in call_upstream(primary, request):
                yield chunk
        else:
            return await call_upstream(primary, request)
    except UpstreamError as e:
        if request.stream and e.partial_sent:
            raise  # 已发送部分内容，直接向上抛错，不做转移
        if fallback:
            return await call_upstream(fallback, request)
        raise
```

## 六、可观测性：路由决策必须可追溯

路由层出问题时，最痛苦的排查场景是"不知道这个请求当时被路由到了哪里、为什么"。最小可用的可观测性设计：

- 每个请求记录：命中的路由规则 ID、选中的上游、健康检查状态、是否发生了故障转移
- 关键指标按上游维度拆分：延迟分布、错误率、熔断状态变化次数
- 故障转移发生时打 WARN 级别日志，包含原始上游和转移目标，方便事后复盘

```
[route] req_id=abc123 rule=claude-* upstream=anthropic-primary status=200 latency=820ms
[route] req_id=def456 rule=claude-* upstream=anthropic-primary status=timeout fallback=anthropic-backup
```

## 七、什么时候不值得自建

如果你的路由需求只是"按模型名分流 + 简单故障转移"，用现成的网关方案（LiteLLM、或直接用 [API 中转服务](/blog/what-is-api-relay-explained/)）性价比更高——自建路由层的隐性成本在于**长期维护**：健康检查阈值调优、新上游接入、熔断策略随流量变化调整，这些都需要持续投入。只有当业务有明确的定制化路由需求（比如复杂的计费联动、多租户隔离），自建才划算。

## 八、相关阅读

- [LiteLLM 自部署 LLM 网关完整指南](/blog/litellm-cn-gateway-self-host/)
- [多模型成本智能路由方案](/blog/multi-model-cost-routing/)
- [LLM API 幂等性设计](/blog/llm-api-idempotency-design/)
- [什么是 API 中转，一篇讲清楚](/blog/what-is-api-relay-explained/)
- [AI API 中转稳定性测试方法](/blog/ai-api-relay-stability-test/)

如果不想自己维护路由层和健康检查逻辑，[YoTradeApi](https://yotradeapi.com) 已经内置了多上游负载均衡与故障转移，一个 API 直接接入即可省去这部分工程投入。
