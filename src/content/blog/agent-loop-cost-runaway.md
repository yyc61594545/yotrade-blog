---
title: Agent 循环的成本失控与控制：为什么循环比单次调用更危险
description: 循环型 Agent 的成本为什么会非线性增长：上下文累积效应、边际成本衰减信号、预算感知型循环终止的设计与实现。
keywords:
  - agent 循环成本
  - agent 成本失控
  - 边际成本检测
  - 预算感知循环
  - react agent 成本控制
pubDate: '2026-09-05'
updatedDate: '2026-09-05'
canonical: https://blog.yotradeapi.com/blog/agent-loop-cost-runaway/
tags:
  - AI Agent
  - 成本优化
  - 循环控制
  - 系统设计
category: 成本优化
---

外层预算上限、告警熔断、成本归因这些通用防护，[《AI API 预算上限自动化设计》](/blog/ai-api-budget-cap-design/)和[《AI 账单异常检测》](/blog/llm-cost-anomaly-detection/)已经讲得很细。本文聚焦一个更窄但更容易被低估的问题：**为什么循环型 Agent（ReAct 式的"思考-调用工具-观察结果"循环）的成本失控风险，本质上跟普通 API 调用的成本失控不是一回事**，以及针对"循环"这个结构本身该加什么控制手段。

## 一、循环成本为什么是非线性的

单次 API 调用出问题，最坏情况是这一次请求贵一点。循环型 Agent 不一样：**每一轮迭代通常会把之前所有轮次的对话历史重新发一遍**。如果一个任务卡在循环里跑了 N 轮，输入 token 消耗大致是：

```
第 1 轮：base_tokens
第 2 轮：base_tokens + round_1_tokens
第 3 轮：base_tokens + round_1_tokens + round_2_tokens
...
第 N 轮：累加前面所有轮次
```

总成本大约是 `O(N²)` 而不是 `O(N)`。这意味着一个正常 5 轮完成的任务如果卡到 50 轮，成本不是涨 10 倍，而是接近 100 倍——这也是为什么"一个循环 bug 导致账单暴涨十几倍"在实战里屡见不鲜。**外层的总预算熔断能兜底，但等它触发时钱已经花出去了**；真正有效的控制要下沉到循环内部，在成本还没滚雪球之前就叫停。

## 二、两种失控模式：卡死 vs 缓慢发散

循环失控不总是"死循环"这么明显，实战里主要是两种模式：

| 模式 | 特征 | 危险程度 |
| --- | --- | --- |
| **卡死重复** | 反复尝试同一个工具调用，观察结果几乎不变 | 高但容易识别——输出内容重复度很高 |
| **缓慢发散** | 每轮都在"做点什么"，但离目标越来越远，上下文越滚越大 | 更隐蔽——每轮看起来都合理，只有拉长看才发现没有收敛 |

第一种可以用简单的"连续 N 次工具调用结果高度相似则终止"规则抓住。第二种更难，因为它不违反任何单轮规则，需要**跨轮次判断进展**，这也是下一节要讲的边际成本检测。

## 三、把预算检查放进循环本身

大部分团队的预算控制是"外挂式"的：循环本身不感知预算，跑完一轮之后由外层监控发现超支再介入。更可靠的方式是让循环在**每次决定要不要继续下一轮之前**，先问一句"这一轮的预期成本，相对于剩余预算，划算吗"：

```python
class BudgetAwareLoop:
    def __init__(self, max_budget_usd, cost_per_token):
        self.max_budget = max_budget_usd
        self.spent = 0.0
        self.cost_per_token = cost_per_token

    def can_continue(self, estimated_next_round_tokens):
        estimated_cost = estimated_next_round_tokens * self.cost_per_token
        if self.spent + estimated_cost > self.max_budget:
            return False, "budget_exhausted"
        # 预留 20% 余量给收尾（比如生成最终回复）
        if self.spent + estimated_cost > self.max_budget * 0.8:
            return False, "approaching_budget_limit"
        return True, None

    def record_round(self, actual_tokens):
        self.spent += actual_tokens * self.cost_per_token
```

关键区别在于：`estimated_next_round_tokens` 是**下一轮**的预估成本（当前累积上下文大小 + 预期输出），不是历史平均。因为循环里每一轮的上下文都在变大，用"平均单轮成本"去估算剩余预算能撑几轮，会系统性低估——第 10 轮的成本远高于第 1 轮。

## 四、边际成本检测：花的钱换来了什么

