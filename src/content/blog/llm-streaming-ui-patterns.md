---
title: LLM 流式 UI 实战模式：React / Vue / SvelteKit
description: AI 聊天界面的流式输出 UI 实战：SSE 解析、增量渲染、abort 控制、错误恢复、思考状态展示、tool call 可视化。
keywords:
- llm 流式 ui
- chatgpt 风格 流式
- react ai streaming
- sveltekit ai
- vue ai chat
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/llm-streaming-ui-patterns/
tags:
- 前端
- 流式
- UI
- React
- Vue
category: 工程实战
heroImage: ../../assets/blog-placeholder-1.jpg
---

ChatGPT 风格的流式输出 UI 看起来简单，写好其实坑很多：abort、错误恢复、Markdown 渐进渲染、思考状态、tool call 可视化。本文给三大框架的实战模式。

## 一、整体架构

```
浏览器 → 你的 Next.js / Express API → LLM API
   ↑          ↑
   SSE        upstream SSE
```

服务端把上游 SSE 转给浏览器。**不要让浏览器直连 LLM**（暴露 API Key）。

## 二、Next.js Route Handler（服务端）

```ts
// app/api/chat/route.ts
import { OpenAI } from "openai";

const client = new OpenAI({
  apiKey: process.env.YOTRADE_KEY,
  baseURL: "https://yotradeapi.com/v1",
});

export async function POST(req: Request) {
  const { messages } = await req.json();

  const stream = await client.chat.completions.create({
    model: "claude-sonnet-4-6",
    messages,
    stream: true,
  });

  const encoder = new TextEncoder();
  const readable = new ReadableStream({
    async start(controller) {
      try {
        for await (const part of stream) {
          const delta = part.choices[0]?.delta?.content || "";
          if (delta) {
            controller.enqueue(encoder.encode(`data: ${JSON.stringify({ delta })}\n\n`));
          }
        }
        controller.enqueue(encoder.encode(`data: [DONE]\n\n`));
      } finally {
        controller.close();
      }
    },
  });

  return new Response(readable, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      "Connection": "keep-alive",
    },
  });
}
```

关键：`no-cache, no-transform`、`Connection: keep-alive`。CDN / 反向代理需要透传 SSE（看 [SSE 故障排查](/blog/streaming-sse-troubleshooting/)）。

## 三、React 客户端

```tsx
"use client";
import { useState } from "react";

export function Chat() {
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);
  const [pending, setPending] = useState("");
  const [loading, setLoading] = useState(false);
  const [abort, setAbort] = useState<AbortController | null>(null);

  async function send(input: string) {
    const next = [...messages, { role: "user", content: input }];
    setMessages(next);
    setLoading(true);
    setPending("");

    const ctrl = new AbortController();
    setAbort(ctrl);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        body: JSON.stringify({ messages: next }),
        signal: ctrl.signal,
      });

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let acc = "";
      let buf = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop()!;
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const payload = line.slice(6);
          if (payload === "[DONE]") break;
          try {
            const obj = JSON.parse(payload);
            if (obj.delta) {
              acc += obj.delta;
              setPending(acc);
            }
          } catch {}
        }
      }

      setMessages([...next, { role: "assistant", content: acc }]);
      setPending("");
    } catch (err: any) {
      if (err.name !== "AbortError") console.error(err);
      if (pending) {
        setMessages([...next, { role: "assistant", content: pending + " [中断]" }]);
        setPending("");
      }
    } finally {
      setLoading(false);
      setAbort(null);
    }
  }

  return (
    <div>
      <div className="messages">
        {messages.map((m, i) => (
          <div key={i} className={m.role}>{m.content}</div>
        ))}
        {pending && <div className="assistant pending">{pending}</div>}
      </div>
      <form onSubmit={(e) => { e.preventDefault(); send((e.target as any).input.value); }}>
        <input name="input" disabled={loading} />
        <button type="submit" disabled={loading}>Send</button>
        {abort && <button type="button" onClick={() => abort.abort()}>Stop</button>}
      </form>
    </div>
  );
}
```

## 四、用 Vercel AI SDK（推荐）

```bash
npm install ai @ai-sdk/openai
```

省 80% 模板代码：

```ts
// app/api/chat/route.ts
import { streamText } from "ai";
import { createOpenAI } from "@ai-sdk/openai";

const openai = createOpenAI({
  apiKey: process.env.YOTRADE_KEY,
  baseURL: "https://yotradeapi.com/v1",
});

export async function POST(req: Request) {
  const { messages } = await req.json();
  const result = streamText({
    model: openai("claude-sonnet-4-6"),
    messages,
  });
  return result.toDataStreamResponse();
}
```

