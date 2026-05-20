---
title: 降低 LLM 延迟的 10 种实战方法
description: AI 应用 TTFB 与总耗时优化全攻略：模型选择、prompt 精简、缓存、并行、预热、流式、就近接入、抢答策略实测。
keywords:
- llm 延迟 优化
- ttfb 优化
- ai 应用 性能
- claude 慢
- 降低 ai 延迟
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/llm-latency-optimization/
tags:
- 性能优化
- 延迟
- 工程实战
- LLM
category: 工程实战
heroImage: ../../assets/blog-placeholder-2.jpg
---

聊天界面慢 5 秒，用户就走了。本文 10 种方法按收益排序，覆盖从"换模型"到"抢答"的全链路优化。

## 一、换更快的模型（收益最大）

| 模型 | TTFB | tps |
| --- | --- | --- |
| Opus 4.7 | 5–8s | 30 |
| Sonnet 4.6 | 3–5s | 35 |
| Haiku 4.5 | 1–2s | 80 |
| Gemini Flash | 1–1.5s | 100 |
| Gemini Flash-Lite | < 1s | 120 |

简单任务换 Haiku 或 Flash，**延迟下降 4–8 倍**。这是性价比最高的优化。

## 二、Prompt 精简

输入越长，TTFB 越长（线性关系）。

| 输入 | Sonnet TTFB |
| --- | --- |
| 1k tokens | 2s |
| 10k tokens | 4s |
| 50k tokens | 10s |
| 100k tokens | 18s |

精简方向：

- 去掉无用的 system prompt 内容
- 把 "few-shot" 例子放到 cache 里
- 用 RAG 替代全文档塞
- 历史对话定期压缩

## 三、Prompt Caching

详见 [prompt caching 省成本指南](/blog/prompt-caching-cost-optimization/)。

```python
# 命中缓存 = TTFB 下降 40-60%
messages=[{
    "role": "system",
    "content": [{
        "type": "text",
        "text": LONG_SYSTEM_PROMPT,
        "cache_control": {"type": "ephemeral"},
    }],
}]
```

**长 system prompt 不开 caching 是浪费**。

## 四、流式输出

```python
stream = client.chat.completions.create(stream=True, ...)
```

用户看到第一个字的时间 = TTFB，不是总耗时。**流式让感知延迟从"总耗时"降到"TTFB"**。

详见 [LLM 流式 UI 实战模式](/blog/llm-streaming-ui-patterns/)。

## 五、并行 Tool Use

Agent 任务串行 → 并行：

```
串行：3 tools × 2s = 6s
并行：max(3 tools) = 2s
```

详见 [Claude 并行 Tool Use 实战](/blog/parallel-tool-use-claude/)。

## 六、缓存确定性请求

不是 prompt caching。是**应用层缓存**：

```python
import hashlib, json

def cache_key(model, messages, params):
    blob = json.dumps({"model": model, "messages": messages, "params": params}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()

async def call_cached(model, messages, **params):
    key = cache_key(model, messages, params)
    cached = await redis.get(key)
    if cached:
        return json.loads(cached)
    resp = await client.chat.completions.create(model=model, messages=messages, **params)
    await redis.setex(key, 3600, json.dumps(resp.dict()))
    return resp
```

适合：

- 用户问相同问题
- 同一 prompt 在不同请求里重复出现
- 内部工具函数返回固定文案

注意：**带用户身份 / 时间敏感的不能缓存**。

## 七、预热（pre-warm）

冷启动惩罚：

- 网关首次连接握手
- 模型首次响应

```python
async def prewarm():
    # 启动时发一个最小请求
    await client.chat.completions.create(
        model="claude-sonnet-4-6",
        messages=[{"role": "user", "content": "ping"}],
        max_tokens=1,
    )

# 服务启动时调
asyncio.create_task(prewarm())
```

后续真实请求 TTFB 能下降 20–40%（网关 keep-alive 还在）。

## 八、就近接入

中转节点位置影响 TTFB：

- 杭州 / 上海用户 → 走华东节点
- 北京用户 → 走华北
- 海外用户 → 直连官方

好的中转支持多地接入：

```python
# 按地区路由
client = OpenAI(base_url=region_endpoint("cn-east"), ...)
```

测试不同地区：

```bash
for region in cn-east cn-north cn-south; do
    time curl -s https://"$region".yotradeapi.com/v1/chat/completions \
      -d '{"model":"claude-sonnet-4-6","messages":[{"role":"user","content":"hi"}]}'
done
```

## 九、抢答策略（speculative execution）

对响应速度极致优化的场景：**同时发给两个模型，谁快用谁**：

```python
async def race(prompt):
    tasks = [
        call("claude-haiku-4-5", prompt),
        call("gpt-5-mini", prompt),
    ]
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for p in pending:
        p.cancel()
    return done.pop().result()
```

代价：

- 双倍 token 消耗
- 只适合"短任务 + 体验极敏感"场景

## 十、限制 `max_tokens`

输出越长 = 总耗时越久。明确知道答案不长就设小：

```python
client.chat.completions.create(
    ...,
    max_tokens=200,   # 强制简洁
)
```

延迟可控。**Tool call / 短回答场景必备**。

## 十一、降低 temperature

```python
temperature=0.0    # 确定性
temperature=0.7    # 默认
temperature=1.0    # 多样性
```

低 temperature 一般出 token 更快、模型计算更少。**事实查询 / 代码生成**用 0.0–0.3。

## 十二、Stop sequences

```python
stop=["\n\n", "###"]
```

模型遇到 stop 立刻停。**适合结构化输出**：

```
Q: ...
A: 答案
###   ← stop
```

强制简短。

## 十三、Reasoning effort（GPT-5 / o-series）

```python
client.responses.create(
    model="gpt-5",
    reasoning={"effort": "low"},   # low / medium / high
    ...,
)
```

低 effort = 快但浅。**简单任务用 low**。

Claude 类似的是 thinking budget：

```python
thinking={"type": "enabled", "budget_tokens": 1024}   # 不要 8000
```

## 十四、Anti-pattern

- ❌ 默认所有任务用 Opus
- ❌ 没流式硬等
- ❌ 长 system prompt 不开 cache
- ❌ 没限 max_tokens
- ❌ 串行 tool call
- ❌ 高 temperature + 长输出 + 复杂任务

## 十五、延迟监控

```python
import time

t0 = time.monotonic()
first_t = None
async for chunk in stream:
    if first_t is None:
        first_t = time.monotonic() - t0
total = time.monotonic() - t0
log("ttfb=%.2f total=%.2f" % (first_t, total))
```

p50 / p95 / p99 跟踪起来，异常立刻发现。

## 十六、相关阅读

- [AI API 中转稳定性测试方法](/blog/ai-api-relay-stability-test/)
- [prompt caching 在国内中转下省成本指南](/blog/prompt-caching-cost-optimization/)
- [Claude 并行 Tool Use 实战](/blog/parallel-tool-use-claude/)
- [LLM 流式 UI 实战模式](/blog/llm-streaming-ui-patterns/)
- [LLM API 限速处理](/blog/llm-rate-limit-handling/)

延迟优化 + 稳定中转 = 用户能感受到的"快"。[YoTradeApi](https://yotradeapi.com) 支持多区域接入 + caching 透传，按上面方法配置即可。
