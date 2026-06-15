---
title: Prompt token 裁剪 12 个秘诀
description: 系统整理 12 种减少 LLM Prompt token 消耗的实战技巧，在不损失输出质量的前提下显著降低 API 调用成本。
keywords:
  - prompt token 优化
  - LLM token 裁剪
  - 减少 token 消耗
  - prompt 成本优化
  - LLM API 省钱
pubDate: '2026-06-15'
updatedDate: '2026-06-15'
canonical: https://blog.yotradeapi.com/blog/llm-prompt-token-trimming-recipes/
tags:
  - 成本优化
  - Prompt工程
  - Token
  - LLM
category: 成本优化
heroImage: ../../assets/blog-placeholder-3.jpg
---

token 是 LLM API 计费的基本单位。每次调用的费用 = (输入 token × 输入单价) + (输出 token × 输出单价)。在规模化使用场景下，Prompt 的 token 消耗往往比输出更容易控制——因为输出取决于任务，而输入完全由你设计。

本文整理了 12 个经过验证的 token 裁剪方法，每条都附有"适用场景"和"注意事项"，直接可以落地使用。

## 一、删除冗余的"客气话"前缀

**Token 节省估算：5–30 tokens/请求**

很多开发者习惯在 user message 里加这样的开头：

> "你好，麻烦你帮我……，谢谢！"

这些礼貌用语对模型输出质量**没有任何提升**，却白白消耗 token。直接陈述任务即可：

```
# 优化前（21 tokens）
你好，麻烦帮我把以下文本翻译成英文，谢谢！

# 优化后（9 tokens）
将以下文本翻译成英文：
```

**适用场景**：所有场景。  
**注意**：去掉礼貌前缀不影响模型行为，这已被大量测试验证。

## 二、用结构化格式替代自然语言描述

**Token 节省估算：20–100 tokens/请求**

自然语言描述的信息密度远低于结构化格式。把"请你从用户的角度……"改成明确的字段定义：

```
# 优化前
请你分析下面这段用户反馈，提取用户的情感（正面/负面/中性），
找出用户提到的具体问题点，以及用户最想要的改进建议。

# 优化后
分析用户反馈，输出 JSON：
{"sentiment": "正面|负面|中性", "issues": [...], "suggestions": [...]}
```

同时，结构化输出还让后续处理更容易，一举两得。

## 三、压缩 System Prompt 中的示例

**Token 节省估算：100–500 tokens/请求**

Few-shot 示例是 token 消耗大户。每个完整示例可能消耗 50–200 tokens，而在很多任务上，1–2 个示例的效果与 5 个几乎相当。

| 示例数量 | 典型 token 消耗 | 质量提升边际 |
|----------|-----------------|--------------|
| 0 个（zero-shot） | 0 | 基线 |
| 1 个 | ~80 | 显著提升 |
| 2 个 | ~160 | 小幅提升 |
| 5 个 | ~400 | 几乎无提升 |

**建议**：先用 2 个示例测试效果，达标则不再增加。

## 四、缩短变量名和字段名

**Token 节省估算：10–50 tokens/请求**

在构建动态 Prompt 时，模板里的字段名也是 token。

```python
# 优化前：字段名冗长
prompt = f"""
用户的历史购买记录如下：{user_purchase_history}
用户的当前浏览商品是：{current_browsing_item}
"""

# 优化后：简化字段名（模型理解不受影响）
prompt = f"""
购买记录：{purchase_history}
当前商品：{current_item}
"""
```

这在大批量调用时（如每天百万次请求）累积节省相当可观。

## 五、用 Markdown 代替重复的自然语言说明

**Token 节省估算：30–80 tokens/请求**

对于输出格式的要求，Markdown 标记比自然语言更紧凑：

```
# 优化前（自然语言，约 40 tokens）
请你的回答用表格形式呈现，表格需要有三列，
分别是"方案名称"、"优点"和"缺点"。

# 优化后（Markdown 指令，约 15 tokens）
以 Markdown 表格输出，列：方案名称 | 优点 | 缺点
```

## 六、截断或摘要化长上下文

**Token 节省估算：200–2000 tokens/请求**

最大的 token 节省往往来自上下文管理。常见的反模式是把整段文档或对话历史原封不动地塞进 Prompt。

**更好的做法**：

```python
def trim_context(messages: list, max_tokens: int = 2000) -> list:
    """保留最近 N 条消息，超出则截断最早的"""
    total = 0
    result = []
    for msg in reversed(messages):
        tokens = estimate_tokens(msg["content"])
        if total + tokens > max_tokens:
            break
        result.insert(0, msg)
        total += tokens
    return result
```

