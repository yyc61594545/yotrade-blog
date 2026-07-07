---
title: 从零开始用 Claude 聊天的 5 分钟教程
description: 不懂技术也能看懂：5 分钟从"没用过 Claude"到"跑通第一次对话"，附网页版和 API 两种最快路径，以及避坑提醒。
keywords:
  - Claude 新手教程
  - 怎么用 Claude
  - Claude 5分钟入门
  - Claude 聊天教程
  - Claude 国内使用教程
pubDate: '2026-07-07'
updatedDate: '2026-07-07'
canonical: https://blog.yotradeapi.com/blog/cn-claude-zero-to-chat-tutorial/
tags:
  - 小白入门
  - Claude
  - 新手教程
category: 小白入门
heroImage: ../../assets/blog-placeholder-2.jpg
---

如果你完全没用过 Claude，只想知道"最快多久能开始聊天"，答案是：**5 分钟以内**。本文不讲复杂的账号体系和三种访问方案的利弊对比（那部分内容看 [Claude 国内直接访问最新方法](/blog/cn-claude-cn-direct-access-2026/)），只给一条最短路径，跟着做就能在 5 分钟内发出第一条消息、收到第一次回复。

## 一、Claude 是什么，值不值得花这 5 分钟

Claude 是 Anthropic 开发的大语言模型系列，目前主力版本是 Claude Sonnet 5、Claude Opus 4.8。它的口碑集中在几点：

- **写作和长文本理解**：处理长文档、总结、改写的效果在业内公认靠前
- **代码能力**：Claude Code、以及被大量 IDE 插件（Cursor、Windsurf 等）默认集成
- **更"听话"**：对复杂指令的遵循度和格式控制通常优于同代竞品

如果你只是想写点文案、读论文摘要、写代码调试，花 5 分钟跑通第一次对话，之后就知道这工具适不适合长期用。

## 二、开始之前要想清楚一件事：走哪条路

国内用户用 Claude 主要卡在两点：**claude.ai 官网不对中国大陆开放**，**订阅 Pro 需要海外信用卡**。这两个障碍决定了新手最快的路径不是去官网注册，而是通过**支持人民币付款的 API 中转服务**直接调用模型——不用海外手机号，不用海外信用卡，跳过所有网络和支付的坑。

本文按这条最快路径走。如果你已经有海外网络和支付方式、想用官网完整的 Projects、文件上传等功能，另外两种方案看上面链接的对比文章。

## 三、5 分钟计时表

| 时间点 | 要做的事 |
| --- | --- |
| 0–1 分钟 | 打开 [YoTradeApi](https://yotradeapi.com) 官网，用邮箱注册 |
| 1–2 分钟 | 人民币充值（支持支付宝/微信），拿到 API Key |
| 2–3 分钟 | 打开一个免费的网页聊天界面，填入 Key 和中转地址 |
| 3–5 分钟 | 发送第一条消息，看到 Claude 回复 |

下面按这个顺序展开每一步。

## 四、第一步：注册拿 Key（1 分钟）

打开 [YoTradeApi](https://yotradeapi.com)，邮箱注册后进入控制台，点"创建 API Key"，复制生成的 Key（通常以 `sk-` 开头）。这一步和注册普通网站账号没有区别，不需要手机号验证、不需要信用卡。

充值走支付宝或微信，到账后余额按调用量（token 数）实时扣减，用多少扣多少，不是固定月费订阅——这也是它比官方 Pro 订阅更适合"先试试看"的原因之一。

## 五、第二步：选一个聊天界面（1 分钟）

拿到 Key 之后，你有两条路可以开始聊天：

**路径 A：桌面客户端（推荐纯新手）**

下载 Cherry Studio 或 NextChat 这类开源聊天客户端，在设置里把"API 地址"改成中转服务提供的地址，把"API Key"填成刚才拿到的 Key，模型选 Claude 系列。详细图文步骤看 [Cherry Studio 配置教程](/blog/cherry-studio-cn-config/)。这条路径界面友好，跟微信聊天窗口差不多，最适合完全不写代码的人。

**路径 B：直接用代码调用（适合会写几行 Python 的人）**

如果你想更快、或者以后要把 Claude 接入自己的程序，直接用几行代码调用 API 更直接。见下一节。

## 六、第三步：用代码跑通第一次对话（2 分钟）

如果选择路径 B，装好 `anthropic` 或 `openai` 官方 SDK 后（两者协议兼容，看你习惯用哪个），几行代码就能跑通：

```python
from openai import OpenAI

client = OpenAI(
    api_key="你的Key",
    base_url="https://api.yotradeapi.com/v1",  # 中转地址，控制台可查
)

response = client.chat.completions.create(
    model="claude-sonnet-5",
    messages=[{"role": "user", "content": "用一句话介绍你自己"}],
)

print(response.choices[0].message.content)
```

运行后几秒内就能看到 Claude 的回复文字打印出来，这就算跑通了。如果你对"为什么这里用的是 OpenAI 的 SDK 却能调用 Claude"感到疑惑，这是因为中转服务把接口协议统一成了 OpenAI 兼容格式，方便已经写过 OpenAI 代码的人直接切换，具体原理看 [OpenAI 兼容协议 vs Anthropic 原生协议](/blog/openai-compatible-vs-anthropic-protocol/)。

## 七、发完第一条消息之后：三个常见问题

**Q1：应该用哪个 Claude 模型？**

新手不用纠结，日常聊天、写作用 Claude Sonnet 5 性价比最高；遇到特别复杂的推理任务（长代码重构、多步骤分析）再切换到 Opus 4.8。两者差价不小，先用便宜的跑起来，不够用再升级。

**Q2：会不会一不小心花很多钱？**

按 token 计费的模式下，个人日常聊天通常一个月几块到几十块人民币就够用。如果担心失控，控制台里可以设置余额上限和用量告警，详细的预算控制方法看 [每月 150 元预算怎么用好 AI 工具](/blog/cn-ai-tool-budget-150-rmb/)。

**Q3：Key 泄露了怎么办？**

不要把 Key 直接写进公开代码仓库或分享截图。一旦怀疑泄露，第一时间去控制台重置 Key，应急处理步骤看 [API Key 泄露应急处理指南](/blog/api-key-leak-emergency-response/)。

## 八、跑通之后，下一步可以做什么

第一次对话成功只是起点。接下来常见的进阶方向：

- 把 Claude 接入自己的小工具或脚本，参考 [Python 异步调用大模型完整指南](/blog/python-async-llm-client/)
- 想要更像 ChatGPT 网页版的多轮对话体验，用 [Open WebUI 搭建自己的对话界面](/blog/open-webui-cn-setup/)
- 想用 Claude 写代码而不只是聊天，看 [Claude Code 入门指南](/blog/claude-code-getting-started/)

## 九、相关阅读

- [Claude 国内直接访问最新方法（2026）](/blog/cn-claude-cn-direct-access-2026/)
- [Cherry Studio 配置教程](/blog/cherry-studio-cn-config/)
- [OpenAI 兼容协议 vs Anthropic 原生协议](/blog/openai-compatible-vs-anthropic-protocol/)
- [每月 150 元预算怎么用好 AI 工具](/blog/cn-ai-tool-budget-150-rmb/)
- [Claude Code 入门指南](/blog/claude-code-getting-started/)

不想折腾海外手机号和信用卡，[YoTradeApi](https://yotradeapi.com) 支持人民币充值，5 分钟拿到 Key 直接开始和 Claude 聊天。
