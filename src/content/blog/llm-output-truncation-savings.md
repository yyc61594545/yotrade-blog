---
title: LLM 输出截断省钱实战：max_tokens 精细化控制指南
description: 深入讲解 max_tokens 精细化设置技巧，通过输出截断策略将 LLM API 账单降低 30%–60%，附真实场景测试数据与 Python 代码示例。
keywords:
  - LLM 输出截断省钱
  - max_tokens 优化
  - LLM API 成本控制
  - token 输出限制
  - 大模型成本优化实战
pubDate: '2026-06-22'
updatedDate: '2026-06-22'
canonical: https://blog.yotradeapi.com/blog/llm-output-truncation-savings/
tags:
  - 成本优化
  - Token 管理
  - API 实战
  - 开发者工具
category: 成本优化
heroImage: ../../assets/blog-placeholder-4.jpg
---

在 LLM API 的账单构成中，输出 token 的单价通常是输入 token 的 3–5 倍。以 Claude Sonnet 为例，输入约 $3/M tokens，输出则约 $15/M tokens。这意味着**控制输出长度**是成本优化中回报率最高的手段之一，而 `max_tokens` 参数是最直接的抓手。

然而，许多开发者要么把 `max_tokens` 设得过高（"万一不够用呢"），要么完全不设置（用模型默认值），导致大量"无效输出"白白消耗预算。本文通过真实场景测试，给出针对不同任务类型的精细化截断策略。

---

## 一、输出 Token 超量的典型场景

在真实项目中，以下几类场景最容易造成输出浪费：

**1. Prompt 写得不够收敛**

```
❌ "介绍一下量子计算"（模型会输出 1000+ token 的长篇大论）
✅ "用 3 句话介绍量子计算的基本原理，面向非技术读者"
```

**2. 不必要的 CoT（Chain of Thought）输出**

某些任务只需要最终结果，但模型习惯性地输出推理过程：

```
❌ 模型输出："首先，我需要分析这道题……其次……因此答案是 42。"（共 300 token）
✅ 期望输出："42"（1 token）
```

**3. 格式"臃肿"**

```
❌ 模型输出完整 JSON 后又加了 "以上就是结果，如需调整请告诉我……"（浪费 50+ token）
✅ 通过 system prompt 约束："只输出 JSON，不要附加任何说明文字"
```

**4. max_tokens 设置远超实际需求**

如果某个接口 99% 的响应都在 200 token 以内，却把 `max_tokens` 设成 4096，虽然不直接多收钱（按实际 token 数计费），但意味着 Prompt 设计本身可能存在问题，也会影响后续的批量处理策略。

---

## 二、如何科学设置 max_tokens

### 步骤一：采样分析历史输出长度

用以下脚本分析你的历史 API 响应，找到实际输出长度的分布：

```python
import json
from collections import Counter

# 假设你已经把历史响应存入 JSONL 文件
output_lengths = []
with open("api_responses.jsonl") as f:
    for line in f:
        resp = json.loads(line)
        output_lengths.append(resp["usage"]["completion_tokens"])

output_lengths.sort()
n = len(output_lengths)

print(f"P50（中位数）: {output_lengths[n//2]} tokens")
print(f"P90: {output_lengths[int(n*0.9)]} tokens")
print(f"P95: {output_lengths[int(n*0.95)]} tokens")
print(f"P99: {output_lengths[int(n*0.99)]} tokens")
print(f"最大值: {max(output_lengths)} tokens")
```

典型场景的参考数据（基于实际项目，仅供参考）：

| 任务类型 | P50 | P90 | P99 | 建议 max_tokens |
|---------|-----|-----|-----|----------------|
| 情感分类（单词输出） | 3 | 5 | 10 | 20 |
| 关键词抽取（5–10 个） | 30 | 60 | 100 | 150 |
| 摘要（3–5 句） | 80 | 150 | 250 | 300 |
| 结构化 JSON 提取 | 100 | 300 | 600 | 800 |
| 代码补全（函数级） | 150 | 400 | 800 | 1000 |
| 长文分析报告 | 500 | 1200 | 2000 | 2500 |

**建议**：将 max_tokens 设为 P99 的 1.2 倍，既覆盖绝大多数情况，又避免无上限浪费。

### 步骤二：按任务类型分组设置

不要对所有接口用同一个 max_tokens。将你的 LLM 调用分组：

```python
MAX_TOKENS_CONFIG = {
    "classify": 20,        # 分类任务
    "extract_keywords": 150,  # 关键词提取
    "summarize": 300,       # 摘要
    "json_extract": 800,    # 结构化提取
    "code_gen": 1000,       # 代码生成
    "report": 2500,         # 长文分析
}

def call_llm(task_type: str, messages: list) -> str:
    max_tokens = MAX_TOKENS_CONFIG.get(task_type, 500)
    resp = client.chat.completions.create(
        model="claude-sonnet-4-5",
        messages=messages,
        max_tokens=max_tokens
    )
    return resp.choices[0].message.content
```

---

## 三、Prompt 工程配合截断

`max_tokens` 是"硬截断"，但更优雅的方式是通过 Prompt 让模型**主动输出更短的内容**。

### 3.1 明确字数/句数限制

