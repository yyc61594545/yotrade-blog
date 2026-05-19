---
title: Claude Code 镜像国内配置完整指南
description: 国内开发者使用 Claude Code 的镜像配置方法，含 ANTHROPIC_BASE_URL、API Key、模型选择、Subagent 与故障排查清单。
keywords:
- claude code 镜像
- claude code 国内
- anthropic base url
- claude code 中转
- claude code 配置
pubDate: '2026-05-16'
updatedDate: '2026-05-16'
canonical: https://blog.yotradeapi.com/blog/claude-code-mirror-cn-setup/
tags:
- Claude Code
- API 中转
- Anthropic
- 配置教程
category: 工具配置
featured: true
heroImage: ../../assets/blog-placeholder-2.jpg
---

# Claude Code 镜像国内配置完整指南

Claude Code 在国内长期处于"能装但调不通"的状态。官方注册门槛、信用卡、网络环路三件事任意一件不顺利，整个 CLI 都会卡在第一步。本文不绕弯子，直接给一份可以复制粘贴的镜像配置流程，覆盖 macOS、Linux、Windows 与 WSL 四种常见环境，并把容易踩坑的细节列出来。

## 一、Claude Code 的网络模型

Claude Code（命令行版本）本质上是一个调用 Anthropic Messages API 的 Node CLI。它通过两个环境变量与服务端通讯：

| 变量 | 作用 | 默认值 |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | Bearer Token，用于身份认证 | 无 |
| `ANTHROPIC_BASE_URL` | API 入口域名 | `https://api.anthropic.com` |
| `ANTHROPIC_MODEL` | 默认模型名（可选） | 由 CLI 决定 |
| `ANTHROPIC_AUTH_TOKEN` | 部分兼容网关使用 | 与 API_KEY 二选一 |

把 `ANTHROPIC_BASE_URL` 指向兼容 Anthropic 协议的中转网关，CLI 的行为就会从"直连官方"切换为"经过中转"。**关键点**：Claude Code 用的是 Anthropic 原生协议，不是 OpenAI 协议，所以中转服务必须明确支持 Anthropic Messages 端点（`/v1/messages`）。

## 二、最小可用配置（推荐起步方式）

以 YoTradeApi 为例，最小配置三行：

```bash
export ANTHROPIC_BASE_URL="https://yotradeapi.com"
export ANTHROPIC_AUTH_TOKEN="sk-your-yotrade-key"
export ANTHROPIC_MODEL="claude-sonnet-4-6"
```

然后直接跑：

```bash
claude
```

第一次启动会让你选工作目录、模型、权限模式。如果你看到 `> Welcome to Claude Code!` 与提示符，说明握手成功。这里要注意三点：

1. **`ANTHROPIC_BASE_URL` 不要带 `/v1`**。Claude Code 会自己拼路径，加了反而 404。
2. **`AUTH_TOKEN` 与 `API_KEY` 只设一个**。大部分中转用 `AUTH_TOKEN`，官方用 `API_KEY`。两个都设有些 CLI 版本会优先选官方。
3. **模型名要用网关支持的写法**。YoTradeApi 当前支持 `claude-sonnet-4-6`、`claude-opus-4-7` 等，写错会直接 404。

## 三、按操作系统的持久化配置

### macOS / Linux（zsh、bash）

在 `~/.zshrc` 或 `~/.bashrc` 追加：

```bash
# Claude Code via YoTradeApi
export ANTHROPIC_BASE_URL="https://yotradeapi.com"
export ANTHROPIC_AUTH_TOKEN="sk-your-yotrade-key"
export ANTHROPIC_MODEL="claude-sonnet-4-6"
```

`source ~/.zshrc` 之后用 `env | grep ANTHROPIC` 检查是否生效。

### Windows PowerShell

```powershell
[Environment]::SetEnvironmentVariable("ANTHROPIC_BASE_URL", "https://yotradeapi.com", "User")
[Environment]::SetEnvironmentVariable("ANTHROPIC_AUTH_TOKEN", "sk-your-yotrade-key", "User")
[Environment]::SetEnvironmentVariable("ANTHROPIC_MODEL", "claude-sonnet-4-6", "User")
```

设置完毕重启终端。**不要**写到系统级别（`Machine`），多用户环境下容易泄露 key。

### WSL（Ubuntu 子系统）

WSL 默认不会继承 Windows 的环境变量。要么把上面那段 export 写进 WSL 自己的 `~/.bashrc`，要么在 `/etc/wsl.conf` 里开 `[interop] appendWindowsPath=true` 后再做继承设置——前者更省心。

