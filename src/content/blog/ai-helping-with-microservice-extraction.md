---
title: AI 辅助微服务拆分实战
description: 记录用 AI 辅助将单体应用拆分为微服务的实战过程，包括边界识别、接口设计、数据解耦和迁移策略。
keywords:
  - AI 辅助微服务拆分
  - 单体应用拆分实战
  - 微服务边界识别
  - Claude 代码重构
  - 微服务迁移策略
pubDate: '2026-06-16'
updatedDate: '2026-06-16'
canonical: https://blog.yotradeapi.com/blog/ai-helping-with-microservice-extraction/
tags:
  - 微服务
  - 实战经验
  - AI 编程
  - 架构设计
category: 实战经验
heroImage: ../../assets/blog-placeholder-3.jpg
---

把一个几十万行代码的单体应用拆成微服务，是很多团队在某个时间点都会面对的事。这类工作的难点不在于技术本身，而在于**边界在哪里、拆的顺序怎么定、数据怎么解耦**——这三个判断题，往往需要有人把整个代码库读透才能回答。

AI 在这里能发挥的作用是：**快速读懂代码结构，辅助你做判断**，而不是替你拆服务。把这个边界搞清楚，工作效率差距会很大。

本文记录一次真实的微服务拆分经历，单体是一个 Python/Django 的电商后台，拆分目标是把"订单服务"和"库存服务"独立出来。

---

## 一、准备阶段：让 AI 读懂你的代码库

拆分前，最重要的一步是**建立依赖关系图**。不用 AI 的话，这一步通常要手动画，耗时巨大。

### 让 AI 生成模块依赖报告

把关键文件喂给 Claude，要求输出依赖关系：

```
Prompt：
下面是我们 Django 项目的目录结构和部分 models.py 内容。请：
1. 列出所有模型之间的外键依赖关系（哪个模型引用了哪个）
2. 标出哪些模型是"订单域"、哪些是"库存域"、哪些是"共享域"
3. 指出跨域依赖最重的 3–5 个模型

[附上 models.py、views.py 的关键片段]
```

AI 输出通常是这样的结构化结果：

```
订单域：Order, OrderItem, OrderStatus, Payment
库存域：Product, SKU, Stock, Warehouse, StockMovement
共享域：User, Address, Category

跨域依赖热点：
- OrderItem.product_id → Product（核心依赖，拆分时必须处理）
- Stock 更新在 order_views.py 第 234 行直接写入（反模式，需要重构）
- Payment 里有 inventory_check 调用（错误放置，建议移入订单域）
```

这个报告的质量高度依赖你给的上下文质量。建议把 `models.py`、关键 `views.py`、`signals.py` 都提供出来。

---

## 二、边界识别：最难的判断

微服务拆分最常见的错误是**按技术层拆**（比如把所有数据库操作单独拆一个服务），而不是按**业务能力**拆。AI 在边界判断上可以提供第二视角：

### 利用 AI 做"粘性分析"

把你初步划定的边界告诉 AI，让它找漏洞：

```
Prompt：
我计划把以下模块拆成独立的"订单服务"：Order, OrderItem, OrderStatus, Payment, Invoice

问题：
1. 这个边界有哪些潜在问题？
2. 哪些函数/方法会跨越这个边界？
3. 如果订单服务和库存服务需要通信，你建议用同步 HTTP 还是异步消息队列？
为什么？

[附上当前代码]
```

AI 通常会指出：

- `Invoice` 可能应该是单独的"财务域"，而不是订单域的一部分
- `Payment` 和第三方支付的集成可能需要单独的支付服务
- 订单减库存这个操作需要强一致性，建议使用 Saga 模式而不是简单的消息队列

这些判断不见得全对，但它们是很好的讨论起点，能帮你快速穷举决策树。

---

## 三、数据库解耦：最棘手的技术问题

单体应用的数据库通常是一个大库，所有表共享同一个 schema。微服务拆分后，每个服务要有自己的数据库，这中间有一段"共库→分库"的过渡期。

### AI 生成数据迁移方案

```
Prompt：
当前情况：
- 订单表（orders）和库存表（products, skus, stock）在同一个 PostgreSQL 数据库
- orders 表通过外键直接引用 products 表
- 每次下单都会在同一事务内更新 stock 表

我要把库存服务拆出来，用独立数据库。请给出：
1. 分阶段迁移方案（保证零停机）
2. 如何处理现有的外键约束
3. 数据一致性如何保证（特别是超卖场景）
```

AI 给出的分阶段方案通常类似：

```
阶段 1 - 双写期（2 周）
  - 订单服务继续操作原库，同时通过 HTTP 调用新库存服务的写接口
  - 库存服务读写自己的新数据库
  - 验证两边数据一致性，差异 < 0.1%

阶段 2 - 流量切换（1 周）
  - 订单服务的库存读操作切换到调用库存服务 API
  - 原有直接 DB 读操作保留作 fallback
  - 监控延迟增量（预期 +5–10ms）

阶段 3 - 清理期（1 个月）
  - 删除订单库中的库存相关外键约束
  - 下线双写逻辑
  - 原库存表改为只读归档，3 个月后删除
```

