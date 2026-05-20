---
title: Claude Code vs Codex CLI 全面对比
description: Claude Code（Anthropic）与 Codex CLI（OpenAI）两个旗舰 CLI 编程代理的实战对比，含协议、工具、Agent 模式、长任务能力。
keywords:
- claude code vs codex
- codex cli vs claude code
- ai cli 对比
- claude codex 选择
- cli 编程代理
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/claude-code-vs-codex-cli/
tags:
- Claude Code
- Codex CLI
- 工具对比
- CLI
- Agent
category: 工具对比
heroImage: ../../assets/blog-placeholder-5.jpg
---

CLI 形态的 AI 编程代理目前两大代表：Anthropic 的 Claude Code、OpenAI 的 Codex CLI。两者形态相似但理念差很多。本文按 8 个维度对比。

## 一、设计哲学

| 维度 | Claude Code | Codex CLI |
| --- | --- | --- |
| 协议 | Anthropic Messages | OpenAI Responses |
| 默认模型 | Claude（Opus/Sonnet/Haiku） | GPT（5/5-mini） |
| 风格 | 通用 agent | 强调安全沙箱 |
| 配置 | settings.json | config.toml + profile |

Claude Code 把"agent 能做什么"留给配置；Codex CLI 把"agent 能做什么"切得更死，沙箱更显眼。

## 二、安装与启动

```bash
# Claude Code
npm install -g @anthropic-ai/claude-code
claude

# Codex CLI
npm install -g @openai/codex
codex
```

第一次启动都需要配置 API key 与 base_url。Claude Code 用 4 个环境变量；Codex CLI 用 toml 文件。

## 三、工具集

| 工具 | Claude Code | Codex CLI |
| --- | --- | --- |
| Read | ✓ | ✓ |
| Write | ✓ | ✓ |
| Edit | ✓ | ✓ |
| Bash | ✓ | ✓（沙箱内） |
| Search/Grep | ✓ | ✓ |
| WebFetch | ✓ | 部分 |
| Notebook | ✓ | ✗ |
| Subagent | ✓ | ✗（无 Subagent） |
| MCP | ✓ | 实验 |

Claude Code 工具更全；Codex CLI 沙箱更严。

## 四、沙箱与权限

### Claude Code

通过 `.claude/settings.json` 的 `permissions` 控制：

```json
{
  "permissions": {
    "allow": ["Bash(npm test:*)", "Bash(git diff:*)"],
    "deny": ["Bash(rm -rf:*)", "Bash(git push --force:*)"]
  }
}
```

加上 hook 系统可以拦截到任意命令。

### Codex CLI

内置三档沙箱：

```toml
sandbox_mode = "workspace-write"   # 默认
# read-only / workspace-write / danger-full-access
```

加 approval policy（never / on-request / on-failure）。

Codex CLI 的沙箱在 OS 层（Linux seccomp / macOS sandbox-exec）。安全性更高，但灵活性低。

## 五、长任务能力

| 维度 | Claude Code | Codex CLI |
| --- | --- | --- |
| 持续时长 | 几小时 | 几小时 |
| Subagent | ✓（核心特性） | ✗ |
| Background mode | 部分 | ✓ |
| Hook 拦截 | 8 种 | 部分 |
| 自动压缩 | ✓ | ✓ |
| 失败恢复 | 强 | 中 |

Claude Code 的 Subagent 是它最强的长任务利器。Codex CLI 没有 Subagent 这种结构，但 Background mode 能让任务挂在云端跑。

## 六、配置粒度

| 维度 | Claude Code | Codex CLI |
| --- | --- | --- |
| 项目级配置 | `.claude/` 目录 | `~/.codex/config.toml` |
| Profile 切换 | 通过 model env | 多 profile |
| Subagent 定义 | `.claude/agents/*.md` | 不支持 |
| Hook | 8 种 | 部分 |
| 团队共享 | 完整可 commit | toml + 环境变量 |

Codex CLI 的 profile 系统切换模型很方便：

```bash
codex --profile daily      # Sonnet
codex --profile heavy      # Opus
codex --profile gpt5       # GPT-5
```

## 七、国内中转适配

| 维度 | Claude Code | Codex CLI |
| --- | --- | --- |
| 接入难度 | 低 | 中 |
| 协议要求 | Anthropic Messages | OpenAI Responses |
| 中转覆盖 | 广泛 | 一般 |
| `base_url` 配置 | `ANTHROPIC_BASE_URL` | toml `base_url` |

**关键差异**：Codex CLI 用的是 Responses API（`/v1/responses`）。**不是所有中转都支持**。接入前用 curl 测一下。

## 八、模型选择

- **Claude Code 默认走 Claude 模型**——通过 base_url 可以走中转下的所有 Anthropic 兼容模型。
- **Codex CLI 默认走 OpenAI 模型**——但可以通过 model_providers 配置接入其他厂商。

通过同一个支持双协议的中转，两个工具都能调到 Claude/GPT/Gemini 全家。

## 九、典型场景

### 场景 1：长重构

```bash
# Claude Code
claude
> 用 architect subagent 规划这次重构，然后 dispatch 给 implementer subagent 执行

# Codex CLI
codex --profile opus
> 重构...（无 subagent，但可以 chained 思考）
```

Claude Code 的 Subagent 在这个场景更顺。

### 场景 2：跑测试 + 修 bug

```bash
# Claude Code
> 跑 npm test，每个失败用 debugger subagent 单独修

# Codex CLI
> 跑 npm test，把失败的逐个分析修复
```

打成平手。

### 场景 3：CI 集成

```bash
# Claude Code headless
claude --headless --task "review the PR" --max-turns 10

# Codex CLI exec
codex exec "review the PR" --approval never
```

两者都能用，体验接近。

## 十、按场景推荐

| 场景 | 推荐 |
| --- | --- |
| 长任务自治、需要 Subagent | Claude Code |
| 安全敏感、需要沙箱 | Codex CLI |
| 国内接入简单 | Claude Code |
| 团队共享 hook | Claude Code |
| 多 profile 快速切换 | Codex CLI |
| OpenAI 生态深耕 | Codex CLI |
| 接入 Claude 模型 | Claude Code |

## 十一、组合用法

两个都装：

- 日常 / 重任务 → Claude Code
- 需要严格沙箱的脚本 → Codex CLI
- 需要 OpenAI 独家工具 → Codex CLI

共享中转 API key，按场景切。

## 十二、相关阅读

- [Claude Code 镜像国内配置完整指南](/blog/claude-code-mirror-cn-setup/)
- [Codex CLI 国内配置](/blog/codex-cli-cn-setup/)
- [Claude Code Subagent 实战](/blog/claude-code-subagent-practice/)
- [Cursor vs Claude Code](/blog/cursor-vs-claude-code-comparison/)
- [2026 AI 编程工具全景图](/blog/ai-coding-tools-2026-overview/)

用一把 Key 同时接 Claude Code 与 Codex CLI？[YoTradeApi](https://yotradeapi.com) 同时支持 Anthropic Messages 与 OpenAI Responses 两个协议。
