---
title: LLM Token 成本账本设计
description: 从原始请求事件、价格快照、调整分录到日级汇总，讲清 LLM Token 成本账本怎么设计，才能支持对账、预警和回溯分析。
keywords:
  - LLM Token 成本账本
  - 大模型成本对账
  - Token 计费系统
  - AI 成本台账
  - LLM 用量核算
pubDate: '2026-08-15'
updatedDate: '2026-08-15'
canonical: https://blog.yotradeapi.com/blog/llm-token-cost-ledger/
tags:
  - LLM
  - Token
  - 成本优化
  - 工程实践
category: 成本优化
heroImage: ../../assets/blog-placeholder-5.jpg
---

很多团队都在做“成本统计”，但真正能撑住运营和财务追问的，往往不是一张月度汇总表，而是一套**可回放、可校验、可修正**的成本账本。尤其在 LLM 场景里，单次请求可能经过缓存、重试、模型回退、批处理或代理层换算，最后供应商账单上的数字，未必能直接映射到你的产品行为。

所以，“LLM Token 成本账本设计”的核心不是把 token 乘上单价，而是建立一条完整链路：这次请求是谁发起的、用了哪种模型、按哪套价格规则估算、后来有没有重算、最终如何和供应商账单对齐。没有这条链路，所有成本分析都会停留在“差不多”。

## 一、账本不是报表，它首先要解决可追溯性

报表适合回答趋势问题，比如过去 7 天成本涨了多少；账本适合回答追责问题，比如为什么 8 月 12 日某租户的成本突然翻倍。两者不能互相替代。

一套合格的 LLM 成本账本，至少要满足四个目标：

| 目标 | 说明 | 典型使用者 |
| --- | --- | --- |
| 可追溯 | 能从汇总数字回钻到单次请求 | 工程、财务 |
| 可重算 | 单价或口径变化后可批量回放 | 平台、数据 |
| 可对账 | 能和供应商账单做差异分析 | 财务、运营 |
| 可分层 | 能按租户、功能、模型聚合 | 产品、商业化 |

如果你的系统只保留“今天总共用了 230 万 token”，那其实还没有账本，只有日报。

## 二、把“原始事件”和“记账分录”分开

做账本时最常见的错误，是直接把 API 响应里的 token 数字当成最终账面记录。更稳的做法是拆成两层：

1. 原始事件层：记录模型调用当时发生了什么
2. 记账分录层：记录这次调用按什么口径入账

为什么要拆？因为原始事件描述的是事实，记账分录描述的是解释。事实不该轻易改写，但解释可能变化。例如：

- 后续发现代理层价格表写错，需要重算
- 某模型从按 token 计费改为混合计费
- 你决定把缓存命中收益回冲到租户账本
- 失败重试从平台吸收改成业务线承担

如果原始事件和分录揉在一起，每次口径调整都会破坏历史一致性。

## 三、原始事件表该记哪些字段

原始事件表建议围绕“谁、何时、做了什么、消耗了什么”来设计：

```json
{
  "request_id": "req_01k2...",
  "occurred_at": "2026-08-15T10:43:19Z",
  "tenant_id": "tenant_acme",
  "provider": "anthropic",
  "model": "claude-sonnet",
  "endpoint": "messages",
  "input_tokens": 8421,
  "output_tokens": 1186,
  "cached_input_tokens": 3200,
  "status": "success",
  "retry_attempt": 0,
  "source": "background_job",
  "feature_key": "weekly_report"
}
```

这里最有用的不是 `input_tokens` 本身，而是让这些 token 带着上下文存在。后面无论你要做[AI Agent 多租户成本归因](/blog/ai-agent-cost-attribution/)、[团队 LLM 预算分配实战](/blog/llm-team-budget-allocation/)还是[AI API 预算上限自动化设计](/blog/ai-api-budget-cap-design/)，都需要这些维度。

## 四、分录层要能表达“估算、调整、冲销”

账本设计真正拉开差距的，是分录层是否支持后续修正。建议把每一次入账都设计成一条显式分录，而不是覆盖更新旧值。

一个简单的分录表可以包含这些字段：

| 字段 | 作用 |
| --- | --- |
| `entry_id` | 分录唯一标识 |
| `request_id` | 对应的原始请求 |
| `entry_type` | `estimate` / `adjustment` / `reversal` |
| `pricing_version` | 使用的价格快照版本 |
| `amount_usd` | 本次入账金额 |
| `reason` | 调整原因 |
| `recorded_at` | 分录入账时间 |

