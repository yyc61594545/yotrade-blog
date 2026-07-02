---
title: LLM 输出验证：schema + 业务规则双层防护
description: 讲清楚为什么 JSON Schema 校验通过不等于输出可信，如何设计 schema 层 + 业务规则层的双层验证体系，附 Pydantic 实现与常见漏检案例。
keywords:
  - llm 输出验证
  - schema 校验 llm
  - 业务规则验证 ai
  - pydantic 双层校验
  - llm 输出可信度
pubDate: '2026-07-02'
updatedDate: '2026-07-02'
canonical: https://blog.yotradeapi.com/blog/llm-output-validation/
tags:
  - 结构化输出
  - 工程实践
  - 数据校验
  - 应用工程
category: 应用工程
heroImage: ../../assets/blog-placeholder-5.jpg
---

很多团队踩过这个坑：接入 Structured Outputs 或 Tool Use 之后，觉得"JSON Schema 校验通过 = 输出可信"，直接把结果写库或调下游接口，结果上线不久就出现"格式完全合法但内容离谱"的输出——金额是负数、日期在未来几十年、引用了一个不存在的用户 ID。本文不讲怎么让模型输出结构化 JSON（这部分参考 [LLM 结构化输出完全指南](/blog/structured-output-llm-guide/) 和 [OpenAI Structured Outputs vs tool_choice 选型指南](/blog/openai-structured-outputs-vs-tool/)），只讲拿到结构化输出之后，**怎么验证它是不是真的可信**。

## 一、为什么 Schema 校验通过不等于输出可信

Schema 校验回答的问题是"这个 JSON 长得对不对"——字段类型对不对、必填项在不在、枚举值合不合法。它回答不了的问题是"这个 JSON 里的内容是不是符合业务事实"。

一个具体例子：让模型从一段客服对话里抽取退款申请，schema 定义如下：

```json
{
  "type": "object",
  "properties": {
    "order_id": {"type": "string"},
    "refund_amount": {"type": "number"},
    "reason": {"type": "string"}
  },
  "required": ["order_id", "refund_amount", "reason"]
}
```

模型输出：

```json
{
  "order_id": "ORD-88812",
  "refund_amount": 15000,
  "reason": "商品质量问题"
}
```

这个 JSON **完全通过 schema 校验**——类型对、必填项齐全。但如果这笔订单实际金额只有 150 元，`refund_amount: 15000` 是模型的数值幻觉（很可能是把商品单价和数量搞混、或者单位搞错了 100 倍），schema 层完全抓不出这个问题。这就是为什么需要第二层——**业务规则验证**。

## 二、双层验证的分工

| 层级 | 回答的问题 | 典型实现 |
| --- | --- | --- |
| Schema 层 | 格式对不对 | JSON Schema / Pydantic / Zod |
| 业务规则层 | 内容合不合理 | 自定义校验函数，通常需要查询业务系统做交叉验证 |

两层缺一不可：只做 schema 层，拦不住"格式对、内容错"的输出；只做业务规则层没有 schema 层兜底，连基本的类型错误都要在业务代码里手写判断，维护成本高且容易漏。

## 三、Schema 层：用 Pydantic 做第一道关

Schema 层除了基本类型，还应该尽量把能表达的约束都写进去，减少留给业务规则层的工作量：

```python
from pydantic import BaseModel, Field, field_validator
from datetime import date

class RefundRequest(BaseModel):
    order_id: str = Field(pattern=r"^ORD-\d{5,}$")
    refund_amount: float = Field(gt=0, le=100000)  # 业务已知的绝对上限
    reason: str = Field(min_length=2, max_length=200)
    request_date: date

    @field_validator("request_date")
    @classmethod
    def not_future_date(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("退款申请日期不能是未来")
        return v
```

这一层能拦住的是**不需要查询外部数据就能判断的问题**：金额超出绝对合理范围、日期格式错误或逻辑上不可能（未来日期）、订单号格式不符合业务规则。

## 四、业务规则层：必须查询业务系统做交叉验证

Schema 层再严格，也拦不住"order_id 格式对，但这个订单根本不存在"或者"退款金额格式对，但超过了这笔订单的实付金额"这类问题。这些校验**必须查询业务系统的真实数据**才能做：

