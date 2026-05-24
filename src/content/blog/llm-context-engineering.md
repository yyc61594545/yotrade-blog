---
title: LLM 上下文工程方法论
description: 系统梳理 LLM 上下文工程的核心概念与实战技巧，涵盖上下文窗口管理、信息压缩、RAG 整合与 Agent 记忆设计。
keywords:
  - LLM 上下文工程
  - context engineering
  - 上下文窗口管理
  - RAG 上下文整合
  - Agent 记忆设计
pubDate: '2026-05-24'
updatedDate: '2026-05-24'
canonical: https://blog.yotradeapi.com/blog/llm-context-engineering/
tags:
  - LLM
  - 提示工程
  - Agent
  - 应用工程
category: 应用工程
heroImage: ../../assets/blog-placeholder-3.jpg
---

"提示工程"这个词已经被用滥了。更准确地描述我们在做的事情，是**上下文工程**（Context Engineering）——系统性地决定在每次 LLM 调用时，把什么信息放入上下文窗口，以什么顺序、什么密度呈现，最终影响模型的输出质量与成本。

模型越来越强，但上下文管理永远是约束：窗口有限、Token 有成本、信息有噪音。本文提供一套可落地的方法论。

## 一、为什么说"上下文工程"而非"提示工程"

提示工程（Prompt Engineering）通常指设计单次请求的文本措辞。上下文工程的范围更广：

- **什么进窗口**：系统提示、历史对话、检索文档、工具结果、用户画像……
- **多少进窗口**：截断策略、摘要压缩、去重过滤
- **如何排列**：信息顺序对注意力分布有实质影响
- **动态管理**：多轮对话中如何随任务进展更新上下文

对于简单的单次问答，提示工程足够。但对于 Agent、多轮对话、长文档处理等场景，不做上下文工程就是在浪费模型能力、烧冗余成本。

## 二、上下文窗口的物理约束

理解限制是设计的前提：

| 模型 | 输入窗口（约估） | 输出上限 | 备注 |
|------|--------------|---------|------|
| claude-sonnet-4-6 | 200K tokens | 64K tokens | 支持 Prompt Caching |
| claude-haiku-4-5 | 200K tokens | 8K tokens | 低延迟场景 |
| GPT-4o | 128K tokens | 16K tokens | |
| Gemini 1.5 Pro | 1M tokens | 8K tokens | 超长但成本高 |

200K tokens 听起来很大，实际上：

- 1 个英文单词 ≈ 1.3 tokens
- 1 个中文字符 ≈ 1.5–2 tokens
- 一本普通小说 ≈ 100K–150K tokens
- 10 万行代码仓库 ≈ 200K–500K tokens

所以即便是 200K 窗口，稍大一点的代码库或多轮长对话也会触顶。

## 三、信息优先级框架

在构建上下文时，先做信息分级：

**P0（必须包含）**：
- 当前任务的核心指令
- 与当前问题直接相关的参考材料
- 影响输出格式/约束的规则

**P1（高价值，尽量包含）**：
- 近期几轮关键对话
- 用户/业务的个性化背景
- 上一步工具调用的结果

**P2（低优先级，按空间决定）**：
- 早期对话历史（已无直接关联）
- 通用知识（模型本身已有）
- 重复出现的冗余信息

**规则**：P0 永远保留；P1 按质量截取；P2 先压缩再裁剪。

## 四、历史对话管理的三种策略

多轮对话是上下文膨胀的主要来源。三种处理策略各有适用场景：

### 策略 A：滑动窗口截断

保留最近 N 轮，直接丢弃更早的对话。

```python
def sliding_window(messages: list[dict], max_turns: int = 10) -> list[dict]:
    # 保留 system message + 最近 max_turns 轮
    system = [m for m in messages if m["role"] == "system"]
    conv = [m for m in messages if m["role"] != "system"]
    return system + conv[-max_turns * 2:]  # 每轮 = user + assistant
```

**适用**：任务无需长期记忆，对话较独立（如客服问答）。

### 策略 B：递进摘要

每隔 N 轮，将历史对话压缩成一段摘要，用摘要替换原始消息。

```python
def summarize_history(client, messages: list[dict]) -> str:
    history_text = "\n".join(
        f"{m['role']}: {m['content']}" for m in messages
    )
    resp = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=512,
        messages=[{
            "role": "user",
            "content": f"请将以下对话历史压缩为 200 字以内的摘要，保留关键事实和决策：\n{history_text}"
        }]
    )
    return resp.content[0].text
```

**适用**：需要保留长期上下文但对精确引用要求不高的场景。

### 策略 C：结构化记忆提取

不保留原始对话，而是从对话中提取结构化事实存入数据库，需要时检索注入。

