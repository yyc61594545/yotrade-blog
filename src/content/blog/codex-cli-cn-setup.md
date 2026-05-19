---
title: Codex CLI 国内配置与使用指南
description: OpenAI Codex CLI 在国内通过中转接入的完整配置流程，含模型切换、approval policy、沙箱与多 profile 实用技巧。
keywords:
- codex cli 国内
- codex cli 配置
- codex cli 中转
- openai codex cli
- codex 命令行
pubDate: '2026-05-18'
updatedDate: '2026-05-18'
canonical: https://blog.yotradeapi.com/blog/codex-cli-cn-setup/
tags:
- Codex CLI
- OpenAI
- 命令行工具
- API 中转
- 配置教程
category: 工具配置
heroImage: ../../assets/blog-placeholder-3.jpg
---

# Codex CLI 国内配置与使用指南

Codex CLI 是 OpenAI 官方推出的命令行 AI 编程代理，功能上和 Claude Code 类似：在终端里调用 LLM 完成长任务、改文件、跑测试。在国内用 Codex CLI 的核心问题不是用法，是接入——它默认假设你能直连 OpenAI API。下面给完整的中转接入步骤。

## 一、安装

```bash
npm install -g @openai/codex
codex --version
```

或者：

```bash
brew install codex   # macOS
```

## 二、最小配置：环境变量

```bash
export OPENAI_API_KEY="sk-your-yotrade-key"
export OPENAI_BASE_URL="https://yotradeapi.com/v1"
```

然后在项目目录跑：

```bash
codex
```

第一次启动会让你选 approval policy 和模型。**核心要点**：

- `OPENAI_BASE_URL` 必须带 `/v1`
- Codex CLI 通过 OpenAI Responses API 调用，网关需要支持 `/responses` 端点（不只是 `/chat/completions`）。**很多中转只支持 chat/completions，会在这里翻车**——确认网关明确写"支持 Responses API"。

## 三、`~/.codex/config.toml` 完整配置

Codex CLI 支持 toml 配置文件。推荐写一份 profile 化的配置：

```toml
# ~/.codex/config.toml
model = "gpt-5"
approval_policy = "on-request"
sandbox_mode = "workspace-write"
disable_response_storage = true

[model_providers.yotrade]
name = "YoTradeApi"
base_url = "https://yotradeapi.com/v1"
wire_api = "responses"
env_key = "YOTRADE_API_KEY"

[profiles.daily]
model_provider = "yotrade"
model = "gpt-5"
approval_policy = "on-request"

[profiles.opus]
model_provider = "yotrade"
model = "claude-opus-4-7"
approval_policy = "on-request"

[profiles.fast]
model_provider = "yotrade"
model = "claude-haiku-4-5"
approval_policy = "on-request"
```

使用 profile：

```bash
codex --profile daily          # 日常
codex --profile opus           # 复杂任务
codex --profile fast           # 快查
```

把 `YOTRADE_API_KEY` 放进 shell 配置：

```bash
export YOTRADE_API_KEY="sk-..."
```

## 四、Approval Policy（批准策略）

Codex CLI 的安全模型有三档：

| 策略 | 行为 |
| --- | --- |
| `never` | 全自动，**仅在沙箱完整时使用** |
| `on-request` | 模型主动请求才弹批准 |
| `on-failure` | 失败时降级到批准 |

推荐：

- 日常开发：`on-request` + `workspace-write` 沙箱
- CI 跑长任务：`never` + 严格沙箱
- 第一次用：`on-request`，看清楚它会做什么

## 五、沙箱模式

```toml
sandbox_mode = "workspace-write"   # 只能改当前 workspace
# 或
sandbox_mode = "read-only"         # 只读
# 或
sandbox_mode = "danger-full-access" # 几乎不要用
```

`workspace-write` 是大多数场景的甜蜜点：能改代码、能跑测试，但不能动 `~/.ssh` 或全局配置。

## 六、`disable_response_storage` 的意义

OpenAI 官方默认会把 Responses API 的会话存储在 OpenAI 端 30 天。走中转时这个行为可能不被网关支持，会触发错误。**走中转一定要设**：

```toml
disable_response_storage = true
```

## 七、Codex CLI 实战工作流

### 场景 1：单文件修复

```bash
$ codex --profile fast
> 修复 src/utils.ts 里的 fetchData 函数，超时改成可配置，加 retry 包装。
```

模型读文件 → 给出 diff → 你 Approve → 写入。

### 场景 2：长任务（推荐 opus profile）

```bash
$ codex --profile opus
> 把项目从 Express 4 升级到 Express 5。先用 search 工具找出所有需要改的位置，列一个 plan，然后逐项实施。每改完一个文件跑 npm test 验证。
```

Opus 4.7 在长任务规划上比较稳，配合 on-request 批准，能在 30 分钟内完成中等项目的迁移。

### 场景 3：仅查询

```bash
$ codex exec "解释 src/auth/middleware.ts 的逻辑流程"
```

`exec` 子命令是非交互式，一次性输出。

## 八、模型选择建议

| 模型 | 强项 | 适用 |
| --- | --- | --- |
| `gpt-5` | 推理 + 编程 | 默认 |
| `gpt-5-mini` | 速度 + 性价比 | 日常 |
| `claude-opus-4-7` | 长任务规划 | 重构、迁移 |
| `claude-sonnet-4-6` | 通用编程 | 日常编程 |
| `claude-haiku-4-5` | 速度极快 | 摘要、草稿 |
| `gemini-2.5-pro` | 超长上下文 | 大文件分析 |

Codex CLI 本身设计是 OpenAI 模型优先，但因为协议兼容，通过中转跑 Claude 系列没问题，关键是网关要把 Anthropic 协议翻译成 Responses API。

## 九、常见报错

| 报错 | 原因 | 解决 |
| --- | --- | --- |
| `Unknown endpoint /responses` | 网关不支持 Responses API | 换支持的中转 |
| `Response storage requires...` | 没设 `disable_response_storage` | 加上配置 |
| `Sandbox violation` | 沙箱拦截 | 用 `--full-auto` 临时跳过，或扩沙箱权限 |
| `Stream interrupted` | 中转流式不稳 | 缩短输入或换模型 |
| 中文输出乱码 | 终端编码 | macOS 设 `LANG=zh_CN.UTF-8` |

## 十、与 Claude Code 的对比

| 维度 | Codex CLI | Claude Code |
| --- | --- | --- |
| 协议 | OpenAI Responses | Anthropic Messages |
| 沙箱 | 内置三档 | settings.json 权限 |
| 工具调用 | Tools API | 内置 Edit/Bash/Read |
| Subagent | 无原生 | 完整支持 |
| 长任务 | 可用 | 强 |
| MCP | 实验性 | 完整支持 |

简单结论：**追 OpenAI 模型生态用 Codex CLI；追长任务自治用 Claude Code**。两者可以同时装，按任务切。

## 十一、相关阅读

- [Cursor API 中转怎么选：2026 实用清单](/blog/2026-05-15-cursor-api-relay-recommendation-2026/)
- [Claude Code 镜像国内配置完整指南](/blog/claude-code-mirror-cn-setup/)
- [Cline 国内 API 配置详解](/blog/cline-cn-api-setup/)
- [Aider 中文配置与最佳实践](/blog/aider-cn-config-guide/)
- [Cherry Studio 国内 API 中转配置指南](/blog/cherry-studio-cn-config/)

需要同时支持 OpenAI Responses API 与 Anthropic Messages 的中转？[YoTradeApi](https://yotradeapi.com) 同 Key 跑两种协议，按上面 toml 配置直接接入。
