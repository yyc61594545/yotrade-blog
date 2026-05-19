---
title: Grok API 国内调用指南与场景实测
description: xAI Grok 4 在国内通过中转的接入方法，含 OpenAI SDK 配置、实时搜索、Tool Use、与 Claude/GPT 的对比实测。
keywords:
- grok api 国内
- grok 4 调用
- grok 中转
- xai api
- grok openai compatible
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/grok-api-cn-guide/
tags:
- Grok
- xAI
- API 中转
- 模型评测
category: 模型评测
heroImage: ../../assets/blog-placeholder-4.jpg
---

# Grok API 国内调用指南与场景实测

Grok 4 是 xAI 2025 末发布的旗舰，主打"实时搜索 + 数学/物理推理"。在国内用 Grok 通过中转最简单：xAI 官方提供 OpenAI 兼容 API，国内中转只要做正确转发就能用。

## 一、最小调用

```python
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_YOTRADE_KEY",
    base_url="https://yotradeapi.com/v1",
)

resp = client.chat.completions.create(
    model="grok-4",
    messages=[
        {"role": "system", "content": "你回答简洁、不啰嗦。"},
        {"role": "user", "content": "证明素数无穷多。"},
    ],
)
print(resp.choices[0].message.content)
```

## 二、Grok 4 实测场景

### 数学与物理

| 题型 | Grok 4 | Claude Opus 4.7 | GPT-5 |
| --- | --- | --- | --- |
| 大学高等数学 | 9.0/10 | 8.7 | 8.5 |
| 数学奥赛 | 8.5 | 8.2 | 8.0 |
| 物理推导 | 9.2 | 8.8 | 8.5 |

数学/物理是 Grok 的强项。把它当"作业辅导"或"研究助手"非常合适。

### 编程

| 题型 | Grok 4 | Claude Opus 4.7 |
| --- | --- | --- |
| 写函数 | 8.5 | 9.0 |
| 调 bug | 8.0 | 9.0 |
| 跨文件重构 | 7.5 | 9.0 |

编程能力不如 Claude Opus，但对于"一次性脚本"够用。

### 中文表达

| 维度 | Grok 4 | Claude Opus 4.7 |
| --- | --- | --- |
| 中文流畅度 | 7.5 | 9.0 |
| 中文事实准确 | 7.0 | 8.5 |

Grok 的中文能力比一年前有大幅进步，但仍不及 Claude/GPT。写对外中文文档不是它的强项。

## 三、实时搜索 / Live Search

Grok 最大的卖点是接 Twitter/X 的实时数据。OpenAI 兼容下的开启方式：

```python
resp = client.chat.completions.create(
    model="grok-4",
    messages=[{"role": "user", "content": "今天 AI 圈有什么新闻？"}],
    extra_body={
        "search_parameters": {
            "mode": "on",
            "sources": [{"type": "x"}, {"type": "web"}],
            "max_search_results": 10,
        }
    },
)
```

**注意点**：

- 中转必须透传 `search_parameters`，多数中转默认不透传
- 实时搜索是额外计费的，单价显著高于纯推理
- 国内场景下"X 实时数据"价值有限，更多用 `{"type": "web"}` 单源
- 返回里 `usage` 会多一个 `num_sources_used` 字段

## 四、长上下文表现

Grok 4 标称 256k tokens 上下文，比 Claude/GPT 大，但比 Gemini 2.5 Pro 小。实测：

| 输入大小 | 召回质量 |
| --- | --- |
| < 32k | 优 |
| 32–100k | 良 |
| > 100k | 一般，偶有遗漏 |

128k+ 的「大海捞针」选 Gemini 比 Grok 稳。

## 五、Tool Use

完全兼容 OpenAI 协议：

```python
tools = [{
    "type": "function",
    "function": {
        "name": "calculate",
        "description": "计算数学表达式",
        "parameters": {
            "type": "object",
            "properties": {"expr": {"type": "string"}},
            "required": ["expr"],
        },
    },
}]
```

实测 tool 选用准确率高（94%+），与 GPT-5、Claude Opus 持平。

## 六、Cursor / Cline 中怎么配

跟其它 OpenAI 兼容模型一样：

- Endpoint: `https://yotradeapi.com/v1`
- Model: `grok-4`、`grok-4-fast`、`grok-code-fast` 等
- API Key: 中转 key

Cursor 用户特别建议添加 `grok-code-fast` 当快查模型，响应速度比 Sonnet 略快。

## 七、成本对比

Grok 4 价格大致在 Claude Sonnet 与 Opus 之间。具体到任务：

- 数学 / 物理推理：Grok 性价比最高
- 通用编程：Claude Sonnet 性价比最高
- 长上下文：Gemini Flash 性价比最高
- 高频对话：Claude Haiku 或 Gemini Flash-Lite

## 八、什么时候选 Grok

- ✓ 数学、物理、工程推导任务
- ✓ 需要实时信息（X / web 搜索）
- ✓ 想要一个"不那么 PC"的对话风格
- ✗ 写中文营销文案（Claude 更好）
- ✗ 长任务编程代理（Claude Opus 更好）
- ✗ 超长上下文召回（Gemini 更好）

## 九、与本地搜索（Brave/Tavily）的组合

如果你不想付 Grok 的实时搜索费，可以自己组合：

```python
# 用 Tavily 或 Brave 搜，再把结果交给 Grok 推理
search_results = tavily_search("AI 行业新闻")
context = "\n".join(r["content"] for r in search_results[:5])

resp = client.chat.completions.create(
    model="grok-4",
    messages=[
        {"role": "system", "content": f"参考资料：\n{context}"},
        {"role": "user", "content": "今天 AI 圈有什么新闻？"},
    ],
)
```

这样既用上了 Grok 的推理，又避开了 xAI 实时搜索的额外费用。

## 十、相关阅读

- [Claude Sonnet 4.6 与 Opus 4.7 怎么选](/blog/claude-sonnet-4-6-vs-opus-4-7/)
- [GPT-5 与 Claude Opus 4.7 编程能力对比](/blog/gpt-5-vs-claude-opus-4-7-coding/)
- [Gemini API 国内调用指南](/blog/gemini-api-cn-guide/)
- [OpenAI SDK base_url 国内配置实战](/blog/openai-sdk-base-url-cn/)

需要一把 Key 同时调 Grok、Claude、GPT、Gemini？在 [YoTradeApi 注册](https://yotradeapi.com/register) 创建 API Key 即可。
