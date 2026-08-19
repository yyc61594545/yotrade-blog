---
title: Prompt Cache 命中率监控：从盲目省钱到有数据支撑
description: 讲解如何采集、计算并监控 Prompt Cache 命中率，涵盖指标定义、日志埋点、告警阈值设计，让缓存优化效果可度量。
keywords:
  - Prompt Cache 命中率
  - 缓存命中率监控
  - LLM 成本可观测性
  - Prompt Caching 指标
  - API 缓存告警设计
pubDate: '2026-08-19'
updatedDate: '2026-08-19'
canonical: https://blog.yotradeapi.com/blog/llm-cache-hit-observability/
tags:
  - Prompt Cache
  - 可观测性
  - 成本优化
  - 监控告警
category: 成本优化
heroImage: ../../assets/blog-placeholder-1.jpg
---

很多团队接入 Prompt Cache 之后,只做了一件事:把 prompt 结构调整成"能命中缓存的样子",然后就再也没管过。[怎么把 prompt 结构设计成可命中缓存](/blog/prompt-caching-cost-optimization/)是第一步,但缓存命中率会随着业务迭代悄悄劣化——prompt 模板改了一个字段顺序、新加了一段动态内容插在了缓存断点前面,命中率可能从 80% 掉到 20% 都没人发现,直到月底账单突然变贵才回头查。本文讲怎么把 Prompt Cache 命中率变成一个持续监控的指标,而不是上线时验证一次就不管的东西。

## 一、命中率不是单一数字,至少要拆成三层看

"缓存命中率"听起来是一个数,但直接监控这一个聚合数字很容易掩盖问题。建议至少拆成三层:

- **全局命中率**:所有请求里,命中缓存的 token 占比。用于看整体成本节省效果的趋势
- **按 prompt 模板拆分的命中率**:不同业务场景(客服问答、代码生成、文档摘要)用不同的 prompt 模板,命中率差异可能很大,合并成一个数会互相掩盖——比如客服场景 95% 命中率,新上线的代码生成场景只有 10%,合并后看到的"整体 70%"会让人误以为一切正常
- **按缓存断点位置拆分的命中率**:如果 prompt 里设置了多段缓存断点(比如系统提示、工具定义、历史对话分别设断点),每一段的命中率可能不同,需要分别追踪才能定位到底是哪一段先失效的

```python
# 从 API 响应里提取分层指标的示例（以 Anthropic 风格 usage 字段为例）
def extract_cache_metrics(response, template_name: str):
    usage = response.usage
    cache_read = getattr(usage, "cache_read_input_tokens", 0)
    cache_write = getattr(usage, "cache_creation_input_tokens", 0)
    total_input = usage.input_tokens + cache_read + cache_write

    return {
        "template": template_name,
        "cache_hit_tokens": cache_read,
        "cache_miss_tokens": total_input - cache_read,
        "hit_rate": cache_read / total_input if total_input > 0 else 0,
        "timestamp": ctx_timestamp(),  # 由调用方注入，避免脚本里直接取系统时间
    }
```

## 二、埋点位置:在调用出口统一采集,而不是分散在业务代码里

命中率指标最容易踩的坑是**埋点散落在各处业务代码里**,导致口径不一致——有的地方按请求数算命中率,有的地方按 token 数算,汇总起来的数字没有可比性。

推荐做法是把指标采集收敛到 API 调用的统一出口(比如封装的 LLM client 层),所有业务代码都走这一层,指标口径天然一致:

```python
class LLMClient:
    def __init__(self, metrics_sink):
        self.metrics_sink = metrics_sink

    async def call(self, template_name: str, messages: list, **kwargs):
        response = await self._raw_call(messages, **kwargs)
        metrics = extract_cache_metrics(response, template_name)
        self.metrics_sink.emit("llm_cache_hit_rate", metrics)
        return response
```

统一口径之后,后续无论是接入 Prometheus、写入时序数据库,还是简单地按天聚合成报表,都基于同一份定义,不需要每次跨团队对齐"你说的命中率和我说的是一回事吗"。

## 三、命中率下降的常见根因,监控时对应看哪张图