```python
class BusinessRuleError(Exception):
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message

def validate_refund_business_rules(refund: RefundRequest) -> list[BusinessRuleError]:
    errors = []

    order = order_service.get_order(refund.order_id)
    if order is None:
        errors.append(BusinessRuleError("order_id", f"订单 {refund.order_id} 不存在"))
        return errors  # 订单都不存在，后续校验没有意义，提前返回

    if refund.refund_amount > order.paid_amount:
        errors.append(BusinessRuleError(
            "refund_amount",
            f"退款金额 {refund.refund_amount} 超过实付金额 {order.paid_amount}"
        ))

    if order.status not in ("completed", "shipped"):
        errors.append(BusinessRuleError(
            "order_id",
            f"订单状态为 {order.status}，不满足退款条件"
        ))

    existing_refund = refund_service.get_pending_refund(refund.order_id)
    if existing_refund is not None:
        errors.append(BusinessRuleError(
            "order_id",
            f"订单已存在待处理退款申请 {existing_refund.id}，避免重复提交"
        ))

    return errors
```

这一步的核心是：**凡是模型可能"看似合理地编造"的字段，只要能用业务系统的真实数据核对，就必须核对**，不能因为 schema 已经校验通过就跳过。

## 五、两层怎么串起来：验证流水线设计

```python
def process_llm_extraction(raw_json: dict) -> RefundRequest:
    try:
        refund = RefundRequest.model_validate(raw_json)
    except PydanticValidationError as e:
        log_extraction_failure("schema_validation_failed", raw_json, e)
        raise

    business_errors = validate_refund_business_rules(refund)
    if business_errors:
        log_extraction_failure("business_rule_failed", raw_json, business_errors)
        raise BusinessValidationError(business_errors)

    return refund
```

**两层验证的失败要分开记录日志**。Schema 层失败通常意味着 prompt 或 schema 设计有问题（模型持续输出格式错误的内容），业务规则层失败更可能是模型的语义幻觉（内容看似合理但和事实不符）。把两类失败分开统计，能更快定位问题出在 prompt 工程还是模型能力上。

## 六、容易被漏掉的业务规则类型

实践中总结下来，容易被遗漏、但恰恰是模型最容易出错的几类业务规则：

1. **跨字段一致性**：比如"结束日期必须晚于开始日期"，schema 层单独校验每个字段都合法，但字段之间的关系需要业务规则层处理
2. **引用完整性**：输出里引用的 ID（用户 ID、订单 ID、商品 ID）是否真实存在，这是模型幻觉最常见的重灾区
3. **数值量级合理性**：金额、数量类字段容易出现"少一个零"或"多一个零"的量级错误，单纯的 min/max 范围校验能拦住极端值，但拦不住"格式对、量级错一个数量级"的情况——这种情况建议结合历史数据做统计异常检测，而不只是硬编码上下限
4. **状态机合法性**：比如订单状态从"已完成"直接跳到"待支付"这种不可能的状态流转，需要业务层的状态机规则来判断

## 七、验证失败后的处理策略

验证不通过不代表直接拒绝，可以按严重程度分级处理：

| 失败类型 | 处理策略 |
| --- | --- |
| Schema 层失败（格式错误） | 直接拒绝，记录日志用于优化 prompt |
| 业务规则严重违反（订单不存在、状态非法） | 拒绝，转人工审核 |
| 业务规则轻微异常（金额略超历史均值但未超硬上限） | 放行但标记，用于后续抽样审计 |

不是所有业务规则失败都要一刀切拒绝，过于严格会导致大量正常请求被误拦，需要结合具体业务的风险容忍度分级处理。

## 八、相关阅读

- [LLM 结构化输出完全指南（JSON Schema / Function Call）](/blog/structured-output-llm-guide/)
- [OpenAI Structured Outputs vs tool_choice 选型指南](/blog/openai-structured-outputs-vs-tool/)
- [Claude Tool Use 最佳实践与陷阱](/blog/claude-tool-use-best-practices/)
- [LLM Agent 评估方法论](/blog/llm-agent-evaluation-methods/)
- [Claude vs GPT 工具调用准确率对比](/blog/claude-vs-gpt-tool-use-accuracy/)

需要同时对比多个模型在结构化抽取任务上的表现，找到幻觉率最低的那个？[YoTradeApi](https://yotradeapi.com) 一个 Key 接入全系模型，方便跑离线批量验证对比。
