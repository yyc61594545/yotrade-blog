---
title: 多模型成本智能路由方案：让 AI 调用自动选最优性价比
description: 详解多模型智能路由设计：按任务复杂度自动分配模型，结合缓存、批处理与动态定价，将 LLM 成本降低 40%~70%。
keywords:
  - 多模型路由
  - LLM 成本优化
  - AI API 路由策略
  - 模型选择自动化
  - LLM 智能调度
pubDate: '2026-06-20'
updatedDate: '2026-06-20'
canonical: https://blog.yotradeapi.com/blog/multi-model-cost-routing/
tags:
  - 成本优化
  - 系统设计
  - LLM
  - API管理
category: 成本优化
heroImage: ../../assets/blog-placeholder-2.jpg
---

大多数团队在使用 LLM 时都在走两个极端：要么所有请求都打到最强的旗舰模型（成本爆炸），要么为了省钱全部用轻量模型（效果打折）。**智能路由**是第三条路——根据任务特征，自动把请求分配给最合适的模型，在质量和成本之间找到最优解。

本文给出一套可落地的多模型成本智能路由方案设计。

## 一、为什么需要智能路由

先看几个真实数据（近似值，仅供量级参考）：

- Claude Opus 4 输出价格约 $75/百万 token
- Claude Haiku 4 输出价格约 $1.25/百万 token
- 两者价格相差约 **60 倍**

如果你的业务里有 60% 的请求是简单的分类、摘要、格式化任务，这些任务用 Haiku 就能完成，却一律打给 Opus，那你在为这 60% 的请求多付了 59 倍的冤枉钱。

智能路由的目标就是**识别任务复杂度，自动匹配最低成本且质量达标的模型**。

## 二、路由维度：从哪些角度判断该用哪个模型

设计路由逻辑前，先理清决策维度。

| 维度 | 描述 | 路由倾向 |
|-----|------|---------|
| 任务复杂度 | 简单分类 vs 多步推理 | 简单 → 轻量模型 |
| 输出质量要求 | 草稿 vs 最终交付物 | 高质量 → 旗舰模型 |
| 响应速度要求 | 实时交互 vs 批量处理 | 实时 → 低延迟模型 |
| Token 预算 | 预期 token 数量 | 长输出 → 关注每 token 价格 |
| 是否有缓存命中 | 相似请求已缓存 | 有缓存 → 直接返回 |
| 失败重试场景 | 主模型失败后重试 | 降级 → 备用模型 |

这些维度不是互斥的，实际的路由决策往往是多个维度的组合评分。

## 三、核心路由策略设计

### 3.1 基于规则的静态路由

最简单的路由方式：为不同类型的任务预定义模型。

```python
from enum import Enum
from dataclasses import dataclass

class TaskType(Enum):
    CLASSIFICATION = "classification"
    SUMMARIZATION = "summarization"
    CODE_GENERATION = "code_generation"
    COMPLEX_REASONING = "complex_reasoning"
    TRANSLATION = "translation"
    EXTRACTION = "extraction"

# 静态路由表：任务类型 → 默认模型
ROUTING_TABLE = {
    TaskType.CLASSIFICATION: "claude-haiku-4-5-20251001",
    TaskType.SUMMARIZATION: "claude-haiku-4-5-20251001",
    TaskType.TRANSLATION: "claude-haiku-4-5-20251001",
    TaskType.EXTRACTION: "claude-haiku-4-5-20251001",
    TaskType.CODE_GENERATION: "claude-sonnet-4-6",
    TaskType.COMPLEX_REASONING: "claude-sonnet-4-6",
}

def route_by_task_type(task_type: TaskType) -> str:
    return ROUTING_TABLE.get(task_type, "claude-sonnet-4-6")
```

这种方式简单可控，适合任务类型清晰的场景。缺点是需要调用方明确传入任务类型，无法自动判断。

### 3.2 基于 Prompt 分析的动态路由

更智能的方式：在发送主请求之前，用一个超轻量的小模型分析请求复杂度，决定用哪个模型。

```python
import anthropic
from typing import Literal

client = anthropic.Anthropic()

COMPLEXITY_CLASSIFIER_PROMPT = """分析以下用户请求的复杂度，只输出一个词：
- simple：简单任务（分类、格式转换、摘要、翻译）
- medium：中等任务（代码编写、文章生成、数据分析）
- complex：复杂任务（多步推理、架构设计、深度分析）

用户请求：{request}

复杂度（只输出 simple/medium/complex）："""

async def classify_complexity(user_request: str) -> Literal["simple", "medium", "complex"]:
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",  # 用最便宜的模型做分类
        max_tokens=10,
        messages=[{
            "role": "user",
            "content": COMPLEXITY_CLASSIFIER_PROMPT.format(request=user_request[:500])
        }]
    )
    result = response.content[0].text.strip().lower()
    if result in ("simple", "medium", "complex"):
        return result
    return "medium"  # 默认中等

MODEL_BY_COMPLEXITY = {
    "simple": "claude-haiku-4-5-20251001",
    "medium": "claude-sonnet-4-6",
    "complex": "claude-sonnet-4-6",  # 最复杂任务用 Sonnet，按需升级到 Opus
}

async def smart_route(user_request: str, system_prompt: str = "") -> str:
    complexity = await classify_complexity(user_request)
    model = MODEL_BY_COMPLEXITY[complexity]

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_request}]
    )
    return response.content[0].text
```

