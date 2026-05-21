---
title: 从零搭建生产级 AI Chatbot：架构设计与工程实践
description: 手把手讲解如何用 Python + FastAPI 构建可扩展的生产级 AI Chatbot，涵盖多轮对话、流式输出、上下文管理和成本控制全链路实践。
keywords:
  - 生产级 AI Chatbot 搭建
  - FastAPI AI 聊天机器人
  - 多轮对话上下文管理
  - LLM 流式输出实践
  - AI Chatbot 架构设计
pubDate: '2026-05-21'
updatedDate: '2026-05-21'
canonical: https://blog.yotradeapi.com/blog/ai-chatbot-from-scratch/
tags:
  - Chatbot
  - FastAPI
  - 应用工程
  - 生产实践
category: 应用工程
heroImage: ../../assets/blog-placeholder-1.jpg
---

很多开发者第一次接触 LLM 时，会用几行 Python 调一次 API，看到回复就觉得"差不多了"。但等真正要上线一个 Chatbot，才发现坑一个接一个：多轮对话历史怎么存？Token 超限了怎么办？流式输出如何接？如何控制每月账单不爆炸？

本文从零开始，系统讲解一个**生产级 AI Chatbot** 需要解决的核心工程问题，并给出可直接参考的代码架构。

---

## 一、整体架构设计

生产级 Chatbot 不是简单的"HTTP 请求套壳"，它需要解决以下五个核心问题：

1. **会话管理**：识别每个用户的独立对话，隔离上下文
2. **历史存储**：持久化对话历史，支持跨请求连续性
3. **上下文裁剪**：防止历史消息超过模型最大 Token 限制
4. **流式输出**：低延迟逐字返回，提升用户体验
5. **成本控制**：Token 用量追踪与限额策略

架构图（文字版）：

```
用户请求
  │
  ▼
FastAPI 路由层（鉴权 + 限流）
  │
  ▼
会话管理器（session_id → 历史记录）
  │
  ▼
上下文裁剪器（超限时滑动窗口）
  │
  ▼
LLM 调用层（OpenAI 兼容 API）
  │
  ▼
流式响应（SSE / WebSocket）→ 前端
```

---

## 二、项目初始化与依赖

```bash
mkdir chatbot-prod && cd chatbot-prod
python -m venv .venv && source .venv/bin/activate

pip install fastapi uvicorn openai redis pydantic python-dotenv tiktoken
```

目录结构：

```
chatbot-prod/
├── main.py           # FastAPI 入口
├── session.py        # 会话与历史管理
├── context.py        # 上下文裁剪
├── llm.py            # LLM 调用封装
├── .env              # 环境变量
└── requirements.txt
```

`.env` 文件：

```env
OPENAI_API_KEY=your_key_here
OPENAI_BASE_URL=https://api.yotradeapi.com/v1
REDIS_URL=redis://localhost:6379
MODEL_NAME=gpt-4o
MAX_HISTORY_TOKENS=6000
```

---

## 三、会话与历史管理

生产环境中，会话历史必须持久化到外部存储（Redis、数据库等），而不能只放在内存里——进程重启会丢失所有上下文。

```python
# session.py
import json
import redis.asyncio as redis
from typing import List, Dict

class SessionManager:
    def __init__(self, redis_url: str, ttl: int = 3600):
        self.redis = redis.from_url(redis_url)
        self.ttl = ttl  # 会话过期时间（秒）

    async def get_history(self, session_id: str) -> List[Dict]:
        raw = await self.redis.get(f"chat:{session_id}")
        if raw is None:
            return []
        return json.loads(raw)

    async def append_message(self, session_id: str, role: str, content: str):
        history = await self.get_history(session_id)
        history.append({"role": role, "content": content})
        await self.redis.setex(
            f"chat:{session_id}",
            self.ttl,
            json.dumps(history, ensure_ascii=False)
        )

    async def clear_session(self, session_id: str):
        await self.redis.delete(f"chat:{session_id}")
```

---

## 四、上下文裁剪器

这是很多初学者跳过但最重要的环节。当对话历史超过模型上下文窗口时，如果不处理，API 会报 `400 context_length_exceeded` 错误。

常见策略对比：

| 策略 | 优点 | 缺点 |
|------|------|------|
| 滑动窗口（删最旧 N 条） | 简单，成本可控 | 可能丢失重要早期信息 |
| Token 数限制（删到 N Token 以内） | 精确 | 需要分词库 |
| 摘要压缩（旧消息 → summary） | 信息保留最好 | 额外 LLM 调用，成本高 |
| 只保留系统提示 + 最近 K 轮 | 兼顾简单与实用 | 对超长单条消息无效 |

生产中推荐"Token 数限制 + 保留系统提示"：

