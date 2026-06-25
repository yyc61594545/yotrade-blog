---
title: LLM 数学推理能力横评：GSM8K、MATH、AIME 全解析
description: 系统横评主流大模型在 GSM8K、MATH、AIME 等数学基准上的表现，分析各模型推理策略与实际使用建议。
keywords:
  - LLM 数学推理评测
  - GSM8K 基准测试
  - MATH benchmark
  - AIME 大模型测试
  - 大模型数学能力对比
pubDate: '2026-06-25'
updatedDate: '2026-06-25'
canonical: https://blog.yotradeapi.com/blog/llm-math-reasoning-benchmark/
tags:
  - LLM 评测
  - 数学推理
  - Benchmark
  - 模型对比
category: 模型评测
heroImage: ../../assets/blog-placeholder-4.jpg
---

数学推理一直是衡量大模型"真实智能"的核心维度之一。与语言生成不同，数学题有客观正确答案，难以靠流畅表达掩盖错误，因此成为研究者和工程师评估模型能力最可信赖的标尺之一。本文系统梳理主流数学基准，横评当前主力大模型的表现，并给出实际开发场景下的选型建议。

---

## 一、主流数学推理基准全解析

在了解各模型表现之前，先搞清楚这些基准实际在测什么。

| 基准 | 题量 | 难度 | 核心考察点 |
|------|------|------|-----------|
| GSM8K | 8500 | 小学/初中 | 多步算术、文字题理解 |
| MATH | 12500 | 高中竞赛 | 代数、几何、数论、组合 |
| AIME | 历年真题 | 全美数学邀请赛 | 高难度整数答案题 |
| AMC 10/12 | 历年真题 | 高中竞赛 | 选择题，较 AIME 略简单 |
| Minerva Math | 272 | 大学数学/物理 | STEM 定量推理 |
| OlympiadBench | 675 | 国际数学奥林匹克 | 极难，证明题+计算题 |

**GSM8K** 是入门级基准，目前顶尖模型已接近甚至达到满分，区分度有限，更多用于验证基础能力；**MATH** 是目前主流研究最常用的综合性基准；**AIME** 是当前区分顶尖推理模型的重要战场——即使是最强的模型，在 AIME 上的准确率也远未饱和。

---

## 二、主力模型表现横评

以下数据综合自各模型官方技术报告及公开 Benchmark 结果，具体数值以各厂商官方发布为准，此处仅作参考量级比较。

### 2.1 旗舰模型对比（MATH 与 AIME）

| 模型 | GSM8K | MATH | AIME 2024 |
|------|-------|------|-----------|
| GPT-4o | ~97% | ~76% | ~9/30 |
| Claude 3.7 Sonnet | ~97% | ~78% | ~11/30 |
| Gemini 2.0 Flash | ~96% | ~80% | ~12/30 |
| DeepSeek-R1 | ~97% | ~92% | ~26/30 |
| o3-mini | ~98% | ~90% | ~23/30 |
| Qwen3-72B | ~97% | ~85% | ~18/30 |

**关键观察**：GSM8K 上几乎所有旗舰模型都在 96%+ 的区间内，差异可忽略不计。真正拉开差距的是 MATH 中的高难度题和 AIME。DeepSeek-R1 和 o3-mini 代表的"推理型模型"（Reasoning Model）在数学上比传统对话模型有质的飞跃。

### 2.2 推理型 vs 标准对话型模型

推理型模型（如 o1、o3、R1 系列）的关键机制是**链式思维（Chain-of-Thought）扩展推理**——模型在生成最终答案前会进行大量内部"思考"步骤，这在数学题上有显著效果：

```python
# 对比标准模式与推理模式的调用示例
from openai import OpenAI

client = OpenAI(api_key="your_key")

# 标准对话模型
standard_response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "解方程：x^2 - 5x + 6 = 0"}],
)

# 推理模型（o3-mini）
reasoning_response = client.chat.completions.create(
    model="o3-mini",
    messages=[{"role": "user", "content": "解方程：x^2 - 5x + 6 = 0"}],
    # o 系列不支持 temperature 参数，推理过程自动展开
)
```

推理模型的缺点是**延迟高、Token 消耗多**，因为内部思考步骤也消耗 Token。对于简单数学（如四则运算、方程求解），标准对话模型完全足够，无需用推理模型。

---

## 三、不同数学子领域的模型差异

并非所有数学任务对模型的要求相同，不同子领域的表现差异值得关注。

### 3.1 代数与方程

这是模型表现最稳定的领域。主流旗舰模型在高中代数题上的准确率普遍在 85%+ 以上，差异主要体现在：
- **符号运算**：涉及多项式展开、因式分解时，部分模型容易在中间步骤引入算术错误
- **不等式处理**：分类讨论题（如绝对值不等式）需要逐步列举，标准模型容易漏掉条件

**建议**：对高中代数问题，GPT-4o 或 Claude 3.7 Sonnet 基本够用，无需动用推理模型。

### 3.2 数论与组合

这是模型最容易"自信犯错"的领域——答案看起来合理，但中间某个推导步骤悄悄出错了。常见失误模式：
- 整除性判断失误（漏掉边界条件）
- 排列组合的重复计数或漏计
- 模运算中的负数处理错误

**建议**：涉及这类问题，强烈推荐使用推理模型，并在 Prompt 中明确要求"逐步验证每个推导步骤"。

### 3.3 几何

平面几何和解析几何的表现分化明显：
- **坐标几何**（解析几何）：模型的数值计算能力使其表现较好
- **合情推理几何**（角度追踪、辅助线构造）：当前模型在纯文字描述的几何题上仍有明显短板，图形信息缺失导致模型"瞎猜"

**建议**：如果有图形，务必使用支持多模态的模型（如 GPT-4V、Gemini 2.0 Flash）并直接上传图片。