比"还有没有预算"更本质的问题是"再花这笔钱值不值"。给循环加一个简单的**进展评分**，跟成本放在一起看：

```python
def marginal_value_check(history, cost_this_round):
    if len(history) < 3:
        return True  # 轮次太少，先不评估

    progress_scores = [round_.progress_score for round_ in history[-3:]]
    # 最近 3 轮进展分数几乎不再提升
    if max(progress_scores) - min(progress_scores) < 0.05:
        cumulative_cost = sum(r.cost for r in history)
        if cost_this_round > cumulative_cost * 0.1:
            return False  # 边际成本高但边际进展趋近于零，不值得继续
    return True
```

`progress_score` 不需要多复杂，可以是"任务是否声明完成""关键子目标是否达成"这类布尔信号的加权，或者干脆让模型自己在每轮输出里附带一个"距离目标完成度"的自评分（不完全可靠，但比完全没有信号强）。**核心思路是把"继续跑"从一个默认行为，变成一个需要被证明划算的决策**。

## 五、上下文增长本身就是成本杠杆，提前对冲

既然成本非线性增长的根源是上下文累积，最直接的对冲手段是在循环内部主动压缩历史，而不是等上下文接近模型上限才被动截断：

```python
CONTEXT_COMPACT_THRESHOLD = 20000  # tokens

def maybe_compact(history):
    total_tokens = sum(r.tokens for r in history)
    if total_tokens > CONTEXT_COMPACT_THRESHOLD:
        # 把较早的轮次压缩成摘要，只保留最近几轮的完整细节
        summary = summarize_early_rounds(history[:-3])
        return [summary] + history[-3:]
    return history
```

这个阈值应该设置在"模型上限的一半"左右而不是"快顶到上限了"——太晚压缩，之前几轮已经按完整上下文计费了，压缩只能防止未来更贵，防不了已经发生的成本。压缩带来的上下文精度损失是一个真实的权衡，具体的窗口分配策略可以参考[《Agent 上下文预算分配》](/blog/agent-context-budget-allocation/)。

## 六、给循环设置分层超时，而不只是总预算

除了金额预算，循环还需要跟"轮次数"和"单轮工具执行时间"两个维度的上限配合，三者缺一都会留下漏洞：

| 维度 | 单独设置的问题 | 建议做法 |
| --- | --- | --- |
| 仅金额上限 | 便宜模型可能在预算耗尽前跑几百轮，纯粹浪费时间 | 叠加最大轮次数（如 30 轮） |
| 仅轮次上限 | 上下文累积让后期每轮都很贵，30 轮可能已经超预算 | 叠加金额预算 |
| 仅单轮超时 | 卡在循环里但每轮单独看都不超时 | 叠加累计总耗时上限 |

三层限制同时生效，任何一层触发都终止循环，这部分跟工具级别的超时预算设计是同一套思路，可以参考[《Agent 工具调用超时预算设计》](/blog/agent-tool-timeout-budget/)。

## 七、终止后的处理：别把中途状态直接丢弃

循环因为预算或边际价值触发终止后，**不代表这个任务就是失败的**——很多时候已经完成了大部分工作，只是最后一步没收敛。终止逻辑应该：

1. 尝试让模型基于已有信息**强制给出一个"尽力而为"的最终答案**，而不是直接报错退出
2. 记录终止原因（预算耗尽 / 边际价值归零 / 轮次超限）区分对待，前两者可能是任务设计问题，最后一种可能只是这个任务本来就需要更多轮次
3. 把终止的任务和它的完整轨迹留存，用于后续判断是否要调整预算阈值或进展评分逻辑——这类数据积累几次之后，阈值设置会比拍脑袋准得多

## 八、相关阅读

- [AI API 预算上限自动化设计](/blog/ai-api-budget-cap-design/)
- [AI 账单异常检测：从告警到根因定位](/blog/llm-cost-anomaly-detection/)
- [预算护栏该放在调用链的哪一层](/blog/budget-guardrail-design/)
- [Agent 上下文预算分配](/blog/agent-context-budget-allocation/)
- [AI Agent 单会话成本监控实现](/blog/ai-agent-cost-monitoring/)

循环型 Agent 的成本控制最终还要落到可观测的调用数据上，[YoTradeApi](https://yotradeapi.com) 的请求级用量统计能按会话拆分每一轮的 token 消耗，方便验证上面这些预算规则是否设对了阈值。
