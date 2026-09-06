---
title: 中英互译质量实测：怎么自己搭一套可复现的评测流程
description: 不追热榜，教你自己搭一套中英互译评测流水线：样本设计、LLM-as-judge 打分模板、人工抽检校验与 CI 接入方法，附可复用脚本。
keywords:
  - 中英互译质量评测
  - LLM 翻译评测方法
  - LLM-as-judge 打分
  - 翻译质量自动化测试
  - AI 翻译回归测试
pubDate: '2026-09-06'
updatedDate: '2026-09-06'
canonical: https://blog.yotradeapi.com/blog/llm-cn-en-translation-bench/
tags:
  - 模型评测
  - 翻译
  - LLM
  - 评测方法论
category: 模型评测
---

网上不缺"GPT vs Claude vs Gemini 翻译能力对比"这类文章——我们自己也写过一篇[LLM 中英翻译能力对比](/blog/llm-translation-benchmark/)。但这类横评有个致命问题：**它测的是别人的场景，不是你的场景**。你的产品要翻译的可能是客服工单、法律条款、电商商品描述，评测榜单里那 50 个通用样本跟你的业务八竿子打不着。

本文不重复讲"谁的分数更高"，而是讲一件更有用的事：**怎么自己搭一套能跑起来、能复现、能接进 CI 的中英互译评测流程**。搭好之后，换模型、换 prompt、换 API 中转商，你都能在 10 分钟内知道翻译质量有没有掉。

## 一、为什么通用榜单救不了你的场景

先说清楚通用评测的三个局限，明白这些你就知道为什么要自建:

1. **领域漂移**：通用测试集覆盖新闻、文学、商务邮件，但你的业务术语（比如"中转 API"、"限流阈值"、"灰度发布"）在通用集里几乎不会出现，模型在这些词上的表现完全是未知数。
2. **格式盲区**：真实业务翻译经常带着 Markdown、HTML 标签、变量占位符（如 `{{username}}`）、代码注释。通用测试很少专门考察格式保留率，但这恰恰是生产环境翻译最容易出错、也最难被人工发现的地方。
3. **时效性问题**：模型会迭代，API 中转商的路由和限流策略会变，今天测出来 95 分的组合，三周后模型版本一换可能就掉到 80 分。别人发布的横评是一次性快照，你需要的是持续能跑的流程。

## 二、样本设计：别只测"好翻译"，要测"边界情况"

一套有效的评测集，样本设计比样本数量更重要。建议按下面四类构建，每类 8–15 条，总量控制在 40–60 条即可（人工评分成本随样本数线性增长，不需要贪多）：

| 类别 | 示例 | 考察点 |
|---|---|---|
| 业务术语 | "调用限流"、"密钥轮换"、"灰度发布" | 术语一致性，不能一句一个译法 |
| 格式混排 | 带 Markdown 表格、代码块、`{{变量}}` 的段落 | 格式是否原样保留 |
| 长上下文 | 3–5 段带指代关系的连续文本 | 代词、术语在段落间是否保持一致 |
| 语气与风格 | 客服致歉话术、法律免责声明 | 正式度是否匹配场景，而非字面直译 |

每条样本固定一个"预期要点"（不是标准答案，而是评分时必须命中的 2-3 个关键点），比如术语翻译是否统一、变量是否原样保留、语气是否得体。这一步决定了后面自动化打分是否可靠。

## 三、自动化打分：LLM-as-judge 怎么设计才不会自欺欺人

人工评分最准，但没法长期跑。实用做法是用另一个模型当裁判（LLM-as-judge），但裁判 prompt 设计不当很容易出现"和稀泥打分"（所有样本都给 80-90 分，区分度归零）。三个关键调整：

**1. 强制给出理由再给分**，避免模型跳过推理直接吐一个数字：

```text
你是翻译质量评审员。请对以下翻译按 4 个维度打分（每项 0-25，满分 100）：
1. 准确性：意思有无遗漏或扭曲
2. 术语一致性：专业词汇译法是否前后统一
3. 格式保留：Markdown/代码/变量占位符是否原样保留
4. 语气匹配：正式度是否符合场景

原文：{source}
译文：{translation}
预期要点：{expected_points}

先逐项写出扣分理由，最后一行单独输出 JSON：
{"accuracy": 分数, "terminology": 分数, "format": 分数, "tone": 分数}
```

