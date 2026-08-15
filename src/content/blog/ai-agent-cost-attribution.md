---
title: AI Agent 多租户成本归因
description: 讲清 AI Agent 产品里如何按租户、用户、任务和模型做成本归因，覆盖数据结构、分摊规则、埋点口径与运营看板设计。
keywords:
  - AI Agent 成本归因
  - 多租户 AI 计费
  - LLM 成本分摊
  - Agent 用量核算
  - AI SaaS 成本看板
pubDate: '2026-08-15'
updatedDate: '2026-08-15'
canonical: https://blog.yotradeapi.com/blog/ai-agent-cost-attribution/
tags:
  - AI Agent
  - 多租户
  - 成本管理
  - 应用工程
category: 应用工程
heroImage: ../../assets/blog-placeholder-2.jpg
---

很多团队在 AI Agent 刚上线时，只盯总账单：这个月花了多少 token、哪个模型最贵、有没有超预算。等真正开始商业化，问题马上会变成另一种形式: 哪个租户在烧钱、哪个功能在赔本、哪些自动化任务值得继续开放。没有成本归因，团队只能看到总成本，却回答不了“钱为什么花在这里”。

AI Agent 的归因难点在于，它不是单次请求型系统，而是一个会串联模型调用、工具执行、异步任务和人工复核的复合流程。同一笔用户行为，可能会拆成十几次请求，跨多个提供商，还夹着缓存命中、失败重试和后台批处理。如果没有一套统一口径，财务、产品和工程看到的数字通常都对不上。

## 一、先定义“归因单位”，不要一开始就只看 token

多租户归因的第一步不是接账单 API，而是定义你到底想把成本落到哪一层。常见有四层：

| 归因层级 | 回答的问题 | 常见主键 |
| --- | --- | --- |
| 租户 tenant | 哪个客户整体最耗资源 | `tenant_id` |
| 用户 user | 哪个账号或团队成员触发最多消耗 | `user_id` |
| 任务 run | 哪类工作流最贵、失败重试是否异常 | `run_id` |
| 功能 feature | 哪个产品入口需要限流或提价 | `feature_key` |

如果你的系统只记录“本次调用用了多少 input/output token”，后面几乎无法做经营分析。更稳妥的做法是把**业务上下文和计费事件同时落库**，让一次模型请求既属于某个租户，也属于某个任务、某个功能和某个计费周期。

建议把“模型调用事件”视为最小核算单元，再通过外键映射回租户、会话和工作流。这样即使后续新增供应商、缓存层或批处理通道，也不需要推翻数据模型。

## 二、成本事件至少要记录哪些字段

一条可用于归因的成本事件，至少要覆盖四组信息：

1. 身份维度：`tenant_id`、`user_id`、`workspace_id`
2. 业务维度：`feature_key`、`run_id`、`conversation_id`
3. 技术维度：`provider`、`model`、`request_type`、`cache_hit`
4. 财务维度：`currency`、`estimated_cost`、`billable_units`、`source`

工程上最容易漏掉的是 `source` 和 `request_type`。没有它们，你会分不清这笔钱是用户前台触发、系统后台补偿、定时任务扫描，还是失败后的自动重试。

下面是一份足够实用的事件结构示例：

```json
{
  "event_id": "evt_01k2...",
  "occurred_at": "2026-08-15T09:12:31Z",
  "tenant_id": "tenant_acme",
  "user_id": "user_42",
  "feature_key": "agent_report_generation",
  "run_id": "run_8f3a",
  "provider": "openai",
  "model": "gpt-5",
  "request_type": "llm_inference",
  "input_tokens": 14820,
  "output_tokens": 1630,
  "cache_hit": false,
  "estimated_cost_usd": 0.2147,
  "source": "interactive"
}
```

这套结构的价值不在“字段多”，而在于后续可以很轻松地按任意维度聚合：按租户汇总、按模型拆分、按功能比较毛利，或者过滤掉 `source=retry` 的补偿成本。

## 三、把 Agent 链路拆开，避免一锅粥式记账

一个 AI Agent 往往包含这几类成本：

- 模型推理成本
- 工具调用成本
- 检索或向量数据库成本
- 后台执行资源成本
- 人工审核成本

如果全部塞进“单次任务总成本”，看起来简单，但无法回答“到底是模型贵，还是工具链贵”。更可操作的方法是把每一层都变成可聚合事件，再在汇总层做二次分摊。

常见拆法如下：

| 成本类型 | 记录方式 | 是否直接向租户计费 |
| --- | --- | --- |
| 模型调用 | 每次请求一条事件 | 通常是 |
| 搜索/检索 | 按查询次数或读写量记录 | 视套餐而定 |
| 后台 worker | 按 CPU 秒或任务数估算 | 常作为平台成本 |
| 人工审核 | 记录审核工时或订单数 | 高客单价场景常需要 |
| 失败重试 | 单独标记 `source=retry` | 是否转嫁取决于策略 |

很多团队在早期阶段会先只做“模型成本归因”，这是合理的。但一旦开始卖工作流产品，建议至少再把检索层和异步任务层拉出来，否则会错误地把所有亏损都归咎到 LLM 单价。