比如某次请求先按代理层价格估算为 0.18 美元，月底对账时发现供应商实际结算是 0.16 美元，那么正确做法不是把 0.18 改成 0.16，而是：

1. 保留原始 `estimate` 分录
2. 新增一条 `adjustment = -0.02`
3. 在报表层汇总净额

这样做的好处是，财务和工程都能回答“为什么这个数字变了”，而不是只看到最终结果。

## 五、价格快照必须版本化

很多团队的单价直接写在代码或配置中心里，结果半年后回头分析某段时间的成本，根本不知道当时用的是哪套价格。账本里一定要保留**价格快照版本**。

建议至少保存：

- 供应商或代理的名称
- 模型标识
- 输入、输出、缓存、批处理等不同计费维度
- 生效开始时间
- 失效时间或当前版本标记

下面这个结构足够实用：

```sql
create table pricing_snapshots (
  pricing_version text primary key,
  provider text not null,
  model text not null,
  input_rate numeric(18,8) not null,
  output_rate numeric(18,8) not null,
  cache_hit_rate numeric(18,8),
  effective_from timestamptz not null,
  effective_to timestamptz
);
```

有了版本化价格表，你后续可以安全做两件事：一是回放历史重算，二是对比不同模型和不同接入层的真实单位成本。

## 六、账本和供应商账单为什么总会有差异

即使系统设计得很好，内部账本和供应商最终账单也很少完全一致，常见差异来源包括：

- 请求在代理层被重试，但只生成一条业务事件
- 缓存命中或批处理折扣在供应商端延迟体现
- 流式响应中断后，客户端和供应商记录的 token 不完全一致
- 内部按 UTC 日切，供应商按其他账期结算

这意味着你不能把“有差异”视为失败，而要建立**差异解释机制**。一个可执行的做法是，每天自动跑一次 reconciliation，把差异分成四类：

| 差异类型 | 建议处理 |
| --- | --- |
| 时间差异 | 等待账期收敛后再关账 |
| 价格差异 | 检查价格版本是否落后 |
| 计量差异 | 回看 token 口径和重试链路 |
| 数据缺失 | 检查埋点丢失或异步落库失败 |

如果你的团队经常碰到“财务看账单说贵了，工程看日志说没问题”，十有八九不是谁算错了，而是缺少一层正式的 reconciliation 流程。

## 七、账本应该输出哪些经营指标

有了底层账本之后，上层报表不要只做“总成本”。至少建议拉出下面几类指标：

1. 单租户日成本和周环比
2. 单功能每千次任务平均成本
3. 重试成本占比
4. 缓存节省金额
5. 各模型单位输出成本

尤其是“重试成本占比”，它和[LLM API 错误重试策略设计](/blog/llm-error-retry-strategy/)以及[AI Agent 错误恢复机制设计](/blog/ai-agent-error-recovery/)结合起来后，能非常快地发现哪些钱不是花在“智能能力”上，而是花在“系统不稳定”上。

## 八、一个最小可用的账本流水线

如果你现在还没有任何账本系统，不必一开始就做复杂平台。一个最小可用方案通常分五步：

1. API 网关或应用层记录原始调用事件
2. 异步任务按价格快照生成 `estimate` 分录
3. 每日汇总生成租户和功能维度报表
4. 定时导入供应商账单做 reconciliation
5. 把差异结果回写为 `adjustment` 分录

只要这五步跑顺了，后续再补充缓存、批处理和共享成本分摊就会轻松很多。相反，如果一开始就只有各种散落的 CSV、日志和周报，后面越做越难补。

## 九、相关阅读

- [AI Agent 多租户成本归因](/blog/ai-agent-cost-attribution/)
- [团队 LLM 预算分配实战](/blog/llm-team-budget-allocation/)
- [AI API 预算上限自动化设计](/blog/ai-api-budget-cap-design/)
- [LLM API 错误重试策略设计](/blog/llm-error-retry-strategy/)

如果你要先把多模型调用统一接入再做自建账本，[YoTradeApi](https://yotradeapi.com) 可以作为统一 API 入口，便于在同一层挂接日志、预算和成本核算流程。
