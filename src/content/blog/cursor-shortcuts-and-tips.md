---
title: Cursor 高效快捷键与 30 个实用技巧
description: Cursor 编辑器全部常用快捷键、@-mention 用法、Composer 技巧、Background Agent 流程、隐藏的高效特性集合。
keywords:
- cursor 快捷键
- cursor 技巧
- cursor 高效
- cursor composer
- cursor at mention
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/cursor-shortcuts-and-tips/
tags:
- Cursor
- 快捷键
- 效率
- 技巧
category: 工具配置
heroImage: ../../assets/blog-placeholder-1.jpg
---

# Cursor 高效快捷键与 30 个实用技巧

用了 Cursor 两年，整理这份清单。前 10 个是必背的，后 20 个是隐藏技能。把它们都熟练了，你的产出速度会有质的提升。

## 一、必背 10 个快捷键

| 快捷键 | 作用 |
| --- | --- |
| Tab | 接受补全 |
| Esc | 拒绝补全 |
| Cmd+K | 行内编辑（选中代码 → 改） |
| Cmd+L | 打开 Chat |
| Cmd+I | 打开 Composer |
| Cmd+J | 切换模型 |
| Cmd+. | Quick Fix |
| Cmd+Shift+L | 在 Chat 里搜历史 |
| Cmd+P | 打开文件 |
| Cmd+Shift+P | 命令面板 |

Windows 把 Cmd 换 Ctrl。

## 二、@-mention 全列表

在 Chat / Composer 里用 @ 引用上下文：

| @-mention | 引用什么 |
| --- | --- |
| `@filename` | 单文件 |
| `@folder/` | 目录 |
| `@codebase` | 整个仓库（自动检索） |
| `@docs` | Cursor 内置文档 |
| `@web` | 联网搜索 |
| `@github` | GitHub issue / PR |
| `@cursor` | Cursor 帮助 |
| `@past chats` | 历史对话 |
| `@recommended` | 自动推荐相关文件 |

实战：

```
@src/api/users.ts 加一个 GET /users/:id endpoint。
参考 @src/api/orders.ts 的写法。
@web 查 Next.js 15 的 params 类型最佳实践。
```

## 三、Composer 进阶

### 多步任务

```
> 任务：
> 1. 加 User.is_admin 字段（prisma + migration）
> 2. 加 admin only 中间件
> 3. /api/admin/* 全部用这个中间件
> 4. 加测试
> 一步步来，每步完成给 diff 让我审。
```

Composer 会按步骤逐个产出 diff。

### Rollback

Composer 改了不喜欢？

- 单文件改回：编辑器 Undo
- 整批改回：Composer 历史里 Restore Checkpoint

## 四、Apply Model 选择

Cursor 把"生成代码" 与 "应用 diff" 拆成两个模型：

- 生成：你选的 main model（如 Sonnet）
- Apply：默认快速 model

```
设置 → Models → Apply Model
```

Apply 可以单独选便宜模型，**省 token 不影响生成质量**。

## 五、Cursor Tab（智能补全）

Tab 补全有几个隐藏特性：

- **多行补全**：补全多行代码（不只一行）
- **跨文件预测**：根据其它文件的模式预测
- **重命名传染**：你重命名一个变量，Cursor 自动建议改其它地方

## 六、Quick Fix（Cmd+.）

光标放在错误上，Cmd+.：

- 修复 TypeScript 错误
- 修复 ESLint warning
- 自动 import
- 重构建议

比手工 fix 快很多。

## 七、Inline Generate（光标处生成）

不用打开 Composer。光标在某行：

```
// TODO: 实现 fibonacci
```

按 Tab 或 Cmd+K，让 AI 在原地生成。

## 八、Composer Generate 模式

写新文件：在空文件按 Cmd+I：

```
> 创建一个 LRU 缓存的 TypeScript 类，支持 TTL。
```

直接写一个完整文件给你。

## 九、Bug Finder

设置里开 Bug Finder。Cursor 在你保存时自动扫描"可能的 bug"——比 ESLint 高一层（看语义不只语法）。

## 十、Project Rules（`.cursorrules`）