**2. 裁判模型和被测模型要分开**，用同一个模型当运动员又当裁判，会系统性偏向自己的表达习惯，分数虚高。

**3. 每批抽 15% 做人工复核**，重点看裁判打分和人工判断的方向是否一致（不要求分数完全相同，只要求排序一致）。如果连续两批出现方向性偏差，说明裁判 prompt 需要调整,而不是继续信任自动化分数。

## 四、跑一次最小可行评测

下面是一个可以直接改造使用的评测骨架，核心逻辑是"批量调用被测模型 → 批量调用裁判模型 → 汇总结果"：

```python
import json
from pathlib import Path

def translate(client, model, text, direction="zh2en"):
    prompt = f"将以下{'中文' if direction=='zh2en' else '英文'}翻译成{'英文' if direction=='zh2en' else '中文'}，保留所有格式和变量占位符：\n\n{text}"
    resp = client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}])
    return resp.choices[0].message.content

def judge(client, judge_model, source, translation, expected_points):
    prompt = JUDGE_TEMPLATE.format(source=source, translation=translation, expected_points=expected_points)
    resp = client.chat.completions.create(model=judge_model, messages=[{"role": "user", "content": prompt}])
    last_line = resp.choices[0].message.content.strip().splitlines()[-1]
    return json.loads(last_line)

def run_benchmark(client, candidate_models, judge_model, samples):
    results = {}
    for model in candidate_models:
        scores = []
        for s in samples:
            translation = translate(client, model, s["source"], s["direction"])
            score = judge(client, judge_model, s["source"], translation, s["expected_points"])
            scores.append(score)
        results[model] = scores
    return results
```

跑完之后按模型汇总四个维度的均值，重点看**方差**而不只是均值——某个模型均分不错但格式保留分数波动很大，说明它在特定样本类型上不稳定，生产环境用起来会踩坑。这类实测数据受样本设计和裁判 prompt 影响较大，*文中不给出具体分数，跑一遍你自己的样本集才是真正有意义的数字*。

## 五、把评测跑进 CI，而不是跑一次就扔

评测流程搭好后最大的浪费，就是只跑一次然后归档吃灰。合理的做法是把它接进 CI：每次 prompt 模板改动、模型版本升级、或 API 中转商切换路由，自动触发一次小样本回测（15-20 条即可，控制成本），分数低于阈值就阻断合并。具体的门禁设计、触发时机和数据集版本管理，可以参考[把模型评测接进 CI 流水线](/blog/llm-eval-in-ci-pipeline/)，评测集本身的构建方法论则可以参考[LLM 评测 Golden Set 构建方法](/blog/llm-eval-golden-set/)。

## 六、常见坑清单

- **编码问题**：中英混排文本经过多次 API 转发后偶发全角/半角符号错乱，评测前先做一次编码归一化，否则会被误判为翻译错误。
- **变量占位符被"翻译"**：部分模型会把 `{{username}}` 当成普通文本处理，字面翻译成 `{{用户名}}`，这是格式保留维度最常见的失分点，务必在 prompt 里显式强调"占位符原样保留，不做翻译"。
- **裁判模型漂移**：裁判模型自身升级后，历史分数就失去了可比性。跑长期回归时锁定裁判模型的具体版本号，而不是用"latest"这种浮动标签。
- **样本泄漏**：如果测试样本长期不变，被测模型的服务商可能通过日志学习到你的测试集（尤其是自部署或有数据反馈协议的场景），定期轮换 10%-20% 的样本能缓解这个问题。

## 七、相关阅读

- [LLM 中英翻译能力对比：GPT vs Claude vs Gemini vs DeepSeek](/blog/llm-translation-benchmark/)
- [LLM 评测 Golden Set 构建方法](/blog/llm-eval-golden-set/)
- [把模型评测接进 CI 流水线](/blog/llm-eval-in-ci-pipeline/)
- [用 AI API 做高质量翻译的工程化流程](/blog/ai-translation-workflow/)

自建评测流程离不开稳定、低延迟的模型调用通道，用 [YoTradeApi](https://yotradeapi.com) 中转 Claude / GPT / Gemini 等主流模型 API，同一套代码切换被测模型和裁判模型都不用改认证逻辑。
