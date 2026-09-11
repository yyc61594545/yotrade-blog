---
title: SSE 断线重连与消息去重：协议层设计怎么做
description: 讲解 SSE 断线重连的协议层设计：Last-Event-ID 机制、事件 ID 分配策略、客户端消息去重方法，以及 LLM 流式场景下的实现取舍。
keywords:
  - SSE断线重连
  - Last-Event-ID
  - 消息去重
  - LLM流式协议设计
  - SSE事件ID
pubDate: '2026-09-11'
updatedDate: '2026-09-11'
canonical: https://blog.yotradeapi.com/blog/llm-sse-reconnect-protocol/
tags:
  - SSE
  - 流式响应
  - 技术深度
  - 协议设计
category: 技术深度
---

SSE 断线重连这件事，SSE 协议本身其实已经预留了机制——`Last-Event-ID` 和自动重连。问题是绝大多数 LLM API（包括 OpenAI、Anthropic）的流式接口并没有完整实现这套协议，导致"断线重连"在实践中变成了业务层自己拼凑的逻辑，而拼凑的过程中最容易出错的就是消息去重。这篇文章专门讲协议层怎么设计，不涉及具体厂商的流式解析实现（那部分可以看 [跨厂商 SSE 流式解析器实现](/blog/llm-streaming-sse-parser/)），也不讲重试退避策略（那是 [LLM API 错误重试策略设计](/blog/llm-error-retry-strategy/) 的范畴），只聚焦"断了之后怎么接得上、接上之后怎么不重复"。

## 一、SSE 原生重连机制：为什么在 LLM 场景里用不上

SSE 规范里，服务端可以在每条事件前加一行 `id: <event_id>`，浏览器的 `EventSource` 收到断连后会自动重连，并在请求头里带上 `Last-Event-ID: <上次收到的最后一个 id>`，服务端理论上应该据此重放漏掉的事件。

这套机制在 LLM 流式场景里几乎用不上，原因有三个：

1. **主流 LLM API 不发 `id:` 字段**。OpenAI、Anthropic 的 SSE 输出里每条事件只有 `event:` 和 `data:`，没有 `id:`，`EventSource` 的自动重连协议因此根本没有锚点可用。
2. **多数 SDK 不用 `EventSource`**。因为要发自定义 header（Authorization）、要用 POST 方法，浏览器原生 `EventSource` 不支持这两点,所以业界基本都是手写 fetch + ReadableStream 或者用 SDK 里的流式客户端，原生重连行为根本没有被触发的机会。
3. **服务端是无状态生成，不是事件重放**。SSE 规范假设的场景是服务端有一个事件日志可以按 id 重放，但 LLM 生成是一次性的 token 流，连接断了，那次生成的下文就丢了，没有"重放"这个操作的对象。

结论是：**LLM 流式场景的断线重连，必须在应用层自己设计协议，不能依赖 SSE/EventSource 的原生机制。**

## 二、协议设计的核心：给每个 chunk 分配可去重的标识

自己设计重连协议，第一步是确定"重复"的判定标准。这里有两种思路，选型直接决定了后面所有实现的复杂度。

### 思路一：序号去重（推荐）

服务端给每次生成分配一个 `stream_id`（比如请求的 request_id），每个 chunk 附带一个从 0 开始递增的 `seq`：

```json
{"stream_id": "req_abc123", "seq": 42, "delta": "的核心", "finish": false}
```

客户端维护一个 `last_seq`，收到 chunk 时：

```python
def on_chunk(chunk):
    if chunk["stream_id"] != current_stream_id:
        return  # 不是当前流的数据，丢弃
    if chunk["seq"] <= last_seq:
        return  # 已经处理过，去重
    if chunk["seq"] != last_seq + 1:
        # 中间有缺口，说明重连时服务端跳过了一段，需要触发补偿逻辑
        log_gap(last_seq, chunk["seq"])
    last_seq = chunk["seq"]
    append_delta(chunk["delta"])
```

序号是整数比较，去重逻辑简单可靠，还能顺带检测出"缺口"（chunk 丢失但没有重复）。这是目前多数生产系统的做法。

### 思路二：内容哈希去重

