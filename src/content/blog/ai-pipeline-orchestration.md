---
title: AI 任务流水线编排实战：从单点调用到多步 Pipeline
description: 系统讲解如何将多个 LLM 调用串联成可靠的 AI 流水线，涵盖顺序、并行、条件分支、错误重试与成本控制的工程实践。
keywords:
  - AI 流水线编排
  - LLM pipeline 实战
  - AI 任务编排 Python
  - 多步骤 LLM 工作流
  - AI workflow 设计模式
pubDate: '2026-06-12'
updatedDate: '2026-06-12'
canonical: https://blog.yotradeapi.com/blog/ai-pipeline-orchestration/
tags:
  - AI 工程
  - Pipeline
  - 应用工程
  - LLM
category: 应用工程
heroImage: ../../assets/blog-placeholder-5.jpg
---

单次 LLM 调用能解决的问题有限——遇到需要"先提取、再分析、再生成报告"的复合任务，就需要把多个 AI 步骤串联起来，形成可靠的流水线。本文从工程角度讲清楚怎么设计、实现和维护一条 AI Pipeline。

如果你需要了解 Agent 框架（如 LangChain、OpenAI Agents SDK），可以分别参考[LangChain 国内中文教程](/blog/langchain-cn-tutorial/)和[OpenAI Agents SDK 国内使用指南](/blog/openai-agents-sdk-cn/)。本文聚焦**无框架依赖的纯 Python 流水线设计**，适合希望控制依赖、自主实现的开发者。

## 一、什么时候需要 Pipeline

单次调用不够用的典型信号：

- 任务太复杂，一个 Prompt 解不了（质量差、幻觉多）
- 需要中间结果驱动下一步（"先判断类型，再用对应的处理逻辑"）
- 有些步骤可以并行处理，节省总耗时
- 需要对每一步单独做质量检查和重试

**经验法则**：当你的 Prompt 超过 1000 字，或者 AI 经常在一次调用里漏掉某个子任务，考虑拆成 Pipeline。

## 二、Pipeline 的四种基本结构

### 2.1 顺序流（Sequential）

最简单的形式——步骤 A → B → C，前一步的输出是下一步的输入。

```python
from openai import OpenAI

client = OpenAI(
    api_key="your_key",
    base_url="https://yotradeapi.com/v1",
)

def call_llm(prompt: str, model: str = "claude-sonnet-4-6") -> str:
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content

def analyze_document_pipeline(document: str) -> dict:
    # 步骤 1：提取关键信息
    entities = call_llm(f"""
    从以下文档中提取：公司名、金额、日期、关键条款。
    输出 JSON 格式。
    
    文档：{document}
    """)
    
    # 步骤 2：基于提取结果做风险评估
    risk_analysis = call_llm(f"""
    基于以下提取的合同信息，评估潜在风险（高/中/低），给出理由。
    
    合同信息：{entities}
    """)
    
    # 步骤 3：生成摘要报告
    report = call_llm(f"""
    根据以下分析结果，写一份 200 字以内的执行摘要，适合发给非技术的业务负责人。
    
    提取信息：{entities}
    风险评估：{risk_analysis}
    """)
    
    return {
        "entities": entities,
        "risk": risk_analysis,
        "report": report,
    }
```

### 2.2 并行流（Parallel）

多个独立子任务同时执行，汇总结果，节省总耗时。

```python
import asyncio

async def call_llm_async(prompt: str, model: str = "claude-sonnet-4-6") -> str:
    # 使用异步客户端
    from openai import AsyncOpenAI
    aclient = AsyncOpenAI(api_key="your_key", base_url="https://yotradeapi.com/v1")
    resp = await aclient.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content

async def parallel_analysis(document: str) -> dict:
    # 三个分析任务并行执行
    results = await asyncio.gather(
        call_llm_async(f"从这份文档里提取所有人名：{document}"),
        call_llm_async(f"从这份文档里提取所有日期事件：{document}"),
        call_llm_async(f"从这份文档里提取所有金额数字：{document}"),
    )
    
    names, dates, amounts = results
    return {"names": names, "dates": dates, "amounts": amounts}
```

