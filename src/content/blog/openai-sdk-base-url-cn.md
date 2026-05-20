---
title: OpenAI SDK base_url 国内配置实战
description: Python、Node、Go、Rust 四种 OpenAI SDK 在国内通过 base_url 接入中转的完整示例，含流式、函数调用、Vision、错误处理写法。
keywords:
- openai sdk base_url
- openai api 国内
- openai 中转
- openai python sdk 国内
- openai node sdk 国内
pubDate: '2026-05-17'
updatedDate: '2026-05-17'
canonical: https://blog.yotradeapi.com/blog/openai-sdk-base-url-cn/
tags:
- OpenAI SDK
- API 中转
- Python
- Node.js
- 配置教程
category: 工具配置
featured: true
heroImage: ../../assets/blog-placeholder-3.jpg
---

"`base_url` 改一下就能用" 这句话在国内每天都被复述，但真正实施的时候，每个 SDK 写法都不一样，错误处理也不一样。本文按 Python、Node、Go、Rust 四种栈展开，把流式、函数调用、Vision、超时和重试都写出来。

## 一、为什么 `base_url` 这一个字段就够了

OpenAI Compatible 网关的设计前提是：客户端不知道也不关心后端是谁。SDK 只要按 OpenAI 协议 POST `/chat/completions`、`/embeddings`、`/responses` 等端点，网关在后端负责模型路由。所以**改 base_url 就能用**这件事是可以成立的，前提有三：

1. 网关确实兼容 OpenAI 协议（chat、embeddings、moderation 等端点完整）。
2. SDK 调用的是 OpenAI 协议的端点，不是各厂商自家 endpoint。
3. 模型名是网关认识的（不要直接传 `gpt-4o`，多半要写成网关定义的别名）。

下文示例统一用 `https://yotradeapi.com/v1` 作为 base_url。

## 二、Python：openai-python SDK

```python
# pip install openai>=1.40
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["YOTRADE_API_KEY"],
    base_url="https://yotradeapi.com/v1",
    timeout=60.0,
    max_retries=2,
)

resp = client.chat.completions.create(
    model="claude-sonnet-4-6",
    messages=[
        {"role": "system", "content": "你是一个严谨的代码助手。"},
        {"role": "user", "content": "用 Python 写一个带指数退避的 HTTP 重试函数。"},
    ],
    temperature=0.2,
    stream=True,
)

for chunk in resp:
    delta = chunk.choices[0].delta.content
    if delta:
        print(delta, end="", flush=True)
```

要点：

- `timeout` 写到 60s 足够，太短会把首 token 慢的请求误判为失败。
- `max_retries=2`：SDK 内置指数退避，遇到 429/500 自动重试。
- `temperature` 编码任务一般 0.1–0.3。

### 函数调用 / Tools

```python
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "获取一个城市的天气",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
        },
    },
}]

resp = client.chat.completions.create(
    model="claude-sonnet-4-6",
    messages=[{"role": "user", "content": "上海今天天气怎么样？"}],
    tools=tools,
    tool_choice="auto",
)

tool_call = resp.choices[0].message.tool_calls[0]
print(tool_call.function.name, tool_call.function.arguments)
```

注意：不同模型的 tool_call 解析行为不一样。Claude 系列对 `tool_choice=auto` 行为接近原生，GPT 系列在某些参数组合下会被网关重写，建议用一组固定 prompt 跑一次回归测试。

### Vision（多模态）

```python
resp = client.chat.completions.create(
    model="claude-sonnet-4-6",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "这张截图里有几个按钮？"},
            {"type": "image_url", "image_url": {"url": "https://example.com/a.png"}},
        ],
    }],
)
print(resp.choices[0].message.content)
```

如果图片是本地文件，先转 base64：

```python
import base64, pathlib
b64 = base64.b64encode(pathlib.Path("a.png").read_bytes()).decode()
data_url = f"data:image/png;base64,{b64}"
```

## 三、Node.js / TypeScript：openai-node SDK

```ts
// npm i openai@^5
import OpenAI from "openai";

const client = new OpenAI({
  apiKey: process.env.YOTRADE_API_KEY,
  baseURL: "https://yotradeapi.com/v1",
  timeout: 60_000,
  maxRetries: 2,
});

const stream = await client.chat.completions.create({
  model: "claude-sonnet-4-6",
  messages: [
    { role: "system", content: "You write production-ready TypeScript." },
    { role: "user", content: "写一个 fetch 包装器，包含超时和 JSON 错误处理。" },
  ],
  stream: true,
});

for await (const part of stream) {
  process.stdout.write(part.choices[0]?.delta?.content ?? "");
}
```

### Abort 控制

长任务最好支持中途取消：

```ts
const controller = new AbortController();
setTimeout(() => controller.abort(), 30_000);

const stream = await client.chat.completions.create(
  { model: "claude-sonnet-4-6", messages, stream: true },
  { signal: controller.signal },
);
```

### 错误分类

```ts
import { APIError, APIConnectionError, RateLimitError } from "openai";

try {
  await client.chat.completions.create({ /* ... */ });
} catch (err) {
  if (err instanceof RateLimitError) {
    // 429：等待后重试
  } else if (err instanceof APIConnectionError) {
    // 网络断流：换节点
  } else if (err instanceof APIError) {
    console.error(err.status, err.message);
  }
}
```

