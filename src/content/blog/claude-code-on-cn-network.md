---
title: Claude Code 在国内网络的实战配置
description: 国内开发者使用 Claude Code 必须面对的网络问题，从 API 中转到环境变量配置，手把手解决连接、鉴权与 MCP 的常见坑。
keywords:
  - Claude Code 国内
  - Claude Code 中转
  - anthropic api 国内访问
  - claude code 配置代理
  - claude code api base url
pubDate: '2026-05-23'
updatedDate: '2026-05-23'
canonical: https://blog.yotradeapi.com/blog/claude-code-on-cn-network/
tags:
  - Claude Code
  - 国内网络
  - 配置指南
  - API中转
category: 国内场景
heroImage: ../../assets/blog-placeholder-1.jpg
---

Claude Code 是目前体验最好的 AI 编程工具之一，但对国内开发者来说，第一道门槛不是学怎么用，而是怎么让它连上。本文整理了从安装到生产使用的完整配置路径，覆盖 API 中转、环境变量、MCP 配置和常见报错。

## 一、为什么国内直连会失败

Claude Code 底层调用 Anthropic API（`api.anthropic.com`），这个域名在大陆网络环境下访问不稳定，直连经常遇到：

- 连接超时（`Connection timed out`）
- TLS 握手失败（`SSL handshake failed`）
- 请求挂起后直接被 RST

即便你本机开了代理，Claude Code 的请求不一定走代理通道——它是 CLI 工具，环境变量配置和浏览器代理是两回事。

解决方案有两条路：

1. **让 CLI 走系统代理**（如果你有稳定的科学上网）
2. **使用 API 中转服务**（更推荐，不依赖个人代理稳定性）

## 二、方案 A：让 Claude Code 走系统代理

如果你已有代理服务（Clash、V2rayN 等），在终端里设置代理环境变量即可：

```bash
# HTTP/HTTPS 代理（替换为你的代理端口）
export HTTPS_PROXY=http://127.0.0.1:7890
export HTTP_PROXY=http://127.0.0.1:7890
export ALL_PROXY=socks5://127.0.0.1:7890

# 然后启动 Claude Code
claude
```

**每次打开终端都要设置**，建议加到 shell 配置文件里：

```bash
# 加到 ~/.bashrc 或 ~/.zshrc
export HTTPS_PROXY=http://127.0.0.1:7890
export HTTP_PROXY=http://127.0.0.1:7890
```

验证代理是否生效：

```bash
curl -x http://127.0.0.1:7890 https://api.anthropic.com/v1/models -H "x-api-key: YOUR_KEY"
```

返回 JSON 说明代理通了。

**局限性**：个人代理的稳定性和速度因线路而异，高峰期容易抖动。如果你在做需要长时间运行的 Agent 任务，中途断开会导致任务失败。

## 三、方案 B：使用 API 中转（推荐）

API 中转服务提供一个国内可访问的 API 端点，你的请求发到中转，中转再转发给 Anthropic。好处是：

- 不依赖本机代理稳定性
- 中转服务通常有多节点负载均衡，比个人线路稳
- 支持团队共享，不用每人都配代理

配置方式是设置 `ANTHROPIC_BASE_URL` 环境变量：

```bash
# 设置中转地址（以 YoTradeApi 为例）
export ANTHROPIC_BASE_URL=https://api.yotradeapi.com
export ANTHROPIC_API_KEY=your_relay_key

# 启动 Claude Code
claude
```

或者写到 shell 配置文件里：

```bash
# ~/.bashrc 或 ~/.zshrc
export ANTHROPIC_BASE_URL=https://api.yotradeapi.com
export ANTHROPIC_API_KEY=your_relay_key
```

**验证配置是否生效**：

```bash
# 用中转地址测试连通性
curl https://api.yotradeapi.com/v1/models \
  -H "x-api-key: your_relay_key" \
  -H "anthropic-version: 2023-06-01"
```

## 四、Claude Code 配置文件详解

除了环境变量，Claude Code 支持通过配置文件做持久化设置。配置文件位置：

```
~/.claude/settings.json        # 全局配置
<project>/.claude/settings.json  # 项目级配置（优先级更高）
```