```python
# context.py
import tiktoken
from typing import List, Dict

def count_tokens(messages: List[Dict], model: str = "gpt-4o") -> int:
    enc = tiktoken.encoding_for_model(model)
    total = 0
    for msg in messages:
        # 每条消息固定开销 4 token
        total += 4 + len(enc.encode(msg.get("content", "")))
    return total + 2  # 回复预留

def trim_context(
    system_prompt: str,
    history: List[Dict],
    max_tokens: int = 6000,
    model: str = "gpt-4o"
) -> List[Dict]:
    system_msg = {"role": "system", "content": system_prompt}
    messages = [system_msg] + history

    while count_tokens(messages, model) > max_tokens and len(messages) > 2:
        # 删除 system 之后的最旧一条用户/助手消息
        messages.pop(1)

    return messages
```

---

## 五、LLM 调用层与流式输出

```python
# llm.py
import os
from openai import AsyncOpenAI
from typing import AsyncGenerator

client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
)

async def stream_chat(messages: list, model: str) -> AsyncGenerator[str, None]:
    stream = await client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
        temperature=0.7,
        max_tokens=1024
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content
```

---

## 六、FastAPI 路由：SSE 流式接口

Server-Sent Events（SSE）是 Chatbot 流式输出的主流实现方式，比 WebSocket 更轻量，适合单向推送场景。

```python
# main.py
import os
import uuid
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from session import SessionManager
from context import trim_context
from llm import stream_chat

load_dotenv()
app = FastAPI()

session_manager = SessionManager(
    redis_url=os.getenv("REDIS_URL", "redis://localhost:6379")
)

SYSTEM_PROMPT = """你是一个专业的 AI 助手，回答简洁、准确、有帮助。
如果不确定，直接说不知道，不要编造信息。"""

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None

@app.post("/chat")
async def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())

    # 1. 获取历史
    history = await session_manager.get_history(session_id)

    # 2. 加入用户新消息
    history.append({"role": "user", "content": req.message})

    # 3. 裁剪上下文
    messages = trim_context(
        system_prompt=SYSTEM_PROMPT,
        history=history,
        max_tokens=int(os.getenv("MAX_HISTORY_TOKENS", 6000)),
        model=os.getenv("MODEL_NAME", "gpt-4o")
    )

    # 4. 流式生成 + 收集完整回复
    collected: list[str] = []

    async def event_stream():
        async for token in stream_chat(messages, os.getenv("MODEL_NAME", "gpt-4o")):
            collected.append(token)
            yield f"data: {token}\n\n"

        # 流结束后持久化
        assistant_reply = "".join(collected)
        await session_manager.append_message(session_id, "user", req.message)
        await session_manager.append_message(session_id, "assistant", assistant_reply)
        yield f"data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "X-Session-Id": session_id,
            "Cache-Control": "no-cache",
        }
    )

@app.delete("/chat/{session_id}")
async def clear_chat(session_id: str):
    await session_manager.clear_session(session_id)
    return {"status": "cleared"}
```

---

## 七、成本控制策略

Chatbot 上线后，成本很容易失控。以下是几个实用的控制手段：

### 7.1 Token 用量追踪

在每次 LLM 调用后记录 usage：

```python
# 非流式调用时，response.usage 包含精确 token 数
print(f"本次消耗：{response.usage.total_tokens} tokens")
```

流式调用时无法直接拿 usage，可以用 `tiktoken` 估算，或开启 `stream_options={"include_usage": True}`（部分 API 支持）。

### 7.2 用户级别限额

用 Redis 做简单的每日限额：

```python
async def check_rate_limit(user_id: str, daily_limit: int = 100) -> bool:
    key = f"limit:{user_id}:{datetime.date.today()}"
    count = await redis_client.incr(key)
    if count == 1:
        await redis_client.expire(key, 86400)  # 次日重置
    return count <= daily_limit
```

### 7.3 模型降级策略

对简单问题用便宜模型，复杂问题才用强模型：

```python
def select_model(message: str) -> str:
    if len(message) < 50 and "代码" not in message:
        return "gpt-4o-mini"  # 短问题用便宜模型
    return "gpt-4o"
```

---

## 八、部署与运维注意事项

### 容器化

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 健康检查

```python
@app.get("/health")
async def health():
    return {"status": "ok"}
```

### 关键监控指标

- **P95 响应时间**：流式首 Token 延迟（TTFT）应 < 1s
- **错误率**：429（限流）、500（模型错误）分类监控
- **每日 Token 消耗**：设置预算告警
- **会话活跃数**：Redis key 数量

---

## 九、相关阅读

- [LLM 流式输出 UI 模式实践](/blog/llm-streaming-ui-patterns/)
- [Streaming SSE 排查指南](/blog/streaming-sse-troubleshooting/)
- [Python 异步 LLM 客户端最佳实践](/blog/python-async-llm-client/)
- [各家 LLM JSON 模式横向对比](/blog/llm-json-mode-comparison/)
- [Token 计算中文指南](/blog/token-counting-cn-guide/)

想快速接入 GPT、Claude、Gemini 等多个模型而不用管理多套 Key？[YoTradeApi](https://yotradeapi.com) 提供统一的 OpenAI 兼容接口，一个 Key 即可在 Chatbot 里随时切换底层模型。
