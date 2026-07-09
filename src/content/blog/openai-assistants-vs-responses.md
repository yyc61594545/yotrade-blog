---
title: OpenAI Assistants API 与 Responses API 迁移指南
description: OpenAI 宣布 Assistants API 进入弃用倒计时，本文讲清楚它和 Responses API 的架构差异、迁移步骤、常见坑与中转兼容性排查方法。
keywords:
  - openai assistants api
  - assistants api 迁移
  - responses api 迁移
  - threads runs 替代方案
  - openai api 弃用
pubDate: '2026-07-09'
updatedDate: '2026-07-09'
canonical: https://blog.yotradeapi.com/blog/openai-assistants-vs-responses/
tags:
  - OpenAI
  - Assistants API
  - Responses API
  - 迁移
category: 技术深度
heroImage: ../../assets/blog-placeholder-3.jpg
---

OpenAI 已经明确 Assistants API 会在未来版本中退役，官方推荐的替代方案是 Responses API。如果你的项目还在用 `threads` / `runs` / `messages` 这一套对象模型，现在是评估迁移成本的时候了。本文不重复讲 Responses API 的基础用法（那部分见[《OpenAI Responses API 完整使用指南》](/blog/openai-responses-api-guide/)），而是聚焦"从 Assistants 迁过去要做什么"。

## 一、为什么 Assistants API 要被替代

Assistants API 在 2023 年底发布时解决了一个真实痛点：把"对话状态管理 + 工具调用 + 文件检索"打包成一套托管对象（Assistant、Thread、Run、Message）。但两年多下来暴露的问题也很明显：

- **对象层级太深**：创建 assistant → 创建 thread → 加 message → 创建 run → 轮询 run 状态 → 取 message，一次简单问答要 5 次以上 API 调用
- **轮询式设计过时**：`run.status` 需要客户端不断 poll，Responses API 原生支持 `background=True` + 事件流
- **和 Chat Completions/Responses 生态割裂**：模型新特性（reasoning、structured outputs 新语法）经常先上 Responses API，Assistants API 落后一到两个版本
- **计费与并发模型不同**：Assistants 的 Threads 长期占用存储配额，Responses 的 `store` 机制更轻量可控

OpenAI 官方迁移文档把 Responses API 定位为"Assistants 的下一代"，新项目已经不建议再起 Assistants。

## 二、对象模型对照表

| Assistants API 概念 | Responses API 对应方案 | 说明 |
| --- | --- | --- |
| `Assistant`（预设 system prompt + 工具） | 每次请求传 `instructions` 参数 | 无持久化对象，靠客户端或自建配置层管理 |
| `Thread`（会话容器） | `previous_response_id` 链式引用 | 不再有独立的 thread 对象 ID |
| `Message`（用户/助手消息） | `input` 参数 + `output` 返回 | 结构更接近 Chat Completions |
| `Run`（一次执行 + 轮询状态） | 同步返回 或 `background=True` | 大多数场景不再需要轮询 |
| `Run Steps`（工具调用中间步骤） | `output` 数组里的 `function_call` 项 | 展开在同一次响应里 |
| File Search（内置检索） | `tools=[{"type": "file_search"}]` | 概念保留，调用方式变了 |
| Code Interpreter | `tools=[{"type": "code_interpreter"}]` | 概念保留 |

核心变化一句话总结：**Assistants API 是"服务端托管的有状态对象图"，Responses API 是"客户端驱动、服务端可选保存的链式调用"**。前者更像传统 Web 框架里的 Session，后者更接近事件溯源（event sourcing）思路——每次响应都有 ID，下一轮拿这个 ID 接着聊。

## 三、迁移前的存量盘点

动手迁移前，先审计现有代码里对 Assistants API 的依赖面：

```bash
# 快速找出项目里所有 Assistants API 调用点
grep -rn "beta.threads\|beta.assistants\|client.beta" --include="*.py" .
grep -rn "beta.threads\|beta.assistants" --include="*.ts" --include="*.js" .
```

重点关注三类调用：

1. **纯对话场景**（无工具、无文件）——迁移成本最低，直接改用 `responses.create`
2. **带 File Search 的知识库问答**——需要把 Assistants 的 vector store 关联迁移到 Responses 的 `file_search` 工具配置，具体检索机制的取舍可以参考[《OpenAI File Search 与自建 RAG 该怎么选》](/blog/openai-file-search-vs-rag/)
3. **带自定义 function call 的 Agent 场景**——工具定义格式改动最大，见下一节

## 四、核心代码迁移示例

### 4.1 简单对话：从轮询变同步

**迁移前（Assistants API）：**

```python
from openai import OpenAI
import time

client = OpenAI(api_key="YOUR_KEY")

assistant = client.beta.assistants.create(
    name="客服助手",
    instructions="你是一个电商客服，回答要简洁友好。",
    model="gpt-5",
)

thread = client.beta.threads.create()
client.beta.threads.messages.create(
    thread_id=thread.id,
    role="user",
    content="订单发货了吗？",
)

run = client.beta.threads.runs.create(
    thread_id=thread.id,
    assistant_id=assistant.id,
)

# 轮询等待完成
while run.status not in ("completed", "failed"):
    time.sleep(1)
    run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

messages = client.beta.threads.messages.list(thread_id=thread.id)
print(messages.data[0].content[0].text.value)
```

**迁移后（Responses API）：**

```python
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_YOTRADE_KEY",
    base_url="https://yotradeapi.com/v1",
)

resp = client.responses.create(
    model="gpt-5",
    instructions="你是一个电商客服，回答要简洁友好。",
    input="订单发货了吗？",
)
print(resp.output_text)
```

一次调用替代了原来的 5 次调用，也不再需要客户端轮询循环。

