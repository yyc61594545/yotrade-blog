---
title: OpenAI Responses API 流式事件处理指南
description: 基于 OpenAI 官方文档梳理 Responses API 的 SSE 流式事件模型，讲清文本增量、工具调用、失败恢复与服务端处理流程。
keywords:
  - OpenAI Responses API 流式
  - Responses API streaming events
  - response.output_text.delta
  - OpenAI SSE 事件处理
  - OpenAI function call streaming
pubDate: '2026-08-17'
updatedDate: '2026-08-17'
canonical: https://blog.yotradeapi.com/blog/openai-responses-api-streaming-guide/
tags:
  - OpenAI
  - Responses API
  - Streaming
  - 技术深度
category: 技术深度
heroImage: ../../assets/blog-placeholder-1.jpg
---

如果你以前是从 Chat Completions 的 `delta` 流式输出一路用过来的，第一次接 `Responses API` 时很容易误判：看起来也是 `stream=true`，但它的事件模型已经不是“收到一个 chunk 就拼一段文本”那么简单了。按照 OpenAI 官方文档当前说明，`Responses API` 的流式接口是基于 SSE 的语义化事件流，设计上就是为了让开发者能稳定处理文本、工具调用、拒答、搜索和代码执行等不同阶段。

这意味着你的服务端如果还沿用旧习惯，只盯着“有没有 token 输出”，往往会漏掉真正关键的状态变更。本文基于 OpenAI 官方文档，把 `Responses API` 的流式事件怎么接、怎么分层处理、哪些事件该落日志、哪些事件该驱动前端状态，拆成一套可直接落地的思路。

## 一、先理解：Responses Streaming 不是“文本流”，而是“事件流”

OpenAI 当前官方流式指南给出的推荐方式，是对 `Responses` 端点设置 `stream=True`，然后迭代返回的事件对象。官方也明确建议：如果要做流式输出，优先用 `Responses API`，因为它从一开始就是围绕流式和类型化事件设计的。

一个最小示例可以这样理解：

```python
from openai import OpenAI

client = OpenAI()

stream = client.responses.create(
    model="gpt-5.6",
    input="用一句话解释 SSE 是什么",
    stream=True,
)

for event in stream:
    print(event.type)
```

重点不在这段代码本身，而在于你得到的不是单一种类的数据，而是一串不同语义的事件。按照官方事件参考，常见主线包括：

| 事件类型 | 说明 | 典型用途 |
| --- | --- | --- |
| `response.created` / `response.in_progress` | 响应已创建、开始执行 | 前端状态切换、trace 起点 |
| `response.output_item.added` | 新输出项开始生成 | 建立消息或工具项容器 |
| `response.output_text.delta` | 文本增量到达 | 实时显示文本 |
| `response.output_text.done` | 某段文本完成 | 做收尾、校验、持久化 |
| `response.function_call_arguments.delta` | 工具参数增量到达 | 调试或渐进式工具 UI |
| `response.function_call_arguments.done` | 工具参数已定稿 | 真正触发工具执行 |
| `response.completed` | 整个响应完成 | 统计 usage、关闭流 |
| `response.failed` / `response.incomplete` | 失败或未完成 | 告警、重试、回退 |

只看这个表就能发现一个关键差异：`Responses API` 是在给你“过程事件”，而不是只给你“最终文本的残片”。

## 二、最常用的文本主线：added -> delta -> done -> completed

在普通问答场景里，很多团队只需要把模型文本实时打到页面上。这条路径最常见，也最容易写错。

推荐的处理顺序是：

1. 收到 `response.output_item.added` 时，为当前 assistant 消息建立容器。
2. 收到 `response.output_text.delta` 时，把 `delta` 拼到对应内容片段。
3. 收到 `response.output_text.done` 时，把这一段文本标记为 finalized。
4. 收到 `response.completed` 时，再把整条响应作为“最终成功结果”落库。

这样做的原因很简单：`output_text.done` 只说明某段文本结束了，`response.completed` 才说明整个响应生命周期结束。两者不要混用。

一个实用的服务端分层可以写成这样：

```ts
for await (const event of stream) {
  switch (event.type) {
    case "response.output_item.added":
      createMessageShell(event.output_index, event.item.id);
      break;
    case "response.output_text.delta":
      appendText(event.item_id, event.content_index, event.delta);
      break;
    case "response.output_text.done":
      finalizeText(event.item_id, event.content_index, event.text);
      break;
    case "response.completed":
      markResponseCompleted(event.response.id, event.response.usage);
      break;
  }
}
```

这里最容易踩的坑，是把 `delta` 直接当最终结果使用。只要网络断流、客户端重连或中途出现工具调用，你就会发现“页面上看着像结束了，服务端其实没收完”。因此，**实时显示和最终确认必须分层**。

## 三、工具调用不要在 `delta` 阶段执行，要等 `done`

很多 Agent 服务在接 `Responses API` 时，会犯一个危险错误：看到函数参数流式出来就开始调用工具。这样做看起来延迟更低，实际上很容易因为参数尚未完整，导致执行出错或触发不一致。

按官方事件定义，更稳妥的做法是：

- `response.function_call_arguments.delta`
  只用于观测、调试，或者前端展示“模型正在组织参数”
- `response.function_call_arguments.done`
  才表示这次函数调用的 `name` 和 `arguments` 已经定稿，可以安全执行

这一点很重要，因为函数参数本质上也是增量文本。你在 `delta` 阶段看到的可能只是一个半截 JSON。正确做法是等到 `done`，再做 JSON 解析和工具执行。

