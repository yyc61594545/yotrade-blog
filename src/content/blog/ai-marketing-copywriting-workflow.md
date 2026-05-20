---
title: 用 AI 写营销文案的实战工作流（中文场景）
description: 中文营销文案 AI 工作流：素材收集、用户调研、品牌调性、模板复用、A/B 测试、避免 AI 味的具体技巧。
keywords:
- ai 营销 文案
- ai 写文案
- claude 文案
- 中文 营销 ai
- ai 广告 文案
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/ai-marketing-copywriting-workflow/
tags:
- 营销
- 文案
- AI 应用
- 中文
- 工作流
category: 工程实战
heroImage: ../../assets/blog-placeholder-3.jpg
---

中文营销文案是 LLM 应用门槛最低、收益最大的场景之一。但写不好就是"AI 味十足的废话"。本文给一份能让甲方真用的工作流。

## 一、为什么直接让 AI 写不行

```
> 写一篇关于 X 产品的小红书种草文案
```

直接这样给 prompt，AI 输出：

```
🌟 姐妹们！今天我要安利一个超棒的好物 ❤️
最近爱上了这款 XX，简直惊艳到我了！
......（一堆套话）
```

问题：

- 套话密度高
- 没有具体卖点
- 文风通用（什么产品都能套）
- emoji 滥用

## 二、好文案的特征

| 维度 | 好文案 |
| --- | --- |
| 具体性 | 给数字、给场景 |
| 真实感 | 像真人写的 |
| 痛点共鸣 | 戳到用户 |
| 卖点突出 | 1-2 个核心点 |
| 行动指引 | 明确 CTA |

AI 要写出这种，**不是模型问题，是素材问题**。

## 三、工作流总览

```
1. 用户调研（人 + AI）
2. 收集素材（人）
3. 写大纲（人）
4. AI 出初稿
5. 人审 + 改
6. A/B 测试
7. 迭代
```

每步都有人介入。

## 四、用户调研 prompt

```
我有一个产品 [一句话描述]。
目标用户 [大致画像]。

请帮我：
1. 列出 5 个目标用户的具体画像（年龄、职业、生活场景）
2. 每个画像列 3 个核心痛点
3. 每个痛点配一个生活场景描述（不要"想象一下"，要具体）
4. 我们产品如何解决（具体到功能）

输出 markdown 表格。
```

这步是"用户洞察"。AI 不能替代真实调研，但能帮你**结构化思考**。

## 五、素材清单

写之前先有：

- ✓ 产品具体功能（截图也行）
- ✓ 用户真实故事（采访 / 评论里挖）
- ✓ 数据（销量、转化率、用户数）
- ✓ 同类产品文案（参考但不抄）
- ✓ 品牌词典（说什么不说什么）

**没素材让 AI 写 = 套话生成**。

## 六、品牌调性 prompt

```
# 品牌调性

## 风格关键词
- 简洁、技术、不浮夸
- 自嘲式幽默（适度）
- 数据导向

## 不允许
- 不用 "革命性 / 颠覆 / 极致 / 卓越"
- 不夸大效果
- 不用 emoji 装饰（除非真有意义）
- 不开头"在当今数字化时代..."

## 例文（学习风格）
[贴你过往优质文案 2 段]
```

让 AI 模仿你的调性，**不要每次从头解释**。

## 七、按平台分模板

不同平台风格差极大：

| 平台 | 风格 |
| --- | --- |
| 小红书 | 闺蜜推荐 + emoji + 短段 |
| 知乎 | 长文 + 数据 + 干货 |
| 微博 | 短、热点、话题 |
| 公众号 | 故事 + 干货混合 |
| 朋友圈 | 短 + 私域感 |
| X / Twitter | 短 + 单一观点 |
| LinkedIn | 专业 + 第一人称 |

每个平台一份模板，AI 按模板填。

## 八、文案 prompt 模板

```
# 任务
写一篇 [平台] 的 [类型] 文案。

# 产品
[产品名 + 一句话]

# 目标用户
[具体画像]

# 核心卖点
1. [卖点 1，配数据]
2. [卖点 2，配场景]

# 文风
[品牌调性模块]

# 结构
[H1 / H2 / 正文 / CTA 的位置]

# 长度
[X 字以内]

# 输出
直接产出，不解释
```

