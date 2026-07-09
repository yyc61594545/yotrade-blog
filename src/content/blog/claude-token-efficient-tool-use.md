---
title: Claude token-efficient tool use 实战：压缩工具调用的输出 token
description: 讲解 Claude token-efficient tool use beta 特性的原理、开启方式、实测收益与适用场景，帮助高频工具调用的 Agent 应用降低输出 token 成本。
keywords:
  - claude token-efficient tool use
  - claude tool use 优化
  - anthropic beta header
  - claude 工具调用成本
  - agent token 优化
pubDate: '2026-07-09'
updatedDate: '2026-07-09'
canonical: https://blog.yotradeapi.com/blog/claude-token-efficient-tool-use/
tags:
  - Claude
  - Tool Use
  - token 优化
  - 技术深度
category: 技术深度
heroImage: ../../assets/blog-placeholder-2.jpg
---

Claude 在处理 Tool Use 时，除了实际的工具调用参数，还会输出一部分格式化开销（工具调用块的结构性 token）。对于高频调用工具的 Agent 应用——比如一次任务里要连续调用十几次搜索、读文件、写代码的场景——这部分开销累积起来相当可观。`token-efficient tool use` 是 Anthropic 提供的一个 beta 特性，专门用来压缩这部分输出。本文讲清楚它是什么、怎么开、什么场景值得开。工具调用本身的设计规范可以参考[《Claude Tool Use 最佳实践与陷阱》](/blog/claude-tool-use-best-practices/)，本文只聚焦 token 优化这一个点。

## 一、它解决的是哪部分 token 开销

Claude 调用工具时，一次完整的交互链路大致是这样的 token 消耗结构：

| 阶段 | Token 类型 | 是否可被 token-efficient 优化 |
| --- | --- | --- |
| 输入：system prompt + 工具定义 | 输入 token | 否（这部分靠 prompt caching 优化） |
| 输出：模型决定调用哪个工具 | 输出 token | 是——减少推理与格式化冗余 |
| 输出：工具调用参数（JSON） | 输出 token | 部分——参数值本身不能压缩，但结构开销可以 |
| 下一轮输入：工具执行结果回填 | 输入 token | 否 |

容易混淆的一点：**token-efficient tool use 优化的是输出 token，prompt caching 优化的是输入 token**，两者是互补关系而不是二选一。如果你的应用同时有"工具定义很长"（输入侧问题）和"频繁多轮工具调用"（输出侧问题），两个特性应该一起开启。Prompt caching 的成本模型详见[《Prompt Caching 成本优化实战》](/blog/prompt-caching-cost-optimization/)。

## 二、开启方式

通过在请求中加入对应的 beta header 启用：

```python
import anthropic

client = anthropic.Anthropic(
    api_key="YOUR_YOTRADE_KEY",
    base_url="https://yotradeapi.com",
)

response = client.beta.messages.create(
    model="claude-opus-4-8",
    max_tokens=1024,
    tools=[
        {
            "name": "search_docs",
            "description": "搜索内部文档库",
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        }
    ],
    messages=[{"role": "user", "content": "帮我查一下退款政策"}],
    extra_headers={"anthropic-beta": "token-efficient-tools-2025-02-19"},
)
```

Node.js 等价写法：

```javascript
const response = await client.beta.messages.create({
  model: "claude-opus-4-8",
  max_tokens: 1024,
  tools: [/* ... */],
  messages: [{ role: "user", content: "帮我查一下退款政策" }],
}, {
  headers: { "anthropic-beta": "token-efficient-tools-2025-02-19" },
});
```

不需要改工具定义本身，只需要在请求头里加这一行——这是它比"重写 prompt 精简工具描述"更省事的地方：改动是请求层面的开关，不涉及业务逻辑。

## 三、走中转时的注意事项

Beta header 属于容易被中转"吃掉"的一类参数——部分中转只透传标准请求体字段，对 `anthropic-beta` 这类 header 处理不一致。接入前建议用最小请求验证：

```bash
curl -i https://yotradeapi.com/v1/messages \
  -H "x-api-key: $KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "anthropic-beta: token-efficient-tools-2025-02-19" \
  -H "content-type: application/json" \
  -d '{
    "model": "claude-opus-4-8",
    "max_tokens": 100,
    "tools": [{"name":"ping","description":"测试","input_schema":{"type":"object","properties":{}}}],
    "messages": [{"role":"user","content":"ping一下"}]
  }'
```

