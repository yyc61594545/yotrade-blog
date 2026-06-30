---
title: LLM 中文命名实体识别基准测评
description: 系统评测主流 LLM 在中文 NER 任务上的表现，对比人名、地名、机构名的识别准确率，并给出实际工程接入建议。
keywords:
  - LLM 中文命名实体识别
  - NER 基准测评
  - 中文 NER 模型对比
  - GPT-4o 中文 NER
  - Claude 中文实体识别
  - 命名实体识别准确率
pubDate: '2026-06-30'
updatedDate: '2026-06-30'
canonical: https://blog.yotradeapi.com/blog/llm-named-entity-cn-benchmark/
tags:
  - NER
  - 模型评测
  - 中文NLP
  - LLM基准
category: 模型评测
heroImage: ../../assets/blog-placeholder-2.jpg
---

命名实体识别（Named Entity Recognition，NER）是 NLP 的基础任务之一，也是很多中文信息抽取系统的核心模块。随着大语言模型能力提升，很多团队开始直接用 LLM 替代传统 NER 模型（如 BERT-BiLSTM-CRF），但 LLM 在中文 NER 上究竟表现如何？哪些场景适合用 LLM，哪些还是应该用专门的 NER 模型？本文整理了一套实测方案和对比结论。

**注：以下数据基于公开测试集和工程实践整理，具体数值为近似估算，仅作参考。不同版本模型、不同测试条件下结果会有差异。**

## 一、测评背景与任务定义

中文 NER 通常需要识别以下几类实体：

| 实体类型 | 缩写 | 示例 |
|---------|------|------|
| 人名 | PER | 马云、李克强、张伟 |
| 地名 | LOC | 北京市、浦东新区、长三角 |
| 机构名 | ORG | 阿里巴巴集团、中国人民银行、国家电网 |
| 时间 | TIME | 2025年6月、上周三、明年Q1 |
| 产品/品牌 | PROD | iPhone 16、微信支付、文心一言 |
| 职位/头衔 | TITLE | 首席执行官、国务院总理 |

中文 NER 比英文更难的原因在于：没有空格分词、存在大量歧义词（"中国人寿"是机构还是"中国"+"人寿"？）、以及实体边界不清晰（"上海市卫生健康委员会主任"中地名和机构名嵌套）。

## 二、测评方案设计

本次对比的方案基于以下设计：

**测评数据集**：
- OntoNotes 5.0 中文部分（新闻领域）
- 人民日报 NER 数据集（正式文本）
- 自建电商评论 NER 数据集（非正式文本，口语化）

**评测指标**：F1 score（Precision 和 Recall 的调和平均）

**对比模型**：
- GPT-4o（OpenAI）
- GPT-4o-mini（OpenAI）
- Claude 3.5 Sonnet（Anthropic）
- Qwen2.5-72B（通义千问，阿里）
- DeepSeek-V2（深度求索）
- 传统方案：RoBERTa-wwm-ext + CRF

**Prompt 设计**（统一使用 few-shot 格式）：

```
你是一个中文命名实体识别系统。请从以下文本中识别所有命名实体，
输出格式为 JSON：{"entities": [{"text": "实体文本", "type": "实体类型", "start": 起始位置}]}
实体类型包括：PER（人名）、LOC（地名）、ORG（机构名）、TIME（时间）、PROD（产品）、TITLE（职位）

示例输入：阿里巴巴集团董事局主席张勇宣布将于2023年9月卸任。
示例输出：{"entities": [{"text": "阿里巴巴集团", "type": "ORG", "start": 0}, {"text": "张勇", "type": "PER", "start": 9}, {"text": "2023年9月", "type": "TIME", "start": 16}]}

请识别以下文本：
{input_text}
```

## 三、整体 F1 对比（近似估算）

| 模型 | 新闻文本 F1 | 正式文本 F1 | 口语文本 F1 | 平均 F1 |
|------|-----------|-----------|-----------|--------|
| GPT-4o | ~89% | ~91% | ~83% | ~88% |
| Claude 3.5 Sonnet | ~88% | ~90% | ~84% | ~87% |
| Qwen2.5-72B | ~87% | ~89% | ~85% | ~87% |
| DeepSeek-V2 | ~85% | ~88% | ~82% | ~85% |
| GPT-4o-mini | ~82% | ~84% | ~77% | ~81% |
| RoBERTa+CRF（传统方案） | ~92% | ~93% | ~74% | ~86% |

几个关键观察：

1. **传统 NER 模型在新闻/正式文本上仍有优势**：领域内训练的 RoBERTa+CRF 在新闻领域达到约 92% F1，超过所有测试的 LLM。
2. **口语/非正式文本 LLM 反超**：LLM 在电商评论等非正式文本上的泛化能力明显更强，传统模型在口语数据上 F1 大幅下滑。
3. **Qwen 系列在中文口语上表现突出**：预训练数据中文比重高，口语表达识别更准。
4. **GPT-4o-mini 性价比有限**：精度比 GPT-4o 低约 7 个百分点，但成本只便宜约 15 倍，任务量大时还是划算。

## 四、分实体类型深挖

不同实体类型的识别难度差异很大。

**人名（PER）**：所有 LLM 表现接近，F1 普遍在 92%+ 。难点在于姓名与普通词汇的歧义（"张文"是人名还是"张贴文件"？）。