| 阶段 | 能不能执行工具 | 更适合做什么 |
| --- | --- | --- |
| `function_call_arguments.delta` | 不建议 | 打日志、显示“正在构造参数” |
| `function_call_arguments.done` | 可以 | 解析参数、校验 schema、调用工具 |
| 工具结果回传后下一轮响应 | 可以继续流式 | 展示最终自然语言答案 |

如果你的系统还会接 `file_search`、`web_search` 或代码执行一类内置工具，官方事件参考里也有对应的 `in_progress`、`searching`、`completed` 状态。它们的价值不在“好看”，而在于你终于可以明确区分：当前慢，是模型在写字，还是工具在跑。

## 四、为什么事件要按 `item_id` 和索引分桶，而不是只拼字符串

`Responses API` 的事件里反复出现 `item_id`、`output_index`、`content_index`，这不是多余设计。它是在提醒你：一个响应并不总是只有一段连续文本。

你至少要准备处理三种情况：

1. 一个响应里有多个输出项，例如先出现工具调用，再出现文本答案。
2. 一个输出项里有多个内容片段，例如文本、拒答、引用标注等。
3. 某些事件需要在前一个事件基础上归并，而不是覆盖。

所以服务端内部状态最好不要只存一个 `currentText += delta`。更稳妥的结构是：

```json
{
  "responseId": "resp_xxx",
  "items": {
    "item_1": {
      "outputIndex": 0,
      "parts": {
        "0": { "type": "output_text", "text": "..." }
      }
    }
  }
}
```

这样做有两个直接好处。第一，你能把流式 UI、日志和持久化统一到同一份状态结构里。第二，后面如果要支持注解、引用、工具执行记录，不需要重写整套聚合逻辑。

## 五、失败和未完成不是一回事，恢复策略也不一样

官方事件列表里，`response.failed` 和 `response.incomplete` 是两个不同结果，很多实现把它们混成同一类异常处理，这是不够细的。

可以这样理解：

| 结束状态 | 含义 | 常见处理方式 |
| --- | --- | --- |
| `response.completed` | 正常完成 | 持久化最终结果、记录 usage |
| `response.failed` | 执行失败，带 `error` | 告警、可重试、回退模型 |
| `response.incomplete` | 响应未完整结束 | 看 `incomplete_details.reason` 决定补救 |

比如 `incomplete` 可能意味着输出被截断、预算不够、或其他非“硬失败”场景。这时如果你直接当成 500 错误重试，有时会把问题越放越大。更合理的办法是：

- 对 `failed` 做模型级或网络级重试
- 对 `incomplete` 优先做业务级补救，例如收敛提示词、缩短上下文、单独提示前端“回答未完整生成”

这和[LLM 流式响应背压处理：防止服务端被打爆的实战指南](/blog/llm-streaming-backpressure/)其实是一体两面：流式系统的难点从来不只是“快”，而是“快的时候还能稳”。

## 六、把流式处理分成三层，系统会好维护很多

很多团队在早期会把所有事件处理写进一个 `switch` 里，能跑，但很快难维护。更推荐拆成三层：

### 1. 传输层

负责接住 SSE 事件、识别断流、维护连接生命周期。它不应该决定业务含义。

### 2. 聚合层

负责按 `response_id`、`item_id`、`content_index` 归并事件，把离散的 `delta/done/completed` 整成一份可读状态。

### 3. 业务层

负责把聚合后的状态分发给 UI、日志、数据库、工具执行器、监控系统。

一个常见的职责分配表如下：

| 层级 | 关心什么 | 不该关心什么 |
| --- | --- | --- |
| 传输层 | SSE 连接、断流、超时 | 文本是否该展示 |
| 聚合层 | 事件归并、状态机 | 业务重试策略 |
| 业务层 | 展示、执行、存储、告警 | 原始 SSE 细节 |

这套分层还有个额外好处：以后你要从 `Responses` 的 HTTP SSE 扩展到 WebSocket 模式时，改动面会小很多。官方流式指南也明确区分了两种 transport：当前这篇主要讨论的是 `stream=true` 的 SSE；如果你需要更持久的双向通道，再考虑 WebSocket 模式即可。

## 七、和旧的 Chat Completions Streaming 相比，迁移重点是什么

如果你现在还在维护旧的 `chat.completions` 流式代码，迁移到 `Responses API` 时最重要的不是改 endpoint，而是改心智模型。

旧模型偏向：

- 每次拿一个 chunk
- 从 `choices[0].delta` 里抽内容
- 主要围绕文本拼接

新的 `Responses` 流式模型更偏向：

- 每次拿一个 typed event
- 围绕 response/item/content 三层状态管理
- 文本、工具、拒答、搜索都走统一事件流

如果你的产品未来还要接工具调用、文件搜索或多模型统一网关，这种事件化设计会明显更省事。迁移的基础背景可以再看[OpenAI Assistants API 与 Responses API 迁移指南](/blog/openai-assistants-vs-responses/)，事件模型对比可以参考[Claude 流式响应事件类型完全指南](/blog/claude-streaming-event-types/)。

## 八、相关阅读

- [OpenAI Assistants API 与 Responses API 迁移指南](/blog/openai-assistants-vs-responses/)
- [LLM 流式响应背压处理：防止服务端被打爆的实战指南](/blog/llm-streaming-backpressure/)
- [Claude 流式响应事件类型完全指南](/blog/claude-streaming-event-types/)
- [OpenAI Realtime API 国内使用指南](/blog/openai-realtime-api-guide/)

如果你要把 OpenAI 的流式能力接进统一的多模型服务层，[YoTradeApi](https://yotradeapi.com) 提供兼容式 API 接入方式，便于把流式输出、工具调用和模型切换放进同一套工程管线里。