详见 [.cursorrules 最佳实践](/blog/cursor-rules-best-practices/)。**配好这个 = AI 输出质量 +50%**。

## 十一、Notepads（已迁移到 Rules）

新版 Cursor 把 Notepads 整合进 `.cursor/rules/`。把"项目知识"分文件归类。

## 十二、Pin 文件

打开多个文件标签时，**Pin** 重要的，避免误关。

## 十三、Goto Anywhere（Cmd+P）

不只是找文件名：

- 输入 `:42` 跳到当前文件 42 行
- 输入 `@functionName` 跳到符号
- 输入 `#tag` 跳到 GitHub issue（如装了集成）

## 十四、Multi-cursor 编辑

Cmd+D：选择下一个相同内容，多光标同时编辑。配合 AI 不一定更快——简单批量替换 multi-cursor 更直接。

## 十五、Terminal AI（Cmd+K in Terminal）

终端里 Cmd+K：

```
> 找到 src/ 下所有大于 1MB 的文件
```

Cursor 生成 shell 命令。不需要再去 stackoverflow 查 `find` 语法。

## 十六、Image Drop

把截图直接拖进 Chat / Composer：

```
> [拖一张设计稿]
> 用 React + Tailwind 实现这个设计。
```

需要支持视觉的模型（GPT-5 / Claude / Gemini）。

## 十七、Cursor Docs（自定义文档）

设置 → Features → Docs → Add Doc：

```
URL: https://docs.your-framework.com
```

Cursor 索引这份文档，之后 `@docs` 可以引用。**最适合内部 framework 文档**。

## 十八、Cursor Settings Sync

登录账号后设置自动同步多台机器。**家里 + 公司**一键同步。

## 十九、Custom Model Endpoint（国内必备）

设置 → Models → 配中转 URL。详见 [Cursor API 中转怎么选](/blog/2026-05-15-cursor-api-relay-recommendation-2026/)。

## 二十、Composer 历史

Composer 右上角时钟图标：看所有历史会话。可以**resume** 中断的会话。

## 二十一、Diff 视图

Composer 给改动后，左边 diff 视图：

- 单文件 reject
- 单 chunk reject
- 整批 accept
- 单文件 accept

按需粒度。

## 二十二、Manual Context（手动控制）

Composer 默认会自动加上下文。如果它选错了：

- 关掉 auto context
- 手动 @-mention 指定

精确控制 = 输出质量更高。

## 二十三、长文件性能

> 1000 行的文件 Composer 处理慢？

- 拆文件
- 用 @specific-symbol 而不是 @whole-file
- 用 Cmd+K 局部编辑而不是 Composer

## 二十四、新 vs 已有 Chat

每个独立任务**起新 Chat**，避免上下文污染。

## 二十五、Cursor Background Agent

最强的功能之一。详见 [Cursor Background Agent 国内配置](/blog/cursor-background-agent-config/)。

## 二十六、`.cursorignore`

```
node_modules/
dist/
*.lock
*.png
docs/_build/
```

让 Cursor 不索引这些目录，**速度 + 准确度都提升**。

## 二十七、Git Commit Message AI

Source Control 面板，commit 输入框旁的 ✨ 图标 → AI 写 commit message。

## 二十八、Inline Chat（在编辑器内对话）

选中代码 → 右键 → "Ask Cursor"。比开 Chat 窗口更轻量。

## 二十九、Cmd+/ 注释

不是 AI 特性，但常被忽略。一键注释/取消注释。

## 三十、Restart Window 救命

Cursor 偶尔卡：Cmd+Shift+P → "Restart Window"。比关掉重开快。

## 三十一、相关阅读

- [Cursor 新手完整教程](/blog/cursor-getting-started-cn/)
- [Cursor API 中转怎么选](/blog/2026-05-15-cursor-api-relay-recommendation-2026/)
- [Cursor Background Agent 国内配置](/blog/cursor-background-agent-config/)
- [.cursorrules 最佳实践](/blog/cursor-rules-best-practices/)
- [Cursor vs Claude Code](/blog/cursor-vs-claude-code-comparison/)

把这些技巧 + [YoTradeApi](https://yotradeapi.com/register) 中转配合，Cursor 体感会比"刚装时"快 3 倍。
