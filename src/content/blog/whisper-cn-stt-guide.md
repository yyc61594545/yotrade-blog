---
title: Whisper API 国内调用指南：中文语音转文字
description: OpenAI Whisper 与替代方案在国内通过中转的语音转文字实战：批量、流式、长音频、说话人分离、中文优化。
keywords:
- whisper api 国内
- 中文 语音转文字
- whisper 中转
- ai 语音识别
- speech to text api
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/whisper-cn-stt-guide/
tags:
- Whisper
- 语音识别
- STT
- 中文
- API
category: 工程实战
heroImage: ../../assets/blog-placeholder-1.jpg
---

# Whisper API 国内调用指南：中文语音转文字

Whisper 是当前最主流的开源语音识别模型，OpenAI 提供托管 API。本文给国内通过中转的调用、批量处理、长音频拆分、与国产替代方案对比。

## 一、Whisper API 接入

```python
from openai import OpenAI

client = OpenAI(api_key="sk-yo-...", base_url="https://yotradeapi.com/v1")

with open("speech.mp3", "rb") as f:
    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=f,
        language="zh",
    )
print(transcript.text)
```

国内中转直接转发到 `audio/transcriptions` 端点。**注意**：

- 单文件 ≤ 25MB
- 支持 mp3, mp4, mpeg, mpga, m4a, wav, webm
- `language="zh"` 显式指定中文，否则识别错语言

## 二、输出格式

```python
transcript = client.audio.transcriptions.create(
    model="whisper-1",
    file=f,
    response_format="verbose_json",   # text / srt / vtt / verbose_json / json
    timestamp_granularities=["segment", "word"],
)

for segment in transcript.segments:
    print(f"[{segment.start:.1f}-{segment.end:.1f}] {segment.text}")
```

- `text`：纯文字
- `srt` / `vtt`：字幕（带时间戳）
- `verbose_json`：带 segment / word 级时间戳
- `json`：简化 JSON

## 三、长音频拆分

> 25MB 上限 ≈ 10 分钟高质量音频。长视频要拆。

```python
from pydub import AudioSegment

audio = AudioSegment.from_file("long.mp4")
chunk_ms = 10 * 60 * 1000   # 10 分钟一段
chunks = [audio[i:i+chunk_ms] for i in range(0, len(audio), chunk_ms)]

results = []
for i, chunk in enumerate(chunks):
    chunk.export(f"/tmp/chunk_{i}.mp3", format="mp3", bitrate="64k")
    with open(f"/tmp/chunk_{i}.mp3", "rb") as f:
        t = client.audio.transcriptions.create(model="whisper-1", file=f, language="zh")
    results.append(t.text)

full_text = "\n".join(results)
```

**注意**：拆分点尽量在静音处，避免词被切断。

## 四、并发处理

```python
import asyncio
from openai import AsyncOpenAI

aclient = AsyncOpenAI(api_key="sk-yo-...", base_url="https://yotradeapi.com/v1")
sem = asyncio.Semaphore(5)

async def transcribe(path):
    async with sem:
        with open(path, "rb") as f:
            t = await aclient.audio.transcriptions.create(model="whisper-1", file=f, language="zh")
        return t.text

results = asyncio.run(asyncio.gather(*[transcribe(p) for p in chunk_paths]))
```

详见 [Python 异步并发调用 LLM API](/blog/python-async-llm-client/)。

## 五、中文优化技巧

### 1. 加 prompt 提示

```python
transcript = client.audio.transcriptions.create(
    model="whisper-1",
    file=f,
    language="zh",
    prompt="以下是中文技术访谈。包含术语：LRU、HNSW、prompt caching、token、embedding、Cursor、Claude Code。",
)
```

prompt 给模型"语境"，**专业术语识别率提升 10–20%**。

### 2. 拆 zh-Hans / zh-Hant

Whisper 偶尔把简体写成繁体。后处理：

