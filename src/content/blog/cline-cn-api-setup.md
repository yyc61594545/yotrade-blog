---
title: Cline 国内 API 配置详解（VSCode 编程代理）
description: Cline VSCode 插件在国内的 API 中转配置完整指南，含 OpenAI Compatible Provider、Plan/Act 模式、MCP 与权限设置实用经验。
keywords:
- cline 国内
- cline api 配置
- cline 中转
- cline vscode 配置
- cline openai compatible
pubDate: '2026-05-18'
updatedDate: '2026-05-18'
canonical: https://blog.yotradeapi.com/blog/cline-cn-api-setup/
tags:
- Cline
- VSCode
- API 中转
- 配置教程
- Plan/Act
category: 工具配置
heroImage: ../../assets/blog-placeholder-5.jpg
---

# Cline 国内 API 配置详解（VSCode 编程代理）

Cline（前身 Claude Dev）在 VSCode 里跑编程代理，特点是「能编辑文件、能跑命令、Plan/Act 双模式」。在国内用它的第一道坎不是学怎么用，是先让它能连上模型。本文给一份不绕弯子的接入流程。

## 一、Cline 在 VSCode 里能选哪些 Provider

打开 Cline 侧栏 → 设置 → API Provider，常见选项：

| Provider | 协议 | 适配中转难度 |
| --- | --- | --- |
| Anthropic | Anthropic 原生 | 中转要支持 `/v1/messages` |
| OpenAI Compatible | OpenAI Chat Completions | 最简单，**推荐起步** |
| OpenRouter | OpenRouter API | 需 OpenRouter key |
| Bedrock / Vertex / Azure | 各家云原生 | 国内基本用不到 |
| LM Studio / Ollama | 本地 | 自己部署模型才用 |

**90% 国内用户走 OpenAI Compatible 这条路**：兼容性好、调试简单、模型选择灵活。

## 二、5 步配置 OpenAI Compatible

1. VSCode 安装 Cline 插件（`saoudrizwan.claude-dev`）。
2. 点击侧栏 Cline 图标 → 右上齿轮。
3. API Provider 选 **OpenAI Compatible**。
4. 填两个字段：
   - **Base URL**: `https://yotradeapi.com/v1`
   - **API Key**: 你在网关后台创建的 Key
5. **Model ID** 填你要用的模型名，例如 `claude-sonnet-4-6`。如果勾选 "Allow custom model ID"，可以输入网关支持的任意模型。

保存后 Cline 会自动跑一次 ping，状态显示 `OK` 才算通。

## 三、Plan / Act 双模式的实际使用

Cline 有两个模式：

| 模式 | 作用 | 适合场景 |
| --- | --- | --- |
| **Plan** | 只读、规划、画思路 | 项目初步分析、设计方案 |
| **Act** | 编辑文件、跑命令 | 真正动手实现 |

国内用中转特别推荐**先 Plan 后 Act**的工作流：

- Plan 模式输入 token 多、输出 token 少，用便宜的模型（`claude-haiku-4-5`、`gpt-5-mini`）就够。
- Act 模式涉及代码生成，用 `claude-sonnet-4-6` 或 `claude-opus-4-7`。

在 Cline 设置里有 "Plan Mode Model" 与 "Act Mode Model" 两个独立配置项，分别设：

```
Plan Mode Model: claude-haiku-4-5
Act Mode Model:  claude-sonnet-4-6
```

按这个配置跑一周，账单能砍 40–60%，而效果几乎无感。

## 四、Auto Approve（自动批准）的边界

Cline 默认每个动作都要点 Approve。`Auto Approve` 设置里可以放开：

```
✓ Read files and directories
✓ Edit files
✓ Execute safe commands
✗ Execute all commands         ← 不要勾
✗ Use MCP servers              ← 看具体 server
```

国内用中转长任务最容易出现的问题是**网络抖一下，Act 模式中途断开，留下半写的文件**。给 `Edit files` 自动批准但留 `Execute all commands` 手动，可以兜住大部分风险。

