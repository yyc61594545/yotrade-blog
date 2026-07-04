---
title: OpenAI Realtime API 国内使用指南
description: 详解 OpenAI Realtime API 的 WebSocket 通信原理、语音交互实现方式，以及国内开发者接入时常遇到的网络与配置问题。
keywords:
  - OpenAI Realtime API
  - Realtime API 语音
  - WebSocket 语音交互
  - Realtime API 国内使用
  - GPT 语音对话开发
pubDate: '2026-07-04'
updatedDate: '2026-07-04'
canonical: https://blog.yotradeapi.com/blog/openai-realtime-api-guide/
tags:
  - OpenAI
  - Realtime API
  - 语音交互
  - 技术深度
category: 技术深度
heroImage: ../../assets/blog-placeholder-4.jpg
---

Realtime API 是 OpenAI 为低延迟语音/多模态交互设计的接口，核心是基于 WebSocket 的持久连接，而不是传统的请求-响应模式。对于要做语音助手、实时客服、AI 通话类产品的开发者，理解它的通信模型和国内接入方式是绕不开的一课。

## 一、Realtime API 解决的是什么问题

传统调用方式（先转文字、再调用 Chat Completions、再转语音）有两个明显缺陷：

- **延迟叠加**：语音转文字（STT）+ 模型推理 + 文字转语音（TTS）三段串联，每段都有网络往返，累计延迟往往超过 2–3 秒
- **打断不自然**：用户说话到一半想打断 AI 回复，传统三段式架构很难做到流畅的"抢话"体验

Realtime API 把这三步压缩进一个持久的 WebSocket 连接里，音频流直接进、直接出，模型内部处理语音理解和生成，省掉了中间的文字转换环节，端到端延迟通常能做到 500ms 以内。

## 二、核心通信模型：事件驱动的 WebSocket

Realtime API 不是简单的"发请求、等响应"，而是**双向事件流**：

```
客户端 → 服务端事件（举例）：
  session.update          # 配置会话参数（模型、语音、指令）
  input_audio_buffer.append   # 追加一段音频数据
  input_audio_buffer.commit   # 提交音频缓冲区，触发处理
  conversation.item.create    # 手动插入一条对话内容
  response.create             # 请求模型生成回复

服务端 → 客户端事件（举例）：
  session.created
  input_audio_buffer.speech_started   # 检测到用户开始说话
  input_audio_buffer.speech_stopped   # 检测到用户停止说话
  response.audio.delta                # 流式返回的音频片段
  response.audio_transcript.delta     # 流式返回的文字转写
  response.done                       # 本轮回复结束
```

理解这套事件模型是接入的关键：你不是"调用一次拿到一个结果"，而是**监听一连串事件，按事件类型分别处理**。

## 三、Python 快速接入示例

```python
import asyncio
import json
import websockets

OPENAI_API_KEY = "your-api-key"
URL = "wss://api.openai.com/v1/realtime?model=gpt-realtime"

async def run_session():
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}

    async with websockets.connect(URL, additional_headers=headers) as ws:
        # 1. 配置会话
        await ws.send(json.dumps({
            "type": "session.update",
            "session": {
                "modalities": ["audio", "text"],
                "instructions": "你是一个中文语音客服助手，回答简洁友好。",
                "voice": "alloy",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "turn_detection": {"type": "server_vad"}
            }
        }))

        # 2. 监听事件循环
        async for message in ws:
            event = json.loads(message)
            event_type = event.get("type")

            if event_type == "response.audio.delta":
                # 收到一段音频，追加播放
                audio_chunk = event["delta"]  # base64 编码的 PCM 数据
                # play_audio(audio_chunk)  # 实际项目中接入播放器
                pass
            elif event_type == "response.audio_transcript.delta":
                print(event["delta"], end="", flush=True)
            elif event_type == "response.done":
                print("\n[本轮回复结束]")

asyncio.run(run_session())
```

关键点：`turn_detection` 设为 `server_vad` 后，服务端会自动检测语音的开始/结束（Voice Activity Detection），不需要客户端自己判断"用户说完了没"。