并行对比顺序的提速效果：假设每个步骤耗时 3 秒，3 个步骤：
- 顺序：9 秒
- 并行：约 3 秒（受最慢那个限制）

### 2.3 条件分支（Conditional）

根据上一步的输出，决定走哪条路——这让 Pipeline 具备了"智能路由"能力。

```python
def classify_and_route(user_input: str) -> str:
    # 步骤 1：分类
    category = call_llm(f"""
    将以下用户问题分类为：
    - "technical"（技术问题）
    - "billing"（账单问题）
    - "general"（一般咨询）
    
    只输出分类标签，不要解释。
    
    问题：{user_input}
    """).strip().lower()
    
    # 步骤 2：根据分类路由到不同处理逻辑
    if category == "technical":
        return call_llm(
            f"你是一位资深工程师，请详细解答技术问题：{user_input}",
            model="claude-opus-4-8",  # 技术问题用更强的模型
        )
    elif category == "billing":
        return call_llm(
            f"你是客服专员，请简洁回答账单相关问题：{user_input}",
            model="claude-sonnet-4-6",
        )
    else:
        return call_llm(
            f"友善地回答用户的一般咨询：{user_input}",
            model="gemini-2.0-flash",  # 一般问题用便宜快速的模型
        )
```

### 2.4 循环与迭代（Loop）

对每个元素执行相同的处理，或反复迭代直到达到质量标准。

```python
def batch_process(items: list[str]) -> list[str]:
    """批量处理一组文本"""
    results = []
    for item in items:
        result = call_llm(f"将以下文本翻译成英文：{item}")
        results.append(result)
    return results

def iterative_improve(draft: str, max_iterations: int = 3) -> str:
    """反复优化直到通过质量检查"""
    for i in range(max_iterations):
        quality_check = call_llm(f"""
        评估以下文本是否达到"专业、简洁、无错别字"的标准。
        只回答 "pass" 或 "fail"，以及改进建议（如果 fail）。
        
        文本：{draft}
        """)
        
        if quality_check.strip().lower().startswith("pass"):
            return draft
        
        # 根据反馈优化
        draft = call_llm(f"""
        根据以下反馈优化文本：
        
        原文：{draft}
        反馈：{quality_check}
        """)
    
    return draft  # 超过最大迭代次数，返回最后版本
```

## 三、错误处理与重试

生产环境中 LLM 调用会失败：网络超时、rate limit、偶发的格式错误。

```python
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def call_llm_with_retry(
    prompt: str,
    model: str = "claude-sonnet-4-6",
    max_retries: int = 3,
    fallback_model: Optional[str] = "gemini-2.0-flash",
) -> str:
    for attempt in range(max_retries):
        try:
            return call_llm(prompt, model=model)
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 指数退避：1s, 2s, 4s
            else:
                # 最后一次失败，尝试 fallback 模型
                if fallback_model:
                    logger.info(f"Falling back to {fallback_model}")
                    return call_llm(prompt, model=fallback_model)
                raise
```

关于 Agent 中的 fallback 设计思路，可以参考[AI Agent Fallback 设计模式](/blog/ai-agent-fallback-design/)。

## 四、输出格式验证

LLM 输出不稳定，要在 Pipeline 步骤间做格式验证。

```python
import json

def call_llm_structured(prompt: str, max_retries: int = 2) -> dict:
    """要求 LLM 返回 JSON，附带验证和重试"""
    for attempt in range(max_retries):
        raw = call_llm(prompt + "\n\n请严格以 JSON 格式输出，不要有多余的说明文字。")
        try:
            # 提取 JSON（应对模型在 JSON 外加了说明文字的情况）
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(raw[start:end])
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse failed (attempt {attempt+1}): {e}")
            if attempt < max_retries - 1:
                prompt = f"上次输出格式有误，请重新生成。原始提示：\n{prompt}"
    
    raise ValueError(f"Failed to get valid JSON after {max_retries} attempts")
```