```tsx
// React
"use client";
import { useChat } from "ai/react";

export function Chat() {
  const { messages, input, handleInputChange, handleSubmit, isLoading, stop } = useChat();
  return (
    <>
      {messages.map((m) => <div key={m.id}>{m.content}</div>)}
      <form onSubmit={handleSubmit}>
        <input value={input} onChange={handleInputChange} />
        {isLoading ? <button onClick={stop}>Stop</button> : <button>Send</button>}
      </form>
    </>
  );
}
```

abort、错误处理、tool call 都内置。

## 五、Vue / Nuxt 实现

```vue
<script setup>
const messages = ref([])
const pending = ref('')
const loading = ref(false)
let controller = null

async function send(input) {
  messages.value.push({ role: 'user', content: input })
  loading.value = true
  pending.value = ''
  controller = new AbortController()

  const res = await fetch('/api/chat', {
    method: 'POST',
    body: JSON.stringify({ messages: messages.value }),
    signal: controller.signal,
  })

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let acc = '', buf = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    const lines = buf.split('\n')
    buf = lines.pop()
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      const p = line.slice(6)
      if (p === '[DONE]') break
      try {
        const obj = JSON.parse(p)
        if (obj.delta) {
          acc += obj.delta
          pending.value = acc
        }
      } catch {}
    }
  }

  messages.value.push({ role: 'assistant', content: acc })
  pending.value = ''
  loading.value = false
}
</script>
```

## 六、SvelteKit

```ts
// +server.ts
export async function POST({ request }) {
  const { messages } = await request.json();
  const upstream = await fetch("https://yotradeapi.com/v1/chat/completions", { ... });
  return new Response(upstream.body, {
    headers: { "content-type": "text/event-stream" },
  });
}
```

Svelte 直接代理 SSE，前端用 fetch + reader 模式同上。

## 七、Markdown 渐进渲染

流式 Markdown 渲染容易：

- 表格只渲染一半时格式错乱
- 代码块未闭合
- 链接 `]()` 半截

解决方案：用 `streaming-markdown` 之类库，或者：

```ts
// 渲染时简单兜底
function safeMarkdown(s: string) {
  // 把未闭合的 ``` 补上
  const backticks = (s.match(/```/g) || []).length;
  if (backticks % 2 === 1) s += "\n```";
  return s;
}
```

## 八、思考状态

如果用了 extended thinking（Claude）：

```ts
{
  type: "thinking_delta",
  thinking: "让我想想..."
}
{
  type: "text_delta",
  text: "答案是..."
}
```

UI 分两段：折叠的"思考过程"+ 显示的"答案"。用户体验更透明。

## 九、Tool Call 可视化

Agent 模式下 UI 可以显示当前在干什么：

```tsx
{toolCalls.map(tc => (
  <div key={tc.id} className="tool-call">
    🔧 调用 {tc.name}({JSON.stringify(tc.args)})
    {tc.result ? <pre>{tc.result}</pre> : <span>...</span>}
  </div>
))}
```

让用户看到 agent 在干嘛，减少"卡了几十秒不知道在干什么"的焦虑。

## 十、错误恢复

```ts
try {
  // 流式调用
} catch (err) {
  if (acc) {
    // 已有部分输出，保留 + 标记中断
    addMessage({ role: "assistant", content: acc + " [中断]" });
  } else {
    // 完全没输出
    showError("LLM 调用失败，请重试");
  }
}
```

最差的体验是"用户等了 30 秒然后什么都没有"。**部分输出也要保留**。

## 十一、Abort 优雅处理

用户点 Stop 时：

```ts
controller.abort()
```

但服务端可能还在跑（如果 fetch 已开始）。**服务端 Route Handler 要监听 client disconnect**：

```ts
export async function POST(req: Request) {
  req.signal.addEventListener("abort", () => {
    // 关闭上游 LLM stream
    upstreamController.abort();
  });
  // ...
}
```

不然客户端断了，服务器还在烧 token。

## 十二、相关阅读

- [流式 SSE 故障排查](/blog/streaming-sse-troubleshooting/)
- [OpenAI SDK base_url 国内配置实战](/blog/openai-sdk-base-url-cn/)
- [LLM API 限速处理](/blog/llm-rate-limit-handling/)
- [前端开发者用 AI 编程的实战工作流](/blog/ai-coding-for-frontend-dev/)

UI 接 [YoTradeApi](https://yotradeapi.com) 中转，按上面的模板服务端代理即可。