### 3.4 大学数学与 STEM 推理

微积分、线性代数、概率论等大学数学是当前模型的分水岭：

| 子领域 | 标准模型 | 推理模型 |
|--------|---------|---------|
| 极限与导数 | 中等可靠 | 高可靠 |
| 多重积分 | 低可靠 | 中等可靠 |
| 线性代数计算 | 高可靠 | 高可靠 |
| 概率分布推导 | 低可靠 | 中等可靠 |

对于物理/工程类 STEM 推理（Minerva Math），DeepSeek-R1 和 o3-mini 展现出比 GPT-4o 明显更强的能力。

---

## 四、影响数学推理表现的关键因素

除了模型本身，以下因素对结果影响显著：

### 4.1 Prompt 工程

```python
# 效果一般的 Prompt
messages = [{"role": "user", "content": "求 1+2+...+100 的和"}]

# 效果更好的 Prompt（引导模型逐步推理）
messages = [
    {
        "role": "system",
        "content": "你是一个数学专家。请逐步推导每个步骤，每步写清楚依据，最后给出答案并验证。"
    },
    {
        "role": "user",
        "content": "求 1+2+...+100 的和。要求：写出完整推导过程，并用另一种方法验证答案。"
    }
]
```

"逐步推导 + 验证"的 Prompt 模式可以将标准模型在 MATH 上的准确率提升约 5–15 个百分点，是免费的性能提升。

### 4.2 Temperature 设置

数学题有唯一正确答案，因此推荐将 `temperature` 设为 0（或接近 0）以获得确定性输出：

```python
response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    temperature=0,  # 确定性输出，适合数学题
    max_tokens=2048,  # 确保有足够空间展开推导
)
```

### 4.3 Self-Consistency（自我一致性采样）

对于高难度题目，可以用多次采样取多数投票的方式提升准确率：

```python
import random
from collections import Counter

def solve_with_voting(client, question: str, n_samples: int = 5) -> str:
    answers = []
    for _ in range(n_samples):
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "请逐步推导，最后用'答案：X'格式给出数值答案"},
                {"role": "user", "content": question}
            ],
            temperature=0.7,  # 轻微随机性以获得多样化推导路径
        )
        content = response.choices[0].message.content
        # 提取最终答案（实际项目需要更健壮的解析逻辑）
        answers.append(content.split("答案：")[-1].strip()[:20])
    
    # 返回出现最多的答案
    return Counter(answers).most_common(1)[0][0]
```

Self-Consistency 在 MATH 上可以再提升 3–8%，代价是 API 调用成本增加 N 倍。

---

## 五、实际选型建议

### 场景一：教育 / 作业辅导 App

- **简单题（小学-初中）**：GPT-4o-mini 或 Yi-Lightning 完全够用，成本最低
- **高中竞赛题**：GPT-4o 或 Claude 3.7 Sonnet，加上逐步推导 Prompt
- **竞赛级别（AMC/AIME）**：o3-mini 或 DeepSeek-R1，接受较高延迟

### 场景二：科学计算辅助工具

- 纯数值计算（矩阵、积分近似）：建议结合代码执行（Code Interpreter 或 Python 工具调用）而非纯依赖模型
- 公式推导与证明思路：推理模型（o3-mini/R1）显著优于标准模型

### 场景三：批量数学题评测（Benchmark 测试）

```python
import json

def batch_math_eval(problems: list[dict], model: str = "gpt-4o") -> dict:
    correct = 0
    results = []
    
    for problem in problems:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "请逐步推导，最后用'答案：'开头单独一行给出数值。"},
                {"role": "user", "content": problem["question"]}
            ],
            temperature=0,
        )
        pred = response.choices[0].message.content
        is_correct = problem["answer"] in pred  # 简化匹配，实际需更严格
        correct += is_correct
        results.append({"question": problem["question"], "correct": is_correct})
    
    return {
        "accuracy": correct / len(problems),
        "total": len(problems),
        "results": results
    }
```

---

## 六、当前局限与发展趋势

**当前局限**：
- 顶尖模型在 AIME 上仍有大量错误，离"可靠数学专家"尚有差距
- 长推导链条（10 步以上）的累积错误率仍然显著
- 图形几何题（需要从图中提取条件）的多模态推理仍是短板

**发展趋势**：
- 推理时计算（Test-time Compute）是当前最有效的提升路径，o3 系列和 DeepSeek-R1 都验证了这一点
- 数学专用微调模型（如 Qwen-Math 系列）在特定子领域展示了超越通用模型的潜力
- 工具增强（让模型调用 Python/Wolfram Alpha）是处理复杂计算的工程实践首选

如果你对 LLM 在代码类推理上的表现同样感兴趣，可以参考 [LLM 编程 Benchmark 横评（中文开发者视角）](/blog/llm-coding-benchmark-cn/)，那篇文章对 HumanEval、SWE-bench 等代码基准有详细分析。

---

## 七、相关阅读

- [LLM 编程 Benchmark 横评（中文开发者视角）](/blog/llm-coding-benchmark-cn/)
- [SWE-bench 榜单如何正确解读](/blog/swe-bench-leaderboard-interpretation/)
- [LLM 评测实战指南（中文）](/blog/llm-evaluation-cn-guide/)
- [零一万物 Yi-Large API 开发者评测](/blog/cn-yi-large-developer-review/)
- [智谱 GLM 系列开发者视角评测](/blog/cn-zhipu-glm-developer-review/)

如果你在构建数学辅导或科学计算类应用，[YoTradeApi](https://yotradeapi.com) 提供统一 API 中转，支持一键切换 o3-mini、DeepSeek-R1、GPT-4o 等推理模型，方便 A/B 测试找到最适合你场景的模型配置。
