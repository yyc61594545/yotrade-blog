---
title: Responses API 多轮工具调用循环实战
description: 基于 OpenAI 官方文档梳理 Responses API 的多轮 tool loop，用实战方式讲清 function_call、function_call_output、previous_response_id 与推理模型的注意点。
keywords:
  - Responses API tool loop
  - OpenAI function_call_output
  - previous_response_id 工具调用
  - OpenAI reasoning tool loop
  - Responses API 多轮函数调用
pubDate: '2026-08-17'
updatedDate: '2026-08-17'
canonical: https://blog.yotradeapi.com/blog/openai-responses-api-tool-loop/
tags:
  - OpenAI
  - Responses API
  - Tool Calling
  - 技术深度
category: 技术深度
heroImage: ../../assets/blog-placeholder-3.jpg
---

很多人第一次用 `Responses API` 做工具调用，第一轮都能跑通：模型返回一个 `function_call`，本地函数执行一下，再把结果喂回模型。但只要流程变成多轮，或者一个响应里同时出现多个工具调用，代码就容易变乱。最典型的问题有三个：上一轮到底哪些内容要带回去？工具结果该挂在哪个 `call_id` 上？推理模型返回的中间项要不要保留？

OpenAI 当前官方函数调用文档对这些点已经给出很明确的答案。`Responses API` 的多轮工具循环不是“重新发一条用户消息”，而是围绕 `response.output`、`function_call_output` 和 `previous_response_id` 建立一条连续的执行链。只要这个链断了，模型就会失忆、重复调用工具，或者产出和上下文对不上的答案。

本文基于官方文档，把 `Responses API` 的多轮工具循环拆成一套实战模板，重点讲真实工程里最容易出错的部分。

## 一、先记住核心心智：循环的单位是“响应链”，不是“聊天轮次”

在 `Chat Completions` 时代，很多工具调用逻辑是把 assistant message 和 tool message 追加到 `messages` 数组里，再发下一轮请求。`Responses API` 也保留了“把历史喂回去”的能力，但组织方式更接近“响应链”。

官方文档里有两个关键事实：

1. `response.output` 数组里会包含 `type=function_call` 的条目，每个条目带有 `call_id`、`name` 和 JSON 编码的 `arguments`。
2. 下一轮请求要把工具结果以 `type=function_call_output` 的输入项发回去，并通过 `previous_response_id` 继续挂在上一轮响应之后。

这意味着一轮 tool loop 不只是“拿到参数 -> 调函数 -> 再问模型”，而是“沿着上一轮响应继续推进”。一旦你把这个链路理解成状态机，代码会稳定很多。

## 二、最小闭环长什么样：收到 function_call，再发 function_call_output

官方文档给出的最小模式可以概括成下面这几步：

1. 第一次 `responses.create`，传 `input` 和 `tools`。
2. 从 `response.output` 中找出所有 `function_call` 项。
3. 执行本地函数，并为每个调用生成一个 `function_call_output`。
4. 第二次 `responses.create` 时传 `previous_response_id`，并把这些输出项作为 `input` 发回。

一个精简的 Python 模板如下：

```python
response = client.responses.create(
    model="gpt-5.6",
    input="查一下巴黎天气，再帮我写一封提醒邮件",
    tools=tools,
)

followup_input = []

for item in response.output:
    if item.type != "function_call":
        continue

    args = json.loads(item.arguments)
    result = call_function(item.name, args)
    followup_input.append({
        "type": "function_call_output",
        "call_id": item.call_id,
        "output": json.dumps(result),
    })

next_response = client.responses.create(
    model="gpt-5.6",
    previous_response_id=response.id,
    input=followup_input,
    tools=tools,
)
```

这里最重要的是 `call_id`。它不是装饰字段，而是模型用来把“哪个工具结果对应哪个工具请求”重新对齐的主键。你只要回错一个 `call_id`，整轮推理就会偏掉。

## 三、多轮循环里，不要只传工具结果，必要时要把输出项也并回输入

当流程从“一轮一个工具”变成“多轮多个工具”时，很多实现会漏掉一个关键动作：把上一轮的 `response.output` 项保留下来，再把本轮工具结果追加进去。

OpenAI 官方函数调用示例里明确展示了这种模式：先把 `response.output` 追加到待发送输入，再继续把每个工具结果包装成 `function_call_output`。这样做的目的，是保留模型上一轮已经产生的结构化上下文，而不是只回传裸工具结果。

可以把它理解成下面这个关系：

| 数据类型 | 作用 | 下一轮是否要考虑带回 |
| --- | --- | --- |
| `response.output` 中的 `function_call` | 说明模型做了什么调用决策 | 多轮场景通常要保留 |
| `function_call_output` | 告诉模型工具执行结果 | 必须带回 |
| 普通文本输出 | 最终回答或中间文本 | 视流程而定 |
| `reasoning` 项 | 推理模型的中间推理上下文 | 推理模型场景下要保留 |

这也是为什么我更建议把 tool loop 看成“响应对象的继续执行”，而不是“发起一个全新的问答请求”。

## 四、多个工具并行返回时，循环重点是归并，而不是顺序

官方文档给出的样例里，一个 `response.output` 里可以同时出现多个 `function_call`。这在真实业务里非常常见，例如先查天气、再查 CRM、最后决定是否发邮件。

