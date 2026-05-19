---
title: Claude Tool Use 最佳实践与陷阱
description: 12 条 Claude Tool Use 设计与生产化经验：工具定义、tool_choice 三模式、调用循环、并行调用、token 优化、上下文爆炸防护与踩坑实录。
keywords:
  - claude tool use
  - claude function calling
  - anthropic tool
  - ai agent 工具设计
  - claude tool_choice
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/claude-tool-use-best-practices/
tags:
  - Claude
  - Tool Use
  - Agent
  - 最佳实践
category: 技术深度
heroImage: ../../assets/blog-placeholder-3.jpg
---

Claude Tool Use 看起来"传个 JSON Schema 就能用"，但生产环境里翻车的细节远不止参数格式。本文整理 12 条来自真实项目的踩坑笔记，从工具定义、调用循环、到 token 控制都有覆盖。

## 一、Tool Use 是什么、不是什么

Tool Use（很多人也叫 function calling）让 Claude 在回复里**输出结构化的"工具调用意图"**而不是直接给文本答复。你的代码拿到意图后真去执行（查数据库、调 API、改文件），把结果回填给 Claude，它再继续推理。

需要先消除两个误解：

- **它不是"Claude 自己执行"**——执行永远是你的代码做的。Claude 只产出 `tool_use` 块。
- **它不是更聪明的 prompt**——工具越多 system prompt 越长，token 成本和模型注意力都被稀释。

## 二、工具定义的 4 条核心原则

### 1. 描述是给模型读的，不是给你自己读的

`description` 字段决定模型什么时候调这个工具。写法应该是"行动指引"，不是"功能罗列"。

```python
# ✗ 含糊
{"name": "search", "description": "搜索功能"}

# ✓ 行动指引
{"name": "search_docs",
 "description": "搜索内部知识库。当用户询问公司政策、产品规格、内部流程时调用。不要用于通用知识问答。"}
```

### 2. 参数能少则少，能有默认则给默认

每个 required 参数都会增加模型"猜错"的概率。能从上下文推断的就别要 required。

### 3. 返回结构化数据，但不要返回全部

工具结果会回填到对话里，**整段算输入 token**。返回 10 KB JSON 不仅烧钱，还淹没模型注意力。压缩到关键字段、必要时只回 ID 让下一轮再 fetch。

### 4. 幂等比"完美"重要

模型偶尔会重复调同一个工具（特别是 retry / 多步任务）。设计成"重复调用结果一致、不产生副作用"会少一半 bug。写入类工具加 `idempotency_key`。

## 三、tool_choice 三种模式怎么选

| 模式 | 行为 | 典型场景 |
| --- | --- | --- |
| `auto`（默认） | 模型自己决定调不调工具 | 多轮对话、Agent、不确定何时该调 |
| `any` | 必须调一个工具（不限定哪个） | 路由场景，强制走工具不走自然语言 |
| `{"type": "tool", "name": "..."}` | 必须调指定工具 | 结构化输出（用工具替代 JSON mode） |

最容易踩的坑：**用了 `any` 或指定工具后忘了关**。在多轮循环里，第二轮也带着同样的 `tool_choice` 会导致死循环（一直被强制调工具，没法给最终回复）。

```python
# 第一轮：强制调路由工具
resp = client.messages.create(..., tool_choice={"type": "any"})

# 第二轮起：必须切回 auto，否则永远不会"完成"
resp = client.messages.create(..., tool_choice={"type": "auto"})
```

## 四、调用循环的标准骨架

90% 的 Agent 代码都长这样：

```python
messages = [{"role": "user", "content": user_input}]

while True:
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        tools=TOOLS,
        messages=messages,
    )

    if resp.stop_reason == "end_turn":
        # 模型给出最终回复，跳出循环
        return resp.content[-1].text

    # 取出所有 tool_use 块
    tool_uses = [b for b in resp.content if b.type == "tool_use"]
    if not tool_uses:
        break

    # 把 assistant 这一轮的完整 content（含 tool_use）追加
    messages.append({"role": "assistant", "content": resp.content})

    # 并行执行所有工具调用
    tool_results = run_tools_in_parallel(tool_uses)

    # 一次性 user 消息回填所有结果
    messages.append({"role": "user", "content": tool_results})
```

四个关键点：

1. **以 `stop_reason == "end_turn"` 判终止**，不要靠 "有没有 text 块"
2. **必须把 assistant 的 `content`（整个数组）按原样回填**，包括 tool_use 块
3. **同一轮多个 tool_use 必须并行执行**（详见下一节），结果用一个 user 消息回填，里面多个 `tool_result` 块
4. **设置最大循环次数**（建议 10–20），死循环防护

## 五、并行工具调用：少踩一半的坑

Claude 4 系列默认会在一轮内并发出多个 `tool_use`。同步串行执行会浪费时间也浪费 token——同一上下文要等多轮才能用完。

```python
import asyncio

async def run_tools_in_parallel(tool_uses):
    async def run_one(tu):
        result = await TOOL_FNS[tu.name](**tu.input)
        return {"type": "tool_result", "tool_use_id": tu.id, "content": str(result)}
    return await asyncio.gather(*[run_one(tu) for tu in tool_uses])
```

注意：

- `tool_result` 的 `tool_use_id` 必须**严格对应**那一轮的 `tool_use.id`，乱序也没关系，但 ID 必须匹配
- 工具执行失败时，`tool_result` 加 `"is_error": true`，并把错误信息放在 `content` 里。模型会基于此决定重试或换路径
- 不要给某个失败工具偷偷 retry 然后假装成功——会让模型基于错误的"成功"继续推理