## 四、Go：go-openai

```go
// go get github.com/sashabaranov/go-openai
package main

import (
    "context"
    "fmt"
    "io"
    "os"

    openai "github.com/sashabaranov/go-openai"
)

func main() {
    cfg := openai.DefaultConfig(os.Getenv("YOTRADE_API_KEY"))
    cfg.BaseURL = "https://yotradeapi.com/v1"
    client := openai.NewClientWithConfig(cfg)

    stream, err := client.CreateChatCompletionStream(context.Background(), openai.ChatCompletionRequest{
        Model: "claude-sonnet-4-6",
        Messages: []openai.ChatCompletionMessage{
            {Role: openai.ChatMessageRoleSystem, Content: "你是简洁的 Go 助手。"},
            {Role: openai.ChatMessageRoleUser, Content: "写一个 channel-based worker pool。"},
        },
        Stream: true,
    })
    if err != nil {
        panic(err)
    }
    defer stream.Close()

    for {
        resp, err := stream.Recv()
        if err == io.EOF {
            return
        }
        if err != nil {
            panic(err)
        }
        fmt.Print(resp.Choices[0].Delta.Content)
    }
}
```

## 五、Rust：async-openai

```rust
// Cargo.toml: async-openai = "0.27"
use async_openai::{config::OpenAIConfig, types::*, Client};
use futures::StreamExt;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let cfg = OpenAIConfig::new()
        .with_api_key(std::env::var("YOTRADE_API_KEY")?)
        .with_api_base("https://yotradeapi.com/v1");
    let client = Client::with_config(cfg);

    let req = CreateChatCompletionRequestArgs::default()
        .model("claude-sonnet-4-6")
        .messages([ChatCompletionRequestUserMessageArgs::default()
            .content("用 Rust 写一个简单的 LRU 缓存。")
            .build()?
            .into()])
        .stream(true)
        .build()?;

    let mut stream = client.chat().create_stream(req).await?;
    while let Some(chunk) = stream.next().await {
        if let Ok(c) = chunk {
            for choice in c.choices {
                if let Some(content) = choice.delta.content {
                    print!("{}", content);
                }
            }
        }
    }
    Ok(())
}
```

## 六、常见误区

1. **base_url 多写或少写 `/v1`**：OpenAI Python/Node SDK 期望完整路径含 `/v1`；Anthropic CLI 则不需要。两者搞混会出 404。
2. **混用环境变量名**：SDK 默认读 `OPENAI_API_KEY`。如果你设置的是 `YOTRADE_API_KEY`，必须手动传 `api_key=`，否则 SDK 静默 fallback 到空字符串再 401。
3. **embeddings 与 chat 走不同模型**：很多人改完 base_url 之后 chat 能用，但 embeddings 报 404，这是因为网关没接 embeddings 模型，需要单独配置或换模型名。
4. **流式调用的 chunk 解析**：部分网关只在 chunk 末尾发 `[DONE]`，部分网关在中间发心跳行。SDK 一般能处理，但自己用裸 fetch 写的需要注意。

## 七、压测脚本：smoke_openai_compatible.py

```python
import argparse, statistics, time
from openai import OpenAI

ap = argparse.ArgumentParser()
ap.add_argument("--base-url", required=True)
ap.add_argument("--api-key", required=True)
ap.add_argument("--model", required=True)
ap.add_argument("--runs", type=int, default=3)
ap.add_argument("--stream", action="store_true")
args = ap.parse_args()

client = OpenAI(api_key=args.api_key, base_url=args.base_url, timeout=60)

ttfb, total = [], []
for i in range(args.runs):
    t0 = time.time()
    first = None
    resp = client.chat.completions.create(
        model=args.model,
        messages=[{"role": "user", "content": "用一句话介绍 Rust。"}],
        stream=args.stream,
    )
    if args.stream:
        for chunk in resp:
            if first is None and chunk.choices[0].delta.content:
                first = time.time() - t0
        total.append(time.time() - t0)
        ttfb.append(first or 0)
    else:
        total.append(time.time() - t0)

print(f"runs={args.runs}")
if ttfb:
    print(f"ttfb p50={statistics.median(ttfb):.2f}s")
print(f"total p50={statistics.median(total):.2f}s")
```

跑法：

```bash
python smoke_openai_compatible.py \
  --base-url https://yotradeapi.com/v1 \
  --api-key sk-... \
  --model claude-sonnet-4-6 \
  --runs 5 --stream
```

把这个脚本接入 CI 之后，新接入一个中转就跑一遍，能用 5 分钟筛掉一大半"看起来能用其实不稳"的服务。

## 八、相关阅读

- [Cursor API 中转怎么选：2026 实用清单](/blog/2026-05-15-cursor-api-relay-recommendation-2026/)
- [Claude Code 镜像国内配置完整指南](/blog/claude-code-mirror-cn-setup/)
- [AI API 中转稳定性测试方法](/blog/ai-api-relay-stability-test/)
- [Cline 国内 API 配置详解](/blog/cline-cn-api-setup/)

需要一个独立 API Key 做小流量测试？在 [YoTradeApi 注册](https://yotradeapi.com) 创建 key，把上面的 `base_url` 直接接进现有 SDK 即可。