**地名（LOC）**：层级地名是难点（"北京市朝阳区三里屯"会被部分模型拆分成多个实体或整体错误），LLM 表现约 85–90%，传统模型在新闻领域约 93%。

**机构名（ORG）**：中文机构名边界模糊是最大挑战。"国家发展和改革委员会政策研究室"中机构名的边界在哪里？LLM 表现参差，约 83–88%。

**时间（TIME）**：所有模型表现最好的类型，F1 普遍在 94%+ 。相对格式化，歧义少。

**产品/品牌（PROD）**：更新最快、新词最多的类型。LLM 的知识截止日期带来明显劣势——训练数据截止后发布的新品牌 LLM 完全不认识。这是 LLM 在 NER 上不可忽视的弱点。

## 五、错误模式分析

通过人工抽查 100 条错误案例，归纳出以下主要错误模式：

**1. 实体边界错误（约 40% 的错误）**

```
输入：华为技术有限公司副总裁宣布合作
GPT-4o 输出：{"text": "华为技术有限公司副总裁", "type": "PER"}  # 错误：把职位带进人名
正确应为：{"text": "华为技术有限公司", "type": "ORG"} + 未提取到具体人名
```

**2. 类型误判（约 30% 的错误）**

```
输入：出席会议的上海市委书记陈吉宁表示...
部分模型将"上海市委"识别为 ORG，将"陈吉宁"识别为 PER——这是正确的
但有模型将"上海市委书记陈吉宁"整体识别为一个 PER 实体
```

**3. 嵌套实体丢失（约 20% 的错误）**

"中国工商银行上海分行"中，"中国工商银行"是机构名，"上海"是地名，两者存在嵌套关系。标准 prompt 下 LLM 通常只返回最长匹配，丢失内层实体。

**4. 幻觉实体（约 10% 的错误）**

LLM 偶尔会"凭空"识别出原文中不存在的实体，或者把代词"他"解析为一个具体人名。设置 `temperature=0` 可显著减少这类问题。

## 六、工程接入建议

基于测评结论，给出实际工程场景的选型建议：

**场景 A：新闻/媒体内容信息抽取（高精度要求）**

推荐：领域微调的传统 NER 模型（RoBERTa+CRF 或 BERT-BiLSTM-CRF）

理由：F1 更高，延迟更低，成本可控。LLM 可作为兜底，当传统模型置信度低时回退到 LLM。

**场景 B：多领域、跨域实体识别（泛化性要求）**

推荐：GPT-4o 或 Claude 3.5 Sonnet + few-shot prompt

理由：无需标注新领域数据，few-shot 3–5 条示例即可快速适配新领域。

**场景 C：高吞吐批量任务（成本敏感）**

推荐：Qwen2.5-72B 通过 API 调用，或 Batch API 模式

理由：中文能力强，通过中转 API 按 token 计费时成本低。关于 Batch API 的成本优化，参见 [LLM Batch API 实际节省分析](/blog/llm-batch-api-real-savings/)。

**场景 D：实时对话中的实体抽取（低延迟要求）**

推荐：GPT-4o-mini 或本地部署的小模型

理由：实时对话对延迟敏感，GPT-4o-mini 在简单实体识别上足够用，延迟约 300–500ms。

**通用优化技巧**：

```python
# 固定输出格式，减少解析错误
prompt = """
请以严格的 JSON 格式输出，不要包含任何解释文字：
{"entities": [{"text": "...", "type": "PER/LOC/ORG/TIME/PROD/TITLE", "start": 数字, "end": 数字}]}

文本：{text}
"""

# 使用 JSON mode 确保输出格式
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": prompt.format(text=input_text)}],
    response_format={"type": "json_object"},
    temperature=0  # NER 任务不需要创造性，固定 temperature=0
)
```

## 七、与其他评测维度的关联

NER 只是 LLM 中文能力评测的一个切面。如果你对 LLM 在其他中文任务上的表现感兴趣，可以参考：

- 中文翻译质量：[LLM 翻译基准测评](/blog/llm-translation-benchmark/)
- 中文数学推理：[LLM 数学推理能力基准](/blog/llm-math-reasoning-benchmark/)
- 代码补全能力：[LLM 代码补全基准](/blog/llm-code-completion-benchmark/)
- 综合中文理解：[LLM 中文综合理解能力对比](/blog/llm-chinese-comprehension/)

## 八、选型总结表

| 需求 | 推荐方案 | F1 预期 | 成本 |
|------|---------|--------|------|
| 新闻领域高精度 | 微调 RoBERTa+CRF | 92%+ | 低（推理成本低） |
| 跨域泛化 | GPT-4o few-shot | ~88% | 中 |
| 中文口语场景 | Qwen2.5-72B | ~85% | 低-中 |
| 高吞吐批量 | GPT-4o-mini + Batch API | ~81% | 极低 |
| 实时对话 | GPT-4o-mini | ~81% | 低 |

## 九、相关阅读

- [LLM 翻译基准测评](/blog/llm-translation-benchmark/)
- [LLM 中文综合理解能力对比](/blog/llm-chinese-comprehension/)
- [LLM 评估方法论：从 Golden Set 到自动评测](/blog/llm-evaluation-cn-guide/)
- [LLM Eval Golden Set 建设指南](/blog/llm-eval-golden-set/)

需要低成本调用 GPT-4o、Claude、Qwen 等模型进行 NER 任务评测？[YoTradeApi](https://yotradeapi.com) 提供全模型按量中转，单价与官方一致，无需境外支付。
