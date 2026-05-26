---
title: LLM 评测 Golden Set 构建方法
description: 系统介绍如何为 LLM 应用构建高质量评测基准集（Golden Set），涵盖数据采集、标注策略、维护机制与自动化评分实践，帮助团队建立可持续的模型质量体系。
keywords:
  - LLM Golden Set 评测集构建
  - 语言模型基准数据集
  - LLM 评测标注策略
  - 自动化模型评分
  - LLM 质量回归测试
pubDate: '2026-05-26'
updatedDate: '2026-05-26'
canonical: https://blog.yotradeapi.com/blog/llm-eval-golden-set/
tags:
  - LLM
  - 评测
  - 数据工程
  - 应用工程
category: 应用工程
heroImage: ../../assets/blog-placeholder-3.jpg
---

大多数团队在上线 LLM 功能时做了充分的 Prompt 调优，但在模型升级、Prompt 修改后却没有系统化的方式验证"有没有变差"。

Golden Set（黄金测试集）就是这个问题的解法：一组精心构建、有明确预期答案的测试案例，让你在每次变更后都能用数字说话。本文从零开始讲清楚如何构建、标注、维护一套真正有用的 LLM 评测基准集。

## 一、Golden Set 是什么，不是什么

### 基本定义

Golden Set 是一组 `(输入, 预期输出 / 评判标准)` 对，用于：

1. **回归测试**：新模型/新 Prompt 上线前，跑一遍确认分数没有下降
2. **A/B 对比**：同时评测两个候选方案，量化差异
3. **监控基线**：定期跑测集，发现模型行为随时间的漂移

### 不是什么

- 不是 Prompt 调优用的训练数据（会导致过拟合测集）
- 不是覆盖所有 case 的测试套件（Golden Set 求精不求全，补全靠 staging 监控）
- 不是一成不变的文件（需要随业务演化持续更新）

## 二、数据来源：从哪里找 Golden Set 的素材

好的 Golden Set 来自真实流量，而不是工程师凭空编造。

### 2.1 生产日志采样

从真实用户请求中采样是最可靠的来源。核心原则：**分层采样**，而非随机采样。

```python
import random
from collections import defaultdict

def stratified_sample(logs: list[dict], n_per_bucket: int = 20) -> list[dict]:
    """
    按业务场景分层采样
    log 格式: {"query": str, "response": str, "scenario": str, "rating": int | None}
    """
    buckets = defaultdict(list)
    for log in logs:
        buckets[log["scenario"]].append(log)
    
    sampled = []
    for scenario, items in buckets.items():
        # 优先采评分差（rating <= 2）的 case，失败案例更有价值
        bad_cases = [x for x in items if x.get("rating") and x["rating"] <= 2]
        good_cases = [x for x in items if x not in bad_cases]
        
        n_bad = min(len(bad_cases), n_per_bucket // 2)
        n_good = min(len(good_cases), n_per_bucket - n_bad)
        
        sampled.extend(random.sample(bad_cases, n_bad))
        sampled.extend(random.sample(good_cases, n_good))
    
    return sampled
```

**可操作结论**：失败案例和边界案例的价值远高于"正常"案例。采样比例建议：失败/边界占 40%，常规 case 占 60%。

### 2.2 刻意设计的对抗案例

除了生产采样，还需要人工设计专门"挑战"模型的 case：

| 类型 | 示例 | 目的 |
|------|------|------|
| 否定指令 | "不要用列表格式回答" | 检验指令遵循 |
| 歧义问题 | 含双关语义的查询 | 检验理解鲁棒性 |
| 超长输入 | 接近上下文上限的文档 | 检验长文能力 |
| 对抗注入 | 含"忽略前面的指令" | 检验 Prompt 安全性 |
| 越界拒答 | 要求提供不该回答的内容 | 检验安全边界 |

### 2.3 业务关键路径

梳理产品最核心的用户旅程，每条路径至少覆盖 5–10 个 case。这是 Golden Set 的"压舱石"——就算其他 case 减少，这部分必须维持。

## 三、标注策略：如何定义"正确答案"

这是 Golden Set 构建最难的部分，因为 LLM 的输出往往没有唯一正确答案。

### 3.1 三种标注粒度

**二元标注（Pass/Fail）**——最简单，适合有明确约束的任务：

```yaml
- query: "用 JSON 格式返回用户姓名和年龄"
  input_context: "用户说：我叫张三，今年28岁"
  expected:
    must_contain_json: true
    required_fields: ["name", "age"]
    name_value: "张三"
    age_value: 28
  eval_type: structured_match
```

**评分量表（1–5 分）**——适合开放式生成任务，需要人工标注参考答案：

```yaml
- query: "总结这篇文章的核心观点"
  reference_answer: "文章核心观点是：技术债务的利息会随时间复利增长..."
  rubric:
    5: 包含所有核心观点，无事实错误，语言简洁
    3: 包含主要观点，允许有细节遗漏
    1: 遗漏关键观点，或有明显错误
  eval_type: rubric_score
```

**偏好对（A vs B）**——适合做模型间对比：

```yaml
- query: "写一封道歉邮件给客户"
  response_a: "..."  # 模型A输出
  response_b: "..."  # 模型B输出  
  preferred: "a"     # 人工标注偏好
  reason: "A语气更真诚，且提供了具体补救方案"
  eval_type: preference
```

### 3.2 标注一致性检验

多人标注时，必须做一致性检验，避免标注噪声污染测集：