### 4.2 多轮对话：thread_id 变 previous_response_id

```python
# 第一轮
r1 = client.responses.create(
    model="gpt-5",
    instructions="你是一个电商客服，回答要简洁友好。",
    input="订单发货了吗？",
    store=True,
)

# 第二轮：不需要重新传 instructions，也不需要 thread 对象
r2 = client.responses.create(
    model="gpt-5",
    input="大概什么时候到？",
    previous_response_id=r1.id,
)
```

注意：`previous_response_id` 是"链式引用"而不是"容器引用"——它只保留到上一轮为止的上下文，不像 Thread 那样是一个可以随时追加消息、多方读写的持久化对象。如果你的业务需要多个客户端同时往一个会话里写消息（比如客服转人工场景），迁移后要自己在业务层维护一个"当前 response_id"指针。

### 4.3 Function Call：工具结构去掉一层包装

**Assistants API 的工具定义：**

```python
tools = [{
    "type": "function",
    "function": {
        "name": "check_order_status",
        "description": "查询订单状态",
        "parameters": {
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"],
        },
    },
}]
```

**Responses API 去掉了 `function` 这层嵌套：**

```python
tools = [{
    "type": "function",
    "name": "check_order_status",
    "description": "查询订单状态",
    "parameters": {
        "type": "object",
        "properties": {"order_id": {"type": "string"}},
        "required": ["order_id"],
    },
}]
```

处理返回结果的代码也要跟着改——Assistants API 需要在 `run.required_action.submit_tool_outputs` 里提交工具结果再触发新一轮 run，Responses API 直接在下一次 `responses.create` 里把 `function_call_output` 作为 input 的一部分传回去：

```python
resp = client.responses.create(
    model="gpt-5",
    input=[
        {"type": "function_call_output",
         "call_id": call_id,
         "output": '{"status": "shipped", "eta": "2 天"}'},
    ],
    previous_response_id=r1.id,
)
```

## 五、File Search / 知识库迁移

Assistants API 里，文件上传到 `vector_store`，再关联到 assistant：

```python
vector_store = client.beta.vector_stores.create(name="产品文档")
client.beta.vector_stores.files.upload_and_poll(
    vector_store_id=vector_store.id, file=open("faq.pdf", "rb")
)
assistant = client.beta.assistants.create(
    tools=[{"type": "file_search"}],
    tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
)
```

Responses API 里 vector store 仍然存在（不属于 Assistants 独有），迁移只是把关联方式改成按次传参：

```python
resp = client.responses.create(
    model="gpt-5",
    input="退货政策是什么？",
    tools=[{"type": "file_search", "vector_store_ids": [vector_store.id]}],
)
```

vector store 本身的创建、上传 API 基本不变，改动集中在"怎么把它挂到一次调用上"。

## 六、中转场景下的迁移注意事项

走 API 中转时，Assistants API 迁移会多踩几个坑：

| 问题 | 现象 | 建议 |
| --- | --- | --- |
| 中转不支持 `/v1/responses` | 请求直接 404 | 迁移前先 curl 测试端点可用性 |
| `store=True` 但中转不落库 | `previous_response_id` 下一轮找不到 | 改自己在业务层拼接完整历史当 `input` |
| vector store 创建接口未透传 | file_search 报错 | 确认中转是否代理 `/v1/vector_stores/*` |
| 计费口径变化 | Responses API 的 `reasoning` token 单独计费 | 迁移后重新核对账单，不能直接套用旧的 Assistants 用量估算 |

用这条命令快速验证中转是否支持 Responses API：

```bash
curl -i https://yotradeapi.com/v1/responses \
  -H "Authorization: Bearer $KEY" \
  -d '{"model":"gpt-5","input":"hi"}'
```

返回 200 且带 `output_text` 字段说明可以放心迁移。如果中转只支持 Chat Completions 协议而不支持 Responses API，可以参考[《OpenAI 兼容协议 vs Anthropic 原生协议》](/blog/openai-compatible-vs-anthropic-protocol/)理解两种协议透传的差异，再决定是升级中转还是过渡期继续用 Chat Completions 顶一段时间。

## 七、迁移节奏建议

不建议一次性重写整个项目，按下面顺序分批迁移风险更低：

1. **先迁无状态场景**：客服首轮问答、单次摘要、单次分类——这类调用改动最小，先上线验证没有隐藏行为差异
2. **再迁多轮对话**：把 thread 管理逻辑换成 `previous_response_id` 链，注意做好会话过期兜底（业务层自己存最近几轮 input/output 作为降级方案）
3. **最后迁工具调用和文件检索**：改动最大，建议灰度发布，观察 function call 的成功率和延迟
4. **全程保留双跑对比一到两周**：新老代码路径并行跑，比对回复质量和延迟差异，确认无回归再下线 Assistants 相关代码

Assistants API 目前还没有给出确切下线日期，但官方文档已经在多处标注"建议使用 Responses API"，早迁移早稳定，避免临近弃用日期时被迫紧急重构。

## 八、相关阅读

- [OpenAI Responses API 完整使用指南](/blog/openai-responses-api-guide/)
- [OpenAI File Search 与自建 RAG 该怎么选](/blog/openai-file-search-vs-rag/)
- [OpenAI 兼容协议 vs Anthropic 原生协议](/blog/openai-compatible-vs-anthropic-protocol/)
- [OpenAI Agents SDK 国内接入指南](/blog/openai-agents-sdk-cn/)

迁移到 Responses API 前先确认中转是否完整支持新端点，[YoTradeApi](https://yotradeapi.com) 同时支持 Chat Completions 与 Responses API，可以在过渡期让新老代码路径都正常工作。
