---
title: LLM finish_reason 各家差异处理指南
description: OpenAI、Anthropic、Gemini 的 finish_reason 字段命名和语义各不相同，本文梳理差异并给出统一处理代码，避免生产环境里的静默 bug。
keywords:
  - LLM finish_reason
  - OpenAI stop_reason
  - Anthropic stop_reason
  - LLM 输出截断处理
  - LLM API 兼容层
pubDate: '2026-06-13'
updatedDate: '2026-06-13'
canonical: https://blog.yotradeapi.com/blog/llm-finish-reason-handling/
tags:
  - LLM
  - API
  - 技术深度
  - 多模型
category: 技术深度
heroImage: ../../assets/blog-placeholder-3.jpg
---

`finish_reason`（或各家的等效字段）告诉你模型为什么停止输出：是自然结束、被截断、触发了工具调用、还是被内容过滤拦截。

这个字段很多人不检查，直接拿 `choices[0].message.content` 就用了。但在生产环境里，忽略 `finish_reason` 会带来静默 bug——用户拿到了一段被截断到一半的 JSON，或者工具调用没有被触发，而代码没有任何报错。

麻烦的是，OpenAI、Anthropic（Claude）、Google（Gemini）这三家的字段名和语义都不完全一致。本文把差异整理清楚，并给出统一处理的代码模式。

---

## 一、三家的字段位置和命名

先看字段在响应结构里的位置：

**OpenAI（Chat Completions API）**：

```json
{
  "choices": [
    {
      "message": { "content": "..." },
      "finish_reason": "stop"
    }
  ]
}
```

字段名：`choices[0].finish_reason`，类型为字符串。

**Anthropic（Messages API）**：

```json
{
  "content": [{ "type": "text", "text": "..." }],
  "stop_reason": "end_turn",
  "stop_sequence": null
}
```

字段名：`stop_reason`（注意不叫 `finish_reason`），在顶层对象，不在嵌套数组里。

**Google（Gemini API）**：

```json
{
  "candidates": [
    {
      "content": { "parts": [{ "text": "..." }] },
      "finishReason": "STOP"
    }
  ]
}
```

字段名：`candidates[0].finishReason`，注意是 camelCase，值是全大写枚举。

---

## 二、各家的值对照表

| 场景 | OpenAI | Anthropic | Gemini |
|-----|--------|-----------|--------|
| 正常结束 | `"stop"` | `"end_turn"` | `"STOP"` |
| max_tokens 截断 | `"length"` | `"max_tokens"` | `"MAX_TOKENS"` |
| 工具调用 | `"tool_calls"` | `"tool_use"` | `"STOP"`（内容是函数调用） |
| 内容过滤 | `"content_filter"` | （通过 HTTP 400 返回，不在正常响应里）| `"SAFETY"` |
| stop_sequence 触发 | `"stop"` | `"stop_sequence"` | `"STOP"` |
| 流式取消 | `null` | `null` | `"FINISH_REASON_UNSPECIFIED"` |

几个容易踩坑的不一致：

**1. 工具调用的信号方式不同**

OpenAI 在 `finish_reason` 里返回 `"tool_calls"`，同时 `choices[0].message.tool_calls` 有工具调用数组。检查逻辑：先看 `finish_reason`，再看 `tool_calls`。

Anthropic 返回 `"tool_use"`，同时 `content` 数组里会有 `type: "tool_use"` 的块。检查逻辑类似，但字段不同。

Gemini 在函数调用时 `finishReason` 仍然是 `"STOP"`，需要检查 `candidates[0].content.parts` 里是否有 `functionCall` 类型的 part。这意味着 Gemini 不能单靠 `finishReason` 判断是否触发了工具。

**2. 内容过滤的响应方式不同**

OpenAI 可能在正常响应里返回 `"content_filter"`（特别是流式），也可能直接报 HTTP 400。

Anthropic 通常通过 HTTP 400 + `error.type = "invalid_request_error"` 返回，不会进入正常响应结构。

