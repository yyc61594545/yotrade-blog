---
title: AI 图像生成 API 国内调用对比（GPT Image/DALL-E/Imagen/Flux）
description: OpenAI Images / Google Imagen / Black Forest Flux 等主流图像生成 API 在国内通过中转的接入对比与实战代码。
keywords:
- 图像生成 api
- dall-e api
- imagen api
- flux api
- ai 生图 国内
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/image-generation-api-cn/
tags:
- 图像生成
- DALL-E
- Imagen
- Flux
- API
category: 工程实战
heroImage: ../../assets/blog-placeholder-2.jpg
---

文本生图 API 这两年百花齐放。本文按场景对比国内可调用的主流模型，给完整代码。

## 一、主流模型

| 模型 | 厂商 | 强项 | 价格 |
| --- | --- | --- | --- |
| GPT Image-1 | OpenAI | 通用 + 文字渲染 | 中高 |
| DALL-E 3 | OpenAI（老） | 风格多 | 中 |
| Imagen 3 | Google | 真实照片 | 中 |
| Flux Pro 1.1 | Black Forest | 摄影级 | 中 |
| Flux Dev | Black Forest | 开源 | 自部署免费 |
| Stable Diffusion XL | StabilityAI | 开源 | 自部署 |
| Recraft V3 | Recraft | 设计图 / SVG | 中 |
| Ideogram 2 | Ideogram | 文字渲染 | 中 |

## 二、OpenAI Images（GPT Image-1）

```python
from openai import OpenAI
import base64

client = OpenAI(api_key="sk-yo-...", base_url="https://yotradeapi.com/v1")

resp = client.images.generate(
    model="gpt-image-1",
    prompt="一只赛博朋克风格的橘猫，坐在霓虹城市夜景中",
    size="1024x1024",
    quality="high",
    n=1,
)

img_b64 = resp.data[0].b64_json
with open("cat.png", "wb") as f:
    f.write(base64.b64decode(img_b64))
```

参数：

| 参数 | 选项 |
| --- | --- |
| size | 1024x1024 / 1024x1536 / 1536x1024 |
| quality | low / medium / high |
| n | 1–10 |

GPT Image-1 **特别强在文字渲染**——画带文字的海报很准。

## 三、图像编辑（同 endpoint）

```python
resp = client.images.edit(
    model="gpt-image-1",
    image=open("source.png", "rb"),
    mask=open("mask.png", "rb"),   # 可选
    prompt="把背景换成夕阳海滩",
)
```

`mask` 指定要改的区域（透明部分会被重画）。**类似 Photoshop 局部修改**。

## 四、Google Imagen 3

```python
import google.generativeai as genai

genai.configure(
    api_key="sk-yo-...",
    transport="rest",
    client_options={"api_endpoint": "https://yotradeapi.com"},
)

model = genai.ImageGenerationModel("imagen-3.0-generate-002")
result = model.generate_images(
    prompt="...",
    number_of_images=1,
    aspect_ratio="1:1",
)
result.images[0].save("out.png")
```

需要中转支持 Imagen 端点。**风格更"真实照片"**，适合产品图。

## 五、Black Forest Flux

```python
# 通过 OpenAI 兼容路径（看中转支持）
resp = client.images.generate(
    model="flux-pro-1.1",
    prompt="...",
    size="1024x1024",
)
```

或走 BFL 原生 API（中转转发）。

| 模型 | 适用 |
| --- | --- |
| flux-pro-1.1 | 摄影级，最贵 |
| flux-pro | 性价比 |
| flux-dev | 中等 |
| flux-schnell | 快速 |

**Flux 在写实人像上是当前最强**。

## 六、模型选择

| 场景 | 推荐 |
| --- | --- |
| 通用 + 带文字 | gpt-image-1 |
| 真实人像 / 摄影 | Flux Pro 1.1 |
| 设计图 / icon / 图标 | Recraft V3 |
| Logo / 海报（文字多） | gpt-image-1 / Ideogram |
| 大批量便宜 | Flux Schnell |
| 自部署 | SDXL / Flux Dev |

## 七、Prompt 最佳实践

### 1. 具体 > 模糊

❌ "一只猫"  
✓ "一只橘色长毛猫，绿眼睛，坐在木地板上，自然光，浅景深，35mm 镜头"

### 2. 风格关键词

```
photography / 35mm film / cinematic
oil painting / watercolor / sketch
3d render / cyberpunk / minimalist
```

### 3. 反向 prompt（部分模型支持）

```python
resp = client.images.generate(
    prompt="...",
    extra_body={"negative_prompt": "blurry, low quality, deformed hands"},
)
```

### 4. 用 LLM 优化 prompt

```python
optimized = client.chat.completions.create(
    model="claude-sonnet-4-6",
    messages=[{
        "role": "user",
        "content": f"把这个生图需求优化成专业的 prompt：\n{user_request}",
    }],
).choices[0].message.content

img = client.images.generate(prompt=optimized, ...)
```

## 八、自部署 Flux Dev

GPU 充足时：

```bash
docker run -p 7860:7860 --gpus all \
    ghcr.io/black-forest-labs/flux:latest
```

或用 ComfyUI / Diffusers。**24GB+ VRAM 才舒服**。

## 九、并发与限流

图生比文生贵 + 慢：

| 模型 | 单图耗时 | 单图价格 |
| --- | --- | --- |
| GPT Image high | 30s | $0.08 |
| Imagen 3 | 10s | $0.04 |
| Flux Pro | 15s | $0.05 |

并发处理：

```python
async def batch_generate(prompts):
    sem = asyncio.Semaphore(5)
    async def one(p):
        async with sem:
            return await aclient.images.generate(model="gpt-image-1", prompt=p, ...)
    return await asyncio.gather(*[one(p) for p in prompts])
```

## 十、内容安全

所有图生模型都有 safety filter：

- 暴力 / 仇恨 / 性内容直接拒
- 名人脸（部分模型）
- 商标 / IP

返回 400 + error message：

```python
try:
    resp = client.images.generate(...)
except OpenAIError as e:
    if "safety" in str(e):
        return "请求被内容安全策略拒绝"
```

## 十一、典型应用场景

- 博客 / 营销文案配图
- 电商商品场景图
- 游戏 / 应用 icon
- 头像 / avatar
- 概念设计 / 故事板
- 数据可视化辅助

## 十二、避坑

- ❌ 用人名要求"画 XXX 的样子"（IP 风险）
- ❌ 高质量 + 大批量（成本爆炸）
- ❌ 没设 max retries 撞 safety filter 无限重试
- ❌ 期待 100% 复现（每次生成都略有不同）
- ❌ 用图片对比"哪家最好"——同 prompt 不同模型出图风格差极大

## 十三、相关阅读

- [OpenAI SDK base_url 国内配置实战](/blog/openai-sdk-base-url-cn/)
- [Gemini API 国内调用指南](/blog/gemini-api-cn-guide/)
- [LLM Vision API 国内对比](/blog/llm-vision-api-comparison/)
- [Python 异步并发调用 LLM API](/blog/python-async-llm-client/)

需要支持 GPT Image / Imagen / Flux 多家的中转？[YoTradeApi](https://yotradeapi.com) 一把 Key 通调，按上面 SDK 代码接入。