## 九、A/B 测试

让 AI 一次出 3 版：

```
出 3 个不同风格的版本：
- 版本 A：理性、数据驱动
- 版本 B：感性、故事驱动
- 版本 C：直接、痛点切入
每版 200 字内。
```

跑投放看哪个转化率高。

## 十、文案质量检查

```python
def check_quality(text):
    issues = []
    
    # AI 味关键词
    cliches = ["在当今", "数字化时代", "革命性", "颠覆", "极致", "卓越", "毋庸置疑", "众所周知", "让我们一起", "希望这对你有帮助"]
    for c in cliches:
        if c in text:
            issues.append(f"AI 味: {c}")
    
    # emoji 密度
    import re
    emoji_count = len(re.findall(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF☀-⛿✀-➿]', text))
    if emoji_count / len(text) * 100 > 5:
        issues.append("emoji 太多")
    
    # 套话句式
    patterns = ["让我们", "首先", "其次", "总而言之", "综上所述"]
    for p in patterns:
        if p in text:
            issues.append(f"套话句式: {p}")
    
    return issues
```

每篇过一遍，**有问题让 AI 重写**。

## 十一、用 LLM 互评

```python
critic_prompt = """
评价以下文案，1-10 分：
- 真实感（不像 AI 写的）
- 卖点突出（用户能记住）
- 文风一致（符合品牌）
- 长度合适
- 有具体行动指引

只输出分数 + 一句评语。

文案：
{copy}
"""

# 让另一个模型来评
score = client.chat.completions.create(
    model="gpt-5",  # 用不同家避免偏见
    messages=[{"role": "user", "content": critic_prompt.format(copy=text)}],
)
```

低分的让原模型重写。

## 十二、Few-shot 例子的力量

最好的提升方式不是改 prompt，**是给 AI 看你过去最好的几篇**：

```
# 学习这 3 篇优秀例文的风格
[例文 1]
[例文 2]
[例文 3]

# 现在写一篇关于 [新主题] 的，保持同样风格
```

Few-shot 比 zero-shot 质量提升 30%+。

## 十三、批量生产 + 人审

```python
def batch_generate(topics, template, style_examples):
    for topic in topics:
        draft = generate(topic, template, style_examples)
        issues = check_quality(draft)
        if issues:
            draft = rewrite(draft, issues)
        save_for_review(draft)
```

每天产 20 篇草稿，人审 5–10 分钟 / 篇，留好的发。

## 十四、避坑

- ❌ 上来就让 AI "写一篇文案"
- ❌ 用 emoji 大轰炸
- ❌ AI 写完直接发布不审
- ❌ 一个 prompt 包打天下（不同平台必须不同模板）
- ❌ 数字凭空编（投放被举报）

## 十五、模型选择

| 任务 | 推荐 |
| --- | --- |
| 重要对外文案 | Claude Opus 4.7 |
| 日常生产 | Claude Sonnet 4.6 |
| 批量初稿 | Haiku 4.5 |
| 翻译 | Sonnet（中→英） / Opus（英→中） |
| 改文（润色） | Sonnet |

**中文营销 Claude 系列最强**，详见 [Claude vs GPT vs Gemini](/blog/claude-vs-gpt-vs-gemini-cn-developer/)。

## 十六、相关阅读

- [用 AI 写 SEO 内容的工程化工作流](/blog/ai-content-seo-workflow/)
- [用 AI 做高质量翻译的工程化流程](/blog/ai-translation-workflow/)
- [Claude vs GPT vs Gemini 国内开发者怎么选](/blog/claude-vs-gpt-vs-gemini-cn-developer/)
- [Claude Sonnet 4.6 与 Opus 4.7 怎么选](/blog/claude-sonnet-4-6-vs-opus-4-7/)

[YoTradeApi](https://yotradeapi.com) 一把 Key 切换 Sonnet / Opus / Haiku，按平台和重要程度分模型。
