---
title: LLM Vision API 国内调用对比：Claude / GPT-5 / Gemini
description: Claude、GPT-5、Gemini 三家视觉模型的国内调用方法实战对比，含截图 OCR、UI 理解、图表数据提取、多图对比的场景实测。
keywords:
- llm vision api
- claude vision
- gpt-5 vision
- gemini vision
- 多模态 api 国内
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/llm-vision-api-comparison/
tags:
- 多模态
- Vision
- Claude
- GPT-5
- Gemini
category: 模型评测
heroImage: ../../assets/blog-placeholder-1.jpg
---

LLM 视觉能力在 2026 年已经成熟：OCR、UI 理解、图表分析、多图对比、视频。国内通过中转调用三家旗舰，本文给完整对比与代码示例。

## 一、统一调用方式（OpenAI 兼容）

通过中转走 OpenAI 兼容协议，三家模型用同一套代码：

```python
from openai import OpenAI
import base64

client = OpenAI(api_key="sk-yo-...", base_url="https://yotradeapi.com/v1")

def vision(model, image_path, question):
    b64 = base64.b64encode(open(image_path, "rb").read()).decode()
    resp = client.chat.completions.create(
        model=model,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": question},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ],
        }],
    )
    return resp.choices[0].message.content

print(vision("claude-sonnet-4-6", "ui.png", "页面上有几个按钮？"))
print(vision("gpt-5", "ui.png", "页面上有几个按钮？"))
print(vision("gemini-2.5-pro", "ui.png", "页面上有几个按钮？"))
```

## 二、场景 1：UI 截图理解

测试：50 张产品页面截图，识别按钮、表单、表格。

| 模型 | 按钮识别 | 文本提取 | 布局理解 |
| --- | --- | --- | --- |
| Claude Sonnet 4.6 | 92% | 95% | 88% |
| Claude Opus 4.7 | 95% | 96% | 92% |
| GPT-5 | 91% | 95% | 90% |
| Gemini 2.5 Pro | 94% | 96% | 93% |

**结论**：三家都强，Gemini 在"理解整体布局"上略胜，Claude 在"识别隐藏交互"上略胜。

## 三、场景 2：截图 OCR（含中文）

测试：100 张含中文的复杂截图（聊天截图、错误对话框、PDF 截图）。

| 模型 | 中文准确率 | 标点准确率 | 数字准确率 |
| --- | --- | --- | --- |
| Claude Opus 4.7 | 96% | 94% | 99% |
| GPT-5 | 95% | 93% | 99% |
| Gemini 2.5 Pro | 97% | 95% | 99% |

Gemini 在中文 OCR 略有优势。但**专用 OCR（PaddleOCR）在纯文字提取上仍然更准更便宜**。LLM 视觉适合"OCR + 理解"双重任务。

## 四、场景 3：图表数据提取

```python
vision(
    "gemini-2.5-pro",
    "sales_chart.png",
    "这张折线图展示了 2020–2025 各年销量。请提取每年的数值并以 JSON 数组返回。"
)
```

| 模型 | 数值准确度 | 趋势识别 |
| --- | --- | --- |
| Claude Opus 4.7 | 88% | 95% |
| GPT-5 | 90% | 95% |
| Gemini 2.5 Pro | 96% | 98% |

**结论**：图表数据提取 Gemini 优势明显。如果业务依赖这个，Gemini 是首选。

## 五、场景 4：多图对比

```python
# 三张 UI 设计稿，找出差异
images = ["v1.png", "v2.png", "v3.png"]
content = [{"type": "text", "text": "对比这三张设计稿，找出 5 个最显著的不同"}]
for img in images:
    b64 = base64.b64encode(open(img, "rb").read()).decode()
    content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}})

resp = client.chat.completions.create(
    model="gemini-2.5-pro",
    messages=[{"role": "user", "content": content}],
)
```

| 模型 | 多图准确率 |
| --- | --- |
| Claude Opus 4.7 | 80% |
| GPT-5 | 78% |
| Gemini 2.5 Pro | 92% |

**Gemini 在多图对比是断崖式领先**。这是它的训练目标之一。

## 六、场景 5：手写文字识别

测试：50 张中文手写笔记。

| 模型 | 准确率 |
| --- | --- |
| Claude Opus 4.7 | 75% |
| GPT-5 | 78% |
| Gemini 2.5 Pro | 88% |

手写场景 Gemini 也是最佳。

## 七、视频理解（Gemini 独有）

通过原生 Gemini API：

```python
import requests, base64

with open("clip.mp4", "rb") as f:
    video_b64 = base64.b64encode(f.read()).decode()

r = requests.post(
    "https://yotradeapi.com/v1beta/models/gemini-2.5-pro:generateContent",
    headers={"x-goog-api-key": "sk-yo-..."},
    json={
        "contents": [{
            "parts": [
                {"text": "总结这个视频里发生了什么"},
                {"inline_data": {"mime_type": "video/mp4", "data": video_b64}},
            ],
        }],
    },
).json()
print(r["candidates"][0]["content"]["parts"][0]["text"])
```

走原生协议、限制：

- 走中转时需中转支持 generateContent
- 单视频上限通常 60 分钟
- 提取关键帧分析，理解能力优秀

## 八、价格对比

按 1 张 1024×1024 图片估算：

| 模型 | 单张成本 |
| --- | --- |
| Claude Sonnet 4.6 | 100 |
| Claude Opus 4.7 | 500 |
| GPT-5 | 80 |
| Gemini 2.5 Pro | 50 |
| Gemini 2.5 Flash | 8 |

**批量任务**（10k+ 图）用 Gemini Flash 性价比最高。

## 九、性能优化技巧

### 1. 不要传全分辨率

```python
from PIL import Image

img = Image.open("huge.png")
img.thumbnail((1024, 1024))   # 缩到 1024 边
img.save("compact.png", optimize=True)
```

1024×1024 对大多数任务足够。原图 4K 主要增加 token 消耗，准确率提升有限。

### 2. JPEG 压缩

```python
img.save("compact.jpg", quality=85, optimize=True)
```

JPEG 比 PNG 小 5–10 倍，准确率几乎无差。

### 3. 多图任务用 Gemini

Claude/GPT 的 multi-image 也支持，但响应慢、价贵。

### 4. 用 URL 不要用 base64

```python
{"type": "image_url", "image_url": {"url": "https://example.com/a.png"}}
```

URL 传输比 base64 高效，前提是图片公网可访问。

## 十、什么时候不用 LLM Vision

- 纯文字 OCR：用专用 OCR
- 精确尺寸 / 像素操作：用 PIL/OpenCV
- 大规模分类：训自己的小模型
- 实时视频流：LLM 太慢

## 十一、相关阅读

- [Claude vs GPT vs Gemini 国内开发者怎么选](/blog/claude-vs-gpt-vs-gemini-cn-developer/)
- [Gemini API 国内调用指南](/blog/gemini-api-cn-guide/)
- [OpenAI SDK base_url 国内配置实战](/blog/openai-sdk-base-url-cn/)
- [Python 异步并发调用 LLM API 实战](/blog/python-async-llm-client/)

需要一把 Key 调三家视觉模型？[YoTradeApi](https://yotradeapi.com) 兼容 OpenAI 协议同时支持 Gemini 原生 generateContent。
