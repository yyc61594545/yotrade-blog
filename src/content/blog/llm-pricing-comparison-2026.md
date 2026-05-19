---
title: 2026 LLM 价格对比与选型决策
description: 2026 年 Claude、GPT、Gemini、Grok 各模型的输入/输出/缓存价格对比，含按工作流的成本估算与省钱选型决策树。
keywords:
- llm 价格 对比
- claude 价格 2026
- gpt-5 价格
- gemini 价格
- llm 成本 选型
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/llm-pricing-comparison-2026/
tags:
- 价格对比
- 成本
- 选型
- '2026'
category: 模型评测
heroImage: ../../assets/blog-placeholder-3.jpg
---

# 2026 LLM 价格对比与选型决策

LLM 一年价格能变三次。本文记录 2026 年中各旗舰模型的相对价格，给出按工作流的成本估算与决策树。**所有数字以相对值呈现**，绝对值随官方调整，请到各家定价页核对。

## 一、旗舰模型相对价格

以 Claude Opus 4.7 输入价为 100 单位：

| 模型 | 输入 | 输出 | 缓存命中 | 上下文 |
| --- | --- | --- | --- | --- |
| Claude Opus 4.7 | 100 | 100 | 10 | 200k / 1M |
| Claude Sonnet 4.6 | 20 | 25 | 2 | 200k |
| Claude Haiku 4.5 | 8 | 12 | 0.8 | 200k |
| GPT-5 | 70 | 75 | 35 | 400k |
| GPT-5 mini | 14 | 18 | 7 | 200k |
| Gemini 2.5 Pro | 50 | 65 | 12 | 2M |
| Gemini 2.5 Flash | 5 | 15 | 1 | 1M |
| Gemini 2.5 Flash-Lite | 2 | 7 | 0.4 | 1M |
| Grok 4 | 60 | 90 | -- | 256k |
| Grok Code Fast | 15 | 30 | -- | 256k |

## 二、按 1k tokens 成本（相对）

| 模型 | 1k 输入 | 1k 输出 | 1k 缓存输入 |
| --- | --- | --- | --- |
| Opus 4.7 | $0.015 | $0.075 | $0.0015 |
| Sonnet 4.6 | $0.003 | $0.015 | $0.0003 |
| Haiku 4.5 | $0.0008 | $0.004 | $0.00008 |
| GPT-5 | $0.0125 | $0.05 | $0.00625 |
| GPT-5 mini | $0.0025 | $0.01 | $0.00125 |
| Gemini 2.5 Pro | $0.00125 | $0.005 | $0.000125 |
| Gemini 2.5 Flash | $0.000075 | $0.0003 | -- |

*仅作相对比较，绝对值以官方为准。

## 三、日常工作流的真实成本

### 工作流 1：个人 Cursor 用户

- 日均 200 次对话
- 平均输入 5k tokens、输出 800 tokens
- 缓存命中率 60%

| 模型方案 | 日成本 | 月成本 |
| --- | --- | --- |
| 纯 Opus 4.7 | $20 | $600 |
| 纯 Sonnet 4.6 | $4 | $120 |
| Sonnet + Haiku 分级 | $2.5 | $75 |
| GPT-5 + GPT-5 mini | $5 | $150 |

**结论**：纯个人开发，Sonnet + Haiku 分级是甜蜜点。

### 工作流 2：Claude Code 长任务

- 平均任务 1 小时
- 单任务消耗 50k 输入 + 5k 输出
- 缓存命中率 80%

| 模型 | 单任务成本 |
| --- | --- |
| Opus 4.7 | $1.0 |
| Sonnet 4.6 | $0.2 |
| Opus（无缓存） | $4.5 |

**结论**：缓存是关键。开缓存后 Opus 也不贵。

### 工作流 3：批量分类 / 摘要

- 10k 条数据
- 单条输入 1k、输出 200 tokens

