---
title: 用 AI API 做高质量翻译的工程化流程
description: 用 Claude / GPT / Gemini 做中英翻译的实战流程：模型选择、术语表、上下文保持、回译验证、批量处理与质量评估。
keywords:
- ai 翻译
- claude 翻译
- gpt 翻译
- ai 翻译 工作流
- 机器翻译 质量
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/ai-translation-workflow/
tags:
- 翻译
- AI 应用
- 工程实战
- Python
- 用例
category: 工程实战
heroImage: ../../assets/blog-placeholder-5.jpg
---

# 用 AI API 做高质量翻译的工程化流程

AI 翻译比传统机翻准确度高一个量级，但要做到"上线级别"还有不少工程化工作。本文给一份完整流程，覆盖模型选择、术语表、上下文、回译验证、批量处理。

## 一、模型选择

| 任务 | 推荐 |
| --- | --- |
| 通用中英翻译 | Claude Sonnet 4.6 |
| 高质量营销文案翻译 | Claude Opus 4.7 |
| 技术文档翻译 | Claude Sonnet 4.6 / GPT-5 |
| 批量低成本 | Gemini Flash 或 GPT-5 mini |
| 小语种 | Claude 系列（多语言强） |
| 视频字幕 | Claude Haiku + 后处理 |

**Claude 系列在中英翻译上特别强**——文风自然、术语准确。

## 二、最小翻译 prompt

```python
from openai import OpenAI

client = OpenAI(api_key="sk-yo-...", base_url="https://yotradeapi.com/v1")

def translate(text, source="en", target="zh"):
    resp = client.chat.completions.create(
        model="claude-sonnet-4-6",
        messages=[
            {"role": "system", "content": f"你是专业翻译。把 {source} 翻译成 {target}。保持原意，自然流畅，不解释。"},
            {"role": "user", "content": text},
        ],
        temperature=0.3,
    )
    return resp.choices[0].message.content
```

简单但够 80% 场景用。

## 三、加术语表

```python
def translate_with_glossary(text, glossary):
    glossary_str = "\n".join(f"- {k} → {v}" for k, v in glossary.items())
    resp = client.chat.completions.create(
        model="claude-sonnet-4-6",
        messages=[
            {
                "role": "system",
                "content": f"""你是专业翻译。把英文翻译成中文。

# 术语表（必须严格使用以下译法）
{glossary_str}

# 要求
- 自然流畅
- 不解释、不加注释
- 保留 markdown 格式（代码块、链接、列表）
""",
            },
            {"role": "user", "content": text},
        ],
        temperature=0.3,
    )
    return resp.choices[0].message.content

glossary = {
    "prompt caching": "提示词缓存",
    "context window": "上下文窗口",
    "agent": "代理",
    "embedding": "向量嵌入",
}
```

术语表是把"AI 翻译"提升到"专业翻译"的最关键一步。**通用模型不会自动用你公司的标准译法**。

## 四、保持上下文（长文档分段）

长文档拆段翻译时，每段独立调用会导致：

- 同一术语前后不一致
- 代词指代丢失
- 语境断裂

解决：**滑动窗口**

```python
def translate_long(paragraphs, glossary, window=2):
    results = []
    for i, p in enumerate(paragraphs):
        # 前 window 个段落的原文 + 译文作为上下文
        ctx = []
        for j in range(max(0, i - window), i):
            ctx.append(f"原文：{paragraphs[j]}\n译文：{results[j]}")
        ctx_str = "\n\n".join(ctx)

        prompt = f"""# 上文（原文 + 已有译文）
{ctx_str}

# 现在翻译这段
{p}
"""
        results.append(translate_with_glossary(prompt, glossary))
    return results
```

## 五、回译验证

简单粗暴但有效的质量检查：

```python
def back_translate_check(source_en, translation_zh):
    back = translate(translation_zh, source="zh", target="en")
    # 用 embedding 算相似度
    e1 = embed(source_en)
    e2 = embed(back)
    return cosine_sim(e1, e2)
```

阈值经验：

- > 0.92：质量优
- 0.85–0.92：可用
- < 0.85：可能漂移，需要人工审

## 六、批量并发

100 段并发：

