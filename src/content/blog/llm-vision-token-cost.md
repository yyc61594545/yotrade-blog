---
title: 多模态 LLM 图片 token 计费详解：省钱的关键参数
description: 深入解析 Claude、GPT-4o、Gemini 的图片 token 计算规则，对比不同分辨率、压缩策略的实际成本，附省钱技巧与计费陷阱。
keywords:
  - LLM 图片 token
  - 多模态计费
  - GPT-4o 图片费用
  - Claude 视觉 token
  - Gemini 图片计费
  - 多模态成本优化
pubDate: '2026-06-03'
updatedDate: '2026-06-03'
canonical: https://blog.yotradeapi.com/blog/llm-vision-token-cost/
tags:
  - 多模态
  - token计费
  - 成本优化
  - 视觉API
  - 技术深度
category: 技术深度
heroImage: ../../assets/blog-placeholder-3.jpg
---

把图片传给 LLM，费用怎么算？这个问题比文字 token 复杂得多，因为不同模型、不同分辨率、不同压缩模式对应的计费规则差异悬殊。一张 4K 截图和一张压缩后的缩略图，价格可能相差 10 倍以上。

本文系统梳理主流多模态 LLM（Claude、GPT-4o、Gemini）的图片计费机制，给出每种场景下的成本估算方式，以及可以立刻用上的省钱策略。

## 一、为什么图片计费更复杂

文字 token 的计算相对直观：大约 1 个汉字 = 1-2 个 token，1 个英文单词 = 1-2 个 token，总体可以通过分词器预估。

图片则不同。模型需要先把图片转换为一组"图像 token"（也叫 image patches），这个过程取决于：

- **图片原始分辨率**：越大，tiles/patches 越多
- **模型的处理模式**：high-detail vs low-detail（OpenAI 命名）、standard vs high（部分 API 区分）
- **图片内容密度**：有些模型会自适应调整 patch 数量

理解这些参数，是控制成本的前提。

## 二、OpenAI GPT-4o 图片计费规则

OpenAI 的图片计费分两个模式：

### low detail 模式

固定消耗 **85 token**，不管图片多大。适合只需要粗略判断图片内容的场景（如"这张图是否包含人脸"）。

```python
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": image_url, "detail": "low"}},
            {"type": "text", "text": "描述这张图片"}
        ]
    }]
)
```

### high detail 模式（默认）

计算规则：
1. 图片缩放到 **2048×2048** 以内（保持比例）
2. 按短边缩放到 **768px**
3. 将图片切成 **512×512** 的 tiles
4. 每个 tile = **170 token**，固定底数 **85 token**

**示例计算**：

| 原始尺寸 | 处理后尺寸 | Tiles 数量 | Token 消耗 |
|---------|-----------|-----------|-----------|
| 512×512 | 512×512 | 1 | 170 + 85 = 255 |
| 1024×1024 | 768×768 | 4 | 4×170 + 85 = 765 |
| 1920×1080 | 1365×768 | 6 | 6×170 + 85 = 1105 |
| 3840×2160（4K）| 2048×1152 | 8 | 8×170 + 85 = 1445 |

4K 截图在 high detail 模式下消耗约 1445 token，按 GPT-4o 输入 $2.5/1M token 计算，单张图片约 $0.0036——听起来不多，但如果一次请求包含 20 张图，就是 $0.07，批量处理时成本会快速累积。

## 三、Claude 图片计费规则

Anthropic 的计费逻辑和 OpenAI 类似，但参数略有不同。

Claude 的图片处理规则（以 Claude Sonnet 为例）：

1. 图片最大支持 **8000×8000**（但实际建议不超过 2000px 宽）
2. 图片按照 **750px×750px** 的 tiles 切割
3. 每个 tile 约 **1500-1600 token**（不同版本略有差异）

**Claude 图片 token 估算公式**：

```
tiles = ceil(width/750) × ceil(height/750)
tokens ≈ tiles × 1600
```

**示例**：

| 图片尺寸 | Tiles | 估算 Token |
|---------|-------|-----------|
| 750×750 | 1 | ~1600 |
| 1500×1500 | 4 | ~6400 |
| 1500×750 | 2 | ~3200 |
| 3000×2000 | 12 | ~19200 |

Claude 的图片 token 消耗明显高于 GPT-4o（因为每个 tile 对应更多 token），但 Claude 的视觉理解质量通常也更高。

**实际费用参考**（Claude Sonnet 4.6，输入 $3/1M token）：

- 750×750 普通截图：~1600 token ≈ $0.0048
- 1920×1080 高清截图：~4800 token ≈ $0.014
- 3000×2000 高分辨率图：~19200 token ≈ $0.058

## 四、Gemini 图片计费规则

Google Gemini 的计费相对简单透明：

- 每张图片固定消耗 **258 token**（Gemini 1.5 系列）
- 不区分图片大小，单张图片统一收费
- Gemini 2.0 Flash 的图片 token 消耗可能不同，需查阅最新文档

这种固定计费对大图片非常友好，但小图片（如图标、缩略图）则相对不划算。

**三家对比**（以 1920×1080 图片为例，估算值）：

| 模型 | 图片 Token | 输入单价 | 单张成本 |
|------|-----------|---------|---------|
| GPT-4o（high）| ~1105 | $2.5/1M | ~$0.003 |
| Claude Sonnet 4.6 | ~4800 | $3/1M | ~$0.014 |
| Gemini 1.5 Flash | 258（固定）| $0.075/1M | ~$0.00002 |