对于文档类任务，先用轻量模型（或向量检索）提取相关段落，再送入主模型，比全文塞入省 60–80% 的输入 token。

## 七、提示词模板复用 + Prompt Caching

**Token 节省估算：最高 90% 缓存 token 费用**

如果你的 System Prompt 在多次请求中保持不变（如角色设定、格式要求），开启 **Prompt Caching** 可以把这部分 token 的费用降低到原来的 10%（Claude 的缓存价格是 0.1× 输入价格）。

关于 Prompt Caching 的详细配置，参考[Prompt Caching 成本优化实战](/blog/prompt-caching-cost-optimization/)——该功能对 System Prompt 超过 1024 tokens 的场景最划算。

## 八、移除不必要的格式要求重复

**Token 节省估算：20–60 tokens/请求**

在 System Prompt 里已经说了"用中文回答"，user message 里就不用重复。在 System Prompt 里已经说了"不要道歉"，每条消息末尾就不用加"请直接回答，不要废话"。

梳理你的 System Prompt，找出所有能覆盖全局的规则，从每条 user message 里删除重复项。

## 九、数字和列表的紧凑写法

**Token 节省估算：5–20 tokens/条**

在动态注入数据时，格式选择影响 token 数：

```python
# 优化前：JSON 格式（token 较多）
data = '{"items": ["苹果", "香蕉", "橙子"], "count": 3}'

# 优化后：简洁分隔符格式（token 少 30%）
data = "商品：苹果、香蕉、橙子（共 3 件）"
```

对于模型只需要"读"而不需要"解析"的数据，纯文本格式比 JSON 更节省 token。

## 十、避免"重申任务"的 user message

**Token 节省估算：20–50 tokens/请求**

有一种常见的多轮对话写法是在每轮 user message 里重新说明任务背景：

> "我们在讨论代码审查系统，你还记得吗？上次你说……，现在我想问……"

把背景信息放进 System Prompt 一次，之后每轮 user message 只传新内容即可。

## 十一、精简 Chain-of-Thought 的输出

**Token 节省估算：50–300 tokens/请求（输出侧）**

CoT（链式思维）能提升推理准确率，但也会大幅增加输出 token。对于不需要解释过程的任务，可以这样限制：

```
分析以下代码是否有内存泄漏。
只输出结论（有/无）和修复建议，不要展示分析过程。
```

如果任务确实需要推理过程，可以要求只输出"最终结论"而不是"每步推导"：

```
推理后直接给出最终答案，无需展示中间步骤。
```

## 十二、动态裁剪：按任务复杂度调整 Prompt

**Token 节省估算：因场景差异大**

不是所有任务都需要同等详细的 Prompt。可以根据用户输入的复杂度，动态选择不同"档次"的 Prompt 模板：

```python
def select_prompt(user_input: str) -> str:
    word_count = len(user_input)
    if word_count < 50:
        return SIMPLE_PROMPT  # 轻量任务，简短 system prompt
    elif word_count < 200:
        return STANDARD_PROMPT
    else:
        return DETAILED_PROMPT  # 复杂任务，完整 system prompt
```

这个思路特别适合对话产品——短消息用轻量 Prompt，长消息才展开完整背景。

## 综合效果估算

假设你的应用每天有 10 万次 LLM 调用，平均输入 500 tokens：

| 优化措施组合 | 预计节省 token 比例 | 月度费用节省（估算） |
|--------------|--------------------|--------------------|
| 只做前 3 条 | 5–10% | 中等 |
| 做 6–8 条 | 15–25% | 显著 |
| 全部 12 条 + Caching | 40–60% | 大幅 |

具体节省金额取决于模型单价和调用量，建议先记录当前的平均 token 数作为基线，逐步实施上述方法并对比效果。

## 相关阅读

- [Prompt Caching 成本优化实战](/blog/prompt-caching-cost-optimization/)
- [LLM Prompt 模板工程实践](/blog/llm-prompt-template-engineering/)
- [Token 计数国内开发者指南](/blog/token-counting-cn-guide/)
- [AI 编程工具月度真实费用拆解](/blog/ai-coding-monthly-cost-real/)
- [AI API 预算上限设计方案](/blog/ai-api-budget-cap-design/)

想在多个模型之间对比 token 消耗和成本，[YoTradeApi](https://yotradeapi.com) 提供统一的 API 接口和用量统计面板，帮助你精准追踪每个模型的 token 使用情况。
