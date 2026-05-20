---
title: AI API 流式输出（SSE）故障排查与最佳实践
description: AI API stream=true 在国内中转下的常见问题排查：断流、压缩失败、超时、心跳、断流恢复，含 curl/Python 调试方法。
keywords:
- ai api 流式 输出
- sse 断流
- stream 调试
- openai sse
- claude stream
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/streaming-sse-troubleshooting/
tags:
- 流式输出
- SSE
- 故障排查
- 调试
- API 中转
category: 故障排查
heroImage: ../../assets/blog-placeholder-3.jpg
---

`stream=true` 是 AI 应用的标配体验：用户能立刻看到第一行字、长回答不卡。但国内走中转时，**流式比非流式难调一个数量级**。本文把常见问题与调试方法一次说清。

## 一、SSE 在 AI API 里长什么样

OpenAI / Claude 的流式响应都是 `text/event-stream` 格式：

```
data: {"choices":[{"delta":{"content":"你"}}]}

data: {"choices":[{"delta":{"content":"好"}}]}

data: [DONE]
```

每行 `data: ` 开头，空行分隔。SDK 内部把它们组装成 chunk。

最小 curl 测试：

```bash
curl -N -H "Authorization: Bearer $KEY" \
  https://yotradeapi.com/v1/chat/completions \
  -d '{
    "model":"claude-sonnet-4-6",
    "messages":[{"role":"user","content":"数到 10"}],
    "stream":true
  }'
```

`-N` 关掉缓冲，让 curl 实时打印。

## 二、常见问题归类

### 问题 A：完全没有任何输出

直到超时才返回。

**原因 1**：中转把 SSE 缓冲了
- 中间有 nginx / cloudflare / 自定义代理压缩了流，到末端一次性吐出
- 处理：联系中转方关 `proxy_buffering off`，或换中转

**原因 2**：客户端没正确读流
- Python 写法不对（用了 `resp.text` 而不是迭代 chunks）
- Node 用了 `await resp.json()` 而不是 `for await`
- 处理：照 SDK 文档来

**原因 3**：实际不是 SSE，是 chunked JSON
- 部分国内中转把 stream 翻译错了
- 用 curl `-N -i` 看 `content-type` 是否是 `text/event-stream`

### 问题 B：开头几个 chunk 后断

可能输出 100 字然后停。

**原因**：中间代理 keep-alive 时间不够
- 多数 CDN 默认 60s 后关连接
- 模型推理慢 + 输出慢，60s 凑齐就被切

**处理**：
- 客户端缩短 prompt
- 网关侧调大 keep-alive timeout
- 用 `extra_headers={"X-Stream-Keepalive": "120"}` 测一下（看网关是否支持）

### 问题 C：流式输出穿插乱码

中文/emoji 字符断在中间。

**原因**：UTF-8 多字节字符被切到不同 chunk，客户端没合并就 print。

**处理**：用 SDK 的内置解析（不要裸 split）；Python 设 `sys.stdout.reconfigure(encoding='utf-8')`。

### 问题 D：心跳行污染数据

每隔几秒看到一行 `: keepalive` 或类似。

**原因**：网关发心跳让客户端不要超时断开。

**处理**：标准 SSE 规则——以 `:` 开头的行是注释，**忽略即可**。SDK 一般自动处理；自己写解析的时候记得过滤。

### 问题 E：tool_call 在流式下解析不出

部分网关在流式 tool_call 上协议不完整。

**处理**：
- 短期：对需要 tool_call 的请求**关闭流式**
- 长期：换支持完整流式 tool_call 的网关
- 测试方法：用一个简单的 function 定义跑 stream=true，看是否能完整组装

## 三、Python 调试模板

