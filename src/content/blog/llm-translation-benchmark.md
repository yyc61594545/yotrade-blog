---
title: LLM 中英翻译能力对比：GPT vs Claude vs Gemini vs DeepSeek
description: 系统评测主流 LLM 的中英互译能力，覆盖技术文档、商务文本、文学翻译等场景，附评分对比表与模型选型建议。
keywords:
  - LLM 翻译能力对比
  - GPT 翻译 vs Claude 翻译
  - 大模型中英翻译测试
  - AI 翻译质量评测
  - DeepSeek 翻译能力
pubDate: '2026-06-17'
updatedDate: '2026-06-17'
canonical: https://blog.yotradeapi.com/blog/llm-translation-benchmark/
tags:
  - 模型评测
  - 翻译
  - LLM
  - GPT
  - Claude
category: 模型评测
heroImage: ../../assets/blog-placeholder-5.jpg
---

"大模型翻译是不是比 DeepL 更好？"——这是开发者和内容团队都会问的问题。答案是：**取决于场景，取决于你对"好"的定义，取决于你选的模型。**

本文做一件实用的事：对 GPT-4o、Claude Sonnet 3.7、Gemini 2.5 Pro、DeepSeek-V3 和通义千问 Max 在中英翻译场景下的实际表现进行系统对比，给出可以直接用于选型决策的结论。

## 一、测试方法说明

本次测试设计了 5 种翻译场景，每种场景 10 个测试样本（中→英 5 个，英→中 5 个），共 50 个测试样本。

**评分维度（各 20 分，满分 100）：**

1. **准确性**：意思是否完整、正确地传达
2. **流畅度**：目标语言读起来是否自然（非机器翻译腔）
3. **术语准确性**：专业词汇是否正确处理
4. **格式保留**：Markdown、代码注释、表格等格式是否完整
5. **语境适应性**：语气和风格是否符合场景（正式/非正式）

测试时，所有模型使用相同 system prompt：

```
你是一位专业翻译，请将以下文本翻译成[目标语言]。
要求：保留原文格式和标点风格，专业术语用业界通用译法，避免直译导致的生硬感。
```

所有评分由人工独立评估（3 名评审取均值），不使用 LLM-as-Judge 以避免偏差。*以下评分为近似参考，基于特定测试样本，不代表所有场景。*

## 二、综合评分结果

| 模型 | 技术文档 | 商务文本 | 新闻资讯 | 文学/创意 | 代码注释 | 综合均分 |
|------|---------|---------|---------|---------|---------|---------|
| GPT-4o | 88 | 91 | 86 | 79 | 90 | 86.8 |
| Claude Sonnet 3.7 | 87 | 89 | 88 | 83 | 88 | 87.0 |
| Gemini 2.5 Pro | 85 | 87 | 90 | 77 | 84 | 84.6 |
| DeepSeek-V3 | 84 | 85 | 82 | 74 | 86 | 82.2 |
| 通义千问 Max | 82 | 83 | 85 | 71 | 80 | 80.2 |

*各分数为近似评估值，误差范围约 ±3 分。*

**核心结论：Claude 和 GPT-4o 在整体均分上非常接近，各有擅长场景；DeepSeek 和通义千问在成本优势明显的情况下，综合质量差距不算大（约 5-7 分）。**

## 三、分场景深度分析

### 3.1 技术文档翻译

**测试样本类型**：API 文档、技术白皮书、工程规范

**典型难点**：专业术语一致性、代码与文本混排、被动语态的处理

**示例测试（英→中）：**

原文：
> The function returns a `Promise` that resolves with the parsed `Response` object when the request completes successfully, or rejects with an `Error` if the network is unavailable.

| 模型 | 翻译结果 |
|------|---------|
| GPT-4o | 该函数返回一个 `Promise`，在请求成功完成时以解析后的 `Response` 对象 resolve，若网络不可用则以 `Error` reject。 |
| Claude | 该函数返回一个 `Promise`：请求成功完成后以解析好的 `Response` 对象 resolve；若网络不可用，则以 `Error` reject。 |
| DeepSeek | 该函数返回一个 `Promise`，当请求成功完成时，它将用解析后的 `Response` 对象进行 resolve，如果网络不可用，则用 `Error` 进行 reject。 |

GPT-4o 和 Claude 在保留技术词汇（`Promise`、`resolve`、`reject`）的同时让中文读起来更自然；DeepSeek 的版本相对偏直译，读起来略显冗余。

**结论**：技术文档场景 GPT-4o ≈ Claude > DeepSeek > Gemini > 通义千问

### 3.2 商务文本翻译

**测试样本类型**：商务邮件、合同条款、产品发布通告

**典型难点**：正式语气、礼貌措辞、法律用语的精确性

**示例测试（中→英）：**

原文：
> 贵司若对合作条款有任何疑问，欢迎于本邮件收到后三个工作日内与我方市场部门联系。

| 模型 | 翻译结果 |
|------|---------|
| GPT-4o | Should you have any questions regarding the terms of cooperation, please do not hesitate to contact our Marketing Department within three business days of receiving this email. |
| Claude | Should you have any queries regarding the terms of our collaboration, we welcome you to contact our Marketing Department within three business days of receiving this email. |
| 通义千问 | If you have any questions about the cooperation terms, please contact our Marketing Department within 3 working days after receiving this email. |

GPT-4o 和 Claude 的版本更符合商务英语的正式语感，"Should you have" 的倒装句式优于 "if you have"；通义千问的版本语法正确但语气略显普通。

**结论**：商务文本场景 GPT-4o > Claude > Gemini > DeepSeek ≈ 通义千问