```python
import opencc

cc = opencc.OpenCC("t2s")   # 繁→简
text = cc.convert(transcript.text)
```

### 3. 标点

```python
# 让 LLM 重新加标点
client.chat.completions.create(
    model="claude-sonnet-4-6",
    messages=[{
        "role": "user",
        "content": f"重新加标点（不改字）：\n{transcript.text}",
    }],
)
```

Whisper 的中文标点不够好，LLM 后处理一遍效果好。

## 六、和 GPT 4o 实时音频对比

GPT 4o-realtime（如支持）能直接对话音频：

```python
# OpenAI Realtime API
# 比 Whisper 更适合"实时对话"
# 但比 Whisper 贵
```

简单转录用 Whisper，**实时对话用 Realtime API**。

## 七、与国产 STT 对比

| STT | 中文识别率 | 价格 | 国内适配 |
| --- | --- | --- | --- |
| OpenAI Whisper | 95%+ | 中 | 走中转 |
| Azure Speech | 96%+ | 中高 | 走中转 |
| 阿里通义听悟 | 96%+ | 中 | 直连 |
| 讯飞星火 | 96%+ | 中 | 直连 |
| 自部署 Whisper | 95%+ | 0（电费） | 完全可控 |
| faster-whisper | 同上 | 0 | 速度更快 |

**国内中文场景**：

- 速度敏感 → 阿里 / 讯飞
- 全球语言 → Whisper API
- 数据敏感 → 自部署 faster-whisper

## 八、自部署 Whisper

```bash
pip install faster-whisper
```

```python
from faster_whisper import WhisperModel

model = WhisperModel("large-v3", device="cuda", compute_type="float16")

segments, info = model.transcribe(
    "speech.mp3",
    language="zh",
    initial_prompt="中文技术访谈...",
)

for seg in segments:
    print(f"[{seg.start:.1f}-{seg.end:.1f}] {seg.text}")
```

`faster-whisper` 比官方 Whisper 快 4 倍，质量相同。RTX 3090 实时速度。

## 九、说话人分离（diarization）

Whisper 本身不分说话人。**pyannote.audio**：

```python
from pyannote.audio import Pipeline
pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1")
diarization = pipeline("speech.wav")

# 合并 Whisper segment + diarization
for seg in diarization.itertracks(yield_label=True):
    # seg: (start, end, speaker_id)
    ...
```

输出：

```
[Speaker 0] 你好今天讨论...
[Speaker 1] 我觉得这个问题...
[Speaker 0] 那么...
```

适合访谈 / 会议转录。

## 十、UI 实战：上传 + 进度

```ts
async function transcribe(file: File) {
  const total = file.size;
  const chunks = await splitAudio(file, 10 * 60);   // 10 分钟一段

  const results: string[] = [];
  for (let i = 0; i < chunks.length; i++) {
    setProgress(i / chunks.length);
    const form = new FormData();
    form.append("file", chunks[i]);
    form.append("language", "zh");
    const res = await fetch("/api/transcribe", { method: "POST", body: form });
    const { text } = await res.json();
    results.push(text);
  }
  return results.join("\n");
}
```

服务端转发到中转。

## 十一、应用场景

- 会议转录
- 视频字幕生成
- 客服质检
- 播客转文字
- 中英翻译流水线（Whisper → LLM 翻译）

## 十二、相关阅读

- [OpenAI SDK base_url 国内配置实战](/blog/openai-sdk-base-url-cn/)
- [Python 异步并发调用 LLM API](/blog/python-async-llm-client/)
- [用 AI API 做高质量翻译的工程化流程](/blog/ai-translation-workflow/)
- [LLM Vision API 国内对比](/blog/llm-vision-api-comparison/)

需要 Whisper + Chat 一把 Key 通用的中转？[YoTradeApi](https://yotradeapi.com) 同时支持 `audio/transcriptions` 与 `chat/completions` 端点。