**注意**：用 Haiku 做分类的成本极低（通常每次分类 < $0.001），但额外引入了一次 API 调用，会增加约 0.5~1 秒延迟。在延迟敏感场景要权衡。

### 3.3 基于启发式规则的零延迟路由

不想增加额外 API 调用？可以用启发式规则在本地直接判断：

```python
import re

def heuristic_route(
    user_request: str,
    expected_output_length: str = "medium"
) -> str:
    request_lower = user_request.lower()
    request_len = len(user_request)

    # 简单任务信号
    simple_signals = [
        "翻译", "translate", "摘要", "summarize", "分类", "classify",
        "提取", "extract", "格式", "format", "转换", "convert",
        "是否", "判断", "对还是错"
    ]

    # 复杂任务信号
    complex_signals = [
        "设计", "架构", "分析", "推理", "证明", "比较", "评估",
        "步骤", "计划", "策略", "如何解决", "optimize", "debug"
    ]

    simple_score = sum(1 for s in simple_signals if s in request_lower)
    complex_score = sum(1 for s in complex_signals if s in request_lower)

    # 短请求 + 简单信号 → 轻量模型
    if request_len < 200 and simple_score > complex_score:
        return "claude-haiku-4-5-20251001"

    # 长请求 + 复杂信号 → 旗舰模型
    if request_len > 500 or complex_score >= 2:
        return "claude-sonnet-4-6"

    return "claude-haiku-4-5-20251001"  # 默认用轻量模型
```

这种方式**零延迟、零成本**，准确性不如 LLM 分类，但覆盖多数常见场景。

## 四、多提供商路由：不只是模型选择

成本路由不仅仅是在同一提供商的不同模型间选择，还可以在**不同提供商**之间路由，利用价格差异进一步降低成本。

```python
from dataclasses import dataclass
from typing import Callable

@dataclass
class ModelOption:
    provider: str
    model_id: str
    input_price_per_million: float  # 美元
    output_price_per_million: float  # 美元
    avg_latency_ms: int
    quality_score: float  # 0~1

MODEL_CATALOG = [
    ModelOption("anthropic", "claude-haiku-4-5-20251001", 0.8, 4.0, 600, 0.75),
    ModelOption("anthropic", "claude-sonnet-4-6", 3.0, 15.0, 1200, 0.90),
    ModelOption("openai", "gpt-4o-mini", 0.15, 0.6, 500, 0.78),
    ModelOption("openai", "gpt-4o", 2.5, 10.0, 1000, 0.92),
    ModelOption("deepseek", "deepseek-v3", 0.27, 1.1, 800, 0.88),
]

def select_optimal_model(
    min_quality: float = 0.80,
    max_latency_ms: int = 2000,
    budget_weight: float = 0.7,    # 0~1，越高越看重成本
    quality_weight: float = 0.3,   # 0~1，越高越看重质量
) -> ModelOption:
    candidates = [
        m for m in MODEL_CATALOG
        if m.quality_score >= min_quality and m.avg_latency_ms <= max_latency_ms
    ]
    if not candidates:
        return MODEL_CATALOG[1]  # 兜底

    # 归一化评分（成本越低分越高，质量越高分越高）
    max_cost = max(m.output_price_per_million for m in candidates)
    scored = [
        (m, budget_weight * (1 - m.output_price_per_million / max_cost) +
              quality_weight * m.quality_score)
        for m in candidates
    ]
    return max(scored, key=lambda x: x[1])[0]
```

## 五、缓存层：路由之前先查缓存

最便宜的 API 调用是**不调用**。在路由层之上加一层语义缓存，相似的请求直接返回缓存结果，可以进一步降低 50%~70% 的调用量。

```python
import hashlib
import json
from typing import Optional
import redis

class SemanticCache:
    def __init__(self, redis_client, ttl_seconds: int = 3600):
        self.redis = redis_client
        self.ttl = ttl_seconds

    def _make_key(self, request: str, model: str) -> str:
        content = f"{model}:{request}"
        return f"llm_cache:{hashlib.md5(content.encode()).hexdigest()}"

    def get(self, request: str, model: str) -> Optional[str]:
        key = self._make_key(request, model)
        cached = self.redis.get(key)
        return cached.decode() if cached else None

    def set(self, request: str, model: str, response: str):
        key = self._make_key(request, model)
        self.redis.setex(key, self.ttl, response)


async def cached_smart_route(user_request: str, cache: SemanticCache) -> str:
    model = heuristic_route(user_request)

    # 先查缓存
    cached = cache.get(user_request, model)
    if cached:
        return cached

    # 缓存未命中，调用 API
    response = client.messages.create(
        model=model,
        max_tokens=2048,
        messages=[{"role": "user", "content": user_request}]
    )
    result = response.content[0].text

    # 写入缓存（只缓存简单任务，复杂任务结果通常不复用）
    if model == "claude-haiku-4-5-20251001":
        cache.set(user_request, model, result)

    return result
```