对每个 chunk 的内容算哈希，用哈希值去重。这种方式在 chunk 内容可能重复（比如某个 token 恰好和前一个一样）时会误判为重复丢弃，**不推荐用在 LLM 流式场景**，序号去重的成本更低也更准确。哈希去重更适合"消息"是完整语义单元、内容不会偶然重复的场景（比如聊天消息去重），不适合 token 级别的流式增量。

## 三、断线之后：重连请求怎么"接上"

拿到 `last_seq` 之后，重连时协议怎么设计，取决于服务端有没有能力"从某个位置继续生成"。这里有两种服务端形态：

### 形态 A：服务端保留生成上下文（有状态）

服务端在生成过程中把已生成的内容和状态缓存下来（比如 Redis，TTL 设为几分钟），重连请求带上 `stream_id` 和 `last_seq`，服务端从缓存里找到对应的生成任务，把 `seq > last_seq` 的部分重新推给客户端，同时继续未完成的生成。

```
POST /v1/stream/resume
{"stream_id": "req_abc123", "last_seq": 42}
```

这是最理想的方案，用户体感是"无缝续上"，但要求服务端做生成状态的持久化和管理，实现成本较高，适合自建的 Agent 编排层或者中间层网关。

### 形态 B：服务端无状态,只能重新生成(常见情况)

大多数直接调用 OpenAI/Anthropic API 的场景是这种——上游模型服务不支持"从某个 token 继续吐"，断线之后只能重新发起一次完整请求。这种情况下,协议设计的重点不是"续传",而是**让客户端能优雅地拼接"重新生成的内容"和"之前已经展示的内容"**,通常做法是:

1. 已经展示给用户的部分内容保留不变（避免用户体感上的"文字消失"）。
2. 明确用视觉提示（比如变灰或加一个"重新生成中"的标记）区分旧内容和新内容,而不是直接拼接,因为重新生成的内容语义上和断点前的内容不是严格连续的。
3. 生成完成后,用完整的新结果替换掉整个展示区,而不是做逐字拼接。

这个形态下"消息去重"的含义变了——不是去重 chunk,而是要避免把"断点前的部分回答"和"重新生成的完整回答"同时展示给用户,造成内容重复或矛盾。国内中转链路上出现断流的具体表现和排查方法可以参考 [AI API 流式输出（SSE）故障排查与最佳实践](/blog/streaming-sse-troubleshooting/)。

## 四、心跳机制:提前发现断连,而不是等超时

被动等待 TCP 超时才发现连接已经断了,代价很高（默认几十秒到几分钟）。更好的做法是服务端定期发送心跳事件:

```
event: ping
data: {"ts": 1757000000}
```

客户端设置一个"心跳超时"（比如 15 秒没收到任何事件，包括心跳）就主动判定连接已死，触发重连逻辑，不用等底层 TCP 超时。心跳间隔建议 5-10 秒，要小于可能存在的中间代理（Nginx、Cloudflare）的空闲连接超时阈值，否则代理会先把连接断掉。

## 五、多副本部署下的一个坑：重连请求路由到了另一台机器

如果服务端是无状态但做了短期缓存（形态 A 的简化版，比如只缓存最近几十个 chunk 方便快速重连），要注意负载均衡器可能把重连请求路由到了另一台没有这份缓存的机器。解决方法通常是二选一：

- 用 `stream_id` 做一致性哈希路由，保证同一个 stream 的初始请求和重连请求落在同一台机器；
- 把生成状态缓存放到共享存储（Redis），任意机器都能取到。

自建中转层或者 Agent 网关如果要支持断线重连，这一点在架构设计阶段就要考虑，不然线上遇到的"重连了但内容对不上"的问题会很难复现和排查。

## 六、相关阅读

- [跨厂商 SSE 流式解析器实现](/blog/llm-streaming-sse-parser/)
- [Anthropic Messages 流式中断恢复实战](/blog/anthropic-message-stream-recovery/)
- [LLM API 错误重试策略设计](/blog/llm-error-retry-strategy/)
- [AI API 流式输出（SSE）故障排查与最佳实践](/blog/streaming-sse-troubleshooting/)

断线重连协议设计好之后，实际调用 OpenAI/Claude 的稳定性还要看链路本身，如果国内直连经常遇到断流，可以试试 [YoTradeApi](https://yotradeapi.com) 的中转节点，减少断连频率能从源头上少踩很多重连的坑。
