---
title: Anthropic Messages 流式中断恢复实战
description: Claude Messages API 流式响应中途断连后如何恢复：为什么不能简单重连、部分内容块的处理、工具调用态的恢复策略与幂等重试设计。
keywords:
  - Claude 流式中断恢复
  - Anthropic Messages API
  - 流式断线重连
  - claude stream resume
  - 幂等重试设计
pubDate: '2026-08-20'
updatedDate: '2026-08-20'
canonical: https://blog.yotradeapi.com/blog/anthropic-message-stream-recovery/
tags:
  - Claude
  - 流式响应
  - 故障恢复
  - 技术深度
category: 技术深度
heroImage: ../../assets/blog-placeholder-1.jpg
---

流式响应中途断连是生产环境里迟早会遇到的问题——网络抖动、代理超时、客户端进程重启都可能打断一个正在进行的 `stream=true` 请求。Anthropic Messages API 没有提供类似"续传 token"的原生恢复机制，断了就是断了，剩下的内容不会凭空补全。本文讲清楚断连之后该怎么处理，而不是假装这个问题不存在。

关于 SSE 事件本身的结构，可以先看 [Claude 流式响应事件类型完全指南](/blog/claude-streaming-event-types/)；关于国内中转链路下的断流排查，参考 [AI API 流式输出（SSE）故障排查与最佳实践](/blog/streaming-sse-troubleshooting/)。本文聚焦断连之后**应用层该怎么恢复**，是前两篇的下一步。

## 一、为什么不能简单地"重连"

流式对话不是文件下载，没有 `Range` 头可以断点续传。一次 `messages.create(stream=True)` 请求断开后，服务端不会记得你已经收到了多少内容——重新发起请求，模型会从头生成一个全新的响应，很可能和之前收到的部分完全不同。

这意味着"恢复"实际上有两种完全不同的含义，必须先分清楚：

- **续写恢复**：假装模型知道自己写到哪了，直接续着写下去——这在 Anthropic 现有 API 上做不到
- **重新生成恢复**：把已收到的部分内容当作已完成的对话历史，让模型基于这个历史继续生成剩下的部分——这是唯一可行的路径

后面的方案都是围绕第二种思路展开的。

## 二、断连时数据状态是什么样

流式响应按 `content_block` 切分，断连可能发生在任意位置。你手上会有以下几种残留状态之一：

| 断连时机 | 收到的数据 | 处理难度 |
| --- | --- | --- |
| 第一个 `content_block_start` 之前 | 几乎没有内容 | 简单，等同于全新请求 |
| 某个 text block 中途 | 部分文本，无 `content_block_stop` | 中等，需要判断截断位置是否在语义完整处 |
| tool_use block 中途 | 部分 JSON 参数，`input` 不完整 | 复杂，不完整的 JSON 无法直接解析 |
| 多个 content block 之间 | 若干完整 block + 一个不完整 block | 中等，完整部分可直接复用 |

**tool_use 中途断连是最麻烦的情况**：`input` 字段是流式增量拼接的 JSON 字符串，断在中间意味着你手上是一段无法解析的半截 JSON，既不能当作有效参数使用，也不能简单丢弃已产生的 token（浪费了这部分生成成本和延迟）。

## 三、恢复策略：把已收到内容降级为历史消息

具体做法：

```python
import anthropic

client = anthropic.Anthropic()

def stream_with_recovery(messages, max_retries=2):
    partial_text = ""
    for attempt in range(max_retries + 1):
        try:
            with client.messages.stream(
                model="claude-sonnet-5",
                max_tokens=2048,
                messages=messages,
            ) as stream:
                for event in stream.text_stream:
                    partial_text += event
                    yield event
            return  # 正常结束，直接返回
        except (anthropic.APIConnectionError, anthropic.APITimeoutError):
            if attempt == max_retries:
                raise
            if partial_text.strip():
                # 把已生成部分降级为 assistant 历史消息，
                # 追加一条 user 消息要求续写，而不是假装没发生过中断
                messages = messages + [
                    {"role": "assistant", "content": partial_text},
                    {"role": "user", "content": "继续，从刚才中断的地方接着写，不要重复已经写过的内容。"},
                ]
                partial_text = ""
```

这个模式的关键是**诚实地告诉模型发生了中断**，而不是把半截内容悄悄拼接后指望模型自己发现。让模型知道"这是接着写"，能显著减少重复和逻辑断裂。

## 四、tool_use 中断的专门处理

如果断连发生在 tool_use block 中途，半截的 `input` JSON 直接丢弃，不要尝试"修补"成合法 JSON——那样拼出来的参数值本身就是不可信的。正确做法：

1. 检查已收到的 `content_block_start` 里的 `name` 字段，你至少知道模型想调用哪个工具
2. 丢弃这个不完整的 tool_use block，不要执行它
3. 重新发起请求，把此前已完整生成的内容作为历史，让模型重新决定是否调用工具、传什么参数

```python
if event.type == "content_block_start" and event.content_block.type == "tool_use":
    pending_tool_name = event.content_block.name
    tool_input_buffer = ""
elif event.type == "input_json_delta":
    tool_input_buffer += event.partial_json
elif event.type == "content_block_stop":
    # 只有走到这一步，tool_input_buffer 才是完整、可解析的 JSON
    tool_call = json.loads(tool_input_buffer)
```

如果中断发生在 `content_block_stop` 之前，`tool_input_buffer` 里的内容不做任何处理，直接丢弃。

## 五、幂等性：重试时避免重复副作用

如果 tool_use 已经执行过一次（比如调用了一个下单接口），断连后的重试流程可能让模型重新决定调用同一个工具。这时候幂等性要在**工具执行层**兜底，而不是指望流式协议本身处理：

- 每次工具调用带上一个业务侧生成的幂等 key（不是 Anthropic 生成的，需要你自己维护）
- 工具执行前先查是否已有相同 key 的执行记录，有则直接返回缓存结果，不重复执行
- 对于不可逆操作（发消息、扣费、下单），幂等 key 是必须项，不是可选优化

这一层逻辑和"流式恢复"是两个独立问题，但断连重试会把它们绑在一起——没有幂等设计的工具调用，遇到断连重试就是事故高发点。

## 六、什么时候不值得做恢复

不是所有场景都值得实现完整的恢复逻辑。对短输出（几百 token 以内）、非关键路径的请求，直接重新发起一次全新请求往往比维护一套恢复状态机更划算——恢复逻辑本身也有 bug 风险，复杂度要花在真正需要的地方：长文本生成、多轮工具调用链、用户已经等待较久的场景。

## 七、相关阅读

- [Claude 流式响应事件类型完全指南](/blog/claude-streaming-event-types/)
- [AI API 流式输出（SSE）故障排查与最佳实践](/blog/streaming-sse-troubleshooting/)
- [Claude Tool Use 与流式响应结合实践](/blog/claude-tool-use-with-streaming/)
- [LLM 流式响应背压处理](/blog/llm-streaming-backpressure/)

如果你的流式请求经常在国内网络环境下断连，先排除中转链路本身的问题——[YoTradeApi](https://yotradeapi.com) 针对流式连接做了链路优化，减少不必要的断流重试。
