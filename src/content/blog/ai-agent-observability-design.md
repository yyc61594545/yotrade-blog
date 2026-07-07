---
title: AI Agent 可观测性设计
description: 讲清 AI Agent 可观测性的核心架构设计：该观测什么、Trace 数据模型怎么建、告警怎么定，以及自建与用现成工具的取舍。
keywords:
  - AI Agent 可观测性
  - Agent 监控设计
  - LLM Trace 架构
  - Agent 可观测性架构
  - AI 系统监控设计
pubDate: '2026-07-07'
updatedDate: '2026-07-07'
canonical: https://blog.yotradeapi.com/blog/ai-agent-observability-design/
tags:
  - AI Agent
  - 可观测性
  - 应用工程
  - 架构设计
category: 应用工程
heroImage: ../../assets/blog-placeholder-4.jpg
---

传统应用的可观测性问了三个问题：请求慢在哪、错误发生在哪、资源用了多少。Agent 系统多问一个更难的问题：**它为什么做了这个决定**。一个 Agent 可能自主规划出 10 步任务、动态选择调用哪个工具、根据上一步结果改变下一步计划——出了问题之后，日志里一堆文本，却很难重建"它当时到底在想什么"。本文讲清 Agent 可观测性该怎么设计，而不是介绍某一个具体工具。

## 一、Agent 可观测性比传统监控多出的维度

普通 Web 服务监控关心延迟、错误率、吞吐量三件事。Agent 系统在这基础上，还要观测：

- **决策路径**：Agent 每一步选择了哪个工具、为什么选它（是模型自己"想"的，不是代码里写死的分支）
- **中间状态**：多轮规划中，Agent 对任务的理解是否随着执行发生了偏移
- **输出质量**：不像传统系统"有输出就算成功"，Agent 的输出可能格式正确但内容是错的（幻觉、工具参数编造），质量判断需要额外一层
- **成本归因**：一次用户请求可能触发几十次模型调用，需要知道钱花在了流程的哪一步

关于成本这一维度的具体实现，已经有专门的深度文章，看 [AI Agent 单会话成本监控实现](/blog/ai-agent-cost-monitoring/)；关于错误定位的具体方案，看 [AI 流水线的错误追踪方案](/blog/ai-pipeline-error-tracing/)。本文聚焦这几个维度之上的**整体架构设计**：怎么把它们串成一套统一的可观测性系统。

## 二、核心数据模型：Trace / Span / Event 三层结构

照搬分布式追踪的经验，但要针对 Agent 的特点做调整：

```
Trace（一次完整的用户请求）
 └─ Span（Agent 的一次"思考-行动"循环）
     ├─ Event: 模型调用（Prompt、输出、token 数、耗时）
     ├─ Event: 工具调用（工具名、入参、返回值、是否报错）
     └─ Span（子任务，如果 Agent 做了任务拆分）
```

关键设计点：

- **Span 要绑定"决策依据"**：不只是记录"调用了搜索工具"，还要记录模型在这一步收到的完整上下文和输出的原始文本，否则事后无法判断"为什么模型选了这个工具"
- **Trace ID 要贯穿到底层模型调用**：包括重试、fallback 到备用模型的情况，一次用户请求无论内部转了几圈，都要能用一个 ID 串起来
- **区分"计划内分支"和"计划外分支"**：Agent 走了预期路径 vs 因为工具报错临时改变计划，这两种情况在排障时的意义完全不同，最好用不同的 Event 类型区分

## 三、最小可用埋点怎么写

不需要一开始就上重型平台，一个装饰器就能跑起来基础版本：

```python
import time
import uuid
import json

def traced_step(span_name):
    def decorator(func):
        def wrapper(*args, trace_id=None, **kwargs):
            span_id = str(uuid.uuid4())
            start = time.time()
            try:
                result = func(*args, trace_id=trace_id, **kwargs)
                status = "success"
                return result
            except Exception as e:
                status = "error"
                result = {"error": str(e)}
                raise
            finally:
                log_span({
                    "trace_id": trace_id,
                    "span_id": span_id,
                    "span_name": span_name,
                    "duration_ms": int((time.time() - start) * 1000),
                    "status": status,
                    "output_preview": json.dumps(result)[:500],
                })
        return wrapper
    return decorator

@traced_step("tool_call:web_search")
def call_search_tool(query, trace_id=None):
    ...
```