Gemini 在正常响应里返回 `"SAFETY"`，同时 `safetyRatings` 字段里有详细的拦截原因。

**3. `null` 的含义不同**

OpenAI 流式响应的中间 chunk 里 `finish_reason` 是 `null`，最后一个 chunk 才有实际值。

Anthropic 的 `stop_reason` 在流式中间事件（`content_block_delta`）里不出现，只在 `message_stop` 事件里返回。

所以不能用 `if (finish_reason === null)` 判断流式是否结束。

---

## 三、统一处理层：TypeScript 示例

如果你的应用支持多个 LLM 提供商，最好做一个统一的标准化层，把各家的 `finish_reason` 映射到你自己的枚举值：

```typescript
// lib/llm/finish-reason.ts

export type NormalizedFinishReason =
  | 'complete'      // 正常结束
  | 'length'        // max_tokens 截断
  | 'tool_call'     // 需要工具调用
  | 'content_filter' // 内容过滤
  | 'stop_sequence' // 触发 stop sequence
  | 'unknown';      // 其他 / null

export function normalizeOpenAIFinishReason(
  reason: string | null
): NormalizedFinishReason {
  switch (reason) {
    case 'stop':           return 'complete';
    case 'length':         return 'length';
    case 'tool_calls':     return 'tool_call';
    case 'function_call':  return 'tool_call'; // 旧版
    case 'content_filter': return 'content_filter';
    default:               return 'unknown';
  }
}

export function normalizeAnthropicStopReason(
  reason: string | null
): NormalizedFinishReason {
  switch (reason) {
    case 'end_turn':      return 'complete';
    case 'max_tokens':    return 'length';
    case 'tool_use':      return 'tool_call';
    case 'stop_sequence': return 'stop_sequence';
    default:              return 'unknown';
  }
}

export function normalizeGeminiFinishReason(
  reason: string | null | undefined
): NormalizedFinishReason {
  switch (reason) {
    case 'STOP':                        return 'complete';
    case 'MAX_TOKENS':                  return 'length';
    case 'SAFETY':                      return 'content_filter';
    case 'RECITATION':                  return 'content_filter';
    case 'FINISH_REASON_UNSPECIFIED':   return 'unknown';
    default:                            return 'unknown';
  }
}
```

在调用层统一使用：

```typescript
// lib/llm/call.ts
import { normalizeOpenAIFinishReason, normalizeAnthropicStopReason, NormalizedFinishReason } from './finish-reason';

interface LLMResult {
  content: string;
  finishReason: NormalizedFinishReason;
  toolCalls?: ToolCall[];
}

async function callOpenAI(prompt: string): Promise<LLMResult> {
  const resp = await openai.chat.completions.create({ ... });
  const choice = resp.choices[0];
  return {
    content: choice.message.content ?? '',
    finishReason: normalizeOpenAIFinishReason(choice.finish_reason),
    toolCalls: choice.message.tool_calls?.map(normalizeToolCall),
  };
}

async function callAnthropic(prompt: string): Promise<LLMResult> {
  const resp = await anthropic.messages.create({ ... });
  const textBlock = resp.content.find(b => b.type === 'text');
  const toolBlocks = resp.content.filter(b => b.type === 'tool_use');
  return {
    content: textBlock?.text ?? '',
    finishReason: normalizeAnthropicStopReason(resp.stop_reason),
    toolCalls: toolBlocks.map(normalizeAnthropicToolUse),
  };
}
```

---

## 四、生产代码里的处理模式

### 4.1 检查截断

`length` 是需要特别处理的情况：内容可能被切断到一半，直接使用可能导致 JSON 解析失败或语义残缺：

```typescript
function assertComplete(result: LLMResult, context: string): void {
  if (result.finishReason === 'length') {
    // 选项 1：记录警告，继续用（如果截断可接受）
    console.warn(`[${context}] Response truncated by max_tokens`);
    
    // 选项 2：抛出异常，让调用方决定（如果截断不可接受）
    throw new LLMTruncationError(context, result.content);
    
    // 选项 3：增加 max_tokens 后重试（如果成本允许）
  }
}
```

