---
title: prompt caching 在国内中转下省成本指南
description: Anthropic 与 OpenAI prompt caching 机制对比，在 Cursor、Claude Code、Cline、Aider 真实工作流下的省成本实战。
keywords:
- prompt caching
- anthropic prompt caching
- openai cache
- claude 缓存 省钱
- ai api 成本优化
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/prompt-caching-cost-optimization/
tags:
- prompt caching
- 成本优化
- Anthropic
- OpenAI
- 缓存
category: 成本优化
featured: true
heroImage: ../../assets/blog-placeholder-2.jpg
---

# prompt caching 在国内中转下省成本指南

prompt caching 是过去一年最被低估的省钱技术。Anthropic 把它推到了一个量级——长 system prompt 二次命中只收 1/10 的钱。本文讲清楚原理、Cursor / Claude Code / Cline / Aider 各自的开启方法、以及中转下需要注意的事。

## 一、为什么 prompt caching 这么重要

一个典型 Cursor 任务的输入构成：

| 部分 | 大小 | 是否会变 |
| --- | --- | --- |
| system prompt | 4–8k tokens | 几乎不变 |
| 项目上下文（文件） | 10–50k tokens | 偶尔变 |
| 历史对话 | 5–30k tokens | 累加 |
| 本次用户提问 | 100–500 tokens | 每次都变 |

每次发请求，**前三部分都重复**。没有 caching 之前，每次都按完整 token 计费。开启 caching 之后，命中部分按 1/10 计价。一个跑 30 轮的 Cursor 长任务，总成本能下降 70–85%。

## 二、Anthropic prompt caching 机制

Anthropic 用 `cache_control` 标记缓存边界：

```json
{
  "model": "claude-sonnet-4-6",
  "system": [
    {
      "type": "text",
      "text": "你是一个严谨的代码助手...（长 system prompt）",
      "cache_control": {"type": "ephemeral"}
    }
  ],
  "messages": [...]
}
```

关键规则：

- **缓存 TTL**：5 分钟（标准）或 1 小时（extended，按倍率计费）
- **缓存命中价**：约 1/10 普通输入价
- **缓存写入价**：约 1.25 倍普通输入价（首次写入）
- **粒度**：从 prompt 起始到最后一个 `cache_control` 标记的位置
- **最小长度**：1024 tokens（Sonnet/Opus）或 2048 tokens（Haiku）

只要二次命中的概率 > 1/8，缓存就赚。所以**只要你长 prompt 复用 ≥ 2 次，就该开**。

## 三、OpenAI 的 automatic prompt caching

OpenAI 在 GPT-5 上默认开自动缓存，**不需要显式标记**：

- 超过 1024 tokens 的 prefix 自动尝试缓存
- 命中价格约 50% 普通价（比 Anthropic 折扣小）
- TTL 几分钟（具体未公开）

不需要改代码，OpenAI SDK 调用自动受益。响应里会带 `cached_tokens` 字段，能看命中情况：

```python
resp = client.chat.completions.create(...)
print(resp.usage.prompt_tokens_details.cached_tokens)
```

## 四、Cursor 中怎么用上 prompt caching

Cursor 本身已经在调 API 时带 `cache_control`。**关键是中转必须透传**这个字段。可以这样验证：

1. 在 Cursor 跑两次同样的对话（不要清上下文）
2. 在中转后台看第二次的 `cached_input_tokens` 是否非零
3. 看账单：第二次的输入费用应该明显低于第一次

如果中转后台没"cached tokens"字段，**这个中转大概率不支持 caching 透传**，直接换掉。

## 五、Claude Code 中的 caching

Claude Code 默认会在 system prompt 末尾加 `cache_control`。但需要注意：

- **PreCompact hook 会改 prompt**：每次 compact 之后缓存会失效
- **每次 `/clear` 也会重置**
- **MCP 工具 schema 占位**：长 MCP schema 算进 system prompt 一部分，但只在它前面打缓存点才有效

