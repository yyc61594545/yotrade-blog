---
title: 用 logprobs 做置信度判断：阈值怎么定才不是拍脑袋
description: 讲解 logprobs 置信度分数为什么经常不校准、如何用可靠性曲线检验分数是否可信，以及自动放行/人工审核/拒答三档阈值的科学设定方法。
keywords:
  - logprobs 置信度阈值
  - 模型置信度校准
  - LLM 置信度判断
  - 可靠性曲线
  - 置信度分布漂移监控
pubDate: '2026-09-03'
updatedDate: '2026-09-03'
canonical: https://blog.yotradeapi.com/blog/llm-logprobs-confidence/
tags:
  - LLM
  - logprobs
  - 技术深度
  - 模型评估
category: 技术深度
heroImage: ../../assets/blog-placeholder-5.jpg
---

logprobs 怎么获取、怎么转成一个 0-1 之间的"置信度分数"，[LLM logprobs 在生产场景的实用价值](/blog/llm-logprobs-applications/)已经讲得很完整。但拿到分数只是第一步，真正决定这套机制在生产里有没有用的，是下一个问题：**这个分数到底能不能信、阈值该定多少**。本文只讲这一层——置信度分数的校准与阈值设定方法。

## 一、置信度分数在回答什么问题

先厘清一个容易混淆的点：`prob = exp(logprob)` 高，说明的是"模型对自己输出的这个 token 序列没有犹豫"，**不等于**"这个答案是对的"。模型可以自信地说错话——尤其是训练数据里某个错误说法出现频率很高的情况下，模型对错误答案的置信度反而可能很高。

所以 logprobs 置信度衡量的是"模型内部的确定性"，而不是"客观正确性"。这两者相关，但不是一回事，混用会导致阈值设置从一开始就建立在错误假设上。

## 二、为什么"直接拿 prob 当置信度"经常不准

这类分数是否"校准良好"（calibrated），指的是：在所有 prob ≈ 0.8 的样本里，实际正确率是不是也接近 80%。多数情况下不是——常见的偏差方向是：

- **过度自信**：模型输出的 prob 普遍偏高，但实际正确率明显低于 prob 数值，尤其在小模型和领域外问题上更明显。
- **温度和采样参数会直接扭曲分布**：`temperature` 越高，概率分布越平，同一个"确定"的答案在不同温度下算出来的 prob 会不一样，用固定阈值跨温度比较没有意义。
- **多 token 答案的聚合方式影响结果**：用平均 logprob 还是最小 token 概率，算出来的置信度分布形状完全不同，选错聚合方式会让阈值调参变得毫无规律。

不校准的分数不是不能用，而是**不能直接拿数值本身当"百分之多少把握"来解读**，必须先验证。

## 三、怎么检验分数是否可信：可靠性曲线

验证校准程度的标准做法是画可靠性曲线（reliability diagram）：把样本按置信度分桶，看每一桶的实际正确率是否接近桶的置信度区间。

```python
import numpy as np

def reliability_diagram(confidences: list[float], correct: list[bool], n_bins: int = 10):
    """按置信度分桶，返回每桶的(平均置信度, 实际正确率, 样本数)"""
    bins = np.linspace(0, 1, n_bins + 1)
    results = []
    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        mask = [(c >= lo and c < hi) for c in confidences]
        idx = [j for j, m in enumerate(mask) if m]
        if not idx:
            continue
        bucket_conf = np.mean([confidences[j] for j in idx])
        bucket_acc = np.mean([correct[j] for j in idx])
        results.append({"range": (lo, hi), "avg_confidence": bucket_conf,
                         "actual_accuracy": bucket_acc, "count": len(idx)})
    return results

def expected_calibration_error(confidences: list[float], correct: list[bool], n_bins: int = 10) -> float:
    """ECE：各桶(置信度-实际正确率)差值的加权平均，越接近 0 越校准"""
    diagram = reliability_diagram(confidences, correct, n_bins)
    total = sum(b["count"] for b in diagram)
    return sum(b["count"] / total * abs(b["avg_confidence"] - b["actual_accuracy"]) for b in diagram)
```

跑这套代码需要一份**带标注答案对错的测试集**——这是绕不开的前提，没有标注数据就没有办法验证校准程度，只能凭感觉设阈值。ECE 低于 0.05 通常认为校准较好；超过 0.15 就说明这个分数的数值本身不可直接信赖，需要额外做校准或改用相对排名而非绝对阈值。

## 四、三档阈值怎么科学地定

有了可靠性曲线之后，阈值设定就从"猜"变成"读图"：

| 档位 | 设定方法 | 典型场景 |
| --- | --- | --- |
| 自动放行 | 找到可靠性曲线上"实际正确率"开始稳定接近 1 的最低置信度分桶，取该分桶下界 | 低风险场景，错误代价小 |
| 人工审核 | 实际正确率明显低于对角线（模型过度自信）的区间，即使置信度看起来不低 | 中风险场景，需要兜底 |
| 直接拒答 | 置信度分布的低尾部，且对应分桶实际正确率明显偏低 | 高风险场景，错误代价大于拒答代价 |

**关键原则：阈值必须来自你自己测试集的可靠性曲线，不能照抄别人文章里的数字**——同样是 0.85，在你的任务、你的模型、你的 prompt 下对应的实际正确率可能完全不同。这也是为什么"设置阈值时先用测试集调参"说起来容易，真正执行时必须配上第三节的验证步骤，否则调出来的阈值本身就是拍脑袋的另一种形式。

## 五、logprobs 之外：还有哪些置信度信号值得组合

logprobs 只是众多不确定性信号之一，单独使用有局限，生产系统里常见的组合方式：

- **Self-consistency（多次采样一致性）**：同一问题采样多次，看答案是否一致。和 logprobs 的区别在于它衡量的是"模型在不同随机种子下是否稳定"，能捕捉 logprobs 捕捉不到的不确定性类型（比如模型对多个候选答案都很自信，但每次选不同的那个）。
- **Verbalized confidence（让模型自己说置信度）**：直接问模型"你有多确定"，成本低但可靠性通常不如 logprobs，且同样存在校准问题，需要单独验证。
- **组合策略**：logprobs 低置信度 **或** self-consistency 不一致，任一触发就转人工审核，比单一信号误判率更低，代价是多一次采样调用的成本。

对准确率要求高的场景，不建议只依赖 logprobs 单一信号，尤其是在还没验证过校准程度的情况下。

## 六、监控置信度分布随时间漂移

阈值不是设完就一劳永逸的。模型版本更新、输入分布变化，都会让原本校准好的阈值失效。最简单的监控做法：

- 定期（比如每周）从生产流量里抽样一批样本，人工标注对错，重新计算 ECE。
- 把置信度分布（不只是均值，包括分位数）画成时序图，突然的整体偏移往往意味着上游模型或输入分布变了。
- ECE 明显上升时，先重新走一遍第四节的阈值设定流程，而不是继续用旧阈值硬撑。

## 七、相关阅读

- [LLM logprobs 在生产场景的实用价值](/blog/llm-logprobs-applications/)
- [LLM 评估方法完全指南：从指标到框架](/blog/llm-evaluation-cn-guide/)
- [LLM 可观测性：Langfuse 完整接入教程](/blog/llm-observability-langfuse/)
- [AI Agent 错误恢复机制设计](/blog/ai-agent-error-recovery/)

想在生产环境稳定拿到 logprobs 数据做置信度校准，[YoTradeApi](https://yotradeapi.com) 提供兼容 OpenAI 格式的 API 中转服务，完整支持 logprobs 参数。
