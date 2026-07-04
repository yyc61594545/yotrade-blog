---
title: Anthropic cache_control 五分钟入门到精通
description: 手把手讲解 Anthropic API 里 cache_control 参数的用法：断点位置、TTL 选择、多段缓存嵌套，附完整可运行代码示例。
keywords:
  - cache_control 用法
  - Anthropic prompt caching 教程
  - Claude API 缓存断点
  - cache_control ephemeral
  - Claude 缓存 TTL
pubDate: '2026-07-04'
updatedDate: '2026-07-04'
canonical: https://blog.yotradeapi.com/blog/anthropic-cache-control-tutorial/
tags:
  - Anthropic
  - Claude API
  - cache_control
  - 技术深度
category: 技术深度
heroImage: ../../assets/blog-placeholder-1.jpg
---

Anthropic 的 prompt caching 省钱效果之前已经讲过（见[prompt caching 在国内中转下省成本指南](/blog/prompt-caching-cost-optimization/)），这篇不谈"值不值"，只讲**怎么写代码**——`cache_control` 参数的具体用法、常见踩坑点，让你五分钟内能跑通第一个缓存请求。

## 一、最小可运行示例

`cache_control` 是加在消息内容块（content block）上的一个字段，标记"这一段之后要被缓存"：

```python
from anthropic import Anthropic

client = Anthropic(api_key="your-api-key")

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    system=[
        {
            "type": "text",
            "text": "你是一个资深代码审查助手。" + "（这里是很长的系统指令，比如几千字的代码规范）" * 50,
            "cache_control": {"type": "ephemeral"}
        }
    ],
    messages=[
        {"role": "user", "content": "帮我审查这段代码：def foo(): pass"}
    ]
)

print(response.content[0].text)
print(response.usage)  # 关注 cache_creation_input_tokens / cache_read_input_tokens
```

关键在 `response.usage` 里的两个字段：

- `cache_creation_input_tokens`：本次请求**新写入缓存**的 token 数（第一次调用会有值）
- `cache_read_input_tokens`：本次请求**命中缓存**的 token 数（第二次及之后调用才会有值）

第一次调用没有缓存可读，反而会比不开缓存略贵（写入缓存有小额溢价）；从第二次调用开始，命中部分只收约 1/10 的费用。

## 二、断点（breakpoint）放在哪里

`cache_control` 标记的是"**从内容开头到这个块为止**"整体作为一个缓存单元，不是只缓存这一个块。这意味着断点的位置直接决定缓存粒度：

```python
messages = [
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "这是项目的完整代码库上下文（很长，10k+ tokens）...",
                "cache_control": {"type": "ephemeral"}  # 断点 1：缓存到这里为止
            },
            {
                "type": "text",
                "text": "这是本次用户的具体问题：如何优化这个函数？"
                # 不加 cache_control：这部分每次都变，不需要缓存
            }
        ]
    }
]
```

**放置原则**：把"几乎不变的内容"放在前面并标记断点，把"每次都变的内容"放在后面不标记。常见的四层结构：

```
[静态 system prompt] → 断点1
[项目文件/长文档上下文] → 断点2
[历史对话（增量累加）] → 断点3（可选）
[本次用户输入] → 不标记
```

一次请求最多可以设置 **4 个缓存断点**，超过会报错，多段场景要合理取舍，优先缓存体积最大、最不常变的部分。

## 三、TTL 怎么选：ephemeral 5 分钟 vs 1 小时

`cache_control` 目前支持两种生存时间：

```python
# 默认：5 分钟 TTL，命中价格约为原价的 1/10
{"type": "ephemeral"}

# 显式指定 1 小时 TTL，命中价格约为原价的 1/5（写入成本也更高）
{"type": "ephemeral", "ttl": "1h"}
```

| 场景 | 建议 TTL | 原因 |
|---|---|---|
| Cursor/Claude Code 等交互式编码，用户操作间隔短 | 5 分钟（默认） | 请求密集，5 分钟足够命中，成本最低 |
| 客服机器人，用户回复间隔可能超过 5 分钟 | 1 小时 | 避免缓存过期后又按全价重新写入 |
| 批量任务，同一 system prompt 跑上百次请求 | 5 分钟，但控制并发让请求连续发出 | 只要请求间隔小于 5 分钟，默认 TTL 更省钱 |

