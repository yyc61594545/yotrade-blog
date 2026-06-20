---
title: AI Agent 错误恢复机制设计：让 Agent 在失败中自我修复
description: 深入讲解 AI Agent 错误恢复机制，涵盖重试策略、降级回退、状态检查点、异常分类与自动修复，帮你构建健壮的 Agent 系统。
keywords:
  - AI Agent 错误恢复
  - Agent 重试策略
  - Agent 降级设计
  - AI Agent 异常处理
  - Agent 健壮性设计
pubDate: '2026-06-20'
updatedDate: '2026-06-20'
canonical: https://blog.yotradeapi.com/blog/ai-agent-error-recovery/
tags:
  - AI Agent
  - 应用工程
  - 错误处理
  - 系统设计
category: 应用工程
heroImage: ../../assets/blog-placeholder-3.jpg
---

Agent 系统一旦上了生产环境，你会发现一个让人头疼的现实：**LLM 调用失败、工具返回异常、上下文截断、输出格式不符合预期**，这些问题每天都在发生。如果没有完善的错误恢复机制，Agent 会频繁卡死，用户体验极差。

本文从工程实践角度，系统梳理 AI Agent 错误恢复机制的设计方案。

## 一、为什么 Agent 比普通服务更难处理错误

传统 API 服务的错误处理相对简单：HTTP 4xx 客户端问题，5xx 服务端问题，重试一下或者返回错误提示即可。AI Agent 的复杂性体现在几个维度：

**1. 错误类型多且难以预测**

Agent 运行过程中的错误来源包括：
- LLM API 调用超时或限流（rate limit）
- 工具执行失败（外部 API 挂了、权限不足）
- LLM 输出格式错误（JSON 不合法、字段缺失）
- 逻辑死循环（Agent 陷入无限重复某个步骤）
- 上下文超长（token 超出模型限制）
- 状态不一致（前一步成功但副作用已发生，后一步失败）

**2. 错误的"传染性"**

一个步骤的错误会影响下游所有步骤。如果 Agent 在第 3 步拿到了错误的工具返回值，而没有识别出来，它可能在错误基础上继续工作 5 步，最终产出完全错误的结果。

**3. 部分成功的副作用**

Agent 在执行过程中可能已经发送了邮件、写了数据库、调用了外部 API。失败后如何处理这些"已发生的副作用"，需要专门设计。

## 二、错误分类：先把错误说清楚

做好错误恢复，第一步是**精确分类错误**。不同类型的错误对应不同的恢复策略。

| 错误类别 | 典型场景 | 是否可重试 | 推荐策略 |
|---------|---------|----------|---------|
| 暂时性网络错误 | LLM API timeout、连接中断 | ✅ 是 | 指数退避重试 |
| 限流错误 | 429 Too Many Requests | ✅ 是 | 等待后重试 |
| 工具执行失败 | 外部 API 5xx | ✅ 是 | 重试 + 降级 |
| 格式错误 | LLM 输出非法 JSON | ✅ 是 | 修复提示重试 |
| 逻辑错误 | Agent 循环或矛盾推理 | ⚠️ 有限 | 重置状态或人工介入 |
| 权限错误 | 403 Forbidden | ❌ 否 | 立即失败，通知用户 |
| 上下文超长 | Token 超限 | ⚠️ 有限 | 压缩上下文后重试 |
| 状态不一致 | 副作用已发生但后续失败 | ❌ 否 | 补偿事务或人工介入 |

这个分类表是你设计错误处理逻辑的起点。在代码里，你需要把每一类错误都能识别出来，而不是把所有错误一律重试。

## 三、重试策略：指数退避 + 抖动是基础

最常见的可恢复错误是**暂时性 API 失败**，包括超时和限流。对这类错误，指数退避（Exponential Backoff）是工业标准。

```python
import asyncio
import random
from typing import Callable, Any

async def retry_with_backoff(
    func: Callable,
    max_retries: int = 4,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable_exceptions: tuple = (TimeoutError, ConnectionError),
) -> Any:
    last_exception = None
    for attempt in range(max_retries + 1):
        try:
            return await func()
        except retryable_exceptions as e:
            last_exception = e
            if attempt == max_retries:
                break
            # 指数退避 + 随机抖动，避免雷群效应
            delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), max_delay)
            await asyncio.sleep(delay)
    raise last_exception
```

几个关键细节：

- **抖动（Jitter）不能省**：如果多个 Agent 实例同时触发重试，没有抖动会造成"重试风暴"，反而让上游服务雪上加霜
- **max_delay 要设上限**：无上限的指数增长会让用户等待几分钟，体验极差
- **区分 retryable 和 non-retryable**：权限错误、客户端参数错误不应该重试

