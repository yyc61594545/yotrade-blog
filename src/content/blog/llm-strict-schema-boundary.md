---
title: 严格模式结构化输出的能力边界：它保证什么、不保证什么
description: strict 模式能保证 JSON 一定符合 Schema，但保证不了语义正确。本文拆解约束解码的实现原理、不被支持的 Schema 特性、以及必须自己补上的四类校验。
keywords:
  - 严格模式结构化输出
  - strict schema
  - JSON Schema 约束解码
  - structured outputs 限制
  - LLM 结构化输出校验
  - 约束解码原理
pubDate: '2026-09-17'
updatedDate: '2026-09-17'
canonical: https://blog.yotradeapi.com/blog/llm-strict-schema-boundary/
tags:
  - 结构化输出
  - JSON Schema
  - 技术深度
  - 可靠性
category: 技术深度
---

严格模式（strict structured outputs）解决了一个真实痛点：模型输出的 JSON 不再会少个括号、多个逗号、或者在前面加一段"好的，以下是结果"。很多团队因此删掉了重试逻辑。

但 strict 模式给的是**语法保证**，不是**语义保证**。这两者的差距，恰恰是线上出事的地方。本文讲清这条边界在哪，以及边界之外你必须自己补什么。

## 一、约束解码做了什么

理解边界要先理解实现。strict 模式的核心是约束解码（constrained decoding）：把 JSON Schema 编译成一个状态机（通常是下推自动机或语法），在每一步采样时，用它算出"当前位置哪些 token 是合法的"，然后把非法 token 的 logits 置为负无穷。

```
生成到 {"age":  这个位置时
  → 状态机说：接下来只能是数字字符或负号
  → 把所有非数字 token 的概率压到 0
  → 采样必然落在合法集合里
```

这个机制的性质决定了一切：

- **它只能约束"下一个 token 的字符层面合法性"**。它知道这里该是数字，不知道这个数字该不该是 34。
- **它不改变模型的偏好排序**，只是裁掉非法选项后重新归一化。模型本来想写错的内容，裁剪之后仍然会写错，只是错得符合格式。
- **它需要 Schema 能被编译成有限状态机**。编不出来的特性就不支持——这是下一节的来源。

**核心判断**：strict 模式把"格式错误"这一类问题降到零，对"内容错误"没有任何帮助。如果你原来的重试逻辑是为了应对内容错误，它不能删。

## 二、不被支持或行为受限的 Schema 特性

各家实现细节不同，但受限的地方高度一致，因为限制来自同一个原理。常见的几类：

| Schema 特性 | 典型状态 | 原因 |
|---|---|---|
| `additionalProperties: true` | 通常必须设为 false | 开放键集无法编译成有限状态机 |
| 可选字段（不在 `required` 里） | 多数要求全部字段必填 | 分支组合爆炸 |
| `minimum` / `maximum` 数值范围 | 不强制 | 数值范围不是字符层面的性质 |
| `minLength` / `pattern` 正则 | 支持程度不一，复杂正则常被忽略 | 编译代价高 |
| `anyOf` / `oneOf` | 有限支持，嵌套深了容易报错 | 状态机分支膨胀 |
| 递归 `$ref`（树形结构） | 有深度上限或不支持 | 无限递归无法有限化 |
| `enum` 值很多时 | 支持，但会显著影响效果 | 见下节 |

这里最容易踩的是**可选字段**。很多人把现有的 API 响应 Schema 直接拿来用，里面一半字段是可选的，结果要么请求被拒，要么被迫全部标 required——后者的副作用是：模型必须为每个字段编一个值，本来该"没有"的字段被填上了幻觉内容。

正确做法是用可空联合来表达"可选"：

```json
{
  "type": "object",
  "properties": {
    "customer_id": { "type": "string" },
    "refund_amount": { "type": ["number", "null"] },
    "reason_code": { "type": ["string", "null"], "enum": ["damaged", "late", "wrong_item", null] }
  },
  "required": ["customer_id", "refund_amount", "reason_code"],
  "additionalProperties": false
}
```

字段都是 required（满足 strict 要求），但允许 null（表达"确实没有"）。这个模式应该成为你的默认写法。

## 三、strict 模式会影响输出质量吗

会，而且方向不总是一样。两种效应同时存在：

**负面效应：约束会打断模型的自然生成路径。** 最典型的场景是推理型任务——模型如果被迫先输出 `{"answer":`，就失去了先思考再回答的机会，准确率可能明显下降。解法是把思考过程作为 Schema 的第一个字段：

```json
{
  "properties": {
    "reasoning": { "type": "string" },
    "answer": { "type": "string" }
  },
  "required": ["reasoning", "answer"]
}
```

**字段顺序是有意义的**——JSON 是按序生成的，写在前面的字段会成为后面字段的上下文。把结论放在第一个字段，等于强迫模型先猜后想。这是 strict 模式下最常见也最隐蔽的性能损失来源。

**正面效应：省掉格式重试。** 非 strict 模式下的 JSON 失败率虽然不高，但在高并发下绝对数量可观，每次重试都是完整的一轮成本。这部分收益在批量场景尤其明显。

