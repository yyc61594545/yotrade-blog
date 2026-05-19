---
title: 为什么你的 AI 编程效果"越用越差"
description: 用 AI 编程一段时间后效果退化的 6 个真正原因：上下文膨胀、依赖蔓延、模式僵化、缓存失效、模型版本变化、prompt 漂移。
keywords:
- ai 编程 效果 下降
- claude 越来越笨
- cursor 不好用
- ai 编程 问题
- 提示词 退化
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/why-ai-coding-getting-worse/
tags:
- 故障排查
- 性能退化
- 最佳实践
- 思考
category: 最佳实践
heroImage: ../../assets/blog-placeholder-5.jpg
---

# 为什么你的 AI 编程效果"越用越差"

很多人都有这种感受：刚开始用 Cursor / Claude Code 神奇得很，几个月后越用越觉得"AI 变笨了"。其实模型没变，**变的是你的项目和工作流**。本文拆 6 个真正原因。

## 一、上下文膨胀

刚开始项目 100 个文件，AI 自动检索准；半年后 1000 个文件，AI 检索的"相关文件"里夹了 80% 噪音。

**修复**：

- 用 `.cursorignore` / `.aiderignore` 排除生成代码、文档、资源
- @ 显式指定，少依赖 @codebase 自动
- 大目录拆 monorepo workspace

## 二、依赖蔓延 + 风格不一致

每次 AI 写代码引入一个新依赖、用一种新风格，半年后项目有 5 种状态管理库、3 种错误处理模式、混乱的命名。

AI 看到混乱代码，**自然产出更混乱**。

**修复**：

- 一次性清理：列所有依赖、去重、统一风格
- `.cursorrules` 加严格的 "禁止引入新依赖" 条款
- 团队 review 时严抓"引入新依赖" 的 PR

## 三、Rules 文件过期

半年前写的 `.cursorrules` 列了用 Next.js 13、jest 28、CSS Modules。现在项目早升级了，Rules 没更新。

AI 按过期的 rules 出代码 → 你觉得"AI 不懂项目"。

**修复**：

- 每个 milestone 后 review rules 文件
- 大依赖升级时同步更新 rules
- 记录"学到的教训"段，持续追加

## 四、Prompt Caching 失效

Claude / GPT 缓存 5-10 分钟。**如果你的 system prompt 频繁变化**（哪怕一个字），缓存命中率会下降，**响应变慢、成本上升**。

可能的原因：

- system prompt 里嵌入了时间戳 / 随机 id
- 工具列表频繁增减
- 历史对话压缩策略不稳定

**修复**：

- system prompt 保持稳定
- 变化的内容放到 user message 末尾
- 检查 `cache_read_input_tokens` 命中率

## 五、模型版本悄悄变了

OpenAI / Anthropic 的模型名 `claude-sonnet-4-6` 指向的实际后端可能变。同样的 prompt 输出可能微妙不同。

**修复**：

- 用具体版本号（`claude-sonnet-4-6-20250915`）而非 alias
- 维护回归 benchmark
- 怀疑模型变化时跑评估对比

详见 [LLM 评估实战](/blog/llm-evaluation-cn-guide/)。

## 六、Prompt 模式僵化

你最初的 prompt 是为某个版本的模型调优的。模型升级后，**老 prompt 反而不适合**。

例子：

- 老模型需要 "step by step" 引导，新模型默认就会
- 老模型 tool call 不稳，老 prompt 用了一堆"如果工具失败"逻辑
- 老模型上下文 64k 时代写的"精简"指令，对 200k 已经过度

**修复**：

- 模型升级时 review 现有 prompt 是否还合适
- 试着删一些"看起来必要的指令"，看效果
- 用最少 prompt 测试基线

## 七、第七个隐藏原因：你

刚开始用 AI 时新鲜感拉满，每次 prompt 都认真写。久了**懒了**，prompt 越写越随便，期待越来越模糊。AI 输出变差不是它的锅。

**修复**：

- 复杂任务正经写 prompt
- 用 prompt 模板
- 把"懒"承认了，恢复纪律

## 八、综合自检清单

效果退化时按这个排：

- [ ] `.cursorrules` / `CLAUDE.md` 多久没更新？
- [ ] `.cursorignore` 有没有更新？
- [ ] 项目是否引入了过多新依赖？
- [ ] system prompt 是否包含动态变化内容？
- [ ] 模型版本是否固定？
- [ ] 你的 prompt 是否变得越来越随便？
- [ ] 当前任务的上下文是否过大？
- [ ] 中转是否换过 / 异常？

## 九、跑一次"基线测试"

写 5 个标准任务：

1. 写一个 fibonacci 函数
2. 修一个明确 bug
3. 写一组单元测试
4. 重构一段代码
5. 写一段文档

用同一个 prompt 模板跑（不带任何项目 rules / 历史）。

- 如果**基线表现正常** → 项目问题（清理上下文）
- 如果**基线也差** → 中转 / 模型问题（换模型或换中转）

## 十、长期可持续的工作流

为了避免重复退化：

- **每月一次 audit**：rules、依赖、prompt 模板
- **每季度一次 benchmark**：回归测试
- **每半年一次"刷新"**：项目知识重写一遍
- **持续学习**：模型升级时跟着调整

## 十一、相关阅读

- [.cursorrules 最佳实践](/blog/cursor-rules-best-practices/)
- [Cline Rules 与 Memory Bank](/blog/cline-rules-and-memory-bank/)
- [AI 编程的 12 个常见错误与避坑指南](/blog/ai-coding-mistakes-to-avoid/)
- [LLM 评估实战](/blog/llm-evaluation-cn-guide/)
- [prompt caching 在国内中转下省成本指南](/blog/prompt-caching-cost-optimization/)
- [AI Agent Prompt Engineering 中文实战](/blog/agent-prompt-engineering-cn/)

用稳定的中转 + 固定版本号能减少很多变量。[YoTradeApi](https://yotradeapi.com/register) 后台可以查每条请求的实际模型版本，便于排查。
