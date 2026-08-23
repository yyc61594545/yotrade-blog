---
title: 跨厂商 SSE 流式解析器实现
description: 从字节流分帧、SSE 字段解析到厂商事件适配，完整实现跨厂商 LLM SSE 流式解析器，并处理 UTF-8 分片、工具参数增量、结束信号与未知事件。
keywords:
  - 跨厂商 SSE 解析器
  - LLM 流式响应解析
  - OpenAI Anthropic Streaming
  - SSE 字节流分帧
  - Tool Call 增量解析
pubDate: '2026-08-23'
updatedDate: '2026-08-23'
canonical: https://blog.yotradeapi.com/blog/llm-streaming-sse-parser/
tags:
  - SSE
  - Streaming
  - LLM API
  - TypeScript
category: 技术深度
heroImage: ../../assets/blog-placeholder-2.jpg
---

同时接入多家 LLM 时，流式响应很容易积累技术债。接口都可能使用 `text/event-stream`，却采用不同事件名、结束信号和 JSON 结构。若业务代码到处判断厂商，展示、工具和错误处理就会缠绕。更稳的实现分四层：字节解码、SSE 分帧、厂商适配、事件聚合。

## 一、先把四种边界分开

网络 chunk 不等于一个 UTF-8 字符、一行或一个 SSE event，更不等于完整 JSON。一次读取可能只拿到汉字的部分字节，也可能包含多个事件；工具参数还可能只是 JSON 字符串片段。

解析器应按以下边界逐层收敛：

| 层级 | 输入 | 输出 | 不负责什么 |
| --- | --- | --- | --- |
| 字节层 | `Uint8Array` | 连续文本 | 不按行猜事件 |
| SSE 层 | 文本行 | `{event, data, id}` | 不理解厂商 JSON |
| 适配层 | 原始 SSE event | 统一领域事件 | 不直接更新 UI |
| 聚合层 | 领域事件 | 消息、工具和用量状态 | 不读取网络 |

这种分层允许逐级单测，厂商增加事件时只改适配器。连接和代理层的断流、缓冲问题，可另见 [AI API 流式输出故障排查](/blog/streaming-sse-troubleshooting/)，本文只关注字节解析。

## 二、字节解码必须保留跨 chunk 状态

浏览器和 Node.js 的 `TextDecoder` 都支持流式解码。关键是对中间 chunk 使用 `{ stream: true }`，结束时再调用一次无参数 `decode()` 冲刷尾部。直接对每个 chunk 单独转字符串，可能把跨边界的中文或 emoji 变成替换字符。

换行也不能只认 `\n\n`。SSE 可出现 `\r\n`，而两个换行符本身也可能被拆到不同 chunk。简单可靠的办法是维护文本缓冲区，逐行取出 `\n`，再移除行尾 `\r`；遇到空行才提交当前事件。最后流结束时，如果还有未提交字段，应根据产品策略提交或报告截断，不能悄悄丢弃。

## 三、实现一个与厂商无关的 SSE 分帧器

SSE 消息可包含 `event`、`data`、`id` 和 `retry`；冒号开头的是注释。多个 `data:` 行要用换行连接，而不是覆盖。核心行解析可写成：

```ts
type RawSse = { event?: string; data: string[]; id?: string };
let current: RawSse = { data: [] };

function consumeLine(raw: string): RawSse | undefined {
  const line = raw.replace(/\r$/, "");
  if (!line) {
    if (!current.data.length) return;
    const ready = current;
    current = { data: [] };
    return ready;
  }
  if (line.startsWith(":")) return; // heartbeat
  const [field, ...rest] = line.split(":");
  const value = rest.join(":").replace(/^ /, "");
  if (field === "data") current.data.push(value);
  if (field === "event") current.event = value;
  if (field === "id" && !value.includes("\0")) current.id = value;
}
```

外层循环负责用 `TextDecoder` 解码、按换行调用它，并把 `data.join("\n")` 交给适配器。生产实现还要限制行与事件大小；`retry` 交给连接管理层，解析器不自行发请求。

## 四、厂商适配器只输出统一领域事件

SSE 层完成后再解析 `data` JSON。不要让上层依赖具体厂商字段；统一事件只需覆盖 `text_delta`、`tool_delta`、`usage`、`completed`、`error` 与 `unknown`，并分别携带流 ID、调用 ID 或结束原因。

每个厂商适配器实现 `adapt(raw): LlmEvent[]`。不同接口的结束信号都映射为 `completed`，文本和工具参数则分别映射。Anthropic 原生序列可参考 [Claude 流式响应事件类型完全指南](/blog/claude-streaming-event-types/)，Responses 模型可参考 [OpenAI Responses API 流式事件处理指南](/blog/openai-responses-api-streaming-guide/)。

统一不等于抹平所有差异。领域模型暂时表达不了的事件应转成 `unknown` 并记录类型、计数和脱敏后的样本。直接忽略未知事件会让厂商协议升级变成静默数据损失。

## 五、工具参数只能累积，不能边到边执行

工具调用的参数经常以字符串增量传输。单个 fragment 可能是 `{"city":"北`，它不是合法 JSON。聚合器应按稳定的 `callId` 分桶，把片段按接收顺序追加；只有收到工具参数完成或内容块结束事件后，才执行 `JSON.parse`、Schema 校验和工具调用。

并行调用不能只维护一个 `currentArguments`。应用至少用 `Map<callId, {name, fragments}>` 分桶；若原协议只有索引，就组合响应 ID 与调用索引生成内部 ID。缺少完成事件时标记 incomplete，绝不执行半截参数。

## 六、结束、错误和取消是三种不同状态

HTTP 连接关闭不等于模型正常完成。只有收到协议定义的完成事件，聚合结果才可标记为 `completed`。连接提前关闭应是 `truncated`；厂商在流内发回错误应是 `failed`；用户主动停止则是 `cancelled`。这四种状态决定是否持久化最终答案、是否允许重试，以及前端显示什么提示。

应用要区分“已展示文本”和“已确认结果”：delta 可实时推给 UI，数据库终态要等完成事件。断流恢复时可给统一事件分配递增序号；完整设计可阅读 [Anthropic 流式消息中断恢复实战](/blog/anthropic-message-stream-recovery/)。

## 七、测试要故意打碎每一个边界

测试不应只喂完整字符串。把同一 fixture 在每个字节位置切开，输出必须一致；还要覆盖 `\n` 与 `\r\n`、多行 `data`、心跳、多个事件同 chunk、UTF-8 拆分、异常 JSON、超长事件和无结束信号。

适配器用原始事件 fixture 做契约测试，聚合器验证文本顺序、工具分桶和终态。日志记录 provider、事件类型、解析错误与未知事件数；`data` 只记长度与哈希，避免泄露提示词或工具参数。

## 八、相关阅读

- [AI API 流式输出故障排查与最佳实践](/blog/streaming-sse-troubleshooting/)
- [Claude 流式响应事件类型完全指南](/blog/claude-streaming-event-types/)
- [OpenAI Responses API 流式事件处理指南](/blog/openai-responses-api-streaming-guide/)
- [Anthropic 流式消息中断恢复实战](/blog/anthropic-message-stream-recovery/)

如果你希望通过一套接入方式调用多种模型并保留流式输出能力，[YoTradeApi](https://yotradeapi.com) 可提供兼容 API，便于在应用侧复用统一的 SSE 解析与聚合管线。