**不要**把截断当做正常完成来处理。特别是当你期望输出是 JSON 或 Markdown 代码块时，截断后的内容几乎肯定会让下游解析失败。

### 4.2 处理工具调用的返回

当 `finishReason === 'tool_call'` 时，`content` 字段可能为空（OpenAI）或包含部分文本（Anthropic）。不要假设内容字段一定有值：

```typescript
function processResult(result: LLMResult): string {
  if (result.finishReason === 'tool_call') {
    // 需要执行工具，然后继续对话
    // 不要直接返回 result.content
    return executeTools(result.toolCalls!);
  }
  return result.content;
}
```

### 4.3 内容过滤的降级

`content_filter` 的处理策略取决于你的应用场景：

```typescript
async function safeCall(prompt: string): Promise<string> {
  const result = await callLLM(prompt);
  
  if (result.finishReason === 'content_filter') {
    // 策略 1：返回通用错误消息
    return '抱歉，该请求无法处理。';
    
    // 策略 2：记录 + 报警，人工审核
    await reportToMonitoring({ prompt, reason: 'content_filter' });
    throw new ContentFilterError();
    
    // 策略 3：换模型重试（有些模型过滤更严格）
    return callFallbackLLM(prompt);
  }
  
  return result.content;
}
```

---

## 五、流式响应里的 finish_reason

流式场景需要额外注意——`finish_reason` 只在最后一个事件里有效：

**OpenAI 流式**：

```typescript
for await (const chunk of stream) {
  const delta = chunk.choices[0].delta.content ?? '';
  process.stdout.write(delta);
  
  const reason = chunk.choices[0].finish_reason;
  if (reason !== null) {
    // 最后一个 chunk，reason 有意义
    const normalized = normalizeOpenAIFinishReason(reason);
    if (normalized === 'length') {
      console.warn('Stream truncated');
    }
  }
}
```

**Anthropic 流式（Server-Sent Events）**：

```python
with anthropic.messages.stream(...) as stream:
    for text in stream.text_stream:
        print(text, end='', flush=True)
    
    # 流结束后才能拿到最终消息和 stop_reason
    final_message = stream.get_final_message()
    stop_reason = final_message.stop_reason
    if stop_reason == 'max_tokens':
        print('\n[WARNING: Response truncated]')
```

---

## 六、常见调试方法

如果你发现应用里偶尔出现"空响应"或"JSON 解析失败"，优先加这两行 debug 日志：

```typescript
console.log('finish_reason:', choice.finish_reason); // OpenAI
console.log('stop_reason:', message.stop_reason);    // Anthropic
```

很多时候，看到 `"length"` 或 `"content_filter"` 就能立刻定位问题。

生产环境里，建议把 `finish_reason` 作为一个维度记录到监控里（Datadog、CloudWatch 等），统计各个值的分布。`length` 比例高说明 `max_tokens` 设置偏小；`content_filter` 比例高说明输入需要预处理或 prompt 需要调整。

---

## 七、相关阅读

- [Claude stop_sequences 高级用法：精准控制输出边界](/blog/claude-stop-sequences-guide/)
- [LLM API 错误码完全指南：重试策略与降级处理](/blog/llm-error-retry-strategy/)
- [LLM 响应格式控制：JSON Mode、结构化输出与解析](/blog/llm-response-format-cn-guide/)
- [AI API 中转错误码速查：常见错误原因与修复](/blog/ai-api-relay-error-codes/)
- [LLM 异步任务队列设计：从原型到生产](/blog/llm-async-job-queue/)

使用中转服务时，各家的 `finish_reason` 会被中转层统一暴露，[YoTradeApi](https://yotradeapi.com) 完整透传原始字段，不会丢失排查问题所需的元数据。
