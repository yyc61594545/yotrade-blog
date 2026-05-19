---
title: LLM 评估实战：怎么科学地比较两个模型
description: LLM 评估的工程化方法：测试集设计、自动评分、人工评分、A/B 测试、Promptfoo 与 LangSmith 实战。
keywords:
- llm 评估
- llm evaluation
- promptfoo 教程
- llm 测试
- ai 模型 评估
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/llm-evaluation-cn-guide/
tags:
- 评估
- 测试
- LLM
- 工程实战
- 选型
category: 工程实战
heroImage: ../../assets/blog-placeholder-1.jpg
---

# LLM 评估实战：怎么科学地比较两个模型

"哪个模型更好" 是 LLM 项目里最常被问、最难回答的问题。"我觉得 A 更聪明" 不算回答。本文给一份工程化的评估方法，让换模型这件事从"感觉"变成"数据"。

## 一、为什么不能凭感觉

凭感觉的问题：

- 偏见：你期待新模型更好，无意识为它打高分
- 样本小：试 3–5 个 prompt 就下结论
- 任务漂移：跑了不一样的 prompt 而不自知
- 时间衰退：上周 A 好，这周 B 好，因为今天心情不同

**评估的本质 = 复用同一组测试集打分 + 算指标**。

## 二、测试集设计

好测试集的 3 个特点：

1. **覆盖性**：包含产品里典型任务的代表样本
2. **难度梯度**：简单到难都有
3. **明确答案**：有金标答案或可验证标准

### 例：编程助手的测试集

```yaml
- id: code-001
  category: 写函数
  difficulty: easy
  prompt: 用 Python 写一个 fibonacci 函数。
  expected_keywords: [def fibonacci, n-1, n-2]

- id: code-005
  category: 调 bug
  difficulty: medium
  prompt: |
    这段代码报错：[贴代码]
    错误：[贴错误]
    找出问题并修复。
  expected_outcome: 修复后能跑通

- id: code-012
  category: 重构
  difficulty: hard
  prompt: |
    把这段 callback 风格代码改成 async/await：[贴代码]
  expected_outcome: 行为不变，无 callback
```

至少 50 个 case，覆盖 5–10 个 category。

## 三、自动评分（适合大批量）

### 方法 1：关键词匹配

```python
def score(output, expected_keywords):
    hits = sum(1 for k in expected_keywords if k in output)
    return hits / len(expected_keywords)
```

简单但容易作弊。适合"必须出现 X" 的硬约束。

### 方法 2：可执行验证

```python
def score(output, test_case):
    # 模型输出代码，运行它，检查输出
    code = extract_code(output)
    result = run_in_sandbox(code, test_case.input)
    return 1.0 if result == test_case.expected_output else 0.0
```

编程任务最适合。**真跑代码，结果对就给分**。

### 方法 3：LLM-as-judge

让另一个 LLM 评分：

```python
def score(output, expected):
    judge_resp = judge_client.messages.create(
        model="claude-opus-4-7",
        messages=[{
            "role": "user",
            "content": f"""评分以下答案，1–10 分。

# 标准答案
{expected}

# 待评分答案
{output}

# 评分维度
- 正确性
- 完整性
- 清晰度

只输出一个数字。""",
        }],
    )
    return float(judge_resp.content[0].text.strip())
```

**注意**：用同一家模型当裁判可能有偏见。最好用不同家。

## 四、人工评分

样本量小、任务主观（写作、设计）时必须人工。要点：

1. **盲测**：评分员不知道哪个是 A、哪个是 B
2. **多评分员**：至少 3 人，看一致性
3. **明确量表**：1–5 分各代表什么写清楚
4. **随机顺序**：避免顺序偏见

## 五、Promptfoo 实战