关于两种模式的实测差异，[LLM JSON 模式横向对比](/blog/llm-json-mode-comparison/) 里有更具体的数据。

## 四、必须自己补的四类校验

strict 模式给你一个"格式合法的 JSON"，从它到"可以直接进数据库的数据"，中间至少还差四步：

**1. 数值与范围校验。** Schema 里写的 `minimum: 0` 不会被强制。模型完全可以输出 `-5` 或 `1e308`。所有数值字段落库前必须自己检查范围，尤其是金额、数量、百分比。

**2. 枚举语义校验。** `enum` 通常会被强制（它可以编译成状态机），但要注意：**枚举值本身的措辞会影响选择准确率**。`"reason_code": "a1"` 这种无语义的编码，准确率会明显低于 `"damaged_on_arrival"`。如果必须用编码，在字段 description 里写清映射。

**3. 跨字段一致性校验。** Schema 表达不了"如果 status 是 refunded，那么 refund_amount 必须非空"。这类业务规则只能在代码里写：

```python
def validate_semantics(obj: dict) -> list[str]:
    errs = []
    if obj["status"] == "refunded" and obj["refund_amount"] is None:
        errs.append("refunded 状态必须有退款金额")
    if obj["refund_amount"] is not None and not (0 < obj["refund_amount"] <= 10000):
        errs.append("退款金额超出合理范围")
    if obj["reason_code"] is None and obj["status"] != "pending":
        errs.append("非 pending 状态必须有原因码")
    return errs
```

**4. 引用真实性校验。** 模型填进来的 ID、日期、订单号，格式再正确也可能是编的。凡是要和外部系统对账的字段，必须回查原始数据确认存在。这类问题的完整处理思路见 [LLM 输出校验实践](/blog/llm-output-validation/)。

## 五、还有三个边界情况要处理

**截断。** strict 模式不能保证输出在 token 上限内写完。被 `max_tokens` 截断的 JSON 仍然是残缺的，解析一样会失败。必须检查 `finish_reason`，为 `length` 时按失败处理，不要试图修补半截 JSON。相关判定见 [finish_reason 的正确处理方式](/blog/llm-finish-reason-handling/)。

**拒答。** 模型可能因为安全策略拒绝回答。这时返回的可能不是你的 Schema，而是一个 refusal 字段或空内容。调用侧必须显式处理这条分支，不能假设"strict 模式一定返回合法对象"。

**流式解析。** strict 模式下的流式输出仍然是逐 token 的，中间态是不完整的 JSON。要在流式过程中用到部分结果，需要一个容忍不完整输入的增量解析器，不能直接 `json.loads`。

```python
def handle(resp):
    if resp.stop_reason == "refusal":
        return Err("model_refused", resp.refusal)
    if resp.stop_reason == "length":
        return Err("truncated", None)          # 不要尝试修补
    obj = json.loads(resp.text)                 # strict 下这一步可以信任
    if errs := validate_semantics(obj):         # 但这一步不能省
        return Err("semantic", errs)
    return Ok(obj)
```

## 六、什么时候不该用 strict 模式

不是所有场景都适合：

- **Schema 会频繁变动的探索阶段**：编译约束有额外开销，且改 Schema 的成本更高，早期用普通 JSON 模式 + 校验更灵活
- **需要模型自由展开推理的任务**：即使用 reasoning 前置字段，约束仍可能损失质量，值得做 A/B 对比
- **输出是长文本为主、结构只占一小部分**：不如让模型正常写，用一个轻量工具调用抽取结构化部分
- **Schema 深度嵌套超过三四层**：编译失败或效果劣化的概率上升，考虑拆成多次调用

反过来，**分类、抽取、路由、打标签**这类输出短、结构固定、量大的任务，是 strict 模式收益最明确的场景。

## 七、一个落地检查清单

上线前对照过一遍：

- [ ] 所有字段都在 `required` 里，可选语义用 `["T", "null"]` 表达
- [ ] `additionalProperties: false` 已设置
- [ ] 推理类任务把思考字段放在结论字段**之前**
- [ ] enum 值使用有语义的措辞，而非无意义编码
- [ ] 数值范围、跨字段一致性在代码里单独校验
- [ ] `finish_reason` 为 `length` 时按失败处理，不修补
- [ ] 拒答分支有显式处理
- [ ] 所有对外 ID / 日期做过真实性回查

做完这八条，strict 模式才真正等于"可以信任的结构化输出"。只开开关不补校验，是把语法问题换成了更难发现的语义问题。

## 八、相关阅读

- [结构化输出 vs 工具调用怎么选](/blog/openai-structured-outputs-vs-tool/)
- [LLM 结构化输出完整指南](/blog/structured-output-llm-guide/)
- [LLM JSON 模式横向对比](/blog/llm-json-mode-comparison/)
- [LLM 输出校验实践](/blog/llm-output-validation/)
- [finish_reason 的正确处理方式](/blog/llm-finish-reason-handling/)
