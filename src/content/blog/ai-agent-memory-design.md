---
title: AI Agent 记忆系统设计：四种模式与工程实践
description: 系统梳理 AI Agent 的四种记忆模式——工作记忆、情节记忆、语义记忆和程序记忆，给出工程选型与落地建议。
keywords:
  - AI Agent 记忆系统
  - agent memory design
  - 工作记忆 LLM
  - 向量数据库记忆
  - agent 长期记忆方案
pubDate: '2026-06-04'
updatedDate: '2026-06-04'
canonical: https://blog.yotradeapi.com/blog/ai-agent-memory-design/
tags:
  - AI Agent
  - 记忆系统
  - 应用工程
  - LLM
category: 应用工程
heroImage: ../../assets/blog-placeholder-2.jpg
---

构建一个能"记住"用户、记住上下文、记住失败经验的 AI Agent，是很多团队在原型之后遇到的第一堵墙。Context Window 装不下、向量搜索返回噪声、数据库写入频率撑不住——这些问题背后，往往缺少的是对**记忆系统分层**的清晰认识。

本文按四种记忆模式逐一拆解，给出每种模式的适用场景、常见坑和可落地的工程方案。

---

## 一、为什么 Agent 需要"记忆系统"

LLM 本身是无状态的。每次调用，它只能看到当前传入的 prompt，历史存在于 Context Window 里，而非模型权重。

这带来两个根本限制：

1. **容量上限**：哪怕是 Claude 的 200K token，长对话积累 3–4 天后也会撑满
2. **召回无策略**：把所有历史塞进 prompt 不可行，需要主动决定"现在应该记住什么"

人类的记忆系统早已解决了这个问题。认知科学把记忆分为短时记忆、情节记忆、语义记忆、程序记忆。Agent 工程把同样的逻辑映射为四种技术层。

---

## 二、工作记忆（Working Memory）

**定义**：当前对话或任务执行过程中，临时保留的信息。

**载体**：LLM Context Window。

对于单次任务，Context Window 就是工作记忆的全部。工程重点是**如何管理这块空间**，而不是如何扩容。

### 常用策略

| 策略 | 说明 | 适用场景 |
|------|------|----------|
| Sliding Window | 丢弃最旧的 N 轮 | 简单问答，历史价值低 |
| Summary Compression | 用 LLM 对旧对话做摘要 | 长对话，需要保留主线 |
| Selective Retention | 显式标记重要信息保留 | 工作流 Agent，关键变量多 |
| Token Budget | 动态计算 token 占用，触发压缩 | 产品级 Agent |

**Summary Compression 示例**（伪代码）：

```python
def compress_history(messages: list[dict], threshold: int = 6000) -> list[dict]:
    if count_tokens(messages) < threshold:
        return messages
    
    old_messages = messages[:-6]  # 保留最近 6 轮
    summary = llm.complete(
        f"请用 200 字总结以下对话要点：\n{format(old_messages)}"
    )
    return [{"role": "system", "content": f"[历史摘要] {summary}"}] + messages[-6:]
```

**关键判断**：工作记忆的压缩时机很重要。太早压缩，当前任务信息丢失；太晚压缩，token 费用飙升。经验上，在剩余 20% 上限时触发压缩是合理阈值。

---

## 三、情节记忆（Episodic Memory）

**定义**：Agent 经历过的具体事件序列——"上周三用户要求过 A，最终选了方案 B"。

**载体**：向量数据库 + 时间戳索引。

情节记忆的核心价值：Agent 能从**自身过去的决策**中学习，而不是每次从零开始。

### 存什么、不存什么

```
✅ 存：
- 用户的偏好决策（选了哪个方案、拒绝了哪个）
- 任务执行的失败原因（哪个工具调用失败了、错误 message）
- 用户反馈（显式 thumbs up/down 或隐式行为）

❌ 不存：
- 每一轮对话原文（太多，噪声高）
- 中间推理步骤（价值低，召回后难被利用）
```

### 召回策略

简单的 top-k 向量搜索容易返回语义相关但场景不匹配的结果。推荐组合过滤：

```python
def recall_episodes(query: str, user_id: str, k: int = 5):
    embedding = embed(query)
    results = vector_db.search(
        embedding,
        filter={"user_id": user_id, "outcome": "success"},  # 只召回成功的经验
        limit=k * 3,
    )
    # 时间衰减：最近 7 天的记忆权重翻倍
    for r in results:
        days_ago = (now() - r.timestamp).days
        r.score *= 2.0 if days_ago <= 7 else 1.0
    return sorted(results, key=lambda x: x.score, reverse=True)[:k]
```

**常见坑**：直接把向量搜索结果拼入 prompt，没有做"已注入不重复"的去重。当多个情节记忆语义高度相似时，会占用大量 token 且效果不比一条好。

---

## 四、语义记忆（Semantic Memory）

**定义**：关于世界的通用知识——用户档案、产品文档、领域规则。

**载体**：结构化数据库（用户档案）+ 向量数据库（文档知识库）+ 图数据库（复杂关系）。

这是目前 RAG（Retrieval-Augmented Generation）最常覆盖的层次。