## 四、国内开发者接入的三个实际问题

### 问题 1：WebSocket 连接不稳定

Realtime API 依赖长连接，国内到 OpenAI 服务器的网络路径本身就不稳定，长连接比短请求更容易被中间节点重置。表现为：连接建立后几十秒到几分钟就断开，且断开时机不规律。

**排查思路**：先用普通 Chat Completions 接口测试网络是否通畅，再单独测试 WebSocket 连接；如果 HTTP 请求正常但 WebSocket 频繁断线，基本可以确定是长连接层面被干扰，而非账号或代码问题。

### 问题 2：音频延迟和抖动

即使连接不断开，网络抖动也会导致音频流"卡顿"——这在语音场景比文字场景敏感得多（文字卡一下用户感知不强，语音卡一下就是明显的断续感）。

**缓解方式**：
- 客户端做适当的音频缓冲（牺牲一点延迟换流畅度）
- 监控 `input_audio_buffer.speech_started/stopped` 事件的时间间隔，异常延迟可以主动重连

### 问题 3：断线重连后的会话状态丢失

WebSocket 断开后重连，默认是全新会话，之前的对话上下文会丢失。生产环境需要自己实现：

```python
# 断线重连时，重放必要的上下文
async def reconnect_with_context(ws, conversation_history):
    await ws.send(json.dumps({
        "type": "session.update",
        "session": {"modalities": ["audio", "text"], "instructions": "..."}
    }))
    for item in conversation_history:
        await ws.send(json.dumps({
            "type": "conversation.item.create",
            "item": item
        }))
```

## 五、通过中转接入的注意事项

如果通过 API 中转服务访问 Realtime API，需要确认两件事：

1. **中转是否支持 WebSocket 协议转发**——不是所有中转商都支持长连接代理，部分中转只做 HTTP 请求转发，这种情况下 Realtime API 无法使用
2. **中转的连接稳定性是否针对长连接优化**——普通 HTTP 中转和长连接中转在底层网络处理上不同，选择中转前建议先做一次几分钟的连接稳定性测试

```python
client_url = "wss://api.yotradeapi.com/v1/realtime?model=gpt-realtime"
# 其余事件收发逻辑与直连完全一致
```

## 六、成本注意事项

Realtime API 按音频输入/输出时长和文本 token 双重计费，通常比纯文字对话贵不少（语音数据量本身远大于文字）。生产环境建议：

- 设置合理的会话超时，避免用户挂断后连接仍在计费
- 对于不需要实时性的场景（如离线语音转写后分析），优先用普通 STT + Batch API 组合，成本更低，参考[OpenAI Batch API 节省 50% 成本实战](/blog/openai-batch-api-cn-guide/)

## 七、常见问题

**Q：Realtime API 支持中文语音吗？**
支持，模型本身具备多语言语音理解和生成能力，中文语音交互体验目前整体可用，但语气/口音的自然度仍在持续迭代中。

**Q：可以只用文字模式，不用语音吗？**
可以，`modalities` 设置为 `["text"]` 即可，这种情况下更接近普通流式对话，但延迟优势会打折扣（因为省掉了语音层面的优化）。

**Q：和 Anthropic 有类似的实时语音接口吗？**
截至本文，Anthropic 尚未发布对标的原生语音 Realtime API，如果项目需要语音交互，目前 OpenAI Realtime API 是更成熟的选择。

## 八、相关阅读

- [OpenAI Batch API 节省 50% 成本实战](/blog/openai-batch-api-cn-guide/)
- [LLM 批处理 vs 实时推理成本对比](/blog/llm-batch-vs-realtime-cost/)
- [AI API 中转 vs 自建 VPN：成本与稳定性对比](/blog/ai-api-relay-vs-self-vpn/)
- [AI API 中转稳定性实测报告](/blog/ai-api-relay-stability-test/)

想在国内稳定接入 Realtime API？[YoTradeApi](https://yotradeapi.com) 支持 WebSocket 长连接中转，为语音交互场景做了专门的连接稳定性优化，支付宝充值即可使用。
