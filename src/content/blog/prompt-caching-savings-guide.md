---
title: Prompt Caching 实战省钱指南
description: 从账单异常排查到五个常见"缓存失效"踩坑点，给出一套可直接照抄的 Prompt Caching 省钱实战清单，附真实场景前后成本对比。
keywords:
  - prompt caching 省钱
  - 缓存失效排查
  - claude api 账单优化
  - prompt caching 踩坑
  - ai 成本控制实战
pubDate: '2026-08-25'
updatedDate: '2026-08-25'
canonical: https://blog.yotradeapi.com/blog/prompt-caching-savings-guide/
tags:
  - 成本优化
  - Prompt Caching
  - API 账单
  - 实战
category: 成本优化
heroImage: ../../assets/blog-placeholder-4.jpg
---

Prompt Caching 的原理和该不该用，[《Claude Prompt Caching ROI 分析》](/blog/claude-prompt-caching-roi-analysis/)和[《prompt caching 在国内中转下省成本指南》](/blog/prompt-caching-cost-optimization/)已经讲得很清楚了。本文不重复这些内容，只聚焦一件事：**你已经开了缓存，为什么账单没降下来，以及怎么排查**。这是团队接入 caching 后最常遇到的真实问题。

## 一、先看一个真实案例

某客服机器人团队接入 caching 后满心期待账单减半，结果一周后账单只降了 8%。排查过程如下：

1. 拉取一周内所有请求的 `usage` 字段，统计 `cache_read_input_tokens` / `cache_creation_input_tokens` / 总 `input_tokens` 的比例
2. 发现 `cache_read_input_tokens` 常年接近 0，说明几乎每次请求都在**重新创建缓存**，而不是命中已有缓存
3. 定位到问题：系统 prompt 里拼了一段动态时间戳（"当前时间：2026-08-25 14:32:07"），导致每次请求内容都不同，缓存断点前的内容每次都变，命中率归零

这类问题不改代码看账单是发现不了根因的，必须落到 token 级别的数据。

## 二、五个最常见的"缓存看似开了但没生效"场景

**1. 缓存断点前混入了动态内容。** 时间戳、随机 ID、用户会话变量——只要断点之前的任何一个字符变了，这段内容就要重新计费写入。把动态内容整体挪到缓存断点**之后**。

**2. 断点位置放错，缓存了变化频繁的部分。** 常见错误是把"最近 5 轮对话"也框进了缓存范围。对话历史本质是易变内容，应该只缓存真正稳定的部分（系统指令、工具定义、长文档），可变部分放在断点外。

**3. TTL 到期后仍以为在命中。** Anthropic 的 ephemeral 缓存默认 5 分钟 TTL，请求间隔超过 5 分钟缓存就失效了。低频调用场景（比如批处理任务、定时任务）天然享受不到缓存收益，除非产品逻辑允许攒批请求。

**4. 多个缓存断点嵌套顺序反了。** 缓存要求"前缀匹配"，如果两个请求在断点 A 之前的内容都相同，但断点 A 和断点 B 的顺序颠倒，等于整体前缀不同，两次都会重新创建。检查请求体里 `cache_control` 标记的先后顺序是否跨请求保持一致。

**5. 中转层未透传缓存相关字段。** 少数中转服务商对上游请求做了处理，把 `cache_control` 字段过滤掉或者没有透传 `usage` 里的缓存统计字段，导致你在业务侧根本看不到真实的缓存命中率，误以为没生效。接入中转时，建议先用一个固定 prompt 连续调用两次，检查第二次的 `cache_read_input_tokens` 是否真的非零。

## 三、监控清单：怎么知道缓存到底有没有生效

不要只看月度账单总数，按以下维度拆开看：

| 指标 | 计算方式 | 健康参考值 |
| --- | --- | --- |
| 缓存命中率 | `cache_read_input_tokens / (cache_read + cache_creation + 非缓存input)` | 高频场景应 > 70% |
| 平均节省比例 | `1 - 实际花费 / 未开缓存理论花费` | 视场景，30%–70% 常见 |
| 缓存创建请求占比 | 触发了 `cache_creation_input_tokens` 的请求数 / 总请求数 | 越低越好，接近 0 最理想 |

这三个指标建议接入日常监控面板，而不是等月底账单出来才发现问题。缓存效率监控体系的搭建思路可以参考[《LLM 缓存命中率可观测性建设》](/blog/llm-cache-hit-observability/)。

## 四、实战省钱清单（可直接照抄执行）

1. 把系统 prompt 中所有动态内容（时间、用户 ID、随机数）挪到缓存断点之后
2. 确认多轮对话场景里，只有"稳定不变"的部分（系统指令、工具定义、长文档参考资料）被框进缓存范围
3. 高频调用场景检查请求间隔是否稳定小于 TTL（Anthropic ephemeral 默认 5 分钟）
4. 用固定 prompt 连续调用两次做基线测试，确认 `cache_read_input_tokens` 确实非零
5. 接入中转服务时，先验证中转是否完整透传 `cache_control` 请求字段和 `usage` 响应字段
6. 把缓存命中率、节省比例两个指标纳入日常监控，而不是月底才复盘

## 五、和其他成本优化手段的关系

Prompt Caching 只是成本优化的一环，不能替代模型选型、批处理等其他手段。如果账单里 caching 已经调到位但整体成本仍然偏高，往回退一步看整体的 API 预算控制策略，可以参考[《AI API 预算上限设计》](/blog/ai-api-budget-cap-design/)。

## 六、相关阅读

- [Claude Prompt Caching ROI 分析：什么场景值得开启缓存](/blog/claude-prompt-caching-roi-analysis/)
- [prompt caching 在国内中转下省成本指南](/blog/prompt-caching-cost-optimization/)
- [Anthropic cache_control 五分钟入门到精通](/blog/anthropic-cache-control-tutorial/)
- [LLM 缓存命中率可观测性建设](/blog/llm-cache-hit-observability/)

如果排查下来发现问题出在中转层没有正确透传缓存字段，不妨换一个明确支持 caching 透传的中转方案试试，[YoTradeApi](https://yotradeapi.com) 的接口对 `cache_control` 和相关 `usage` 字段做了完整透传，方便直接核对账单。
