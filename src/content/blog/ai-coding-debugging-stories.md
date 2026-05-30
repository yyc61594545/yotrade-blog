---
title: AI 编程调试踩坑实录：那些让人哭笑不得的真实案例
description: 收录开发者用 AI 编程时遭遇的典型调试坑：幻觉 API、循环修复、上下文遗忘等，每个案例附带可操作的规避方法。
keywords:
  - AI编程踩坑
  - AI调试经验
  - Cursor调试案例
  - LLM编程错误
  - AI编程最佳实践
pubDate: '2026-05-30'
updatedDate: '2026-05-30'
canonical: https://blog.yotradeapi.com/blog/ai-coding-debugging-stories/
tags:
  - AI编程
  - 调试
  - 实战经验
  - 踩坑
category: 实战经验
heroImage: ../../assets/blog-placeholder-4.jpg
---

用 AI 写代码已经成为很多开发者的日常。但随着使用深入，一类新问题开始集中出现：**不是 AI 不够聪明，而是你不知道它会在哪里犯什么样的错**。

这篇文章收录了几类有代表性的真实调试场景（案例基于开发者社区的普遍反馈，细节已泛化处理），每个案例后面给出可操作的规避思路。

## 一、幻觉 API：代码跑起来才发现方法根本不存在

**场景**：让 AI 写一段调用某 SDK 的代码，代码看上去完全正确，IDE 也没报红，但一运行就报 `AttributeError: module 'xxx' has no attribute 'yyy'`。

**实际发生了什么**：AI 根据训练数据中的模式"推断"出一个合理的 API 名称，但这个方法要么从未存在，要么已在某次版本更新中被移除或重命名。

**典型例子**：

```python
# AI 生成的代码（看起来很合理）
response = client.chat.completions.create_with_retry(
    model="gpt-4o",
    messages=[...]
)

# 实际上 openai SDK 没有 create_with_retry，正确的是 create
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[...]
)
```

**规避方法**：

1. 调用第三方 SDK 时，让 AI 生成代码后**立刻查阅官方文档或 `help(module)` 输出**
2. 在 prompt 里指定版本号：`使用 openai Python SDK 1.x，不要使用已废弃的 API`
3. 对 AI 生成的每一个方法调用，做一次"这个方法名真的存在吗"的确认

## 二、循环修复陷阱：越改越乱

**场景**：代码有一个 Bug，让 AI 修复后又引入新问题，再让它修新问题，再引入另一个问题……几轮下来代码面目全非，原始逻辑也模糊了。

**为什么会这样**：

- AI 每次修复都是局部视角，不了解整体架构约束
- 上下文窗口里"错误代码"越来越多，AI 开始在错误假设上叠加修复
- 缺乏"恢复点"意识，没有对应的版本回退策略

**实战中常见的循环路径**：

```
Bug A → AI 修复 → Bug B（新问题）
→ AI 修复 Bug B → Bug A 复现 + Bug C（新问题）
→ AI 修复 → 代码结构崩坏
→ 开发者不知道从哪里开始
```

**规避方法**：

1. **先 git commit，再让 AI 改**：每次让 AI 修复前 commit 当前状态，出问题随时 `git checkout`
2. **限制修复范围**：不要说"修复这个问题"，而是说"只修改 `parseResponse` 函数，不要动其他部分"
3. **超过两轮未解决，换策略**：停止让 AI 继续修，改为让 AI 解释问题原因，自己来写修复
4. **贴错误堆栈而不是描述错误**：把完整的 `traceback` 给 AI，比"有时会崩"精确 10 倍

## 三、上下文遗忘：前面说好的约定后面全忘了

**场景**：在对话开头告诉 AI"这个项目使用 TypeScript strict 模式，所有函数必须有类型注释"，结果聊了二十条后，AI 生成的代码开始出现 `any` 类型，之前的约定全然不顾。

**为什么会这样**：

大语言模型的注意力机制在长对话中会对早期内容分配更少的权重。这不是 AI 的"记忆问题"，而是**上下文注意力的物理限制**。

**规避方法**：

1. **把关键约定写进 `.cursorrules` 或系统 prompt**，而不是依赖对话上下文
2. **分治会话**：每个独立功能模块开一个新会话，在开头贴当前模块的关键约束
3. **定期重申**：长会话中每隔五轮左右，把核心约束作为 `[重申约束]` 前缀加到下一条消息里
4. **代码审查兜底**：配合 ESLint / TypeScript 检查，AI 违反约定时工具会报错

## 四、测试通过但功能错误：AI 写的测试在测自己的假设

