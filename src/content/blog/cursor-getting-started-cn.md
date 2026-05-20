---
title: Cursor 新手完整教程：从零开始的中文指南
description: 第一次用 Cursor？这份教程从安装、登录、配置中转、Tab 补全、Composer、Agent 模式到 .cursorrules 完整覆盖。
keywords:
- cursor 新手 教程
- cursor 怎么用
- cursor 入门
- cursor 中文
- cursor 配置
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/cursor-getting-started-cn/
tags:
- Cursor
- 入门
- 教程
- 新手
category: 入门
heroImage: ../../assets/blog-placeholder-1.jpg
---

第一次接触 Cursor，第一感觉是"和 VSCode 长得一样啊"。但用过之后就会发现完全不同——AI 是一等公民。本教程从安装开始，给一份能让你上手的中文实战指南。

## 一、安装

[cursor.com](https://cursor.com) 下载对应平台版本。macOS 用 .dmg，Windows 用 .exe，Linux 用 .AppImage。

安装后第一次启动会问几个问题：

- 是否导入 VSCode 设置？（**推荐导入**，扩展、主题、快捷键全继承）
- 选默认主题
- 注册账号（**国内邮箱注册有时较慢**，等一会儿）

## 二、第一次打开项目

```bash
cd your-project
cursor .
```

或者直接拖目录到 Cursor 图标。

界面布局基本同 VSCode：

- 左边文件树
- 中间编辑器
- 右边可能弹出 AI 侧栏

## 三、四种 AI 用法

Cursor 的 AI 有 4 个主要触发方式：

### 1. Tab 补全

在编辑器里写代码，AI 自动建议下一段，按 Tab 接受、Esc 拒绝。

```typescript
function fibonacci(n: number): number {
  // 按 Tab：Cursor 自动生成实现
```

补全是 Cursor 体验最好的部分。**不需要任何额外操作，写代码就有**。

### 2. 行内编辑（Cmd+K）

选中一段代码 → Cmd+K → 输入你想改的内容：

> 改成更高效的实现

模型给你 diff，按 Accept 或 Reject。

### 3. Chat（Cmd+L）

打开右边对话面板。在这里可以：

- 问代码相关问题
- 让 AI 解释函数
- 让 AI 写小段代码（自己复制）

### 4. Composer（Cmd+I）

最强大的形态：跨多文件改动。

```
> 添加用户管理：注册、登录、修改资料。
> 后端 src/api/users/*.ts
> 前端 src/components/user/*.tsx
> 数据库 prisma/schema.prisma 加 User 表
```

Composer 会同时改多个文件，给你完整 diff 一次性 review。

## 四、国内接入中转（重要）

默认情况下 Cursor 调 OpenAI/Anthropic 官方。国内可能不稳。换中转：

设置（Cmd+,）→ 搜 "Custom Endpoint" → AI → Models：

```
OpenAI API Key: sk-yo-...
Override OpenAI Base URL: https://yotradeapi.com/v1
```

勾选 "Enable Override"。

然后 Models 列表里选 `gpt-5` 或加 Custom Model `claude-sonnet-4-6` 等。

**测试**：开个 Chat 问 "今天几号"，看是否能正常对话。可以的话中转生效了。

## 五、`.cursorrules`：项目知识

在项目根创建 `.cursorrules`：

```markdown
# 项目知识

## 技术栈
- Next.js 15 + React 19 + TypeScript
- 数据库: PostgreSQL + Prisma
- 部署: Cloudflare Pages

## 编码约定
- 函数名 camelCase，组件 PascalCase
- 不用 console.log，用 src/lib/logger
- 所有 API 路由返回 { ok, data?, error? } 形式

## 不能做
- 不修改 package.json 主版本号
- 不引入新依赖，除非必要
- 不写空 try/catch
```

每次 AI 调用都会读这份文件。**写好它 = AI 立刻"懂你的项目"**。

## 六、五个最有用的快捷键

| 快捷键 | 作用 |
| --- | --- |
| Tab | 接受补全 |
| Cmd+K | 行内编辑 |
| Cmd+L | 打开 Chat |
| Cmd+I | 打开 Composer |
| Cmd+J | 切换模型 |

## 七、@ 引用（Composer/Chat 都能用）

| 命令 | 作用 |
| --- | --- |
| `@filename` | 引用单文件 |
| `@folder/` | 引用整个目录 |
| `@codebase` | 让 AI 检索整个项目 |
| `@docs` | 引用 cursor docs |
| `@web` | 联网搜索 |
| `@cursor` | 引用 cursor 自带知识 |

实战例子：

```
@src/api/users.ts 修改这个文件，加一个 createUser 端点。
参考 @src/api/orders.ts 的写法。
```

## 八、模型选择

Cursor 默认免费额度有限。配了 Custom Endpoint 之后用自己中转的模型：

| 任务 | 推荐 |
| --- | --- |
| 日常 | claude-sonnet-4-6 |
| 长任务 | claude-opus-4-7 |
| 快查 | claude-haiku-4-5 |
| OpenAI 用户 | gpt-5 |

Cmd+J 临时切换，或者 .cursorrules 写默认。

## 九、避坑提醒

1. **不要把 .env 加进 .cursorignore 的反向**——你不希望 AI 读到 secrets
2. **Composer 跑大任务时关掉自动保存**——AI 写一半你不小心 Cmd+S 会冲突
3. **Tab 补全不准时按 Esc 拒绝**——不要在错误的补全上继续敲，会越来越歪
4. **遇到模型不响应**：检查中转 base_url 与 key 是否正确
5. **想撤销 AI 的改动**：用 git，不要依赖编辑器历史

## 十、第一个练手任务

打开一个空目录：

```bash
mkdir my-first-cursor && cd my-first-cursor
cursor .
```

在 Composer 输入：

```
创建一个 React + TypeScript + Tailwind 的 todo app：
- 加 / 删 / 完成
- 数据存 localStorage
- 简洁界面
跑起来后告诉我命令
```

5–10 分钟后你有一个能跑的 demo。这是 Cursor 最直观的展示。

## 十一、接下来学什么

| 你的下一步 | 看这个 |
| --- | --- |
| 学 Composer 长任务 | <a href="/blog/cursor-background-agent-config/">Background Agent</a> |
| 比较其它工具 | <a href="/blog/cursor-vs-claude-code-comparison/">Cursor vs Claude Code</a> |
| 控制成本 | <a href="/blog/ai-coding-agent-cost-control/">AI 编程成本控制</a> |
| 选模型 | <a href="/blog/claude-sonnet-4-6-vs-opus-4-7/">Sonnet vs Opus</a> |
| 配中转 | <a href="/blog/2026-05-15-cursor-api-relay-recommendation-2026/">Cursor 中转选型</a> |

## 十二、相关阅读

- [Cursor API 中转怎么选](/blog/2026-05-15-cursor-api-relay-recommendation-2026/)
- [Cursor Background Agent 国内配置](/blog/cursor-background-agent-config/)
- [Cursor vs Claude Code](/blog/cursor-vs-claude-code-comparison/)
- [Claude Sonnet 4.6 与 Opus 4.7 怎么选](/blog/claude-sonnet-4-6-vs-opus-4-7/)
- [AI Agent Prompt Engineering 中文实战](/blog/agent-prompt-engineering-cn/)

需要给 Cursor 配一个稳定的 base_url？[YoTradeApi](https://yotradeapi.com) 注册即可拿独立 API Key，按本教程第 4 节配置接入。