```python
# 每轮对话后提取实体/事实
memory_prompt = """
从以下对话中提取关键事实，以 JSON 返回：
{
  "user_preferences": [...],
  "decided_facts": [...],
  "pending_questions": [...]
}
对话：{conversation}
"""
```

**适用**：长期个性化 Agent、需要持久记忆的助手产品。

## 五、RAG 上下文整合的常见陷阱

RAG（检索增强生成）本质上是往上下文里注入检索结果。整合质量直接决定效果：

**陷阱 1：检索结果堆砌**

把 Top-10 检索结果全放进去，模型会被低质量片段干扰。

**建议**：用相关性阈值过滤（如余弦相似度 > 0.75），或用 reranker 精选 Top-3。

**陷阱 2：来源信息缺失**

模型不知道文档来自哪里，无法评估可信度。

**建议**：每段检索结果加元信息标注：

```
[来源：产品文档 v2.3，第 4 章，更新于 2026-01]
检索内容：...
```

**陷阱 3：上下文位置效应**

研究表明，LLM 对窗口中间的内容注意力最弱（"Lost in the Middle"现象）。

**建议**：将最重要的检索片段放在系统提示紧后方，或用户消息之前，而不是夹在中间。

**陷阱 4：检索结果与问题错位**

用户问 A，检索结果回答 B，但模型还是"用"了这些结果。

**建议**：在检索结果前加一句上下文锚定：
```
以下是与用户问题相关的参考材料（若不相关请忽略）：
```

## 六、系统提示的结构化设计

系统提示是每次调用必然占据的上下文空间，值得精心设计：

```markdown
# 角色定义
你是 [产品名] 的技术支持助手，负责解答用户关于 API 集成的问题。

# 行为准则
- 优先引用官方文档，不要凭空捏造 API 参数
- 代码示例使用 Python，除非用户明确指定其他语言
- 遇到超出范围的问题，引导用户联系人工客服

# 输出格式
- 技术问题：先结论，再步骤，最后注意事项
- 非技术问题：简洁回答，不超过 3 句话
- 代码块始终标注语言类型

# 当前上下文
用户级别：{user_tier}
当前使用的 SDK 版本：{sdk_version}
```

结构化系统提示的好处：模型更容易"找到"相关规则，且便于程序动态插值。

## 七、Token 密度优化

同样的信息量，Token 数可以差很多。提高 Token 密度的技巧：

**用列表替代长句**：

❌ 低密度：
> 请注意，在发送请求时，你需要确保请求头中包含正确的认证信息，同时请求体需要符合 JSON 格式规范，另外要注意设置合适的超时时间以防止请求挂起。

✅ 高密度：
> 请求要求：① 请求头含 Authorization ② Body 为合法 JSON ③ 设置 timeout（建议 30s）

**删除装饰性语言**：

"非常感谢您的提问，这是一个很好的问题，让我来为您详细解释……" → 直接给答案。

**用代码替代文字描述**：

解释一个算法逻辑，20 行代码比 200 字描述更紧凑且准确。

## 八、Agent 场景的上下文设计

多步骤 Agent 任务中，上下文工程更为关键：

```python
def build_agent_context(
    task: str,
    completed_steps: list[dict],
    available_tools: list[str],
    constraints: dict
) -> list[dict]:
    """为 Agent 单步调用构建精简上下文"""
    
    # 压缩历史步骤为简洁摘要
    steps_summary = "\n".join(
        f"步骤{i+1}：{s['action']} → {s['result'][:100]}"
        for i, s in enumerate(completed_steps[-5:])  # 只保留最近 5 步
    )
    
    system_content = f"""你是任务执行 Agent。

当前任务：{task}

已完成步骤：
{steps_summary}

可用工具：{', '.join(available_tools)}

约束条件：
- 最大步骤数：{constraints.get('max_steps', 20)}
- 禁止操作：{constraints.get('forbidden', '无')}

请决定下一步行动。"""
    
    return [{"role": "system", "content": system_content}]
```

核心原则：**每步调用只告诉模型它当前需要知道的**，历史步骤压缩为摘要，避免原始工具输出堆积。

## 九、相关阅读

- [Agent 提示词工程实战](/blog/agent-prompt-engineering-cn/)
- [RAG 中文最佳实践](/blog/rag-cn-best-practices/)
- [Prompt Caching 成本优化实战](/blog/prompt-caching-cost-optimization/)
- [Claude 1M 超长上下文使用指南](/blog/claude-1m-context-guide/)
- [LLM 延迟优化指南](/blog/llm-latency-optimization/)

上下文工程做好了，每次调用都能用更少的 Token 获得更好的结果，[YoTradeApi](https://yotradeapi.com) 提供稳定的 Claude 中转接口，让你专注于工程而非网络问题。