**场景**：让 AI 同时生成功能代码和单元测试，测试全绿，但实际功能有 Bug。

**问题根源**：AI 写测试时，测试用例基于它对代码行为的"理解"，而不是基于真实的业务需求。如果代码本身有逻辑错误，AI 写的测试往往会跟着这个错误走，测试"验证"的是错误行为本身。

**示例**：

```python
# AI 生成的函数
def calculate_discount(price, user_type):
    if user_type == "vip":
        return price * 0.8  # 8折
    return price * 0.9      # 9折（这里应该是不打折，AI 理解错了需求）

# AI 生成的测试
def test_regular_user_discount():
    assert calculate_discount(100, "regular") == 90  # 测试通过，但业务逻辑是错的
```

**规避方法**：

1. **先写测试，再让 AI 写实现**（TDD 思路），测试由你基于业务需求来写
2. 或者：让 AI 分两步做——"先解释你对这个函数需求的理解"，确认无误后再写代码
3. **关键业务逻辑的测试用例要覆盖边界**：不要只测正常路径，让 AI 生成边界测试时明确说明边界条件

## 五、过度重构：修一个 Bug，顺便改了五个"顺眼的地方"

**场景**：让 AI 修复一个小 Bug，结果 AI 顺手把周边代码"优化"了一遍——函数重命名、逻辑重写、引入新的设计模式……改动范围远超预期，审查成本激增。

**为什么会这样**：AI 在生成时倾向于产出"看起来好"的代码，会自动触发重构冲动。这在 Composer / Agent 模式下尤为明显。

**规避方法**：

1. **明确限定范围**：`只修改 src/utils/parser.ts 文件的第 45-60 行，不要修改其他文件或函数签名`
2. **diff 审查前不要接受**：使用 Cursor 的改动预览（或 `git diff`），对每一处改动问自己"这个改动是必要的吗"
3. **分离 Bug Fix 和重构**：如果 AI 发现了值得重构的地方，让它记录下来，但当前 commit 只做 Bug Fix

## 六、环境假设错误：AI 不知道你的 Node 版本 / 操作系统

**场景**：AI 生成了一段完美的代码，但在你的环境里跑不起来。错误指向一个环境相关的问题，而 AI 的代码是基于它"默认"的环境假设写的。

**常见触发点**：

- AI 使用了 ES2022+ 的 `Array.at(-1)` 语法，但项目 `tsconfig` 目标是 ES2019
- AI 使用了 `path.resolve(__dirname)` 但项目是 ESM 模块（没有 `__dirname`）
- AI 给出了 Linux 的 shell 命令，但你在 Windows 环境

**规避方法**：

在 prompt 里主动说明环境上下文：

```
环境：Node 20，TypeScript 5.x，ESM 模块（"type": "module"），部署在 Cloudflare Workers
```

这一句话能规避大多数环境假设错误。

## 七、总结：和 AI 结对编程的心理模型

用 AI 写代码，最大的认知误区是把它当成"比你厉害的程序员"，然后把思考的主导权让出去。更准确的心理模型是：

> AI 是一个速度极快、知识广博但**容易自信地犯错**的实习生。你是 Tech Lead，负责最终决策和代码审查。

基于这个模型，几个原则自然推出：

- **你需要保持对代码的理解**，不能因为 AI 生成了就跳过阅读
- **AI 的自信不代表正确**，语气笃定的代码同样需要验证
- **工具约束 > 口头约定**：让 TypeScript / ESLint / 测试框架来守住约束，而不是靠 AI "记住"

掌握这些调试思路后，AI 编程的效率收益才能真正落地，而不是用"修 AI 引入的 Bug"的时间抵消掉"AI 帮你写代码"的收益。

## 八、相关阅读

- [AI 编程常见错误与规避指南](/blog/ai-coding-mistakes-to-avoid/)
- [AI 结对编程：与 AI 高效协作的工作方式](/blog/ai-coding-pair-programming/)
- [AI 编程学习路线图](/blog/ai-coding-learning-roadmap/)
- [AI 编程工具的供应商锁定风险](/blog/ai-coding-tool-vendor-lockin/)
- [Cursor 商业模式分析：订阅定价背后的增长逻辑](/blog/cursor-business-model-analysis/)

想在调试中使用更强的模型能力（如 Claude Opus 或 GPT-4o），[YoTradeApi](https://yotradeapi.com) 提供稳定的 API 中转，无需翻墙，按量计费，支持 Cursor、Cline 等主流 AI 编辑器接入。