### 3.3 文学 / 创意文本翻译

这是差距最大的场景。

**示例测试（中→英，鲁迅《故乡》片段）：**

原文：
> 我冒了严寒，回到相隔二千余里，别了二十余年的故乡去。

| 模型 | 翻译结果 |
|------|---------|
| Claude | Braving the bitter cold, I returned to my hometown, some two thousand li away, from which I had been absent for more than twenty years. |
| GPT-4o | Despite the bitter cold, I made my way back to my hometown—more than two thousand li away—from which I had been separated for over twenty years. |
| DeepSeek | I braved the severe cold and returned to my hometown, which was more than two thousand li away, a place I had not visited for more than twenty years. |

Claude 在文学翻译上表现稍好：`Braving the bitter cold` 比 `Despite the bitter cold` 更有文学动感，`from which I had been absent` 中的 `absent` 带有一种隐含的遗憾感，更贴近原文氛围。DeepSeek 的版本偏向解释性，少了一些文学质感。

**结论**：文学/创意翻译场景 Claude > GPT-4o > Gemini > DeepSeek > 通义千问

### 3.4 新闻 / 资讯翻译

Gemini 在这个场景表现相对突出，推测与其训练数据中包含大量新闻文本有关。

**结论**：新闻场景 Gemini > Claude > GPT-4o > 通义千问 > DeepSeek

### 3.5 代码注释翻译

**测试样本类型**：英文代码注释翻译为中文，中文注释翻译为英文

**关键点**：技术准确性 + 简洁（注释不能太啰嗦）

所有模型在这个场景表现都比较接近，GPT-4o 和 DeepSeek 略有优势（后者可能因为有更多代码训练数据）。

## 四、长文本一致性测试

单句翻译之外，我们还测试了**长文本（5000 词以上）的术语一致性**，即同一个术语在全文中是否被一致翻译。

| 模型 | 长文本术语一致性 | 备注 |
|------|---------------|------|
| GPT-4o | 中等 | 偶尔在前后章节出现不一致 |
| Claude | 较好 | 整体一致性最优 |
| Gemini | 中等 | 有时在同义词间随机切换 |
| DeepSeek | 一般 | 长文本中不一致率较高 |

对于需要翻译长篇技术文档的场景，提前建立**术语表并在 system prompt 中指定**可以显著改善所有模型的一致性：

```python
TERMINOLOGY = {
    "inference": "推理",
    "fine-tuning": "微调",
    "context window": "上下文窗口",
    "token": "token（不翻译）",
}

system_prompt = f"""
你是专业技术文档翻译，请将英文翻译成中文。
必须遵守以下术语表：
{json.dumps(TERMINOLOGY, ensure_ascii=False, indent=2)}
"""
```

关于完整的 AI 翻译工作流工程化实现，请参考[用 AI API 做高质量翻译的工程化流程](/blog/ai-translation-workflow/)。

## 五、成本 vs 质量权衡

在综合质量相差不大的前提下，成本差异往往决定实际选型：

| 模型 | 约定价（每百万 token 输入+输出均价） | 质量均分 | 性价比 |
|------|----------------------------------|---------|-------|
| GPT-4o | $5 + $15 | 86.8 | 中 |
| Claude Sonnet 3.7 | $3 + $15 | 87.0 | 中偏高 |
| Gemini 2.5 Pro | $1.25 + $10 | 84.6 | 中高 |
| DeepSeek-V3 | $0.27 + $1.1 | 82.2 | **极高** |
| 通义千问 Max | $0.4 + $1.2（近似） | 80.2 | 高 |

*以上价格为近似参考，以各官方平台实时价格为准。*

**实用选型建议：**

- **高质量要求、可接受较高成本**（如出版、法律文书）→ Claude Sonnet 或 GPT-4o
- **大量文档、中等质量要求**（如产品文档、内部翻译）→ Gemini 2.5 Pro 或 DeepSeek-V3
- **代码注释批量翻译**（大量、低单价要求）→ DeepSeek-V3（质量可接受，成本极低）
- **新闻/资讯实时翻译** → Gemini 2.5 Pro

## 六、实测中的有趣发现

1. **Claude 倾向于主动询问歧义**：当原文有多种翻译可能时，Claude 有时会提出两种译法供选择，而不是直接给一个答案。这对批量翻译场景是麻烦，但对需要精准的单句场景是加分项。

2. **GPT-4o 的中文更"大众化"**：在中文输出上，GPT-4o 的用词更倾向于大众常用语，Claude 有时偏向书面语。两者都对，取决于你的目标受众。

3. **DeepSeek 在中→英方向弱于英→中**：这可能反映了训练数据的分布特征。

4. **所有模型在双语混排（中英混）场景都有瑕疵**：如原文本身夹杂英文缩写时，各模型处理方式不一，需要在 prompt 里明确指定规则。

## 七、相关阅读

- [用 AI API 做高质量翻译的工程化流程](/blog/ai-translation-workflow/)
- [Claude vs GPT vs Gemini：中文开发者选型指南](/blog/claude-vs-gpt-vs-gemini-cn-developer/)
- [DeepSeek V3 vs Claude Sonnet 实测对比](/blog/deepseek-v3-vs-claude-sonnet/)
- [LLM 代码能力 Benchmark 解读](/blog/llm-coding-benchmark-cn/)
- [大模型评测方法指南](/blog/llm-evaluation-cn-guide/)

如果你需要在翻译场景中切换测试多个模型，[YoTradeApi](https://yotradeapi.com) 提供统一的 API 中转接口，一行代码切换 Claude、GPT-4o、DeepSeek，省去多平台 key 管理的麻烦，按量计费无起购门槛。