实战建议：

```bash
# 长会话尽量不要 /clear，让自动 compact 处理
# 把 MCP 限制到当前任务需要的几个，减小变动
```

## 六、Cline 中怎么开

Cline 在最近版本默认开 Anthropic caching。检查方法：设置 → Advanced → "Enable Prompt Caching" 应该是开的。

Cline 的 Plan/Act 双模式有个小陷阱：**模式切换时上下文会被重新组织**，可能导致缓存失效。如果你想最大化命中率：

- 整个任务用同一种模式
- 避免频繁来回切

## 七、Aider 中怎么开

Aider 通过 LiteLLM 调用模型，需要显式开 cache：

```yaml
# .aider.conf.yml
cache-prompts: true
cache-keepalive-pings: 0
```

或命令行：

```bash
aider --cache-prompts
```

注意 `cache-keepalive-pings`：Aider 会定期发心跳保活 5 分钟缓存。但每次心跳 = 1 次请求，按计费算并不划算，建议设 0 关闭。

## 八、中转侧的关键检查

不是所有中转都正确实现 caching 透传。最小验证：

```bash
# 同一个 prompt 发两次
for i in 1 2; do
  curl -s https://yotradeapi.com/v1/messages \
    -H "x-api-key: $KEY" -H "anthropic-version: 2023-06-01" \
    -H "content-type: application/json" \
    -d "$(cat payload.json)" \
    | jq '.usage'
done
```

第二次的输出应该有：

```json
{
  "input_tokens": 50,
  "cache_creation_input_tokens": 0,
  "cache_read_input_tokens": 5000,
  "output_tokens": 100
}
```

`cache_read_input_tokens` 非零才代表缓存命中。如果一直是 0，中转没接 caching。

## 九、长 prompt 缓存的边界

不是"什么都缓存"就最优：

- **变化频繁的内容不要放在缓存边界前**。比如 user message 永远在最后，不应该出现在 cache_control 之前。
- **多个缓存断点要规划好**：Anthropic 允许最多 4 个 cache_control。可以分别缓存 system prompt、工具 schema、历史对话三段，命中粒度更细。
- **超过 1 小时不用就失效**：长间隔后第一次请求会重新写入，付一次更贵的写入费。

## 十、成本测算示例

假设你的 Cursor 工作流：

- system prompt: 6k tokens
- 上下文: 20k tokens
- 历史: 平均 10k tokens
- 单轮提问: 200 tokens
- 单轮回复: 500 tokens
- 一天 50 轮

按 Sonnet 4.6 估算（数字仅作相对比较）：

**没有 caching**：
- 输入: (6+20+10+0.2) × 50 = 1810k tokens
- 输出: 0.5 × 50 = 25k tokens

**有 caching（90% 命中率）**：
- 缓存读: 36 × 50 × 0.9 = 1620k tokens（1/10 价）
- 普通输入: 36 × 50 × 0.1 + 0.2 × 50 = 190k tokens
- 缓存写: 36 × 5 = 180k tokens（1.25 倍价，假设一天写入 5 次新缓存）
- 输出: 25k tokens

相对成本下降约 **65–80%**。

## 十一、相关阅读

- [Cursor API 中转怎么选](/blog/2026-05-15-cursor-api-relay-recommendation-2026/)
- [Claude Code 镜像国内配置完整指南](/blog/claude-code-mirror-cn-setup/)
- [Cline 国内 API 配置详解](/blog/cline-cn-api-setup/)
- [Aider 中文配置与最佳实践](/blog/aider-cn-config-guide/)
- [Claude Sonnet 4.6 与 Opus 4.7 怎么选](/blog/claude-sonnet-4-6-vs-opus-4-7/)

[YoTradeApi](https://yotradeapi.com) 后台展示每条请求的 `cache_read_input_tokens` 与 `cache_creation_input_tokens`，方便量化缓存命中率与节省额。