```python
import json
import requests

def debug_stream(url, key, model):
    r = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": "数到 10"}],
            "stream": True,
        },
        stream=True,
        timeout=120,
    )
    print(f"HTTP {r.status_code}")
    print(f"Content-Type: {r.headers.get('content-type')}")
    print("---")
    for line in r.iter_lines(decode_unicode=True):
        if not line:
            continue
        if line.startswith(":"):
            print(f"[heartbeat] {line}")
            continue
        if line.startswith("data: "):
            payload = line[6:]
            if payload == "[DONE]":
                print("[done]")
                break
            try:
                obj = json.loads(payload)
                delta = obj.get("choices", [{}])[0].get("delta", {}).get("content", "")
                print(f"[chunk] {repr(delta)}")
            except Exception as e:
                print(f"[parse-error] {e} | {payload[:100]}")
        else:
            print(f"[unknown] {line[:100]}")

debug_stream("https://yotradeapi.com/v1/chat/completions", "sk-yo-...", "claude-sonnet-4-6")
```

裸调试能帮你看到：

- HTTP 状态
- 真实 content-type
- 心跳间隔
- chunk 大小与间隔
- 协议异常

## 四、Node 调试模板

```ts
const res = await fetch("https://yotradeapi.com/v1/chat/completions", {
  method: "POST",
  headers: {
    Authorization: `Bearer ${KEY}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    model: "claude-sonnet-4-6",
    messages: [{ role: "user", content: "数到 10" }],
    stream: true,
  }),
});

const reader = res.body!.getReader();
const decoder = new TextDecoder();
let buf = "";
let first = true;
const t0 = Date.now();

while (true) {
  const { value, done } = await reader.read();
  if (done) break;
  buf += decoder.decode(value, { stream: true });
  const lines = buf.split("\n");
  buf = lines.pop()!;
  for (const line of lines) {
    if (first) {
      console.log(`TTFB: ${Date.now() - t0}ms`);
      first = false;
    }
    if (line.startsWith("data: ")) {
      const payload = line.slice(6);
      if (payload === "[DONE]") return;
      try {
        const obj = JSON.parse(payload);
        process.stdout.write(obj.choices?.[0]?.delta?.content ?? "");
      } catch {}
    }
  }
}
```

## 五、性能阈值参考

对编程代理体验，下面是个人推荐阈值：

| 指标 | 良 | 中 | 差 |
| --- | --- | --- | --- |
| TTFB | < 2s | 2–5s | > 5s |
| chunk 间隔 | < 100ms | 100–500ms | > 500ms |
| 输出速率 | > 50 tps | 20–50 tps | < 20 tps |
| 断流率 | < 0.5% | 0.5–2% | > 2% |

超出"差"的列直接换中转。

## 六、Anthropic vs OpenAI SSE 的差异

| 维度 | OpenAI | Anthropic |
| --- | --- | --- |
| 端点 | `/chat/completions` | `/messages` |
| 控制字段 | `stream:true` | `stream:true` |
| 终止信号 | `data: [DONE]` | `event: message_stop` |
| 事件类型 | 单一 `data:` | `event: ...` + `data: ...` |
| tool_call 流 | choices[].delta.tool_calls | content_block_start/delta |

写客户端时如果想同时支持两种协议，建议用 SDK（openai / anthropic）做底层。

## 七、降级到非流式

如果流式问题排查不顺，可以临时降级：

```python
resp = client.chat.completions.create(
    model="claude-sonnet-4-6",
    messages=[...],
    stream=False,   # 关
)
print(resp.choices[0].message.content)
```

牺牲首字延迟，但确定能拿到完整输出。线上长任务（>30s）流式不稳就先用这个。

## 八、相关阅读

- [AI API 中转稳定性测试方法](/blog/ai-api-relay-stability-test/)
- [OpenAI SDK base_url 国内配置实战](/blog/openai-sdk-base-url-cn/)
- [AI API 中转常见错误码排查手册](/blog/ai-api-relay-error-codes/)
- [Cursor API 中转怎么选](/blog/2026-05-15-cursor-api-relay-recommendation-2026/)

需要一个 SSE 透传稳定的中转？[YoTradeApi](https://yotradeapi.com) 后台展示每条 stream 请求的 TTFB、chunk 数、是否完整结束，问题可追溯。
