---
title: Gemini API 国内调用指南（含 2.5 Pro / Flash）
description: Gemini 2.5 Pro / Flash 在国内通过 OpenAI 兼容中转的接入方法，含 SDK、长上下文、Vision、Tool Use 与成本对比。
keywords:
- gemini api 国内
- gemini 2.5 pro
- gemini flash
- google gemini 中转
- gemini openai compatible
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/gemini-api-cn-guide/
tags:
- Gemini
- Google
- 长上下文
- API 中转
- 模型评测
category: 模型评测
heroImage: ../../assets/blog-placeholder-3.jpg
---

# Gemini API 国内调用指南（含 2.5 Pro / Flash）

Gemini 2.5 系列的杀手锏是**超长上下文**——2M tokens 的输入窗口，远超 Claude 与 GPT。但在国内直连 Google AI Studio 一直是大坎，需要走中转。本文按"为什么要用 Gemini → 怎么接 → 怎么用好"三段展开。

## 一、Gemini 2.5 现在能干什么

| 模型 | 上下文 | 强项 | 适合场景 |
| --- | --- | --- | --- |
| `gemini-2.5-pro` | 2M | 推理 + 长上下文 | 大文档分析、代码库理解 |
| `gemini-2.5-flash` | 1M | 速度 + 性价比 | 高频请求、批量处理 |
| `gemini-2.5-flash-lite` | 1M | 极快 | 分类、摘要、初筛 |

「2M tokens」是什么概念：

- 一本 300 页的技术书完整塞进去还有 30% 余量
- 几乎所有中小型开源项目可以一次性灌入
- 上千张图片一次性分析

## 二、最小调用：OpenAI 兼容路径

通过中转走 OpenAI 兼容协议是最简单的：

```python
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_YOTRADE_KEY",
    base_url="https://yotradeapi.com/v1",
)

resp = client.chat.completions.create(
    model="gemini-2.5-pro",
    messages=[
        {"role": "system", "content": "你是一个严谨的代码评审。"},
        {"role": "user", "content": "评审这段代码：def f(x): return x+1"},
    ],
    stream=True,
)
for chunk in resp:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

这里**只换 model 字符串就行**。其它 SDK 写法和调用 Claude/GPT 完全一致。

## 三、长上下文实战：让 Gemini 看懂整个代码仓库

Gemini 的核心价值场景：

```python
import pathlib

def collect_repo(root, exts=(".py", ".ts", ".md")):
    parts = []
    for p in pathlib.Path(root).rglob("*"):
        if p.is_file() and p.suffix in exts:
            content = p.read_text(errors="ignore")
            parts.append(f"=== {p} ===\n{content}\n")
    return "\n".join(parts)

repo = collect_repo("./my-project")
print(f"total chars: {len(repo)}")  # 一般 200k-1.5M chars 都可以塞进 2M token

resp = client.chat.completions.create(
    model="gemini-2.5-pro",
    messages=[
        {"role": "system", "content": "你是经验丰富的架构师。"},
        {"role": "user", "content": f"以下是项目全部代码。请回答：\n\n{repo}\n\n问题：函数 process_packet 被哪些地方调用？参数有什么演化？"},
    ],
)
print(resp.choices[0].message.content)
```

这种「一次塞整个仓库」的能力是 Claude/GPT 200k 上下文做不到的。Gemini 适合做"代码考古"、"重构前的总体分析"这类一次性深度任务。

## 四、Vision 多模态

Gemini 在多图片同时处理上表现突出：

```python
import base64

images = []
for p in ["a.png", "b.png", "c.png"]:
    b64 = base64.b64encode(open(p, "rb").read()).decode()
    images.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}})

resp = client.chat.completions.create(
    model="gemini-2.5-pro",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "对比这三张截图，找出 UI 上的不同。"},
            *images,
        ],
    }],
)
print(resp.choices[0].message.content)
```

Gemini 在「多图对比」"图表理解"两个场景有明显优势。对于纯视觉问答，Claude/GPT-5 也不弱。

## 五、Tool Use（函数调用）

OpenAI 兼容下：

```python
tools = [{
    "type": "function",
    "function": {
        "name": "search_docs",
        "description": "搜索内部文档",
        "parameters": {
            "type": "object",
            "properties": {"q": {"type": "string"}, "top_k": {"type": "integer"}},
            "required": ["q"],
        },
    },
}]