单纯知道"命中率降了"用处有限,监控设计时最好能直接提示可能的根因,常见的四类问题及对应排查方向:

| 现象 | 常见根因 | 排查方向 |
|------|---------|---------|
| 某个模板命中率突然归零 | 缓存断点前的内容被改动(如加了时间戳、请求 ID 等动态字段) | diff 该模板最近的代码变更 |
| 命中率缓慢下降 | 缓存 TTL 到期后请求间隔变长,导致缓存持续失效重建 | 对比请求间隔分布与 TTL 设置 |
| 命中率忽高忽低,无规律 | 多个实例/多个中转节点分别维护缓存,请求被负载均衡打散 | 检查请求路由是否有会话粘性 |
| 命中率整体偏低但稳定 | prompt 结构设计问题,动态内容放在了缓存断点之前 | 参考 prompt 结构设计核对断点位置 |

把这张表格对应到监控面板上,意味着面板不能只画一条命中率曲线,还需要配上"请求间隔分布"和"按模板/按节点拆分"的辅助视图,出问题时不用现查代码就能大致定位方向。

## 四、告警阈值怎么设:相对值比绝对值更稳定

直接给命中率设一个固定阈值(比如"低于 50% 告警")容易出两类问题:不同模板天然的命中率上限不同(有的场景对话历史短、天然缓存收益有限),固定阈值要么对高命中率场景太宽松,要么对低命中率场景太敏感产生噪音告警。

更稳定的做法是监控**相对于自身历史基线的变化率**,而不是绝对值:

```python
def check_cache_alert(current_hit_rate: float, baseline_hit_rate: float, threshold_drop=0.3):
    if baseline_hit_rate == 0:
        return False
    relative_drop = (baseline_hit_rate - current_hit_rate) / baseline_hit_rate
    return relative_drop > threshold_drop  # 相对基线下降超过 30% 才告警

# baseline_hit_rate 建议用过去 7 天同一模板的滚动均值，而不是写死的常量
```

这样即使某个模板天然命中率只有 40%,只要它稳定在 40% 附近,就不会触发误报;一旦它相对自己的历史基线明显下滑,才说明确实出了问题,这时候告警才是有信息量的。

## 五、把命中率和实际成本节省挂钩,而不是只看百分比

命中率本身是个中间指标,业务方真正关心的是"这省了多少钱"。建议在监控面板上把命中率直接换算成成本节省金额,比单独一个百分比更有说服力,也更容易在成本复盘会议上说清楚投入产出比:

```python
def estimate_cache_savings(cache_hit_tokens: int, cache_miss_tokens: int,
                             full_price_per_1k: float, cache_price_per_1k: float):
    full_cost_if_no_cache = (cache_hit_tokens + cache_miss_tokens) / 1000 * full_price_per_1k
    actual_cost = (cache_hit_tokens / 1000 * cache_price_per_1k) + (cache_miss_tokens / 1000 * full_price_per_1k)
    return {
        "savings": full_cost_if_no_cache - actual_cost,
        "savings_pct": (full_cost_if_no_cache - actual_cost) / full_cost_if_no_cache if full_cost_if_no_cache else 0,
    }
```

把这个数字接入日/周报,团队更容易对"要不要继续投入优化缓存命中率"做出有依据的判断,而不是凭感觉觉得"应该已经省了不少"。

## 六、相关阅读

- [prompt caching 在国内中转下省成本指南](/blog/prompt-caching-cost-optimization/)
- [Anthropic cache_control 五分钟入门到精通](/blog/anthropic-cache-control-tutorial/)
- [LLM 应用缓存层设计：从语义缓存到 Prompt 缓存的完整方案](/blog/llm-cache-layer-design/)
- [AI Agent 成本监控体系搭建](/blog/ai-agent-cost-monitoring/)

命中率监控能不能跑起来,前提是中转层能如实透传 `cache_read_input_tokens` 这类原始 usage 字段,而不是做了归一化处理导致细粒度数据丢失,[YoTradeApi](https://yotradeapi.com) 保留完整的 usage 字段透传,方便接入本文这套监控方案。