对于限流（429），还需要读取响应头里的 `Retry-After` 字段，按服务端建议的时间等待。

## 四、格式错误恢复：让 LLM 自我修正

LLM 输出不合法 JSON、缺少必填字段，是 Agent 开发中最常见的问题之一。纯粹的解析失败处理不够——更好的方式是**把错误信息反馈给 LLM，让它修正自己的输出**。

```python
import json
from anthropic import Anthropic

client = Anthropic()

async def call_with_format_recovery(
    messages: list,
    schema_description: str,
    max_format_retries: int = 2
) -> dict:
    current_messages = messages.copy()

    for attempt in range(max_format_retries + 1):
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            messages=current_messages
        )
        raw_text = response.content[0].text

        try:
            # 尝试提取 JSON（有时 LLM 会在 JSON 外包裹解释文字）
            start = raw_text.find('{')
            end = raw_text.rfind('}') + 1
            if start >= 0 and end > start:
                result = json.loads(raw_text[start:end])
                return result
        except json.JSONDecodeError as e:
            if attempt == max_format_retries:
                raise ValueError(f"LLM 连续 {max_format_retries+1} 次输出非法 JSON") from e

            # 把错误信息追加到对话，让 LLM 修正
            current_messages.append({"role": "assistant", "content": raw_text})
            current_messages.append({
                "role": "user",
                "content": f"你的输出解析失败：{e}\n请严格按照以下 schema 重新输出合法 JSON，不要包含任何其他文字：\n{schema_description}"
            })

    raise RuntimeError("格式恢复失败")
```

这个模式的核心是：**不要丢弃 LLM 的错误输出**，把它作为上下文追加进对话，LLM 通常能看到自己的错误并修正。

## 五、状态检查点：为长流程 Agent 设置恢复点

对于执行时间超过 30 秒、步骤超过 5 步的 Agent，必须设计**状态检查点（Checkpoint）**。思路是定期把 Agent 当前状态序列化保存，失败后从最近的检查点恢复，而不是从头重跑。

```python
import json
import time
from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class AgentState:
    task_id: str
    current_step: int
    completed_steps: list[str]
    context: dict
    last_checkpoint_at: float

class CheckpointManager:
    def __init__(self, storage_backend):
        self.storage = storage_backend

    def save(self, state: AgentState):
        state.last_checkpoint_at = time.time()
        self.storage.set(
            f"checkpoint:{state.task_id}",
            json.dumps(asdict(state))
        )

    def load(self, task_id: str) -> Optional[AgentState]:
        data = self.storage.get(f"checkpoint:{task_id}")
        if not data:
            return None
        d = json.loads(data)
        return AgentState(**d)

    def clear(self, task_id: str):
        self.storage.delete(f"checkpoint:{task_id}")


async def run_agent_with_checkpoint(task_id: str, steps: list, checkpoint_mgr: CheckpointManager):
    # 尝试从检查点恢复
    state = checkpoint_mgr.load(task_id)
    if state:
        start_step = state.current_step
        print(f"从检查点恢复：第 {start_step} 步")
    else:
        state = AgentState(
            task_id=task_id,
            current_step=0,
            completed_steps=[],
            context={},
            last_checkpoint_at=time.time()
        )
        start_step = 0

    for i, step_func in enumerate(steps[start_step:], start=start_step):
        result = await step_func(state.context)
        state.context[f"step_{i}_result"] = result
        state.completed_steps.append(step_func.__name__)
        state.current_step = i + 1
        checkpoint_mgr.save(state)  # 每步完成后保存检查点

    checkpoint_mgr.clear(task_id)
    return state.context
```

**检查点设计的注意事项**：

- 检查点只保存"可序列化"的状态，不要把 LLM 客户端对象放进去
- 检查点存储要用持久化方案（Redis、数据库），不能只放内存
- 检查点要有过期时间，避免"僵尸任务"残留

## 六、降级策略：当最优路径不可用时的备选方案

Agent 遇到错误时，除了重试，另一个重要手段是**降级（Fallback）**：换一种方式完成任务，即使结果质量略低，也比完全失败好。

常见的降级场景：

**1. 模型降级**

主模型（如 Claude Opus）调用失败或超限时，自动切换到次级模型（如 Claude Haiku）。

```python
MODEL_FALLBACK_CHAIN = [
    "claude-opus-4-8",
    "claude-sonnet-4-6",
    "claude-haiku-4-5-20251001",
]

async def call_with_model_fallback(messages: list, **kwargs) -> str:
    for model in MODEL_FALLBACK_CHAIN:
        try:
            response = client.messages.create(
                model=model,
                messages=messages,
                **kwargs
            )
            return response.content[0].text
        except Exception as e:
            if model == MODEL_FALLBACK_CHAIN[-1]:
                raise
            print(f"模型 {model} 失败（{e}），尝试下一个")
```

