---
title: Continue.dev 国内 API 配置完整教程
description: Continue.dev VSCode/JetBrains 插件在国内通过中转的接入指南，含 config.json 模板、Edit/Apply、自定义 Provider 与上下文管理。
keywords:
- continue.dev 国内
- continue.dev 配置
- continue.dev api
- continue 中转
- continue jetbrains
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/continue-dev-cn-setup/
tags:
- Continue.dev
- VSCode
- JetBrains
- API 中转
- 配置教程
category: 工具配置
heroImage: ../../assets/blog-placeholder-2.jpg
---

# Continue.dev 国内 API 配置完整教程

Continue.dev 是 VSCode/JetBrains 上少数完全开源、支持自定义模型的 AI 编程助手。它的核心价值是「`config.yaml` 全配置」——所有行为都在一个文件里，团队协作可以直接 commit 进 repo。本文给国内使用的完整接入流程。

## 一、安装

VSCode：搜索 "Continue" 安装。
JetBrains：Settings → Plugins 搜 "Continue"。

第一次启动会引导你做配置。**不要走默认 Anthropic 登录**，直接跳过到手动配置。

## 二、配置文件路径

- macOS / Linux: `~/.continue/config.yaml`
- Windows: `%USERPROFILE%\.continue\config.yaml`

老版本是 `config.json`，新版本统一用 yaml。下面示例都用 yaml。

## 三、最小配置

```yaml
name: my-config
version: 0.0.1
schema: v1

models:
  - name: Sonnet 4.6
    provider: openai
    model: claude-sonnet-4-6
    apiBase: https://yotradeapi.com/v1
    apiKey: sk-yo-...
    roles: [chat, edit, apply]

  - name: Haiku 4.5
    provider: openai
    model: claude-haiku-4-5
    apiBase: https://yotradeapi.com/v1
    apiKey: sk-yo-...
    roles: [autocomplete, summarize]

context:
  - provider: file
  - provider: code
  - provider: diff
  - provider: open
  - provider: terminal
  - provider: tree
```

保存后 VSCode 侧栏 Continue 会自动加载。

## 四、按角色分模型（roles）

Continue 的 `roles` 让一个模型只承担特定职责。常见角色：

| Role | 用途 | 推荐模型 |
| --- | --- | --- |
| `chat` | 对话 | Sonnet 4.6 |
| `edit` | 内联编辑（选中代码改） | Sonnet 4.6 |
| `apply` | 应用 diff | Haiku 4.5 |
| `autocomplete` | Tab 自动补全 | Haiku 4.5 |
| `summarize` | 上下文摘要 | Haiku 4.5 |
| `embed` | embedding | text-embedding-3-large |
| `rerank` | 检索重排 | rerank model |

按角色分能让最贵的模型只处理最难的任务。

## 五、上下文 Provider 详解

Continue 把上下文做成 plugin 化：

| Provider | 触发方式 | 作用 |
| --- | --- | --- |
| `@file` | `@filename` | 加单文件 |
| `@code` | 选中代码 | 加片段 |
| `@diff` | `@diff` | git diff |
| `@open` | `@open` | 所有打开的文件 |
| `@terminal` | `@terminal` | 最近终端输出 |
| `@tree` | `@tree` | 目录树 |
| `@docs` | `@docs` | 文档检索 |
| `@web` | `@web` | 联网搜索（需配置） |
| `@codebase` | `@codebase` | 全代码库 RAG |

**`@codebase` 需要先建索引**，长跑一次建索引（用 embedding 模型）。建好后能快速回答"这个项目里哪里实现了 X"。

## 六、JetBrains 注意点

JetBrains（IntelliJ / GoLand / PyCharm）配置同 VSCode，但有几点差异：

- 快捷键不同：`Cmd+L`（VSCode）= `Cmd+J`（JetBrains 默认）
- Edit 行为略不同：JetBrains 上下文窗口宽度限制更严
- Terminal Provider 在 JetBrains 抓的是 Run 控制台

## 七、本地模型混搭

Continue 的特色是可以本地 + 云端混用：

```yaml
models:
  - name: Local Code
    provider: ollama
    model: qwen2.5-coder:7b
    apiBase: http://localhost:11434
    roles: [autocomplete]  # 本地跑补全

  - name: Cloud Chat
    provider: openai
    model: claude-sonnet-4-6
    apiBase: https://yotradeapi.com/v1
    apiKey: sk-yo-...
    roles: [chat, edit]    # 云端跑复杂任务
```

补全这种高频低复杂度任务，本地小模型完全够用；复杂任务走云端大模型。

## 八、slash commands（自定义命令）

定义项目特定指令：

```yaml
slashCommands:
  - name: review
    description: 代码评审
    prompt: |
      请评审选中代码，按以下维度：
      1. 正确性
      2. 性能
      3. 可读性
      4. 安全性
      为每个维度给出 1-10 分和具体建议。

  - name: test
    description: 生成单元测试
    prompt: |
      为选中函数生成完整 Jest 单元测试，覆盖：
      - 正常路径
      - 边界值
      - 异常输入
```

侧栏输入 `/review` 或 `/test` 即可触发。

## 九、Quick Actions（行内提示）

Continue 在每个函数上方默认显示 "Continue" 行内按钮。可以在配置里加自定义动作：

```yaml
quickActions:
  - title: 加 docstring
    prompt: 给这个函数加完整 docstring，包含参数、返回值、异常。

  - title: 加日志
    prompt: 在关键步骤加 logger 日志，使用项目里现有的 logger 实例。
```

## 十、常见报错

| 报错 | 原因 |
| --- | --- |
| `404 Unknown model` | model 名拼错 |
| `apiBase must be defined` | 写成 `baseURL` 而不是 `apiBase` |
| Autocomplete 没反应 | 没给 autocomplete 角色配模型 |
| `@codebase` 出错 | 没配 embed 模型 |
| 中文乱码 | 终端 / IDE 编码问题 |

## 十一、与 Cline / Cursor 的差异

| 维度 | Continue.dev | Cline | Cursor |
| --- | --- | --- | --- |
| 开源 | 是 | 是 | 否 |
| 形态 | 插件 | 插件 | 独立 |
| 配置 | yaml 文件 | 设置 UI | 设置 UI |
| 团队协作 | commit 配置 | 各自配 | 各自配 |
| 长任务 agent | 弱 | 强 | 强 |
| 自定义 | 极强 | 中 | 中 |

如果你的诉求是「团队统一配置、能 commit 进 repo、配置驱动」，Continue.dev 是最自然的选择。如果是「单人长任务 agent」，Cline / Cursor 更顺。

## 十二、相关阅读

- [Cursor API 中转怎么选](/blog/2026-05-15-cursor-api-relay-recommendation-2026/)
- [Cline 国内 API 配置详解](/blog/cline-cn-api-setup/)
- [Aider 中文配置与最佳实践](/blog/aider-cn-config-guide/)
- [OpenAI SDK base_url 国内配置实战](/blog/openai-sdk-base-url-cn/)

用一把 Key 同时配置 Continue.dev 的 chat / edit / autocomplete / embed？[YoTradeApi](https://yotradeapi.com) 创建 API Key 后按上面 yaml 模板填即可。
