---
title: MCP 服务器实战：Claude Code/Cursor/Cherry Studio 接入
description: Model Context Protocol（MCP）服务器在国内开发者工具里的接入方法，含 filesystem/github/postgres 配置、自定义 server、安全边界。
keywords:
- mcp 服务器
- model context protocol
- claude code mcp
- cursor mcp
- mcp 配置
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/mcp-server-cn-guide/
tags:
- MCP
- Model Context Protocol
- Claude Code
- Cursor
- 工具集成
category: 工具配置
heroImage: ../../assets/blog-placeholder-1.jpg
---

# MCP 服务器实战：Claude Code/Cursor/Cherry Studio 接入

MCP（Model Context Protocol）是 Anthropic 推出的开放协议，让 LLM 客户端能用同一套接口接入任何工具与数据源。2025 年 MCP 生态爆发，几乎所有主流 LLM 客户端都支持。本文给一份不绕弯子的接入指南。

## 一、MCP 是什么

简单说：**一个 LLM 客户端（Cursor / Claude Code / Cherry Studio）→ 一个 MCP 服务器（filesystem / github / postgres / ...）→ 一组工具**。

MCP 标准化了：

- 工具定义格式（schema）
- 调用协议（JSON-RPC over stdio / SSE / HTTP）
- 权限模型
- 状态管理

最大价值：**写一个 MCP server，所有支持 MCP 的客户端都能用**。

## 二、常用官方 MCP server

```bash
# filesystem：读写本地文件
npx -y @modelcontextprotocol/server-filesystem /path

# github：查 PR / issue / repo
npx -y @modelcontextprotocol/server-github

# brave-search：联网搜索
npx -y @modelcontextprotocol/server-brave-search

# postgres：查数据库
npx -y @modelcontextprotocol/server-postgres postgresql://...

# slack：发消息
npx -y @modelcontextprotocol/server-slack

# memory：跨会话记忆
npx -y @modelcontextprotocol/server-memory
```

## 三、在 Claude Code 接入

编辑 `~/.claude/settings.json`（或项目 `.claude/settings.json`）：

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/you/projects"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxx"
      }
    }
  }
}
```

重启 `claude`。`/mcp` 命令查看接入的 server 与可用工具。

## 四、在 Cursor 接入

设置 → MCP → Add Server：

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/you/projects"]
    }
  }
}
```

Cursor 在 Composer 模式下自动让 agent 使用 MCP 工具。

## 五、在 Cherry Studio 接入

设置 → MCP 服务器 → 添加，UI 直接填字段，不需要写 json。Cherry Studio 还提供"市场"，一键安装常用 server。

## 六、token 成本警告

MCP 不是免费午餐。每个 server 装入后：

- 所有工具的 schema 会被加入 system prompt
- 一个 server 平均 5–10 个工具
- 每个工具 schema 平均 300–800 tokens
- 加 5 个 server = 多 8–15k tokens **每次请求都付**

按月算，无意义的 MCP 启用一个月能多花几十美金。**纪律**：

- 当前任务用不到的 server **关掉**
- 项目 / 全局两层配置：全局只留 filesystem / memory，项目按需开
- 配合 prompt caching，命中后这部分变便宜

## 七、写一个自定义 MCP server

20 行 Python 就能起一个 server。装：

```bash
pip install mcp
```

写 `weather_server.py`：

```python
from mcp.server.fastmcp import FastMCP
import httpx

mcp = FastMCP("weather")

@mcp.tool()
async def get_weather(city: str) -> str:
    """获取一个中国城市的天气"""
    r = httpx.get(f"https://wttr.in/{city}?format=3")
    return r.text

if __name__ == "__main__":
    mcp.run()
```

在客户端配置：

```json
{
  "mcpServers": {
    "weather": {
      "command": "python",
      "args": ["/path/to/weather_server.py"]
    }
  }
}
```

完事。

## 八、安全边界

MCP 服务器拿到的权限 = 模型能间接调用的命令。常见风险：

| Server | 风险 |
| --- | --- |
| filesystem | 路径越界（暴露 ~/.ssh） |
| github | token 权限过大 |
| postgres | 写 SQL 损坏数据 |
| shell | 命令注入 |
| browser | 上传敏感页面 |

防御：

- **filesystem 只指向工作目录**，不要给 home
- **github token 用 fine-grained PAT**，只授给你需要的 repo
- **postgres 用只读账号**
- **不装来路不明的第三方 MCP**
- **重要操作启用 Approval**（Cursor / Cline / Claude Code 都支持）

## 九、HTTP vs stdio MCP

| 传输 | 何时用 |
| --- | --- |
| stdio | 本地工具（filesystem、shell） |
| SSE | 服务端长连接 |
| streamable HTTP | 远程托管 server |

远程 SaaS 的 MCP（比如 GitHub 的 HTTP MCP、Notion 的 MCP）走 HTTP，需要 OAuth 或 API Key。配置：

```json
{
  "github-remote": {
    "type": "http",
    "url": "https://api.githubcopilot.com/mcp/",
    "headers": {
      "Authorization": "Bearer ghp_xxx"
    }
  }
}
```

## 十、调试技巧

MCP 服务器跑挂了排查：

1. **直接终端跑 command**：手动 `npx -y @modelcontextprotocol/server-xxx` 看输出
2. **Inspector**：`npx -y @modelcontextprotocol/inspector` 启动 web UI，连任意 server 看工具列表
3. **客户端 log**：Cursor 的 Output 面板、Claude Code 的 `--verbose` 模式

## 十一、相关阅读

- [Claude Code 镜像国内配置完整指南](/blog/claude-code-mirror-cn-setup/)
- [Cursor API 中转怎么选](/blog/2026-05-15-cursor-api-relay-recommendation-2026/)
- [Cherry Studio 国内 API 中转配置指南](/blog/cherry-studio-cn-config/)
- [Claude Code Subagent 实战](/blog/claude-code-subagent-practice/)

需要把 MCP 用得稳又便宜？配合 [YoTradeApi](https://yotradeapi.com) 的 prompt caching + 按 key 预算上限，MCP 的固定开销也可控。