[Promptfoo](https://www.promptfoo.dev/) 是 LLM 测试的开源工具。

`promptfooconfig.yaml`：

```yaml
providers:
  - id: openai:gpt-5
    config:
      apiKey: ${YOTRADE_KEY}
      apiBaseUrl: https://yotradeapi.com/v1
  - id: openai:claude-sonnet-4-6
    config:
      apiKey: ${YOTRADE_KEY}
      apiBaseUrl: https://yotradeapi.com/v1

prompts:
  - "用 Python 写 {{task}}"

tests:
  - vars:
      task: 一个 fibonacci 函数
    assert:
      - type: contains
        value: "def fibonacci"
      - type: javascript
        value: |
          output.includes("return") && output.length < 500

  - vars:
      task: 一个 LRU 缓存
    assert:
      - type: llm-rubric
        value: 包含完整 TypeScript 类型，含单元测试
```

跑：

```bash
npx promptfoo eval
npx promptfoo view
```

打开 web UI 看每个 test 在不同模型下的表现。

## 六、A/B 测试（线上）

测试集再好也是离线。**真实流量 A/B** 是最终答案。

最小实现：

```python
import random

def chat(user_message, user_id):
    # 按 user_id hash 分流，确保用户一致体验
    if hash(user_id) % 100 < 50:
        model = "claude-sonnet-4-6"
        variant = "A"
    else:
        model = "gpt-5"
        variant = "B"

    resp = client.chat.completions.create(model=model, messages=[...])

    # 记录
    log_event({
        "user_id": user_id,
        "variant": variant,
        "model": model,
        "input_tokens": resp.usage.prompt_tokens,
        "output_tokens": resp.usage.completion_tokens,
        "latency": ...,
    })

    return resp
```

然后跟踪业务指标：

- 用户满意度（thumbs up/down）
- 对话延续率
- 任务完成率
- 留存

A/B 跑 2 周 + 显著性检验，结论可靠。

## 七、关键指标

| 指标 | 适用任务 |
| --- | --- |
| 准确率 | 单选答案 |
| F1 | 多标签分类 |
| BLEU/ROUGE | 翻译 / 摘要（局限大） |
| BertScore | 翻译 / 摘要 |
| pass@1 / pass@10 | 编程 |
| LLM-judge score | 通用 |
| 人工 5 分制 | 主观任务 |
| 用户 thumbs up 率 | 线上 |
| 任务完成率 | Agent |

## 八、踩坑

### 1. 测试集泄漏

如果测试题 + 答案在网上公开过，新模型很可能在训练时见过——分数虚高。**自建测试集**比用公开 benchmark 更可靠。

### 2. 单次评估方差

LLM 输出非确定。同 prompt 跑 3 次可能 3 个分数。**至少跑 3 次取平均**。

### 3. 模型版本变化

`gpt-5` 在不同时间可能指向不同后端。Anthropic、Google 也类似。**定期重跑评估**。

### 4. prompt 偏向某模型

很多 prompt 是为某模型调优的。换模型评估时，应该**给每个模型用它最适合的 prompt**，不是用同一份 prompt。

### 5. 不评估成本

光看质量不看成本不完整。**质量 / 成本** 才是真实价值。

## 九、最小评估流水线

```python
# eval.py
from openai import OpenAI

MODELS = ["claude-sonnet-4-6", "gpt-5", "gemini-2.5-pro"]
TESTS = [...]   # 50+ case

client = OpenAI(api_key="sk-yo-...", base_url="https://yotradeapi.com/v1")

results = {}
for model in MODELS:
    scores = []
    for test in TESTS:
        out = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": test.prompt}],
        ).choices[0].message.content
        scores.append(score(out, test))
    results[model] = {
        "mean": sum(scores) / len(scores),
        "scores": scores,
    }

# 输出 markdown 报告
for model, r in results.items():
    print(f"## {model}: {r['mean']:.3f}")
```

把这个加入 CI，每周跑一次。模型升级 / prompt 改 / 中转换都跑一遍，回归立刻发现。

## 十、相关阅读

- [Claude vs GPT vs Gemini 国内开发者怎么选](/blog/claude-vs-gpt-vs-gemini-cn-developer/)
- [AI API 中转稳定性测试方法](/blog/ai-api-relay-stability-test/)
- [Python 异步并发调用 LLM API](/blog/python-async-llm-client/)
- [GPT-5 与 Claude Opus 4.7 编程能力对比](/blog/gpt-5-vs-claude-opus-4-7-coding/)
- [AI Agent Prompt Engineering 中文实战](/blog/agent-prompt-engineering-cn/)

需要一把 Key 同时调多家模型做 A/B 评估？[YoTradeApi](https://yotradeapi.com/register) 创建独立 Key 后按上面 promptfoo 配置跑即可。
