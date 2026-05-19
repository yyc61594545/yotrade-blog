---
title: Windsurf 国内配置与 Cascade 模式使用
description: Windsurf 编辑器在国内的 API 中转配置、Cascade Agent 模式、内置模型 vs 自定义模型、与 Cursor 的实战差异对比。
keywords:
- windsurf 国内
- windsurf 配置
- windsurf cascade
- windsurf vs cursor
- windsurf api
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/windsurf-cn-setup/
tags:
- Windsurf
- 编辑器
- Cascade
- API 中转
- 配置教程
category: 工具配置
heroImage: ../../assets/blog-placeholder-4.jpg
---

# Windsurf 国内配置与 Cascade 模式使用

Windsurf 是 Codeium 推出的 AI 编辑器，定位上是 Cursor 的直接竞品。在国内用 Windsurf 的接入难度比 Cursor 略高，但优势是 Cascade Agent 自治能力较强。本文给完整接入流程。

## 一、Windsurf 与 Cursor 的核心差异

| 维度 | Windsurf | Cursor |
| --- | --- | --- |
| 基础 | VSCode fork | VSCode fork |
| 代理 | Cascade（云端 agent） | Composer + Background Agent |
| Tab 补全 | Codeium（自研） | 自研 |
| 自定义模型 | 部分支持 | 完整支持 |
| 订阅模式 | Free + Pro | Free + Pro + Pro+ |

Windsurf 的强项：

- Cascade 模式默认更"自主"，少打断
- 补全质量高（Codeium 训练时间长）
- Free 套餐相对慷慨

Windsurf 的弱项：

- 自定义模型选项比 Cursor 少
- 国内接入门槛略高

## 二、第一次启动

下载安装 → 启动 → 创建 Codeium 账号（**需要邮箱验证，有时国内邮件接收慢**）。

如果不想创建账号，部分功能会受限。**Cascade 高级特性必须有账号**。

## 三、配置 Custom Model（如果支持）

Windsurf 的 Custom Model 功能在不同版本支持度不同。最新版（2026）：

设置 → AI → Models → Custom Endpoint：

```
Endpoint: https://yotradeapi.com/v1
API Key: sk-yo-...
Model: claude-sonnet-4-6
Protocol: OpenAI Compatible
```

部分功能（Cascade 长任务）可能仍要走官方模型——这一点比 Cursor 限制更紧。**Tab 补全只能走 Codeium 自有模型**。

## 四、Cascade 模式

Cascade 是 Windsurf 的核心特性，类似 Cursor Composer + Background Agent 的合体：

- **Write Mode**：直接改文件
- **Chat Mode**：只对话
- **Cascade（autonomous）**：长任务自治，跨多文件、跑命令、自我修复

```
> Cascade: 把项目从 Vue 2 迁移到 Vue 3。先调研 breaking changes，列计划，然后逐项实施。
```

Cascade 会自动：

1. 读项目结构
2. 找出所有 Vue 组件
3. 列迁移计划
4. 逐文件改
5. 跑测试验证

类似 Cursor Background Agent，但运行在本地，不在云端。

## 五、Memory 系统

Windsurf 的 "Memory" 让 Cascade 跨会话记住关键事实：

```
> 记住：本项目用 pnpm 不用 npm
> 记住：所有 API 路由必须按 /api/v1/* 命名
```

Memory 写到 `.windsurf/memories.json`，可以 commit。**类似 Cursor 的 .cursorrules，但更动态**。

## 六、Rules 文件

`.windsurfrules` 或 `.windsurf/rules/*.md`：

```markdown
# 编码规范

- 函数名 camelCase
- 类名 PascalCase
- 测试文件 `*.test.ts`
- 公开 API 必须有 TSDoc

# 不能做的事

- 不修改 package.json 主版本
- 不写 console.log（用 logger）
- 不引入新依赖除非必要
```

每次 Cascade 调用都会读这份文件。

## 七、Memory + Rules 配合 prompt caching

Windsurf 默认让 Memory 和 Rules 内容稳定，**这部分高度复用，开启 prompt caching 收益大**。如果中转支持透传 cache_control，会自动受益。

## 八、Windsurf vs Cursor 选择

| 你的诉求 | 推荐 |
| --- | --- |
| Tab 补全质量优先 | Windsurf |
| 国内中转简单 | Cursor |
| Cascade 长任务 | Windsurf |
| Background Agent 云端 | Cursor |
| Free 套餐够用 | Windsurf |
| 自定义模型灵活 | Cursor |

国内开发者**默认推荐 Cursor**——除非你特别在意 Tab 补全质量。

## 九、Windsurf 国内常见报错

| 报错 | 原因 |
| --- | --- |
| 账号注册邮件收不到 | 国内邮箱慢 / 拦截 |
| Cascade 卡住 | 自定义模型部分功能受限 |
| 补全无响应 | Codeium 服务网络问题 |
| Custom Model 没保存 | 部分版本 bug |

## 十、Cascade + 中转的兼容性

实测：

- ✓ Chat Mode 完全可用
- ✓ Write Mode 完全可用
- 部分版本 Cascade 长任务会回退到官方模型（即使配了 Custom）

接入前用一个简单 Cascade 任务测试，确认是否走的是你的中转（看中转后台用量）。

## 十一、与 Claude Code 组合

很多 Windsurf 用户的工作流：

- **日常 IDE 编辑** → Windsurf（Tab 补全 + Cascade）
- **CLI 长任务** → Claude Code（Subagent 更强）

共享一把中转 Key，按场景切。

## 十二、相关阅读

- [Cursor API 中转怎么选](/blog/2026-05-15-cursor-api-relay-recommendation-2026/)
- [Cursor vs Claude Code](/blog/cursor-vs-claude-code-comparison/)
- [Claude Code 镜像国内配置完整指南](/blog/claude-code-mirror-cn-setup/)
- [2026 AI 编程工具全景图](/blog/ai-coding-tools-2026-overview/)

需要 Windsurf Custom Model + Claude Code 共享 Key？[YoTradeApi](https://yotradeapi.com/register) 一把 Key 通调，按上面配置接入。