这个最小版本先落地三件事：每一步有唯一 span_id、每一步归属到同一个 trace_id、每一步记录耗时和状态。等规模上来了，再考虑接入专门的可观测性平台（比如自部署 Langfuse，具体部署方式看 [LLM 可观测性实战：Langfuse 自部署完整指南](/blog/llm-observability-langfuse/)），把这些字段结构化写入即可，架构不需要推倒重来。

## 四、告警该设在哪几条线上

Agent 系统的告警不能只靠"错误率超过阈值"这一种规则，几个 Agent 特有的告警场景：

| 告警场景 | 触发条件示例 | 为什么重要 |
| --- | --- | --- |
| 循环未收敛 | 单个 Trace 内 Span 数量超过预设上限（如 20） | Agent 可能陷入"规划-失败-重新规划"死循环，不加限制会持续烧钱 |
| 工具调用参数异常率上升 | 同一工具连续 N 次调用参数校验失败 | 提示模型对工具 Schema 理解出现偏差，或者上游 Prompt 被改动影响了工具选择 |
| 单 Trace 成本突增 | 单次请求成本超过历史 P95 的 3 倍 | 比全局成本告警更早发现单个异常任务，配合预算控制看 [AI API 预算上限设计](/blog/ai-api-budget-cap-design/) |
| 输出格式合规率下降 | 结构化输出解析失败率环比上升 | 往往是模型版本切换或者上游 Prompt 微调引入的回归 |

告警阈值不要一开始就定死，先跑一到两周收集基线数据（P50/P95 的 Span 数、成本、耗时），再基于基线设置相对阈值，比拍脑袋定绝对值更稳。

## 五、Dashboard 该展示什么，而不是塞满图表

排障时真正有用的视图通常只有三类：

1. **单条 Trace 的完整时间线**：点开一次用户请求，能看到从第一次模型调用到最终输出的完整决策链路，逐步展开每个 Span 的输入输出
2. **按工具/按步骤聚合的失败率**：哪个工具、哪个环节的失败率最高，比"整体错误率 5%"这种笼统数字有用得多
3. **成本/延迟的分布而不是均值**：均值会被极端值掩盖，P95、P99 更能反映真实用户体验，尤其是 Agent 这种耗时波动大的系统

不需要一开始就做大而全的 Dashboard，先把"点开一条 Trace 能看清全过程"这一条做扎实，其他视图可以逐步补。

## 六、自建还是用现成工具

| 方案 | 适合场景 | 代价 |
| --- | --- | --- |
| 自建最小埋点（日志 + 结构化字段） | 早期项目、Agent 逻辑简单、团队小 | 开发量小，但排查复杂问题时效率较低 |
| 自部署 Langfuse 等开源平台 | 有一定规模、要求数据不出境、团队有运维能力 | 部署和维护成本，换来完整的 Trace UI 和用量分析 |
| 商业 SaaS 可观测性平台 | 追求快速上线、不介意数据出境 | 按量付费，通常有免费额度，接入最快 |

国内团队如果数据合规是硬性要求，自部署开源方案通常是更稳妥的选择，具体合规考虑看 [国内大模型数据合规指南](/blog/cn-llm-data-compliance/)。不管选哪种方案，核心原则不变：先把 Trace/Span/Event 的数据模型设计对，工具只是把这套模型可视化，模型设计错了，换什么工具都白搭。

## 七、相关阅读

- [AI Agent 单会话成本监控实现](/blog/ai-agent-cost-monitoring/)
- [AI 流水线的错误追踪方案：从日志到根因定位](/blog/ai-pipeline-error-tracing/)
- [LLM 可观测性实战：Langfuse 自部署完整指南](/blog/llm-observability-langfuse/)
- [AI API 预算上限设计](/blog/ai-api-budget-cap-design/)
- [国内大模型数据合规指南](/blog/cn-llm-data-compliance/)

搭建 Agent 可观测性系统离不开稳定、可追踪调用记录的模型接口，[YoTradeApi](https://yotradeapi.com) 提供完整的调用日志和用量明细，方便和自建的 Trace 系统对账。