Gemini 的图片成本极低，适合大批量图片处理场景；Claude 的图片理解精度最高，但成本也最高；GPT-4o 在成本和能力间取得了较好平衡。

## 五、省钱技巧：图片预处理是关键

### 技巧 1：降低分辨率再传入

对于大多数任务（OCR、内容分类、UI 截图分析），图片不需要原始分辨率。把图片预处理到合适大小再发送：

```python
from PIL import Image
import io, base64

def compress_image(image_path, max_width=1024):
    img = Image.open(image_path)
    if img.width > max_width:
        ratio = max_width / img.width
        new_size = (max_width, int(img.height * ratio))
        img = img.resize(new_size, Image.LANCZOS)
    
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=85)
    return base64.b64encode(buffer.getvalue()).decode()
```

将 4K 截图压缩到 1024px 宽，GPT-4o 的 token 消耗从 1445 降到约 425，节省约 70%。

### 技巧 2：对简单任务使用 low detail

如果只是判断图片类别、检测是否包含特定元素，`detail: "low"` 的 85 token 远胜 high detail 的 1000+ token：

```python
# 只判断图片是否包含表格，不需要 high detail
{"type": "image_url", "image_url": {"url": url, "detail": "low"}}
```

### 技巧 3：裁剪感兴趣区域

如果只需要分析图片的某个区域（如截图中的某个表单），先裁剪再发送：

```python
from PIL import Image

img = Image.open('screenshot.png')
# 只裁剪左上角的表单区域
cropped = img.crop((0, 0, 800, 600))
cropped.save('cropped.jpg', quality=85)
```

### 技巧 4：批量任务用 Gemini

如果任务不需要最高质量（内容审核、图片分类、批量 OCR），Gemini Flash 的成本极低，是批量处理的首选。只在需要精细理解时才切换到 Claude 或 GPT-4o。

### 技巧 5：避免重复传相同图片

在多轮对话中，如果需要反复引用同一张图片，部分 API 支持缓存（如 Claude 的 prompt caching）。把图片放在 system prompt 中并开启 cache_control，后续对话不会重复计费：

```python
# Claude prompt caching for images
messages = [{
    "role": "user",
    "content": [
        {
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": image_b64},
            "cache_control": {"type": "ephemeral"}  # 启用缓存
        },
        {"type": "text", "text": "分析这张架构图的主要组件"}
    ]
}]
```

## 六、计费陷阱：常见误区

**误区 1：以为图片大小不影响费用**

很多开发者直接把原始截图传入 API，没意识到分辨率直接影响 token 数量。一个月后看账单才发现成本失控。

**误区 2：多图片 × 多轮对话**

如果每轮对话都带着 5 张图片，每次对话的图片 token 都会重新计费（除非使用 prompt caching）。10 轮对话 × 5 张图 × 1000 token = 50000 token，只是图片就花了 $0.125（Claude Sonnet 价格）。

**误区 3：Gemini 固定计费不代表可以无限传大图**

虽然 Gemini 计费固定，但超大图片仍然受 API 的尺寸限制，且处理时间会更长，影响响应速度。

**误区 4：忘记输出 token 的成本**

对于需要详细描述图片内容的场景，输出 token 有时比输入的图片 token 更贵（输出价格通常是输入的 3-5 倍）。控制输出长度同样重要。

## 七、实际场景成本估算工具

以下是一个简单的 Python 成本计算脚本，可以在项目中用于预估费用：

```python
import math
from PIL import Image

def estimate_gpt4o_tokens(width, height, detail='high'):
    if detail == 'low':
        return 85
    
    # 缩放到 2048 以内
    max_dim = 2048
    if width > max_dim or height > max_dim:
        ratio = min(max_dim/width, max_dim/height)
        width, height = int(width*ratio), int(height*ratio)
    
    # 短边缩放到 768
    short_side = min(width, height)
    if short_side > 768:
        ratio = 768 / short_side
        width, height = int(width*ratio), int(height*ratio)
    
    tiles = math.ceil(width/512) * math.ceil(height/512)
    return tiles * 170 + 85

def estimate_claude_tokens(width, height):
    tiles = math.ceil(width/750) * math.ceil(height/750)
    return tiles * 1600

# 示例：1920×1080 截图
w, h = 1920, 1080
gpt4o_tokens = estimate_gpt4o_tokens(w, h)
claude_tokens = estimate_claude_tokens(w, h)

print(f"GPT-4o: {gpt4o_tokens} tokens (≈${gpt4o_tokens * 2.5 / 1_000_000:.5f})")
print(f"Claude Sonnet: {claude_tokens} tokens (≈${claude_tokens * 3 / 1_000_000:.5f})")
```

## 八、相关阅读

- [LLM 主流模型价格对比 2026](/blog/llm-pricing-comparison-2026/)
- [LLM 视觉 API 横向对比](/blog/llm-vision-api-comparison/)
- [Prompt Caching 成本优化指南](/blog/prompt-caching-cost-optimization/)
- [LLM 成本优化检查清单](/blog/llm-cost-optimization-checklist/)

如果你需要在国内无需代理地调用 GPT-4o、Claude 等多模态模型的视觉 API，[YoTradeApi](https://yotradeapi.com) 提供稳定的中转接入，支持图片 base64 和 URL 两种传入方式。
