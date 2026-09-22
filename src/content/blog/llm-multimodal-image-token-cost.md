---
title: 图片输入的 token 计费机制
description: 图片输入并不是按 JPEG 或 PNG 文件字节直接计费。本文拆解视觉模型如何缩放图片、切成 tile 或 patch、应用模型倍率并换算 billable token，比较 OpenAI、Anthropic 与 Gemini 当前机制差异，给出规则版本化、usage 回填、批量请求监控、成本预估和账单核对的工程方法。
keywords:
  - 图片输入 token 计费
  - Vision API 成本
  - 多模态 token 计算
  - image token 估算
  - 视觉模型成本控制
pubDate: '2026-09-14'
updatedDate: '2026-09-14'
canonical: https://blog.yotradeapi.com/blog/llm-multimodal-image-token-cost/
tags:
  - 多模态
  - Image Token
  - 成本工程
  - 技术深度
category: 技术深度
---

把一张 5 MB 的图片压缩到 500 KB，API 费用会降低十倍吗？通常不会。视觉模型的计费依据不是网络传输字节，而是图片经过缩放、切块后得到的 image token。压缩格式主要影响上传耗时；像素尺寸、细节等级、模型规则和同一请求中的图片数量，才更直接影响 token。

仓库已有文章介绍过常见视觉模型的基础用法与早期规则，本文不再重复厂商横评，而是解决一个更工程化的问题：怎样把“原图”转换为“可预估、可观测、可对账”的成本记录。以下规则依据 2026 年 9 月 14 日三家官方文档核对，实际接入时仍应以所选模型当日文档与响应中的 usage 为准。

## 一、先把传输大小和视觉 token 分开

图片请求至少经过三个不同维度：文件字节、像素矩阵和视觉 token。JPEG quality 从 95 降到 80，可能显著减少字节，但宽高不变时，按 patch 或 tile 计算的 token 可能完全不变。反过来，把 4000×3000 缩到 1000×750，即使仍保存为 PNG，也可能减少模型要处理的视觉单元。

| 变量 | 主要影响 | 是否通常直接决定 image token |
|---|---|---|
| 文件格式与压缩率 | 上传带宽、延迟、清晰度 | 否 |
| 图片宽高 | patch/tile 数量 | 是 |
| detail/media resolution | 内部缩放与预算 | 是 |
| 图片张数 | 总输入规模 | 是 |
| 输出长度 | output token | 与图片输入分开 |

因此优化顺序应是：先保证任务所需的可读性，再裁剪无关区域并调整分辨率，最后才优化编码质量。过度压缩导致小字模糊，虽然上传更快，却可能增加重试次数，反而抬高总成本。

## 二、两类主流换算：patch 与 tile

patch 机制把缩放后的图片覆盖成规则小块，常见形式是：

```text
patches = ceil(width / patch_size) × ceil(height / patch_size)
billable_image_tokens = ceil(patches × model_multiplier)
```

若像素或 patch 数超过模型预算，服务端通常会先按比例缩小，再计算覆盖数量。OpenAI 当前官方文档显示，不同模型与 detail 组合可能采用 32×32 patch，也可能走 tile 规则，因此不能拿一个 GPT 模型的常数套到所有模型。

tile 机制则常由“基础 token + 分块 token”组成：图片先按规则缩放，再用固定大小方块覆盖。低细节模式可能只收固定基础量，高细节模式则随覆盖 tile 数增长。两种机制的共同点是存在阶梯：宽度只多一个像素，也可能跨过块边界，多出一整列视觉单元。

## 三、三家规则不能用同一公式

OpenAI 的[图片与视觉官方文档](https://developers.openai.com/api/docs/guides/images-vision)同时列出了 patch 型和 tile 型规则，并按模型给出 detail 行为、预算与倍率。工程上必须把 `model + snapshot + detail` 当成计费规则的联合主键，而不是只保存供应商名称。

Anthropic 的[视觉官方文档](https://platform.claude.com/docs/en/build-with-claude/vision)目前以 28×28 像素 patch 表达视觉 token，并说明超过对应模型原生分辨率或视觉 token 上限时会缩放。不同分辨率层级的长边与 token 上限不同，所以旧的“宽×高除以固定数”只能视作特定版本的近似，不能永久写死。

Google 的[图片理解官方文档](https://ai.google.dev/gemini-api/docs/image-understanding)说明，小图与大图采用不同处理方式，大图会切为 tile；新模型还可通过 `media_resolution` 控制分配给每张图片的 token 上限。由此可见，“Gemini 每张图永远固定 token”同样不是安全假设。

## 四、预估器要版本化，不要只写一个函数

可靠的预估器应输出区间和计算过程，而不是伪装成精确账单。建议建立规则表，字段至少包括 provider、model、effective_date、detail、resize_limit、patch_or_tile_size、base_tokens、multiplier 与文档 URL。规则变化时新增版本，不覆盖历史行。

伪代码可以保持简单：

```python
def estimate_image(rule, width, height):
    w, h = rule.resize(width, height)
    units = rule.coverage_units(w, h)
    return rule.base_tokens + rule.apply_multiplier(units)
```

调用前记录原始尺寸和所选模式，调用后用响应 usage 回填实际输入 token。由于 usage 往往包含文字、图片、工具结果等全部输入，若 API 不提供按模态拆分，就用“相同文字、不含图片”的基线请求做抽样差值，而不要假设总 input token 全来自图片。

## 五、多轮和批量请求是最容易漏算的地方

单张图片估算正确，不代表月账单正确。多轮对话若每次重发历史图片，传输与上下文消耗会重复发生；一次批量请求包含多张图时，总 image token 是每张图处理结果的累加，还要加文字输入与输出 token。

应用层应为每次调用记录 `request_id`、模型快照、图片数量、每张处理后尺寸、细节等级、输入与输出 usage、重试次数。重试必须有幂等标识，否则网络超时后再次提交，业务只看到一个结果，账单却可能出现两次有效推理。

预算告警也不要只看平均值。截图尺寸具有长尾分布，一批超长网页截图可能突然跨过多个 tile 阶梯。更有用的监控是每任务 P50/P95 image token、每成功任务成本，以及图片 token 占总输入的比例。

## 六、降低成本要从任务分辨率出发

粗粒度分类、主体识别和颜色判断通常不需要高分辨率；票据小字、UI 坐标、密集表格与图表则需要保留细节。可以先用低分辨率完成分流，只对不确定样本或感兴趣区域做高分辨率二次调用。

裁剪往往比压缩更有效：去掉浏览器空白、聊天侧栏和无关页边，既减少视觉单元，也降低模型被干扰的概率。对文档批处理，先判断能否直接提取原生文本；只有布局、图表或扫描页需要视觉理解时再传图片。

最终要用自己的任务集做质量—成本曲线。分别测试两到三个分辨率档位，记录正确率、拒答率、延迟和实际 usage，选满足质量门槛的最低档。模型名字不能替代这一步。

## 七、相关阅读

- [多模态 LLM 图片 token 计费详解：省钱的关键参数](/blog/llm-vision-token-cost/)
- [LLM Vision API 国内调用对比：Claude / GPT-5 / Gemini](/blog/llm-vision-api-comparison/)
- [LLM Token 计算完整指南：tiktoken / Anthropic / 中文](/blog/token-counting-cn-guide/)
- [LLM Token 成本台账怎么设计](/blog/llm-token-cost-ledger/)

如果你需要在一个成本台账里统一观察不同模型的输入与输出用量，[YoTradeApi](https://yotradeapi.com) 可提供统一的 API 接入方式，便于集中记录 usage 并执行模型路由。