| 模型 | 总成本 |
| --- | --- |
| Sonnet 4.6 | $60 |
| Haiku 4.5 | $14 |
| GPT-5 mini | $40 |
| Gemini Flash | $5 |
| Gemini Flash-Lite | $2 |

**结论**：批量任务用 Gemini Flash 系列性价比最高。

### 工作流 4：RAG 系统

- 1000 次提问
- 每次输入 8k（含 5k 检索内容）、输出 500
- embedding 1M tokens

| 模型 | 总成本 |
| --- | --- |
| Sonnet 4.6 + 3-large emb | $35 |
| Haiku 4.5 + 3-small emb | $12 |
| Gemini Pro + 3-small emb | $15 |

**结论**：成本敏感的 RAG 用 Haiku + small embedding。

## 四、选型决策树

```
你的主要工作流？

A. AI 编程代理（Cursor / Claude Code / Cline）
   ├── 日常 → Sonnet 4.6
   ├── 重任务 → Opus 4.7（短时间）
   └── 快查 → Haiku 4.5

B. 批量数据处理
   ├── 简单分类 → Gemini Flash-Lite
   ├── 复杂分析 → Gemini Flash 或 Haiku
   └── 长上下文 → Gemini Pro

C. RAG / 知识库
   ├── embedding → text-embedding-3-large
   ├── 生成 → Sonnet 4.6 / GPT-5
   └── rerank → 看场景

D. 多模态
   ├── 单图 OCR → Gemini Flash
   ├── 多图对比 → Gemini Pro
   └── 视频 → Gemini Pro

E. 推理 / 数学
   └── Grok 4 / Gemini Pro

F. 高频聊天界面
   └── Haiku / Flash / GPT-5-mini
```

## 五、被低估的省钱杠杆

### 1. Prompt Caching（杠杆 5x）

详见 [prompt caching 省成本指南](/blog/prompt-caching-cost-optimization/)。命中率 80% 能让长 prompt 任务成本下降 70%+。

### 2. 模型分级（杠杆 3x）

不要全部走 Opus。L1/L2/L3 三级模型按任务难度切，总成本能压到 1/3。

### 3. 上下文裁剪（杠杆 2–5x）

`.cursorignore` 排除 node_modules 等大目录，平均上下文从 50k 降到 15k。

### 4. 限制 Subagent 并发（杠杆 1.5x）

并发跑 5 个 subagent 在很多场景没有 5 倍价值，但 5 倍开销实打实。

### 5. 关闭无意义的 MCP（杠杆 1.2x）

每个 MCP 添加 5–8k system prompt 开销。只开当前任务需要的。

## 六、不要在这些事上"省"

- ❌ 用差很多的模型省小钱（质量损失更贵）
- ❌ 关闭流式输出（体验下降但成本不变）
- ❌ 反复手工裁剪上下文（人力成本大于 token 成本）
- ❌ 强行用 fine-tune 替代 prompt（除非任务非常稳定）

## 七、月预算管理建议

| 角色 | 建议月预算 |
| --- | --- |
| 个人学习 | $5–15 |
| 个人项目 | $20–50 |
| 个人重度 | $50–200 |
| 小团队（5 人） | $200–800 |
| 中等团队（20 人） | $800–3000 |
| Background Agent 长跑 | 单独预算 $50+ |

设置中转后台日上限，超额触发告警。

## 八、相关阅读

- [Claude Sonnet 4.6 与 Opus 4.7 怎么选](/blog/claude-sonnet-4-6-vs-opus-4-7/)
- [Claude vs GPT vs Gemini 国内开发者怎么选](/blog/claude-vs-gpt-vs-gemini-cn-developer/)
- [AI 编程代理成本控制实战](/blog/ai-coding-agent-cost-control/)
- [prompt caching 在国内中转下省成本指南](/blog/prompt-caching-cost-optimization/)

价格持续变动，建议在 [YoTradeApi](https://yotradeapi.com) 后台查看实时价格表与你的实际消费。