```python
import asyncio
from openai import AsyncOpenAI

aclient = AsyncOpenAI(api_key="sk-yo-...", base_url="https://yotradeapi.com/v1")

async def translate_async(text, glossary):
    glossary_str = "\n".join(f"- {k} → {v}" for k, v in glossary.items())
    resp = await aclient.chat.completions.create(
        model="claude-haiku-4-5",
        messages=[
            {"role": "system", "content": f"翻译。术语：{glossary_str}"},
            {"role": "user", "content": text},
        ],
    )
    return resp.choices[0].message.content

async def batch(texts, glossary, concurrency=10):
    sem = asyncio.Semaphore(concurrency)
    async def one(t):
        async with sem:
            return await translate_async(t, glossary)
    return await asyncio.gather(*[one(t) for t in texts])

results = asyncio.run(batch(texts, glossary, concurrency=10))
```

详见 [Python 异步并发调用 LLM API](/blog/python-async-llm-client/)。

## 七、保留 Markdown / HTML 格式

需要明确写在 system prompt：

```
保留：
- 代码块 ``` 内的内容不要翻译
- HTML 标签（<a> <strong> 等）保持
- markdown 链接 [text](url) 的 url 不动，text 翻译
- 内联 `code` 不要翻译
- frontmatter（--- 之间）按字段处理：title/description 翻译，slug/date 不动
```

## 八、专业领域微调 prompt

针对不同领域：

### 技术文档

```
你是技术文档翻译。
- 代码示例不动
- 术语使用业界标准译法
- 命令、参数、文件路径保留原文
- 风格简洁，不啰嗦
```

### 营销文案

```
你是营销文案翻译。
- 不直译，要意译
- 保持品牌调性
- 文化适配（节日、习语本地化）
- 输出 3 个版本供选择
```

### 法律文档

```
你是法律翻译。
- 严格忠实原文，不增删
- 法律术语用标准译法
- 不修改条款结构
- 不确定的地方明确标记 [?]
```

## 九、字幕翻译特例

字幕需要保留时间戳：

```srt
1
00:00:01,000 --> 00:00:03,000
Hello, welcome to our channel.

2
00:00:04,000 --> 00:00:07,000
Today we're talking about...
```

只翻译文本行：

```python
import re

def translate_srt(srt_text, glossary):
    blocks = srt_text.strip().split("\n\n")
    out = []
    for block in blocks:
        lines = block.split("\n")
        if len(lines) >= 3:
            idx, ts = lines[0], lines[1]
            text = "\n".join(lines[2:])
            translated = translate_with_glossary(text, glossary)
            out.append(f"{idx}\n{ts}\n{translated}")
    return "\n\n".join(out)
```

## 十、成本估算

| 任务 | 模型 | 文档大小 | 估算成本 |
| --- | --- | --- | --- |
| 1 万字技术文章 | Sonnet 4.6 | 8k tokens | $0.20 |
| 1 万字技术文章 | Haiku 4.5 | 8k tokens | $0.05 |
| 1 万字营销文案 | Opus 4.7 | 8k tokens | $1.00 |
| 1 本书（10 万字） | Sonnet 4.6 | 80k tokens | $2.00 |
| 100 集字幕 | Haiku 4.5 | 50k tokens | $0.30 |

加上 caching 还能再降 60%。

## 十一、与 DeepL / Google Translate 的对比

| 维度 | LLM 翻译 | DeepL | Google Translate |
| --- | --- | --- | --- |
| 文风 | 优 | 良 | 中 |
| 术语遵循 | 优（可注入术语表） | 中 | 弱 |
| 上下文 | 优 | 中 | 弱 |
| 速度 | 中 | 快 | 极快 |
| 价格 | 中 | 中 | 低 |
| 适合 | 高质量、专业 | 通用 | 速查 |

## 十二、相关阅读

- [Claude vs GPT vs Gemini 国内开发者怎么选](/blog/claude-vs-gpt-vs-gemini-cn-developer/)
- [OpenAI SDK base_url 国内配置实战](/blog/openai-sdk-base-url-cn/)
- [Python 异步并发调用 LLM API](/blog/python-async-llm-client/)
- [prompt caching 在国内中转下省成本指南](/blog/prompt-caching-cost-optimization/)

需要批量翻译稳定的中转 + 同 Key 调多家模型？[YoTradeApi](https://yotradeapi.com/register) 一把 Key 调 Claude / GPT / Gemini 全家，按场景切。
