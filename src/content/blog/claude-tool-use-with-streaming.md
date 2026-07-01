---
title: Claude 流式 + 工具调用的正确姿势
description: 讲清楚 Claude 在流式响应中携带 tool_use 内容块时的事件顺序、input_json_delta 拼接、以及工具执行后如何续接流式对话的完整实现。
keywords:
  - claude streaming tool use
  - claude 流式工具调用
  - input_json_delta
  - claude sse tool_use
  - 工具调用流式续接
pubDate: '2026-07-01'
updatedDate: '2026-07-01'
canonical: https://blog.yotradeapi.com/blog/claude-tool-use-with-streaming/
tags:
  - Claude
  - Tool Use
  - 流式响应
  - 技术深度
category: 技术深度
heroImage: ../../assets/blog-placeholder-5.jpg
---

流式响应（streaming）和工具调用（tool use）分开看都不复杂，但组合在一起——也就是让模型在流式输出中途决定调用一个工具——很多开发者第一次实现时会踩坑：工具参数是分片到达的、什么时候算"工具调用参数已经完整"不直观、执行完工具后怎么让对话继续以流式方式输出后续内容。本文只讲这个交叉场景，SSE 事件类型的完整清单和 tool_use 本身的设计原则，站内已有专门文章，这里不重复展开基础概念。

## 一、为什么这个组合场景容易出错

单独看流式响应，你处理的是一串文本增量（`content_block_delta` 里的 `text_delta`），逐块拼起来显示给用户。单独看工具调用（非流式），你拿到的是一个完整的 JSON 参数对象，可以直接解析使用。但两者结合后，工具调用的**参数本身也是分片流式到达的**——不是一次性给你一个完整 JSON，而是通过一连串 `input_json_delta` 事件，把参数 JSON 的文本内容一小块一小块地发过来，你需要自己把这些片段拼接成完整字符串，再解析成 JSON。这一步是最容易被忽略的细节。

## 二、事件流的实际顺序

当 Claude 决定调用工具时，流式响应里会出现下面这样的事件序列（简化示意，真实事件可能包含更多细节字段）：

```
message_start
content_block_start   (index: 0, type: text)          # 模型先输出一段说明性文字（可选）
content_block_delta   (index: 0, text_delta: "让我查一下...")
content_block_stop    (index: 0)
content_block_start   (index: 1, type: tool_use, name: "get_weather", id: "toolu_xxx")
content_block_delta   (index: 1, input_json_delta: partial_json: "{\"loc")
content_block_delta   (index: 1, input_json_delta: partial_json: "ation\": \"")
content_block_delta   (index: 1, input_json_delta: partial_json: "上海\"}")
content_block_stop    (index: 1)
message_delta         (stop_reason: "tool_use")
message_stop
```

关键观察：**`index: 1` 对应的这个 tool_use 内容块，它的参数是通过多个 `input_json_delta` 事件累加的，必须等到对应的 `content_block_stop` 事件出现，才能确认这个工具的参数已经完整，可以安全解析**。在此之前尝试解析拼接了一半的 JSON 字符串，大概率会因为 JSON 不完整而解析失败。

## 三、完整实现：累积并处理工具调用

```python
import json
import anthropic

client = anthropic.Anthropic()

def handle_streaming_with_tools(messages: list, tools: list) -> dict:
    text_parts = []
    tool_calls = []
    current_tool = None
    current_json_buffer = ""

    with client.messages.stream(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        tools=tools,
        messages=messages,
    ) as stream:
        for event in stream:
            if event.type == "content_block_start":
                if event.content_block.type == "tool_use":
                    current_tool = {
                        "id": event.content_block.id,
                        "name": event.content_block.name,
                    }
                    current_json_buffer = ""
            elif event.type == "content_block_delta":
                if event.delta.type == "text_delta":
                    text_parts.append(event.delta.text)
                    print(event.delta.text, end="", flush=True)  # 实时展示给用户
                elif event.delta.type == "input_json_delta":
                    current_json_buffer += event.delta.partial_json
            elif event.type == "content_block_stop":
                if current_tool is not None:
                    current_tool["input"] = json.loads(current_json_buffer)
                    tool_calls.append(current_tool)
                    current_tool = None

    return {"text": "".join(text_parts), "tool_calls": tool_calls}
```

用官方 SDK 的 `stream()` 辅助方法时，实际上很多 SDK（包括 Python SDK）已经内置了 `input_json_delta` 的累积逻辑，可以直接通过 `stream.get_final_message()` 拿到组装好的完整 message，不需要手动拼接 buffer——上面的手写版本是为了讲清楚底层机制，生产代码建议优先用 SDK 提供的高层封装，减少自己维护拼接逻辑的出错概率。

## 四、执行工具后如何续接流式对话

拿到完整的工具调用参数后，下一步是执行工具、把结果传回去，并让模型继续以流式方式生成后续内容。这一步的关键是把工具结果作为一条新的 user message（角色仍是 `tool_result` 类型的内容块）加入对话历史，再发起新的流式请求：