判断标准很简单：**估算两次请求之间的典型间隔**，如果经常超过 5 分钟，上 1 小时 TTL；如果请求密集（几秒到几十秒一次），默认 5 分钟性价比最高。

## 四、常见踩坑

### 踩坑 1：内容块太小，缓存不生效

Anthropic 对可缓存内容有最小 token 数要求（不同模型略有差异，通常是 1024 或 2048 tokens 起）。如果你标记 `cache_control` 的内容块本身很短（比如只有几十个 token 的系统提示），缓存不会生效，`cache_creation_input_tokens` 会一直是 0。

**排查方法**：检查 `usage` 里 `cache_creation_input_tokens` 和 `cache_read_input_tokens` 是否都是 0——如果是，说明内容块没达到最小缓存阈值。

### 踩坑 2：每次请求内容"看似相同"但实际有细微差异

缓存命中要求前缀**逐字节完全一致**。常见的隐藏差异：

- 时间戳、请求 ID 混入了 system prompt
- 文件内容读取顺序不稳定（比如用 `os.listdir` 遍历文件，顺序在不同系统上可能不同）
- JSON 序列化时字段顺序不固定

```python
# 错误示范：每次请求 system prompt 都不同，永远无法命中缓存
system_prompt = f"当前时间：{datetime.now()}\n你是代码审查助手..."

# 正确做法：把易变内容放到不参与缓存的部分
system_prompt = "你是代码审查助手..."  # 固定不变，可缓存
user_message = f"当前时间：{datetime.now()}\n{user_question}"  # 易变，不缓存
```

### 踩坑 3：多轮对话里忘记对历史消息也加断点

多轮对话场景中，如果只缓存了 system prompt，而不断增长的历史消息没有断点，随着对话轮次增加，未缓存部分会越来越大，缓存带来的省钱效果逐渐被摊薄。做法是每隔几轮对话，在最新一条历史消息上重新打一个断点：

```python
def build_messages_with_cache(history, latest_user_input):
    msgs = history.copy()
    if msgs:
        # 在历史消息的最后一条上打断点，缓存到目前为止的全部历史
        msgs[-1] = {**msgs[-1], "cache_control": {"type": "ephemeral"}}
    msgs.append({"role": "user", "content": latest_user_input})
    return msgs
```

## 五、通过中转使用时的注意事项

通过 API 中转调用时，`cache_control` 参数本身完全透传，用法和直连 Anthropic API 一致：

```python
client = Anthropic(
    api_key="your-relay-api-key",
    base_url="https://api.yotradeapi.com"
)
# messages.create 的调用方式和上面完全相同
```

需要确认的是中转商是否**按 Anthropic 官方的缓存计费规则结算**——即命中缓存部分是否也按折扣价计费，还是按全价计费后中转自己吃掉差价（不同中转商的计费口径可能不同，建议先用小额测试请求核对账单）。

## 六、常见问题

**Q：缓存是跨账号共享的吗？**
不是，缓存是隔离在单个 API Key（或组织）范围内的，不同用户/账号之间的相同内容不会互相命中。

**Q：可以缓存 tool 定义（tools 参数）吗？**
可以，`tools` 数组里的定义同样可以通过在最后一个 tool 上加 `cache_control` 来缓存，用法和 system/messages 一致。

**Q：为什么第一次调用比不用缓存还贵一点？**
因为写入缓存本身有约 25% 的溢价（相对该内容的原价）。这个成本会在后续命中时被摊销，只要同一内容会被复用 2 次以上，总体就是省钱的。

## 七、相关阅读

- [prompt caching 在国内中转下省成本指南](/blog/prompt-caching-cost-optimization/)
- [Claude Prompt Caching ROI 分析：什么场景值得开启缓存](/blog/claude-prompt-caching-roi-analysis/)
- [LLM 应用缓存层设计：从语义缓存到 Prompt 缓存的完整方案](/blog/llm-cache-layer-design/)
- [OpenAI Batch API 节省 50% 成本实战](/blog/openai-batch-api-cn-guide/)

想用 Claude API 但担心国内网络不稳定影响缓存命中率？[YoTradeApi](https://yotradeapi.com) 提供低延迟中转线路，按官方计费规则结算缓存折扣，支付宝充值即可接入。