### 分层存储方案

```
用户档案（高频读写）
  → PostgreSQL / Redis
  → 字段：name, language, plan, preferences, last_active

产品文档（低频写、高频读）
  → 向量数据库（Chroma / Pinecone / pgvector）
  → 预切块、预 embed，查询时 top-k 召回

知识图谱（实体关系）
  → Neo4j / Kuzu（轻量嵌入式）
  → 适合"A 依赖 B 哪个版本"这类关系查询
```

### 什么时候该用图数据库

90% 的场景，向量数据库已经够用。以下情况考虑引入图数据库：

- 实体之间的关系本身是查询目标（如"找出所有依赖 OpenSSL 1.1 的服务"）
- 需要多跳推理（"A 依赖 B，B 依赖 C，C 有漏洞，A 受影响吗"）
- 数据量不大（< 百万节点），关系维度多

---

## 五、程序记忆（Procedural Memory）

**定义**：Agent 执行任务的"技能"和"工作流"——如何完成某类任务的步骤模板。

**载体**：代码 / Prompt 模板 / 工具定义 / 工作流图。

这一层通常被开发者忽视，但它是 Agent 一致性的基础。

### 工程实现形式

**1. Prompt 模板库**

把验证过的、高质量的 prompt 存储为可调用模板，按任务类型检索：

```python
# 根据任务类型选择对应的系统 prompt 模板
template = prompt_store.get(
    task_type="code_review",
    language="python",
    style="strict"
)
```

**2. 工具选择记忆**

记录在什么场景下哪个工具调用成功率高：

```json
{
  "task_pattern": "查询实时股价",
  "preferred_tool": "market_data_api",
  "fallback_tool": "web_search",
  "success_rate": 0.94,
  "avg_latency_ms": 320
}
```

**3. Few-shot 示例池**

把经过用户验证的高质量输入-输出对存起来，动态注入：

```python
examples = example_store.retrieve(
    task=current_task,
    quality_threshold=0.9,
    max_examples=3
)
system_prompt += format_few_shot(examples)
```

**关键判断**：程序记忆应当有版本管理。当你修改了某个 prompt 模板，老版本的 A/B 效果对比数据要保留，否则线上性能回归很难定位原因。

---

## 六、四种记忆的工程组合方案

实际项目中，很少只用一种记忆模式。下面是按 Agent 复杂度给出的推荐组合：

| Agent 类型 | 工作记忆 | 情节记忆 | 语义记忆 | 程序记忆 |
|-----------|---------|---------|---------|---------|
| 简单问答 Bot | Context Window | - | 文档 RAG | - |
| 客服 Agent | 压缩摘要 | 用户历史决策 | 用户档案 + 知识库 | 工单分类模板 |
| 编程 Agent | Token Budget | 失败案例库 | 代码库索引 | 工具选择策略 |
| 长期个人助理 | 滑动窗口 + 摘要 | 完整事件流 | 用户知识图谱 | 个性化 prompt |

---

## 七、常见设计误区

**误区 1：向量数据库万能**

向量搜索擅长语义相似，但不擅长精确匹配。"用户 ID = 12345 的偏好"这类查询，用 PostgreSQL 字段查询比向量搜索快 100 倍、准确率 100%。

**误区 2：存越多越好**

记忆系统的价值在于**召回的相关性**，不在于存储量。低质量信息进入向量库后，会稀释搜索结果，导致真正重要的记忆被埋没。

**误区 3：记忆不需要遗忘机制**

用户的偏好会变化，系统的规则会更新。没有过期机制的记忆库，随时间积累大量过时信息，反而拖累 Agent 判断。推荐对情节记忆设置 90 天的 TTL，并在用户显式修改偏好时立即覆盖。

**误区 4：记忆写入是同步操作**

Agent 在回复用户时，不应该等待记忆写入完成。把写入放到异步队列，主流程只负责召回。

---

## 八、与 API 成本的关联

记忆系统设计好不好，直接影响 API 费用。未压缩的长上下文、低效的 RAG 召回都会导致 token 消耗翻倍。

以情节记忆为例：如果每次召回返回 5 条记忆，每条平均 200 token，注入 prompt 增加 1000 token。按 Claude Sonnet 计费，每 1000 次 Agent 调用约多花 \$0.3–0.5。乘上日活用户数，一周的额外成本很可观。

好的记忆系统不只是功能问题，也是成本优化的一部分。

---

## 九、相关阅读

- [AI Agent 工具系统设计](/blog/ai-agent-tool-design/)
- [Agent Prompt 工程实战](/blog/agent-prompt-engineering-cn/)
- [Claude Agent SDK 中文指南](/blog/claude-agent-sdk-cn/)
- [LLM Context 工程实践](/blog/llm-context-engineering/)
- [LLM 成本优化清单](/blog/llm-cost-optimization-checklist/)

需要稳定、低延迟地调用 Claude、GPT-4o 等模型来构建 Agent 记忆系统，[YoTradeApi](https://yotradeapi.com) 提供全系模型 API 中转，按量计费，无需海外信用卡。