```python
def run_tool(name: str, tool_input: dict) -> str:
    if name == "get_weather":
        return f"{tool_input['location']} 当前 26°C，晴"
    return "未知工具"

def full_conversation_turn(messages: list, tools: list) -> list:
    result = handle_streaming_with_tools(messages, tools)

    if not result["tool_calls"]:
        return messages + [{"role": "assistant", "content": result["text"]}]

    assistant_content = []
    if result["text"]:
        assistant_content.append({"type": "text", "text": result["text"]})
    for call in result["tool_calls"]:
        assistant_content.append({
            "type": "tool_use", "id": call["id"], "name": call["name"], "input": call["input"],
        })
    messages = messages + [{"role": "assistant", "content": assistant_content}]

    tool_results = []
    for call in result["tool_calls"]:
        output = run_tool(call["name"], call["input"])
        tool_results.append({
            "type": "tool_result", "tool_use_id": call["id"], "content": output,
        })
    messages = messages + [{"role": "user", "content": tool_results}]

    # 递归/循环再次发起流式请求，让模型基于工具结果继续生成
    return full_conversation_turn(messages, tools)
```

这个循环的终止条件是模型这一轮不再返回 `tool_use` 内容块（`result["tool_calls"]` 为空），此时把最终的文本回复追加进历史即可。注意每一轮都要把上一轮的 assistant 消息（包含文字说明和工具调用请求）完整保留在历史里，再紧跟一条包含 `tool_result` 的 user 消息，顺序不能颠倒，否则 API 会报错提示 tool_use 和 tool_result 没有正确配对。

## 五、给用户的实时体验设计

流式 + 工具调用组合场景下，用户体验设计上有一个容易被忽略的点：**工具执行本身需要时间（调用外部 API、查数据库），这段时间里前端应该给用户明确的反馈，而不是让界面看起来卡住了**。推荐的处理方式：

1. 模型输出的说明性文字（比如"让我查一下天气"）实时流式展示，让用户知道接下来会发生什么。
2. 检测到 `tool_use` 内容块开始时，前端可以展示一个"正在调用工具"的加载状态（比如显示工具名称，"正在查询天气..."）。
3. 工具执行完成、新一轮流式响应开始后，正常展示后续文字增量。

这种"文字-加载态-文字"的交替体验，比让用户盯着一个没有任何反馈的空白等待要好得多，具体的流式 UI 交互模式可以参考站内《LLM 流式响应 UI 交互模式》一文，这里只强调工具调用场景下这个反馈节点的必要性。

## 六、常见问题排查

- **JSON 解析失败**：确认是在收到对应的 `content_block_stop` 事件之后才尝试解析累积的 JSON 字符串，中途解析必然失败，这是最常见的错误。
- **多个工具并行调用时的索引混淆**：如果模型在一轮里并行调用多个工具，会有多个 `index` 并行推进的 content block，务必按 `index` 分别维护各自的 buffer，不要用一个全局 buffer 累积所有工具的参数，并行工具调用的具体机制可参考站内《Claude 并行 Tool Use 实战》。
- **消息历史顺序错误**：`tool_use` 内容块所在的 assistant 消息和紧随其后包含 `tool_result` 的 user 消息必须严格配对且顺序正确，中间不能插入其他消息，否则 API 会拒绝请求。
- **中转服务的流式兼容性**：如果通过 API 中转访问，确认中转层对 SSE 流的转发没有做缓冲式的"攒够一批再转发"处理（这会让流式变成伪流式，`input_json_delta` 的实时性也会受影响），可以通过实际抓包测试首字节到达时间来验证。

## 七、结论

流式响应和工具调用的组合，核心难点在于**工具参数本身是分片到达的，必须等 `content_block_stop` 事件确认完整性后再解析**，以及**执行完工具后要严格按顺序把 assistant 的工具调用请求和 user 的工具结果配对放入历史，再发起新一轮流式请求**。掌握这两个机制后，剩下的就是常规的流式 UI 状态管理。生产环境建议优先使用官方 SDK 提供的高层封装（如 Python SDK 的 `stream.get_final_message()`），只在需要精细控制实时展示逻辑时才手动处理底层事件。

## 八、相关阅读

- [Claude 流式响应事件类型完全指南](/blog/claude-streaming-event-types/)
- [Claude Tool Use 最佳实践与陷阱](/blog/claude-tool-use-best-practices/)
- [Claude 并行 Tool Use 实战：一次调用多个工具](/blog/parallel-tool-use-claude/)
- [LLM 流式响应 UI 交互模式](/blog/llm-streaming-ui-patterns/)

如果你的应用需要稳定调用 Claude 的流式和工具调用能力，[YoTradeApi](https://yotradeapi.com) 提供国内可直连的 API 中转服务，完整支持 SSE 流式转发，避免自建代理导致的连接不稳定问题。
