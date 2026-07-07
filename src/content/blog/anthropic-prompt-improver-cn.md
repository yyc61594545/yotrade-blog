---
title: Anthropic Prompt Improver 实战体验
description: 实测 Anthropic Console 的 Prompt Improver 功能：它具体改了什么、哪些场景效果明显、哪些场景不如手动调，附改写前后对比。
keywords:
  - Anthropic Prompt Improver
  - Claude 提示词优化
  - Prompt Improver 教程
  - Claude Console 功能
  - 提示词自动优化
pubDate: '2026-07-07'
updatedDate: '2026-07-07'
canonical: https://blog.yotradeapi.com/blog/anthropic-prompt-improver-cn/
tags:
  - Claude
  - Prompt Engineering
  - 技术深度
  - Anthropic Console
category: 技术深度
heroImage: ../../assets/blog-placeholder-5.jpg
---

Anthropic Console 里有一个不少人没注意到的功能：**Prompt Improver**。它不是简单地帮你润色措辞，而是按 Anthropic 自己总结的 Prompt 工程最佳实践，对你的原始 Prompt 做结构性重写。本文记录实际用它跑几个真实场景的体验，说清楚它到底改了什么、什么时候有用、什么时候不如自己手动调。

## 一、Prompt Improver 是什么，不是什么

它在 Anthropic Console 的 Prompt 工作台里，输入一段原始 Prompt（可以带几个示例输入输出），点击生成后，Improver 会输出一版重写后的 Prompt。它做的事情本质上是**自动应用 Anthropic 官方 Prompt 工程指南里的固定套路**：

- 把模糊的自然语言指令改写成结构化的分步指令
- 补充思维链（chain-of-thought）引导，让模型"先想后答"
- 用 XML 标签把不同部分的内容（背景信息、任务指令、输出格式要求）分隔清楚
- 如果你提供了示例，会把示例整理成规范的 few-shot 格式插入

它**不是**帮你生成一个全新的创意 Prompt，也**不是**万能药——如果你的原始 Prompt 本身任务定义就模糊（比如"帮我写点营销文案"这种没有约束条件的需求），Improver 能把措辞变规范，但解决不了"你自己都没想清楚要什么"的问题。

## 二、实测案例一：分类任务，效果提升明显

原始 Prompt（典型的新手写法）：

```
判断这条评论是好评还是差评：{{review}}
```

跑十条测试评论，遇到语气模糊的评论（比如先夸后吐槽）时输出不稳定，有时候还会输出"中评"这种没要求的类别。

用 Prompt Improver 处理后，输出结构大致是这样（简化版）：

```xml
<instructions>
你是一个评论情感分类助手。仔细阅读以下评论，判断其情感倾向。

分类规则：
1. 如果评论整体倾向正面，即使包含个别负面细节，也归类为"好评"
2. 如果评论整体倾向负面，即使包含个别正面细节，也归类为"差评"
3. 只允许输出"好评"或"差评"这两个类别之一，不允许输出其他标签
</instructions>

<review>{{review}}</review>

请在 <thinking> 标签中简要分析评论的情感倾向，然后在 <answer> 标签中给出最终分类。
```

**效果**：同样十条测试评论，混合语气的边界情况判断准确率明显提升，输出格式也不再跑出预期之外的类别。这类**分类、抽取、格式转换类任务**，Improver 的结构化重写带来的收益最直接——因为这类任务的痛点通常就是"边界情况定义不清楚"，而这正是 Improver 擅长补的部分。

## 三、实测案例二：开放式创作任务，提升有限

原始 Prompt：

```
写一段产品介绍，语气活泼一点，字数 300 字左右。
```

用 Improver 处理后，主要变化是把"语气活泼""字数 300 字左右"这些散落的要求整理成清单式的约束条件，并加了思维链引导（先想目标受众，再想核心卖点，最后组织成文案）。

**效果**：文案的格式规范性略有提升（比如更严格控制在字数范围内），但"活泼"的语气本身好不好，改善不明显——因为语气这种主观、模糊的要求，靠结构化重写解决不了，真正需要的是给具体的风格参考例子（few-shot），而不是更清楚的指令结构。这类**创意生成类任务**，Improver 的收益上限比分类任务低很多。

## 四、什么场景该用，什么场景该跳过

| 任务类型 | Prompt Improver 收益 | 原因 |
| --- | --- | --- |
| 分类、抽取、结构化输出 | 高 | 边界情况定义清楚 + 格式约束是这类任务的核心痛点，正好是 Improver 的强项 |
| 多步推理、复杂逻辑判断 | 中高 | 思维链引导对复杂推理任务帮助明显，能减少"跳步骤"导致的错误 |
| 开放式创作、风格模仿 | 低 | 主观风格问题靠结构重写解决不了，需要 few-shot 示例或人工迭代 |
| 已经手动精调过很多轮的 Prompt | 低 | 如果你已经针对具体场景踩过坑、加过针对性的约束，通用套路可能反而把你的定制内容冲淡 |

## 五、一个实用技巧：把 Improver 当起点而不是终点

比较高效的工作流是：先写一版最简单直白的 Prompt，跑 Improver 得到结构化的第一版，再针对你的具体场景做二次调整——比如把 `<instructions>` 里 Improver 生成的通用规则替换成你业务里真实的边界情况列表。直接用 Improver 的输出上生产，往往还差最后一步"结合具体业务场景打磨"，这一步机器还替代不了。

如果你想理解 Improver 背后套用的那套 Prompt 工程方法论本身，可以看 [Claude System Prompt 工程实战](/blog/claude-system-prompt-engineering/) 和 [大模型提示词模板工程](/blog/llm-prompt-template-engineering/)，这两篇讲的是手动构建这套结构的原理，理解原理之后再用 Improver，能更快判断它生成的结果哪里需要改。

## 六、和其它优化路径的关系

Prompt Improver 解决的是"Prompt 结构写得不够规范"的问题，它不能替代下面这几类工作：

- **上下文工程**：给模型喂什么背景信息、怎么组织长上下文，这是另一个维度的问题，看 [LLM Context Engineering 实践](/blog/llm-context-engineering/)
- **系统性评估**：Prompt 改完之后效果好不好，不能靠肉眼看几条样本，需要固定的评估集，看 [LLM 评估黄金测试集怎么建](/blog/llm-eval-golden-set/)
- **输出格式的强约束**：如果业务需要严格保证输出格式合法，光靠 Prompt 措辞不够保险，应该配合 [Structured Outputs](/blog/structured-output-llm-guide/) 这类接口层面的约束

## 七、相关阅读

- [Claude System Prompt 工程实战](/blog/claude-system-prompt-engineering/)
- [大模型提示词模板工程](/blog/llm-prompt-template-engineering/)
- [LLM Context Engineering 实践](/blog/llm-context-engineering/)
- [LLM 评估黄金测试集怎么建](/blog/llm-eval-golden-set/)
- [结构化输出完整指南](/blog/structured-output-llm-guide/)

用 Prompt Improver 生成的结构化 Prompt 做迭代测试，需要稳定低成本的 API 调用支撑，[YoTradeApi](https://yotradeapi.com) 按量计费，方便反复跑 A/B 对比不心疼调用成本。