这时服务端更重要的不是“按固定顺序执行”，而是做好归并：

1. 遍历本轮所有 `function_call`
2. 按 `name + call_id` 路由到对应实现
3. 收集所有工具结果
4. 一次性把多条 `function_call_output` 发回模型

这样的好处有两个：

- 模型能在同一轮里同时消费多个外部结果，减少往返次数
- 你的服务端更容易做批量日志、超时控制和幂等保护

一个工程上够用的队列结构大致像这样：

```json
{
  "response_id": "resp_123",
  "tool_calls": [
    {"call_id": "call_weather", "name": "get_weather", "status": "done"},
    {"call_id": "call_mail", "name": "send_email", "status": "waiting"}
  ]
}
```

注意这里追踪的是每个 `call_id` 的状态，而不是只追踪整轮“是否完成”。如果某一个工具超时，整轮策略才有机会做局部重试，而不是整轮重来。

## 五、推理模型有一个额外规则：reasoning 项也要带回去

这是 `Responses API` tool loop 里最容易被忽略、也最容易导致“为什么第二轮突然变笨了”的点。

OpenAI 官方文档明确写到：对于 GPT-5、o4-mini 这类 reasoning models，如果模型在带工具调用的响应里返回了 `reasoning` 项，那么在把工具结果发回去时，这些 reasoning items 也必须一并带回。

这条规则的工程含义非常直接：

- 非推理模型场景，很多时候只处理 `function_call` / `function_call_output` 就够了
- 推理模型场景，不能只把工具结果回传，否则你会丢失模型刚才已经展开的推理上下文

因此，一个更稳妥的 follow-up 组装逻辑应该是：

```python
next_input = []

for item in response.output:
    if item.type in ("function_call", "reasoning"):
        next_input.append(item)

for call in function_calls:
    next_input.append({
        "type": "function_call_output",
        "call_id": call.call_id,
        "output": call.result_json,
    })
```

这也是为什么推理模型的 tool loop 更适合先设计成明确状态流，再去追求极限延迟。否则丢一段 reasoning，就可能让下一轮决策完全变样。

## 六、工具 schema 设计越严格，循环越短

很多 tool loop 之所以拖成 3 轮、4 轮，并不是模型不聪明，而是函数 schema 太松。官方文档在函数定义部分推荐使用 JSON Schema，并允许为函数设置 `strict: true`。

这会直接影响循环效率。原因很简单：

- schema 模糊时，模型容易先试探性调用，再根据报错修正参数
- schema 清晰时，模型第一次生成参数就更接近可执行结果

一个实用判断标准是：如果你发现模型经常因为字段缺失、枚举不对、嵌套结构不完整而重复调用工具，先别急着调 prompt，优先收紧 schema 和字段描述。相关校验思路可以和[LLM 输出验证：schema + 业务规则双层防护](/blog/llm-output-validation/)结合起来看。

## 七、把 tool loop 设计成状态机，排障成本会低很多

多轮工具循环一旦进入生产，常见故障几乎都和状态不透明有关：

- 模型重复调用同一个工具，到底是幂等没做好，还是上下文丢了？
- 第二轮没产出文本，是因为工具失败，还是因为回传格式不对？
- 任务卡住时，当前是在等工具、等模型，还是等人工确认？

所以我更推荐为 tool loop 单独建一个小状态机：

| 状态 | 含义 |
| --- | --- |
| `awaiting_model` | 等待本轮 Responses 输出 |
| `awaiting_tools` | 已收到 function_call，等待工具执行 |
| `assembling_followup` | 正在组装 `function_call_output` 与保留项 |
| `awaiting_final_answer` | 已把工具结果发回，等待模型收尾 |
| `failed` / `completed` | 终态 |

这种设计和[AI Agent 状态机设计与落地](/blog/agent-state-machine-design/)是同一类思路：你不一定需要大而全的编排系统，但至少要让每一轮调用知道自己处在哪个阶段。

## 八、一个够用的实战模板：先保守正确，再优化轮次

如果你准备第一次把 `Responses API` 工具调用接进生产，我建议先采用偏保守的模板：

1. 每轮完整遍历 `response.output`
2. 显式筛出 `function_call`、`reasoning` 等需要保留的项
3. 对每个 `call_id` 记录执行状态和结果
4. 用 `previous_response_id` 发起下一轮
5. 直到出现最终文本输出或明确终态

等这条链稳定以后，再去做并行、流式工具参数处理、部分结果预渲染之类的优化。因为在 tool loop 里，错一次上下文拼接，往往比多一次请求更贵。

## 九、相关阅读

- [OpenAI Responses API 流式事件处理指南](/blog/openai-responses-api-streaming-guide/)
- [OpenAI Assistants API 与 Responses API 迁移指南](/blog/openai-assistants-vs-responses/)
- [LLM 输出验证：schema + 业务规则双层防护](/blog/llm-output-validation/)
- [AI Agent 状态机设计与落地](/blog/agent-state-machine-design/)

如果你要把多轮 tool loop 接进统一的模型服务层，[YoTradeApi](https://yotradeapi.com) 提供兼容式 API 接入方式，便于把 OpenAI、Claude、DeepSeek 等模型的工具调用工作流放进同一套工程管线里。