resp = client.chat.completions.create(
    model="gemini-2.5-pro",
    messages=[{"role": "user", "content": "查一下我们公司的 RAG 接入文档。"}],
    tools=tools,
    tool_choice="auto",
)
print(resp.choices[0].message.tool_calls)
```

Gemini Flash 系列的 tool call 速度极快（< 1s），适合做 agent 路由层。

## 六、什么时候用 Pro / Flash / Flash-Lite

| 任务 | 推荐 |
| --- | --- |
| 整个仓库一次性分析 | Pro |
| 推理 + 长上下文 | Pro |
| 高频对话（聊天界面） | Flash |
| 批量分类 / 摘要 / 翻译 | Flash 或 Flash-Lite |
| Agent 路由层 | Flash-Lite |
| 视觉 OCR | Pro |

成本对比（相对值）：

| 模型 | 输入 | 输出 |
| --- | --- | --- |
| Pro | 100 | 100 |
| Flash | 8 | 25 |
| Flash-Lite | 2 | 8 |

**Flash 系列性价比极高**。如果你的任务是大批量调用，Flash 经常比 GPT-5-mini、Claude Haiku 更便宜。

## 七、Cursor / Cline / Aider 里怎么配

### Cursor

设置 → Models → 添加 Custom Model：

```
Name: gemini-2.5-pro
ID: gemini-2.5-pro
Endpoint: https://yotradeapi.com/v1
API Key: sk-yo-...
```

### Cline

API Provider: OpenAI Compatible
Model ID: `gemini-2.5-pro`

### Aider

```bash
aider --model openai/gemini-2.5-pro
```

注意：Aider 默认 `--map-tokens 1024`，对 Gemini 2M 上下文来说太小，可以放心拉到 8192。

## 八、走原生 Gemini API（高级）

如果中转支持原生 `generateContent` 端点：

```python
import requests

r = requests.post(
    "https://yotradeapi.com/v1beta/models/gemini-2.5-pro:generateContent",
    headers={"x-goog-api-key": "sk-yo-..."},
    json={
        "contents": [{"parts": [{"text": "解释 LRU 缓存"}]}],
        "generationConfig": {"maxOutputTokens": 256},
    },
).json()
print(r["candidates"][0]["content"]["parts"][0]["text"])
```

原生协议的优势：

- 可以用 Gemini 独有特性（grounding、search retrieval、code execution）
- 更精细的 generation config

劣势：现有 SDK 改造成本高。除非确定要用独家功能，**默认走 OpenAI 兼容路径**。

## 九、常见报错

| 报错 | 原因 |
| --- | --- |
| `400 invalid request` | 上下文超过 2M tokens（实际限制略小于标称值） |
| `429 quota exceeded` | Gemini 全局限流，等几秒重试 |
| 输出突然为空 | 触发 safety filter，部分主题被拦截 |
| 多图调用 401 | 部分中转对 multi-image 的鉴权不一致 |

### Safety filter 怎么放宽

OpenAI 兼容下一般通过 `extra_body` 传：

```python
client.chat.completions.create(
    model="gemini-2.5-pro",
    messages=[...],
    extra_body={
        "safety_settings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
        ]
    },
)
```

是否生效取决于中转是否透传。如果中转后台不允许放宽 safety，需要换中转或换模型。

## 十、相关阅读

- [Claude Sonnet 4.6 与 Opus 4.7 怎么选](/blog/claude-sonnet-4-6-vs-opus-4-7/)
- [GPT-5 与 Claude Opus 4.7 编程能力对比](/blog/gpt-5-vs-claude-opus-4-7-coding/)
- [OpenAI SDK base_url 国内配置实战](/blog/openai-sdk-base-url-cn/)
- [Cursor API 中转怎么选](/blog/2026-05-15-cursor-api-relay-recommendation-2026/)
- [AI API 中转稳定性测试方法](/blog/ai-api-relay-stability-test/)

需要一把 Key 同时调 Gemini、Claude、GPT、Grok？在 [YoTradeApi 注册](https://yotradeapi.com/register) 创建 API Key 即可。