**2. 工具降级**

工具执行失败时，用简化版工具或缓存数据代替：

```python
async def search_with_fallback(query: str) -> str:
    try:
        # 首选：实时搜索
        return await live_search(query)
    except Exception:
        try:
            # 降级：向量数据库本地搜索
            return await local_vector_search(query)
        except Exception:
            # 兜底：告知 LLM 搜索不可用，让它基于已知信息回答
            return "搜索服务暂时不可用，请基于你的已有知识回答。"
```

**3. 任务降级**

完整任务无法完成时，完成可以完成的子集：

```python
async def run_task_with_partial_success(subtasks: list) -> dict:
    results = {}
    failures = []
    for subtask in subtasks:
        try:
            results[subtask.name] = await subtask.run()
        except Exception as e:
            failures.append({"task": subtask.name, "error": str(e)})
    return {"results": results, "failures": failures, "partial": len(failures) > 0}
```

## 七、循环检测：防止 Agent 陷入死循环

Agent 有时会在某个步骤上无限循环，比如：反复尝试同一个失败的工具调用，或者在两个相互矛盾的结论之间反复横跳。这类问题靠普通错误处理发现不了，需要专门的循环检测。

```python
from collections import defaultdict
import hashlib

class LoopDetector:
    def __init__(self, max_repetitions: int = 3):
        self.action_counts = defaultdict(int)
        self.max_repetitions = max_repetitions

    def check(self, action: dict) -> bool:
        """返回 True 表示检测到循环"""
        # 对 action 做哈希，忽略时间戳等变化字段
        key = hashlib.md5(
            str(sorted(action.items())).encode()
        ).hexdigest()
        self.action_counts[key] += 1
        return self.action_counts[key] > self.max_repetitions

    def get_repeated_action(self) -> str:
        for key, count in self.action_counts.items():
            if count > self.max_repetitions:
                return f"动作 {key[:8]}... 已重复 {count} 次"
        return ""
```

检测到循环后，可以采取以下措施：
- 向 LLM 注入提示："你已经尝试了相同的操作 N 次，请换一种方式"
- 跳过当前子任务，继续后续步骤
- 触发人工介入流程

## 八、人工介入：错误恢复的最后一道防线

不是所有错误都能自动恢复。对于涉及高价值操作、状态不一致、重复失败的场景，**引入人工介入（Human-in-the-Loop）**是更安全的选择。

设计人工介入的关键点：

- **明确触发条件**：不是所有错误都值得打扰人工，只有真正无法自动恢复的情况才触发
- **提供完整上下文**：人工介入时要给出任务目标、已完成步骤、当前错误、Agent 的判断
- **支持继续/放弃/修改**三种操作：人工确认后，Agent 可以继续从检查点恢复

```python
async def request_human_intervention(
    task_id: str,
    error_description: str,
    agent_state: AgentState,
    notification_channel  # Slack/Email/Webhook
):
    context_summary = {
        "task_id": task_id,
        "completed_steps": agent_state.completed_steps,
        "current_step": agent_state.current_step,
        "error": error_description,
        "resume_url": f"https://your-app.com/tasks/{task_id}/resume"
    }
    await notification_channel.send(
        f"[AI Agent] 任务 {task_id} 需要人工介入\n"
        f"错误：{error_description}\n"
        f"已完成 {len(agent_state.completed_steps)} 步\n"
        f"点击继续：{context_summary['resume_url']}"
    )
```

## 九、实战建议：构建错误恢复的优先级

不要试图一次把所有错误恢复机制全部实现。建议按以下优先级推进：

**第一阶段（必做）**：
- 所有 LLM 调用加指数退避重试
- LLM 输出格式校验 + 自我修正
- 超时设置（避免永久挂起）

**第二阶段（生产就绪）**：
- 错误分类与精准处理
- 长流程检查点
- 循环检测

**第三阶段（高可靠性）**：
- 模型降级链
- 工具降级方案
- 人工介入流程

这个优先级基于"投入产出比"——第一阶段能解决 80% 的生产问题，成本最低。

## 十、相关阅读

- [AI Agent 降级回退设计](/blog/ai-agent-fallback-design/)
- [AI Agent 工具设计最佳实践](/blog/ai-agent-tool-design/)
- [AI Agent 记忆机制设计](/blog/ai-agent-memory-design/)
- [LLM API 错误码速查与处理指南](/blog/ai-api-relay-error-codes/)
- [AI Agent 成本控制实战](/blog/ai-coding-agent-cost-control/)

想在生产环境中稳定调用 Claude、GPT-4 等模型？[YoTradeApi](https://yotradeapi.com) 提供高可用 API 中转，内置限流保护与自动重试，让你的 Agent 系统更可靠。