这个三阶段结构是行业通用的，AI 会根据你的具体情况补充细节。

---

## 四、接口设计：让 AI 起草契约

服务边界确定后，需要定义 API 契约。AI 在这里能做的是快速生成初版 OpenAPI 规范，你再审查修改。

```
Prompt：
库存服务需要提供以下能力：
1. 查询 SKU 库存
2. 预扣库存（下单时）
3. 确认扣减（支付成功后）
4. 释放预扣（取消订单时）

请生成这 4 个接口的 OpenAPI 3.0 YAML 规范，包括：
- 请求/响应体 Schema
- 错误码定义（特别是库存不足的场景）
- 幂等性设计（通过 idempotency-key）
```

AI 生成的草稿通常 80% 可用，重点检查：

- 错误码是否覆盖所有业务异常
- 幂等键的粒度是否合理（是按 order_id 还是 order_item_id）
- 批量接口的设计（下单通常涉及多个 SKU）

---

## 五、实际迁移：用 AI 写胶水代码

这一阶段是 AI 价值最直接的地方——写重复性的适配代码。

### 生成 Service Client

```
Prompt：
请根据上面的 OpenAPI 规范，生成 Python 的 InventoryServiceClient 类：
- 使用 httpx 异步客户端
- 包含重试逻辑（最多 3 次，指数退避）
- 超时设置：连接超时 3s，读超时 10s
- 错误要转成项目统一的 ServiceException 体系
- 包含完整的类型注解
```

```python
# AI 生成的客户端示例（需要人工审查和调整）
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

class InventoryServiceClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=httpx.Timeout(connect=3.0, read=10.0, write=5.0, pool=2.0),
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    async def reserve_stock(
        self,
        order_id: str,
        items: list[dict],
        idempotency_key: str,
    ) -> dict:
        response = await self.client.post(
            "/v1/stock/reserve",
            json={"order_id": order_id, "items": items},
            headers={"Idempotency-Key": idempotency_key},
        )
        if response.status_code == 409:
            raise InsufficientStockError(response.json()["message"])
        response.raise_for_status()
        return response.json()
```

---

## 六、常见踩坑与经验

**坑 1：AI 给的拆分建议过于"教科书"**

AI 读到一个大单体，往往会建议拆 10+ 个微服务。这在书上看起来漂亮，但对一个 5 人团队来说是灾难。要明确告诉 AI 你的团队规模和运维能力，让它调整建议。

**坑 2：跨服务事务的低估**

AI 通常会建议用 Saga 模式处理分布式事务，但 Saga 的实现复杂度远超预期。拆分前要评估有多少操作需要跨服务强一致性——如果超过 30%，拆分的收益可能不如预期。

**坑 3：忽视非功能性需求的变化**

单体里，调用一个函数的延迟是纳秒级的；微服务里，一次 HTTP 调用至少 5–10ms。AI 帮你设计接口时，记得提醒它考虑调用链的累积延迟。

**坑 4：测试覆盖率下降**

拆分后，原有的集成测试大部分失效。AI 可以帮你快速生成契约测试（Contract Testing），用 Pact 等框架验证服务间接口的兼容性。

---

## 七、AI 在不同阶段的价值评估

| 阶段 | AI 价值 | 人工不可替代的部分 |
|------|---------|-----------------|
| 依赖分析 | 高（省去大量手动读代码） | 最终业务决策 |
| 边界识别 | 中（提供第二视角） | 对业务发展方向的判断 |
| 数据解耦方案 | 中（方案框架正确，细节需调整） | 具体一致性保证的取舍 |
| 接口设计 | 高（快速生成初稿） | 幂等性、错误码的业务含义 |
| 胶水代码编写 | 高（直接可用率 70–80%） | 错误处理的具体策略 |
| 迁移验证 | 低（AI 无法运行代码） | 全量由人工测试 |

---

## 八、相关阅读

- [AI 辅助重构遗留单体应用实战](/blog/ai-refactor-legacy-monolith/)
- [AI 辅助代码重构模式与实践](/blog/ai-refactoring-patterns/)
- [用 Aider 重构 Legacy Python 项目实录](/blog/legacy-python-refactor-with-aider/)
- [AI 编程工具团队落地经验](/blog/ai-coding-team-adoption/)
- [AI 辅助微服务拆分后，接口调用成本可能上升——合理使用](/blog/llm-cost-optimization-checklist/)

大规模重构中需要频繁调用 Claude 或 GPT-4o 分析代码，[YoTradeApi](https://yotradeapi.com) 提供稳定的 API 中转和人民币计费，让你专注于架构决策而不是网络和账单问题。