**缓存策略建议**：
- 只缓存确定性强的任务（分类、摘要、翻译），不缓存创意写作
- TTL 根据业务特性设置，事实性内容可以缓存 24 小时
- 用精确匹配而不是语义相似度（后者实现复杂，成本收益不一定合算）

## 六、成本监控：让节省看得见

路由策略上线后，必须有监控来验证效果，并发现新的优化机会。

```python
from collections import defaultdict
from datetime import datetime

class CostTracker:
    def __init__(self):
        self.records = defaultdict(list)

    def record(self, model: str, input_tokens: int, output_tokens: int, task_type: str):
        # 这里用近似价格，以实际账单为准
        price_table = {
            "claude-haiku-4-5-20251001": (0.8, 4.0),
            "claude-sonnet-4-6": (3.0, 15.0),
            "gpt-4o-mini": (0.15, 0.6),
        }
        input_price, output_price = price_table.get(model, (3.0, 15.0))
        cost = (input_tokens * input_price + output_tokens * output_price) / 1_000_000

        self.records[task_type].append({
            "model": model,
            "cost": cost,
            "timestamp": datetime.now().isoformat()
        })

    def summary(self) -> dict:
        result = {}
        for task_type, records in self.records.items():
            total_cost = sum(r["cost"] for r in records)
            model_breakdown = defaultdict(float)
            for r in records:
                model_breakdown[r["model"]] += r["cost"]
            result[task_type] = {
                "total_cost": round(total_cost, 4),
                "call_count": len(records),
                "avg_cost": round(total_cost / len(records), 6),
                "model_breakdown": dict(model_breakdown)
            }
        return result
```

**关键监控指标**：
- 各模型调用占比（轻量模型比例是否达到目标）
- 每种任务类型的平均成本
- 路由决策准确率（需要人工抽样验证质量）
- 缓存命中率

## 七、路由降级：主模型失败时的自动切换

路由不只是"选最优"，还要处理"主模型不可用"的情况。关于完整的错误恢复与降级设计，参见 [AI Agent 降级回退设计](/blog/ai-agent-fallback-design/) 和 [AI Agent 错误恢复机制设计](/blog/ai-agent-error-recovery/)。

简单版本：

```python
FALLBACK_CHAIN = {
    "claude-sonnet-4-6": ["claude-haiku-4-5-20251001", "gpt-4o-mini"],
    "claude-haiku-4-5-20251001": ["gpt-4o-mini"],
}

async def call_with_fallback(model: str, messages: list, **kwargs) -> str:
    models_to_try = [model] + FALLBACK_CHAIN.get(model, [])
    for m in models_to_try:
        try:
            response = client.messages.create(model=m, messages=messages, **kwargs)
            return response.content[0].text
        except Exception as e:
            if m == models_to_try[-1]:
                raise
            print(f"{m} 失败，降级到下一个模型: {e}")
```

## 八、实战：一个完整路由系统的结构

把上面各个组件串起来，一个完整的成本路由系统结构如下：

```
用户请求
    ↓
[缓存层] → 命中 → 直接返回
    ↓ 未命中
[路由层] → 分析任务复杂度 → 选择目标模型
    ↓
[调用层] → 调用 API → 失败时降级
    ↓
[监控层] → 记录成本、延迟、质量指标
    ↓
返回结果 + 写入缓存
```

在实际落地中，建议**从静态规则路由开始**，上线后观察数据，再逐步引入动态分类和语义缓存。不要一开始就做最复杂的系统，每个复杂度都有其成本。

## 九、预期收益

根据实践经验（近似估算，具体效果取决于业务场景）：

| 优化手段 | 预期成本降低 |
|---------|------------|
| 静态路由（任务分级） | 30%~50% |
| + 语义缓存 | 额外 20%~40% |
| + 多提供商路由 | 额外 10%~20% |
| 组合使用 | 总计 40%~70% |

代价是系统复杂度增加，需要维护路由规则和缓存层。

## 十、相关阅读

- [LLM API 成本优化完整清单](/blog/llm-cost-optimization-checklist/)
- [Prompt 缓存成本优化实战](/blog/prompt-caching-cost-optimization/)
- [AI API 预算上限设计](/blog/ai-api-budget-cap-design/)
- [AI 编码工具月度成本实测](/blog/ai-coding-monthly-cost-real/)
- [LLM 价格对比 2026](/blog/llm-pricing-comparison-2026/)

想要一个现成的多模型路由方案？[YoTradeApi](https://yotradeapi.com) 提供统一入口访问 Claude、GPT-4、DeepSeek 等主流模型，支持按需切换，让你专注业务逻辑而非模型管理。