观察返回的 `usage` 字段里输出 token 数是否有明显下降（同样的工具调用场景，对比开关 header 前后的差异）。如果数值几乎没变化，说明中转没有正确透传这个 beta header，需要联系中转方确认支持情况，或者换一个完整透传 beta 特性的中转。

## 四、实测收益的量级

收益大小取决于工具调用的密度和参数复杂度，几个典型场景的粗略估算（**以下数字为实测参考量级，具体收益因工具设计和调用模式而异，建议在自己的场景里实测**）：

| 场景 | 每次任务工具调用次数 | 输出 token 节省估算 |
| --- | --- | --- |
| 单次简单查询（1 次工具调用） | 1 | 个位数百分比，不明显 |
| 多步骤 Agent 任务（5-10 次调用） | 5-10 | 中等幅度，累积效果明显 |
| 长链路自动化任务（20+ 次调用） | 20+ | 效果最明显，因为格式开销随调用次数线性累积 |

结论很直接：**调用次数越多，这个特性的边际收益越大**。如果你的应用是"用户问一句、Claude 答一句、偶尔查个数据库"这种低频工具调用模式，开不开差别不大；如果是"Claude 自主规划多步任务、连续调用十几个工具才给出最终答案"的 Agent 场景，值得认真评估。

## 五、和并行工具调用一起用

`token-efficient tool use` 和并行工具调用（parallel tool use）可以叠加使用——并行调用减少的是"轮次数量"（多个工具一次性发起而不是排队），token-efficient 减少的是"单次调用的格式开销"，两者作用维度不同，同时开启效果可以叠加：

```python
response = client.beta.messages.create(
    model="claude-opus-4-8",
    max_tokens=2048,
    tools=[search_tool, calculator_tool, weather_tool],
    messages=[{"role": "user", "content": "帮我查下上海天气，再算一下人均消费"}],
    extra_headers={"anthropic-beta": "token-efficient-tools-2025-02-19"},
)

# 一次响应里可能包含多个 tool_use 块
for block in response.content:
    if block.type == "tool_use":
        print(block.name, block.input)
```

并行工具调用的设计模式和触发条件，详见[《Claude 并行工具调用实践》](/blog/parallel-tool-use-claude/)。

## 六、什么情况下不需要开

不是所有场景都值得引入这个 beta 特性，几种可以跳过的情况：

- **工具调用频率很低**（平均每次对话不到 2 次工具调用）：节省的绝对 token 数量太小，不值得额外维护一个 beta header
- **对输出确定性要求极高的场景**：beta 特性偶尔会有输出格式的细微差异，如果你的下游解析逻辑对格式极度敏感，先在测试环境充分验证再上生产
- **中转不支持 beta header 透传**：与其排查中转兼容性问题，不如先确认收益是否值得投入这个排查成本

## 七、成本对比的简单心算模型

假设一次 Agent 任务平均调用工具 10 次，每次工具调用块的格式开销大约几十到上百 token（具体因工具复杂度而异）。按 Claude Opus 的输出定价估算，单次任务节省的输出 token 换算成成本可能只是几厘钱级别，但乘以你的日调用量（比如日均 10 万次 Agent 任务）后，月度差异可能达到有意义的规模。建议接入后先跑一周 A/B 对比，用实际账单数据决定是否全量开启，而不是单纯凭理论估算下结论。

## 八、相关阅读

- [Claude Tool Use 最佳实践与陷阱](/blog/claude-tool-use-best-practices/)
- [Claude 并行工具调用实践](/blog/parallel-tool-use-claude/)
- [Prompt Caching 成本优化实战](/blog/prompt-caching-cost-optimization/)
- [Function Calling vs Tool Use：概念辨析](/blog/function-calling-vs-tool-use/)

高频工具调用的 Agent 应用对 API 稳定性和 beta 特性透传要求更高，[YoTradeApi](https://yotradeapi.com) 完整支持 Claude 的 beta header 透传，方便你直接验证这类优化特性的实际收益。