## 四、共享成本怎么分摊，先定规则再上报表

归因最容易引发争议的，不是专属成本，而是共享成本。比如：

- 系统级 prompt cache 的命中收益分给谁
- 公共知识库的向量检索成本如何拆
- 同一批批处理任务服务多个租户时怎么平摊
- 安全审核、观测平台、日志存储算不算租户成本

这类问题没有唯一正确答案，但必须提前确定口径。常见分摊规则有三种：

1. 按调用量分摊：实现简单，适合早期
2. 按资源占用分摊：更准确，但埋点成本更高
3. 按套餐吸收：把共享成本算进平台毛利，不逐笔回写租户

如果你同时服务中小客户和大客户，建议采用“双账本”思路：

- 经营账：尽量完整，便于看真实毛利
- 客单账：按对外承诺口径，只展示对客户有意义的 billable 成本

这样不会因为内部核算复杂，直接把对外计费页面也做得难以理解。

## 五、落地时最实用的三张表

很多人以为要先上大型 BI，实际上只要三张表就能跑起来：

### 1. 原始事件表 `cost_events`

存每一笔请求和执行动作，保持不可变，便于审计和回放。

### 2. 任务汇总表 `run_cost_daily`

每天按 `run_id` 聚合，回答“哪个工作流最贵”“哪些任务重试过多”。这类分析和[AI Agent 错误恢复机制设计](/blog/ai-agent-error-recovery/)结合起来看最有价值，因为很多成本浪费并不是模型太贵，而是任务反复失败。

### 3. 租户汇总表 `tenant_margin_daily`

把收入、模型成本、工具成本、共享分摊成本放在同一张日报里，直接给产品和运营看。再配合[团队 LLM 预算分配实战](/blog/llm-team-budget-allocation/)和[AI API 预算上限自动化设计](/blog/ai-api-budget-cap-design/)，就能把“看成本”推进到“控成本”。

一个典型的聚合 SQL 会像这样：

```sql
select
  tenant_id,
  date_trunc('day', occurred_at) as day,
  sum(estimated_cost_usd) as total_cost_usd,
  sum(case when request_type = 'llm_inference' then estimated_cost_usd else 0 end) as llm_cost_usd,
  sum(case when source = 'retry' then estimated_cost_usd else 0 end) as retry_cost_usd,
  count(distinct run_id) as run_count
from cost_events
where occurred_at >= now() - interval '30 days'
group by 1, 2
order by day desc, total_cost_usd desc;
```

这类 SQL 不复杂，但前提是你一开始就把埋点字段记全。

## 六、成本归因要和限额、告警、定价联动

如果归因只停留在报表层，价值会很有限。真正能帮业务的，是让归因结果继续触发动作：

- 某租户 3 天内重试成本异常升高，自动告警
- 某功能单位任务成本持续高于套餐收入，提醒调整产品策略
- 某模型在特定任务中性价比偏低，切换到更合适的路由策略
- 某批量任务超过预算阈值，进入人工审批

这部分通常和[AI Agent 单会话成本监控实现](/blog/ai-agent-cost-monitoring/)以及[多模型成本智能路由方案](/blog/multi-model-cost-routing/)一起设计。没有归因，路由只能按平均成本优化；有了归因，路由才能按“哪个租户、哪种任务、什么 SLA”做更细的选择。

## 七、最常见的四个误区

### 误区 1：直接使用供应商账单作为唯一真相

供应商账单适合对账，不适合作为产品分析事实表，因为它缺少你的业务上下文。

### 误区 2：只记录成功请求

失败、超时、重试往往正是成本黑洞。如果没有它们，团队会低估真实消耗。

### 误区 3：把缓存收益忽略掉

无论是 prompt cache、结果复用还是知识库命中，都会改变单位任务成本，不纳入核算会让优化方向失真。

### 误区 4：所有客户都使用同一种分摊规则

自助版、团队版和大客户版的计费解释口径往往不同，内部经营账和外部结算账不一定要完全一致。

## 八、什么时候说明你已经“做对了”

如果你的系统能稳定回答下面五个问题，成本归因体系基本就合格了：

1. 过去 30 天哪个租户的毛利下降最快
2. 哪个 Agent 工作流的重试成本最高
3. 哪个模型在某类任务上成本明显偏离平均值
4. 某个客户升级套餐后，平台边际成本是否同步改善
5. 某次预算超限，到底是用户行为、系统缺陷还是路由策略导致

这五个问题都回答不了，就说明你现在看到的多半只是“账单”，还不是“归因系统”。

## 九、相关阅读

- [AI Agent 单会话成本监控实现](/blog/ai-agent-cost-monitoring/)
- [团队 LLM 预算分配实战](/blog/llm-team-budget-allocation/)
- [AI API 预算上限自动化设计](/blog/ai-api-budget-cap-design/)
- [多模型成本智能路由方案](/blog/multi-model-cost-routing/)

如果你想先把多模型接入层统一起来，[YoTradeApi](https://yotradeapi.com) 可以作为 API 接入入口，方便你在自己的系统里继续做成本归因、限额和日志治理。