```python
SYSTEM_PROMPTS = {
    "summarize": "用不超过 3 句话总结以下内容。不要附加任何说明。",
    "classify": "判断文本的情感倾向，只输出：正面 / 负面 / 中性，不要输出其他内容。",
    "json_extract": "从文本中提取信息，只输出 JSON，格式：{\"name\": \"\", \"date\": \"\"}，不要输出其他内容。"
}
```

### 3.2 禁止模型"自我解释"

模型有时会在答案后面加上"如需进一步帮助，请告诉我"之类的套话。可以在 system prompt 中明确禁止：

```
你是一个 API 处理器，只输出所请求的内容。
- 不要在答案前后加任何前缀或后缀说明
- 不要输出"当然"、"好的"、"以下是"等引导语
- 如果任务是输出 JSON，只输出有效的 JSON，不要包含代码块标记
```

### 3.3 Few-shot 示例控制输出格式

```python
messages = [
    {"role": "system", "content": "提取文本中的产品名称和价格，只输出 JSON。"},
    # Few-shot 示例
    {"role": "user", "content": "iPhone 16 现在售价 5999 元"},
    {"role": "assistant", "content": '{"product": "iPhone 16", "price": 5999}'},
    {"role": "user", "content": "MacBook Air M4 促销价 7999 元起"},
    {"role": "assistant", "content": '{"product": "MacBook Air M4", "price": 7999}'},
    # 真实任务
    {"role": "user", "content": user_input}
]
```

Few-shot 示例的输出通常比 Zero-shot 短 20–40%，且格式更稳定。

---

## 四、流式输出 + 主动中断

对于某些场景，你可以启用流式输出，在检测到满足条件时**主动停止**接收，节省剩余输出费用（注意：部分提供商按完整 completion 计费，非按实际接收量，需确认服务商策略）：

```python
import tiktoken

def stream_until_done(client, messages, stop_condition, max_tokens=1000):
    """
    流式接收输出，满足 stop_condition 时提前停止。
    stop_condition: callable，接收当前累积文本，返回 bool
    """
    enc = tiktoken.get_encoding("cl100k_base")
    accumulated = ""
    total_tokens = 0

    with client.chat.completions.create(
        model="claude-sonnet-4-5",
        messages=messages,
        max_tokens=max_tokens,
        stream=True
    ) as stream:
        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            accumulated += delta
            total_tokens += len(enc.encode(delta))

            if stop_condition(accumulated):
                break  # 提前中止流

    return accumulated, total_tokens

# 示例：找到完整 JSON 对象后立即停止
import json

def is_complete_json(text):
    try:
        json.loads(text.strip())
        return True
    except json.JSONDecodeError:
        return False

result, tokens_used = stream_until_done(
    client,
    messages=[{"role": "user", "content": "提取：苹果手机售价4999"}],
    stop_condition=is_complete_json
)
```

---

## 五、真实场景节省数据

以下是某内容处理项目在引入输出截断优化前后的对比（估算数据，仅供参考）：

| 优化措施 | 月均输出 token | 变化 | 月账单变化（估算） |
|---------|-------------|------|----------------|
| 基线（无优化） | 4,200 万 | — | $630 |
| 加 max_tokens 分组设置 | 3,100 万 | -26% | $465 |
| 加 Prompt 约束 | 2,400 万 | -43% | $360 |
| 加 Few-shot 示例 | 1,800 万 | -57% | $270 |
| **综合优化后** | **1,700 万** | **-59%** | **$255** |

关键结论：**Prompt 优化的边际收益往往高于 max_tokens 设置本身**，两者配合才能达到最优效果。

---

## 六、不同模型的 max_tokens 默认值差异

在切换模型时，需要注意各家的默认输出长度设置不同：

| 模型 | 默认 max_tokens | 最大 max_tokens |
|------|---------------|---------------|
| Claude Sonnet / Haiku | 8192 | 8192（可扩展至 64K） |
| GPT-4o | 4096 | 16384 |
| Gemini 1.5 Pro | 8192 | 8192 |
| 混元-Turbo | 2048 | 8192 |
| GLM-4-Plus | 4096 | 128K |

如果你未显式设置 `max_tokens`，不同模型的默认行为差异较大，可能导致同样的任务产生截然不同的账单。**最佳实践：始终显式设置 max_tokens。**

---

## 七、与批量 API 配合使用

输出截断与批量 API 是两个互补的省钱手段。批量 API 通常提供 40–50% 的折扣，但延迟较高（通常数小时）；输出截断则对延迟没有影响，可以同时应用：

详细的批量 API 使用方法，可参考[LLM Batch API 真实省钱效果测试](/blog/llm-batch-api-real-savings/)。

---

## 八、相关阅读

- [LLM Batch API 真实省钱效果测试](/blog/llm-batch-api-real-savings/)
- [Prompt Token 精简配方：输入端的降本实战](/blog/llm-prompt-token-trimming-recipes/)
- [LLM 成本优化完整检查清单](/blog/llm-cost-optimization-checklist/)
- [腾讯元宝大模型 API 评测：混元能力、接入体验与定价分析](/blog/cn-tencent-yuanbao-review/)

想要一个 Key 管理多家模型、统一账单并享受折扣价，可以试试 [YoTradeApi](https://yotradeapi.com)，支持 Claude、GPT、混元、豆包等主流模型，人民币充值即用。