一个典型的全局配置：

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.yotradeapi.com",
    "ANTHROPIC_API_KEY": "your_relay_key"
  },
  "model": "claude-sonnet-4-6",
  "permissions": {
    "allow": [
      "Bash(git:*)",
      "Bash(npm:*)",
      "Read(*)",
      "Edit(*)"
    ]
  }
}
```

`env` 字段里的环境变量会在 Claude Code 启动时自动注入，不需要每次手动 export。

**推荐做法**：不要把 API Key 硬编码在 settings.json 里提交到 Git——如果是团队共用，用环境变量注入；如果是个人机器，直接写 `~/.claude/settings.json`（不在 Git 里）。

## 五、不同系统的配置差异

### macOS

终端代理通常能覆盖 Claude Code，直接在 `.zshrc` 里设环境变量即可。注意 macOS 的系统代理设置（系统偏好设置→网络→代理）不等同于终端里的环境变量——两者独立。

```bash
# 验证终端环境变量是否生效
env | grep -i proxy
env | grep ANTHROPIC
```

### Linux

和 macOS 类似，在 `.bashrc` 或 `.bash_profile` 里设置即可。如果是服务器环境，可以用 systemd 的 `Environment` 字段注入。

### Windows（WSL2）

WSL2 内的网络和 Windows 主机不完全共享。如果 Windows 上有 Clash，WSL2 里默认不走这个代理。

```bash
# WSL2 里获取宿主机 IP
export WIN_HOST=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}')

# 设置代理指向宿主机
export HTTPS_PROXY=http://${WIN_HOST}:7890
```

或者直接用 API 中转，不需要处理 WSL2 的代理穿透问题。

## 六、MCP Server 在国内的注意事项

Claude Code 支持通过 MCP（Model Context Protocol）扩展功能，很多 MCP server 在启动时也会访问外部服务（npm registry、GitHub API 等）。

配置 MCP server 时，同样需要注意网络问题：

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/user"],
      "env": {
        "HTTPS_PROXY": "http://127.0.0.1:7890"
      }
    }
  }
}
```

`npx` 拉取 MCP server 包时访问 npm registry，国内也可能慢。建议配置 npm 镜像：

```bash
npm config set registry https://registry.npmmirror.com
```

或者提前 `npm install -g` 安装好 MCP server，避免每次启动时拉包。

## 七、常见报错与解决方案

### 报错：`ECONNREFUSED` 或 `ECONNRESET`

```
Error: connect ECONNREFUSED api.anthropic.com:443
```

**原因**：直连超时被拒绝。  
**解决**：设置 `ANTHROPIC_BASE_URL` 为中转地址，或者设置代理环境变量。

### 报错：`401 Unauthorized`

```
Error: 401 {"error":{"type":"authentication_error","message":"invalid x-api-key"}}
```

**原因**：API Key 错误，或者用的是 Anthropic 官方 Key 但设置了中转地址（中转服务需要中转平台的 Key）。  
**解决**：确认 `ANTHROPIC_API_KEY` 是中转平台颁发的 Key，不是 Anthropic 控制台的 Key。

### 报错：`Request timeout`

```
Claude Code request timed out after 60s
```

**原因**：网络延迟过高，或者模型处理时间过长。  
**解决**：
1. 检查代理/中转连通性
2. 对于长任务，Claude Code 本身有重试机制，等待即可
3. 如果频繁超时，换延迟更低的中转节点

### 报错：`SSL certificate verification failed`

```
SSL: CERTIFICATE_VERIFY_FAILED
```

**原因**：某些代理工具会注入自己的证书，导致 TLS 验证失败。  
**解决**：
```bash
export NODE_TLS_REJECT_UNAUTHORIZED=0
```
⚠️ 这会关闭证书验证，只在排查阶段临时用，生产不要这样做。正确做法是把代理的根证书加入系统信任。

## 八、团队多人配置的推荐方案

如果是团队使用，每人都配代理太繁琐，推荐的统一方案：

1. **共享中转账号**：团队购买一个 API 中转账号，统一分发 Key
2. **项目级 settings.json**：在代码仓库里放 `.claude/settings.json`，配置 `ANTHROPIC_BASE_URL`（不放 Key，Key 通过其他方式注入）
3. **CI/CD 环境**：在 GitHub Actions / GitLab CI 的环境变量里配置，让 Claude Code 在流水线里也能正常工作

```yaml
# GitHub Actions 示例
env:
  ANTHROPIC_BASE_URL: https://api.yotradeapi.com
  ANTHROPIC_API_KEY: ${{ secrets.RELAY_API_KEY }}
```

## 九、相关阅读

- [Claude Code 镜像中转配置指南](/blog/claude-code-mirror-cn-setup/)
- [Claude Code 入门上手指南](/blog/claude-code-getting-started/)
- [什么是 API 中转？一文讲清楚](/blog/what-is-api-relay-explained/)
- [Cline 国内 API 配置教程](/blog/cline-cn-api-setup/)
- [LLM API 错误重试策略设计](/blog/llm-error-retry-strategy/)

在国内稳定使用 Claude Code，[YoTradeApi](https://yotradeapi.com) 提供低延迟的 Anthropic API 中转，无需配置代理，直接设置 `ANTHROPIC_BASE_URL` 即可开始使用。