## 五、上下文管理与价格

Cline 的上下文随项目大小膨胀。一个 1k 文件的中等项目，跑几个 Act 之后上下文经常飙到 50k+。三招控制成本：

1. **`@/folder` 显式指定上下文**，不要让 Cline 自由探索整个仓库。
2. **`Auto Compact at` 设为 80%**，让它在上下文快满时自动压缩。
3. **网关侧开启 prompt caching**：YoTradeApi 这类中转支持 Anthropic prompt caching，长 system prompt 二次命中能省 90% 输入费用。

## 六、MCP 服务器接入

Cline 支持 MCP（Model Context Protocol）。如果你接入了 GitHub MCP、Slack MCP，工具调用会通过 Cline 转给 LLM。这里有一个**容易忽略的成本陷阱**：

> 每加一个 MCP 服务器，所有工具的 schema 都会被塞进 system prompt。

10 个 MCP 工具就是 5–8k 输入 token 的固定开销，按每次请求计费。国内中转一般按 token 计费，乘上每天几百次请求，月底账单会很可观。建议只在当前任务真正需要时启用对应 MCP。

## 七、常见报错对照表

| 报错 | 原因 | 解决 |
| --- | --- | --- |
| `400 Bad Request: model not found` | Model ID 不被网关识别 | 改成网关模型列表里的名字 |
| `401 Unauthorized` | API Key 错或过期 | 后台重新生成 |
| `429 Too Many Requests` | 短时间内 token 用太快 | 降低并发；Plan 模式换便宜模型 |
| `Request timed out` | 中转首 token 超时 | Cline 设置里把 Request Timeout 调到 120s |
| `Stream interrupted` | 网关流式不稳 | 换模型 / 换中转，或缩短输入 |
| `Tool use turn limit exceeded` | Cline 内置工具循环上限 | 在设置里改 Max Requests Per Task |

## 八、Cline vs Cursor vs Claude Code 的选择

简单的工作流对比：

| 维度 | Cline | Cursor | Claude Code |
| --- | --- | --- | --- |
| 形态 | VSCode 插件 | 独立编辑器 | CLI |
| 文件编辑 | 直接修改 | Composer / Inline | Edit 工具 |
| Plan/Act | 内置 | 无 | 通过 Plan Mode |
| 长任务自治 | 中 | 中 | 强 |
| 国内中转难度 | 低 | 中（绑定订阅） | 低 |

如果是「VSCode 用户、想要可视化、需要编辑器内对话」，Cline 是国内最容易上手的选择。

## 九、实战工作流：用 Cline 重构一个 Express 项目

下面是我推荐的标准流程：

1. **Plan 模式**，输入：`@/src 分析整个项目结构，列出可重构的地方，按优先级排序`。
2. 看完输出，选 2–3 个高优先级项写到一个 markdown 当 backlog。
3. 切到 **Act 模式**，每次选一项，输入：`实现 backlog 里第 1 项：[具体描述]。修改后跑 npm test 确认通过。`
4. Cline 会编辑文件 + 跑测试。如果测试失败，它会自动尝试修复。
5. 一项完成后 commit，进入下一项。

这样既能利用 LLM 的代码能力，又能避免单次任务过长导致中转断流。

## 十、相关阅读

- [Cursor API 中转怎么选：2026 实用清单](/blog/2026-05-15-cursor-api-relay-recommendation-2026/)
- [Claude Code 镜像国内配置完整指南](/blog/claude-code-mirror-cn-setup/)
- [OpenAI SDK base_url 国内配置实战](/blog/openai-sdk-base-url-cn/)
- [Aider 中文配置与最佳实践](/blog/aider-cn-config-guide/)

需要一个支持 Cline 全部模型的中转？在 [YoTradeApi 注册](https://yotradeapi.com) 创建独立 API Key，按上面的 base_url 直接接入。