## 五、成本控制在 Pipeline 中的实践

Pipeline 里每多一步就多一次 API 调用，成本会累加。几个控制点：

**1. 步骤级模型选择**：不是所有步骤都需要最强模型。

```python
STEP_MODELS = {
    "classify": "gemini-2.0-flash",      # 分类：简单，用便宜模型
    "extract": "claude-sonnet-4-6",       # 提取：中等复杂
    "analyze": "claude-opus-4-8",         # 分析：复杂推理，用强模型
    "summarize": "gemini-2.0-flash",      # 摘要：简单，用便宜模型
}
```

**2. 中间结果缓存**：对相同输入不重复调用。

```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=500)
def _cached_call(prompt_hash: str, model: str) -> str:
    # 实际调用逻辑
    pass

def call_with_cache(prompt: str, model: str) -> str:
    h = hashlib.sha256(f"{prompt}:{model}".encode()).hexdigest()
    return _cached_call(h, model)
```

**3. 短路逻辑**：早期步骤发现"无需处理"时，跳过后续步骤。

```python
def smart_pipeline(document: str) -> dict:
    # 先做快速预检
    is_relevant = call_llm(
        f"这份文档是否与财务相关？只回答 yes 或 no。\n{document[:500]}",
        model="gemini-2.0-flash",  # 用便宜模型做预检
    ).strip().lower()
    
    if is_relevant != "yes":
        return {"skipped": True, "reason": "not financial document"}
    
    # 只有相关文档才走后续重量级步骤
    return full_analysis_pipeline(document)
```

## 六、可观测性：怎么知道 Pipeline 是否健康

```python
import time
from dataclasses import dataclass, field
from typing import Any

@dataclass
class StepResult:
    step_name: str
    model: str
    input_tokens: int
    output_tokens: int
    duration_ms: float
    success: bool
    error: str = ""
    output: Any = None

class TrackedPipeline:
    def __init__(self):
        self.steps: list[StepResult] = []
    
    def run_step(self, step_name: str, prompt: str, model: str) -> str:
        start = time.time()
        try:
            result = call_llm(prompt, model=model)
            duration = (time.time() - start) * 1000
            self.steps.append(StepResult(
                step_name=step_name, model=model,
                input_tokens=len(prompt) // 4,  # 粗略估算
                output_tokens=len(result) // 4,
                duration_ms=duration, success=True, output=result,
            ))
            return result
        except Exception as e:
            self.steps.append(StepResult(
                step_name=step_name, model=model,
                input_tokens=0, output_tokens=0,
                duration_ms=(time.time() - start) * 1000,
                success=False, error=str(e),
            ))
            raise
    
    def summary(self) -> dict:
        total_cost_approx = sum(
            (s.input_tokens * 0.000003 + s.output_tokens * 0.000015)
            for s in self.steps
        )
        return {
            "steps": len(self.steps),
            "total_duration_ms": sum(s.duration_ms for s in self.steps),
            "estimated_cost_usd": total_cost_approx,
            "failed_steps": [s.step_name for s in self.steps if not s.success],
        }
```

## 七、相关阅读

- [AI Agent 工具设计：如何让模型正确使用函数](/blog/ai-agent-tool-design/)
- [AI Agent Fallback 设计模式](/blog/ai-agent-fallback-design/)
- [LangChain 国内中文教程](/blog/langchain-cn-tutorial/)
- [Claude Agent SDK 国内使用指南](/blog/claude-agent-sdk-cn/)
- [个人开发者用 AI 编程：月度成本实录与优化经验](/blog/ai-coding-monthly-cost-real/)

在国内稳定运行 AI Pipeline，需要可靠的 API 接入层，[YoTradeApi](https://yotradeapi.com) 支持多模型统一接口，适合多步骤 Pipeline 中按任务选择最合适的模型。