## 四、Claude Code 项目级配置

Claude Code 支持把项目相关的设置写进 `.claude/settings.json`，团队协作时建议这样做：

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://yotradeapi.com",
    "ANTHROPIC_MODEL": "claude-sonnet-4-6"
  },
  "permissions": {
    "allow": ["Bash(git diff:*)", "Bash(npm test:*)"],
    "deny": ["Bash(rm -rf:*)", "Bash(git push --force:*)"]
  }
}
```

把 `AUTH_TOKEN` 放在 `.env` 文件里、加进 `.gitignore`，避免误提交。

## 五、Subagent 与 Hook 在中转下的注意点

Claude Code 的 Subagent 与 Hook 都通过同一个 `ANTHROPIC_BASE_URL` 发请求，不需要额外配置。但要留意：

- **长任务的 token 数**：一个 Subagent 调用一次 `pull_request_read` 之类工具，输入 token 很容易飙到几万。中转服务的限频策略如果是按 RPM 计算，可能会触发 429。
- **Hook 里调用外部命令**：Hook 自身是本地 shell，不走 API。但如果 Hook 内部又用了 `curl` 调 LLM，请确认那个 curl 也指向中转，而不是默认官方。
- **PreCompact 钩子**：长会话会自动压缩，压缩本身也是 LLM 请求。中转必须支持完整 Messages 协议（含 system prompt 数组、cache_control 字段），否则压缩失败导致整个会话报错。

## 六、故障排查清单

下面这张表按错误码排序，是最常见的中转问题：

| 现象 | 多半原因 | 处理方法 |
| --- | --- | --- |
| `401 Unauthorized` | Token 写错、过期、没充值 | 在网关后台核对 Key 与余额 |
| `403 Forbidden` | Key 没有目标模型权限 | 检查网关的模型白名单 |
| `404 Not Found` | base_url 多了 `/v1`，或模型名错 | 去掉 `/v1`；用网关支持的模型名 |
| `429 Too Many Requests` | 短时间内并发过高 | 降低 Subagent 并发；检查 RPM/TPM 上限 |
| `502 / 504` | 中转上游断流 | 切换备用网关；缩短 system prompt |
| 首 token 超过 8 秒 | 网络绕路 | 换节点或换中转 |
| 流式输出中断 | SSE 没正确转发 | 确认网关支持 `stream` |
| 中文乱码 | 网关 gzip 配置错误 | 临时关闭流式定位问题 |

## 七、最小验证脚本

把下面这段保存为 `smoke_claude.sh`，用来快速验证一个新的中转 URL 是否真的可用：

```bash
#!/usr/bin/env bash
set -e
: "${ANTHROPIC_BASE_URL:?need base url}"
: "${ANTHROPIC_AUTH_TOKEN:?need token}"

curl -sS -X POST "$ANTHROPIC_BASE_URL/v1/messages" \
  -H "x-api-key: $ANTHROPIC_AUTH_TOKEN" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{
    "model": "claude-sonnet-4-6",
    "max_tokens": 64,
    "messages": [{"role": "user", "content": "回答：1+1=？只回答数字。"}]
  }' | head -c 500
```

正常返回里能看到 `"content":[{"type":"text","text":"2"}]` 才算通。

## 八、安全边界提醒

- **API Key 永远不要提交到 git**。Claude Code 的 `.claude/settings.json` 可以提交，但 `.env` 不要。
- **不要把同一个 key 同时给多人共用**。配额耗光后排查归属会非常麻烦。
- **生产环境隔离 key**。给 Claude Code 用的 key、给 CI 用的 key、给业务后端用的 key，建议分开签发，方便单独吊销。

## 九、相关阅读

- [Cursor API 中转怎么选：2026 实用清单](/blog/2026-05-15-cursor-api-relay-recommendation-2026/)
- [OpenAI SDK base_url 国内配置](/blog/openai-sdk-base-url-cn/)
- [AI API 中转稳定性测试方法](/blog/ai-api-relay-stability-test/)
- [Claude Sonnet 4.6 与 Opus 4.7 怎么选](/blog/claude-sonnet-4-6-vs-opus-4-7/)

如果想先用最小流量验证 Claude Code 在国内的可用性，可以在 [YoTradeApi 注册](https://yotradeapi.com) 创建独立 API Key，按上面的 5 行环境变量直接接入，跑通后再决定要不要扩量。