```python
from sklearn.metrics import cohen_kappa_score

def check_annotation_agreement(rater1_scores: list, rater2_scores: list) -> dict:
    kappa = cohen_kappa_score(rater1_scores, rater2_scores, weights="linear")
    agreement_rate = sum(a == b for a, b in zip(rater1_scores, rater2_scores)) / len(rater1_scores)
    
    return {
        "cohen_kappa": kappa,
        "raw_agreement": agreement_rate,
        "quality": "good" if kappa > 0.6 else "needs_review" if kappa > 0.4 else "poor",
    }
```

Kappa > 0.6 才算可接受的标注质量。低于这个值说明评分标准需要重新对齐。

## 四、自动化评分：让测集跑起来

手动评分不可持续，生产级 Golden Set 需要自动化评分流水线。

### 4.1 规则型评分器

对于有明确约束的任务，规则评分既快又准：

```python
import json
import re

def eval_structured_output(response: str, expected: dict) -> dict:
    score = 0
    details = []
    
    # 检查 JSON 格式
    try:
        parsed = json.loads(response)
        score += 30
        details.append(("json_valid", True))
    except json.JSONDecodeError:
        # 尝试提取 JSON 块
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
                score += 20
                details.append(("json_extracted", True))
            except:
                details.append(("json_valid", False))
                return {"score": 0, "details": details}
    
    # 检查必填字段
    for field in expected.get("required_fields", []):
        if field in parsed:
            score += 20
            details.append((f"field_{field}", True))
        else:
            details.append((f"field_{field}", False))
    
    # 检查字段值
    for field, value in expected.get("field_values", {}).items():
        if parsed.get(field) == value:
            score += 10
            details.append((f"value_{field}", True))
    
    return {"score": min(score, 100), "details": details}
```

### 4.2 LLM-as-Judge

对于开放式生成，用更强的模型做评判：

```python
def llm_judge(query: str, response: str, rubric: str, 
               judge_model: str = "gpt-4o") -> dict:
    prompt = f"""你是一个严格的 LLM 输出质量评审员。

问题：{query}

模型回答：
{response}

评分标准：
{rubric}

请按照评分标准给出 1-5 分的评分，并简要说明理由。
只输出 JSON：{{"score": <1-5>, "reason": "<简要理由>"}}"""

    resp = client.chat.completions.create(
        model=judge_model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0,  # 评分用确定性模式
    )
    
    result = json.loads(resp.choices[0].message.content)
    return result
```

**使用 LLM-as-Judge 的注意事项**：
- 评判模型应比被测模型更强，或至少同级
- temperature 设为 0，保证评分可复现
- 定期抽样做人工校对，防止评判模型本身漂移
- 对同一 case 跑 3 次取多数票，降低随机性

### 4.3 跑测管道

```python
def run_golden_set(test_cases: list[dict], model: str) -> dict:
    results = []
    
    for case in test_cases:
        # 跑模型
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": case["query"]}],
            temperature=0,
        ).choices[0].message.content
        
        # 评分
        if case["eval_type"] == "structured_match":
            score = eval_structured_output(response, case["expected"])
        elif case["eval_type"] == "rubric_score":
            score = llm_judge(case["query"], response, case.get("rubric", ""))
        else:
            score = {"score": None}
        
        results.append({
            "case_id": case["id"],
            "scenario": case.get("scenario", "default"),
            "score": score["score"],
            "response": response,
        })
    
    # 汇总
    scores = [r["score"] for r in results if r["score"] is not None]
    return {
        "model": model,
        "n_cases": len(test_cases),
        "avg_score": sum(scores) / len(scores) if scores else 0,
        "pass_rate": sum(1 for s in scores if s >= 4) / len(scores) if scores else 0,
        "results": results,
    }
```

## 五、维护机制：让 Golden Set 不过时

### 5.1 老化检测

随着业务变化，测集中的 case 会失效（查询方式变了、业务规则更新了）。定期运行"老化检测"：

```python
def detect_stale_cases(test_cases: list[dict], days_threshold: int = 90) -> list:
    """标记超过 N 天没有被验证过的 case"""
    from datetime import datetime, timedelta
    cutoff = datetime.now() - timedelta(days=days_threshold)
    
    stale = []
    for case in test_cases:
        last_verified = datetime.fromisoformat(case.get("last_verified", "2020-01-01"))
        if last_verified < cutoff:
            stale.append(case["id"])
    
    return stale
```

### 5.2 增量补充流程

建议设立"每月评测集更新"机制：

1. 从上月生产日志中采样 20–30 个新 case（尤其是出错 case）
2. 标注团队（或 LLM-as-Judge）打分
3. Kappa 检验通过后合并入 Golden Set
4. 同步剔除已标记为 stale 的旧 case

### 5.3 分数基线管理

每次正式评测后，记录分数快照作为基线：

```yaml
# baselines.yaml
gpt-4o-mini:
  date: '2026-05-01'
  avg_score: 3.82
  pass_rate: 0.71
  
gpt-4o:
  date: '2026-05-01'
  avg_score: 4.31
  pass_rate: 0.88
```

**可操作结论**：设定"回归门槛"，例如 avg_score 不得低于基线 0.2 分，pass_rate 不得低于基线 5%。CI 中跑不过测集就阻断上线。

## 六、相关阅读

- [LLM 评估方法完全指南：从指标到框架](/blog/llm-evaluation-cn-guide/)
- [LLM logprobs 在生产场景的实用价值](/blog/llm-logprobs-applications/)
- [LLM 可观测性：Langfuse 完整接入教程](/blog/llm-observability-langfuse/)
- [LLM Agent 评测方法：如何衡量智能体的真实能力](/blog/llm-agent-evaluation-methods/)

想快速搭建评测流水线，[YoTradeApi](https://yotradeapi.com) 支持多模型统一 API 接入，一套代码同时跑 GPT-4o、Claude 3.5 等模型对比评测，省去多平台配置的麻烦。