## 六、token 与上下文爆炸防护

工具结果是最容易让上下文爆炸的来源。我们项目里抓到过这样的 bug：

- 一个 `list_files` 工具返回了 1.2 万个文件名
- 单轮工具结果回填后输入 token 从 2k 飙到 80k
- 第二轮再调一次直接超出 200k 上下文

三个防护：

1. **工具内部做截断**：list 类工具默认 `limit=50`，超过返回 `{"items": [...], "truncated": true, "total": N, "next_cursor": "..."}`
2. **结果摘要化**：大对象返回前先在工具内 LLM-summarize 或规则裁剪
3. **token 预算监控**：每轮拿 `usage.input_tokens`，超出阈值就强制结束循环

## 七、用工具替代 JSON Mode 输出结构化数据

很多场景"我只想要一个 JSON"——不要用 prompt 工程让模型吐 JSON，**用 tool_choice 锁定一个工具**：

```python
EXTRACT = {
    "name": "submit_extraction",
    "description": "提交从用户输入中提取的字段。",
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "email": {"type": "string"},
            "urgency": {"type": "string", "enum": ["low", "high"]},
        },
        "required": ["name", "email", "urgency"],
    },
}

resp = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    tools=[EXTRACT],
    tool_choice={"type": "tool", "name": "submit_extraction"},
    messages=[{"role": "user", "content": text}],
)

data = next(b.input for b in resp.content if b.type == "tool_use")
```

优势：

- Schema 校验 100% 严格（vs JSON mode 偶尔会漏字段）
- 不用解析 markdown 里的 ```json 块
- 错误处理（缺字段、类型错）模型自己会修正再吐

## 八、System Prompt 与工具协作

工具描述写得再清楚，模型也可能"不知道何时该调"。这时候 system prompt 是最后一道防线：

```
你是订单查询助手。规则：
1. 涉及具体订单时，必须先调 lookup_order 拿到状态。
2. 不要凭印象回答订单状态。
3. lookup_order 失败时，回复用户"查询超时，请稍后再试"，不要重试。
```

不要重复 description 里写过的内容，**只写跨工具的协调规则、错误处理策略、风格要求**。

## 九、12 个踩坑速查

| # | 现象 | 原因 |
| --- | --- | --- |
| 1 | 模型不调工具 | description 太抽象、system prompt 没明确触发条件 |
| 2 | 调用死循环 | 没设 max_loops、`tool_choice` 没切回 auto |
| 3 | 参数乱猜 | required 太多、缺枚举约束、description 没给例子 |
| 4 | 上下文爆炸 | 工具返回未截断的列表、未摘要的大对象 |
| 5 | 工具结果乱序 | tool_use_id 没对齐 |
| 6 | 重复执行副作用 | 没设计幂等 / 没传 idempotency_key |
| 7 | 模型重写工具结果 | 没用结构化输出，模型把"结果"和"推理"混在一起 |
| 8 | 单轮成本高 | 工具数量太多、每个 description 都很长 |
| 9 | 输出 JSON 不完整 | 用了 JSON mode 而不是 tool_choice |
| 10 | 并行调用错配 | 串行执行了本可并行的工具 |
| 11 | 失败时偷偷重试 | 没正确返回 `is_error: true` |
| 12 | 200k 上下文撑爆 | 没做 token 预算监控、循环跑了 30 轮 |

## 十、生产化 checklist

上线前对照检查：

- [ ] 每个工具 description 给出**触发条件 + 不该触发的反例**
- [ ] 所有写入类工具有 `idempotency_key`
- [ ] 列表类工具默认 `limit + cursor`，禁返全集
- [ ] 工具执行端有超时、有降级、失败正确返回 `is_error`
- [ ] 调用循环有 `max_loops`（建议 15）
- [ ] 调用循环有 `max_input_tokens`（建议 100k，留余量给后续推理）
- [ ] 监控指标：单次会话工具调用次数、单工具 P99 耗时、失败率
- [ ] 结构化输出场景统一用 `tool_choice` 而非 JSON mode
- [ ] 多轮场景注意第二轮起 `tool_choice` 切回 `auto`
- [ ] 通过中转服务接入时，确认中转支持 tool use 透传

## 十一、走中转的兼容性提示

国内开发者走 Anthropic 中转时，不是所有中转都完整支持 tool use（特别是 streaming + tool use 的组合）。验收一个中转时跑这三个用例：

1. **单工具非流式**：基本通路验证
2. **多工具并发非流式**：验证 `tool_use_id` 一致性
3. **工具调用 + streaming**：很多中转在 SSE 块拆分上有 bug

`[YoTradeApi](https://yotradeapi.com)` 完整透传 Anthropic Tool Use 协议（含流式 + 并行调用），适合做生产部署的基准对照。

## 十二、相关阅读

- [Claude 并行工具调用实战与原理](/blog/parallel-tool-use-claude/)
- [Agent 提示工程：让 LLM 真正"会做事"](/blog/agent-prompt-engineering-cn/)
- [开发自定义 MCP Server 完整指南](/blog/mcp-custom-server-development/)
- [Claude Agent SDK 中文上手](/blog/claude-agent-sdk-cn/)
- [Claude Code Subagent 实战经验](/blog/claude-code-subagent-practice/)

Tool Use 是 Agent 应用的核心机制，调通这一层后多数复杂 workflow 都能跑。需要一把支持完整 Anthropic 协议的 Key？[YoTradeApi](https://yotradeapi.com) 在国内网络下稳定透传 tool use 与 streaming，方便从开发直接平滑到生产。
