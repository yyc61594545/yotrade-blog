---
title: 自定义 MCP Server 开发实战（Python + TypeScript）
description: 用 Python FastMCP 和 TypeScript SDK 开发一个完整 MCP Server 的完整教程，含工具定义、状态管理、调试、发布与安全。
keywords:
- mcp server 开发
- 自定义 mcp
- fastmcp
- mcp typescript
- mcp protocol
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/mcp-custom-server-development/
tags:
- MCP
- Python
- TypeScript
- SDK
- 开发
category: 工程实战
heroImage: ../../assets/blog-placeholder-4.jpg
---

# 自定义 MCP Server 开发实战（Python + TypeScript）

接入官方 MCP server 是消费侧；自己写一个 MCP server 是生产侧。本文用 Python 和 TypeScript 各写一个完整 MCP server，覆盖工具、状态、调试、发布、安全。

## 一、MCP 协议速览

MCP 客户端（Cursor / Claude Code 等）通过 stdio / SSE / HTTP 与 server 通讯，调用三类对象：

- **Tools**：可执行函数
- **Resources**：可读取的数据
- **Prompts**：预定义 prompt 模板

最常见的是 Tools。本文重点。

## 二、Python：FastMCP

最简单。`pip install mcp`：

```python
# weather_server.py
from mcp.server.fastmcp import FastMCP
import httpx

mcp = FastMCP("weather")

@mcp.tool()
async def get_weather(city: str) -> str:
    """获取中国城市的天气
    
    Args:
        city: 城市名，如 北京、上海、深圳
    """
    async with httpx.AsyncClient() as client:
        r = await client.get(f"https://wttr.in/{city}?format=3", timeout=5)
        return r.text

@mcp.tool()
async def list_cities() -> list[str]:
    """列出支持的城市"""
    return ["北京", "上海", "深圳", "广州", "杭州"]

if __name__ == "__main__":
    mcp.run()
```

完事。`@mcp.tool()` 装饰器自动从函数签名 + docstring 生成 schema。

跑：

```bash
python weather_server.py
```

或在 client 配置里：

```json
{
  "weather": {
    "command": "python",
    "args": ["/path/to/weather_server.py"]
  }
}
```

## 三、TypeScript：MCP SDK

```bash
npm init -y
npm install @modelcontextprotocol/sdk
```

```ts
// server.ts
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

const server = new Server(
  { name: "weather", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "get_weather",
      description: "获取中国城市的天气",
      inputSchema: {
        type: "object",
        properties: {
          city: { type: "string", description: "城市名" },
        },
        required: ["city"],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (req) => {
  if (req.params.name === "get_weather") {
    const city = req.params.arguments?.city;
    const r = await fetch(`https://wttr.in/${city}?format=3`);
    const text = await r.text();
    return { content: [{ type: "text", text }] };
  }
  throw new Error("unknown tool");
});

const transport = new StdioServerTransport();
await server.connect(transport);
```

配置：

```json
{
  "weather-ts": {
    "command": "node",
    "args": ["dist/server.js"]
  }
}
```

## 四、状态：在 server 里持久化

MCP server 是长连接进程，可以持久化状态：

```python
state = {"counter": 0, "items": []}

@mcp.tool()
async def add_item(name: str) -> str:
    state["items"].append({"id": state["counter"], "name": name})
    state["counter"] += 1
    return f"added id={state['counter']-1}"

@mcp.tool()
async def list_items() -> list[dict]:
    return state["items"]
```

但**注意**：state 在 process 重启时丢失。需要持久化用 sqlite / 文件。

## 五、Resources（可读数据）

不只是函数。Resources 让 LLM 主动读取数据：

```python
@mcp.resource("db://users/{user_id}")
async def get_user(user_id: str) -> str:
    user = await db.fetch_user(user_id)
    return json.dumps(user)
```

LLM 可以 read `db://users/123`。**适合"数据查询而非动作"**。

## 六、Prompts（模板）

```python
@mcp.prompt()
def code_review(code: str, language: str = "python") -> str:
    return f"""请评审以下 {language} 代码：

```{language}
{code}
```

按以下维度：
1. 正确性
2. 性能
3. 可读性
4. 安全
"""
```

Client 看到这个 prompt 可以让用户一键调用。

## 七、错误处理

```python
@mcp.tool()
async def divide(a: float, b: float) -> float:
    """除法"""
    if b == 0:
        raise ValueError("除数不能为 0")
    return a / b
```

抛 Python 异常会自动转 MCP error，模型看到错误信息会自适应。

## 八、本地调试

用 MCP Inspector：

```bash
npx -y @modelcontextprotocol/inspector python weather_server.py
```

打开浏览器 UI，能：

- 看 server 暴露的所有 tools / resources / prompts
- 手动调用 tool 看返回
- 看完整 JSON-RPC 协议交互

调试 server 必备。

## 九、HTTP / SSE 传输

stdio 适合本地。**远程 server 用 HTTP**：

```python
# 用 FastMCP HTTP 模式
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("weather", host="0.0.0.0", port=8765)
# ... tool 定义同上

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

客户端配置：

```json
{
  "weather": {
    "type": "http",
    "url": "https://your-server.com/mcp",
    "headers": {"Authorization": "Bearer token"}
  }
}
```

## 十、安全

### 1. 权限边界

```python
ALLOWED_DIRS = {"/home/user/workspace"}

@mcp.tool()
async def read_file(path: str) -> str:
    abs_path = os.path.realpath(path)
    if not any(abs_path.startswith(d) for d in ALLOWED_DIRS):
        raise PermissionError("forbidden path")
    return open(abs_path).read()
```

**所有路径相关的 tool 必须 whitelist**。

### 2. SQL 注入防御

```python
@mcp.tool()
async def query_user(user_id: int) -> dict:
    # 用参数化查询，不要拼字符串
    return await db.fetch_one("SELECT * FROM users WHERE id = $1", user_id)
```

### 3. 命令注入防御

```python
@mcp.tool()
async def run_test(name: str) -> str:
    # ✗ 危险：直接拼接
    # os.system(f"pytest {name}")
    
    # ✓ 安全：明确参数
    import subprocess, re
    if not re.match(r"^[a-zA-Z0-9_]+$", name):
        raise ValueError("invalid test name")
    return subprocess.run(["pytest", name], capture_output=True).stdout
```

### 4. 鉴权（HTTP 模式）

```python
from fastapi import Depends, HTTPException, Header

async def verify_token(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401)
    token = authorization[7:]
    if not is_valid_token(token):
        raise HTTPException(403)
```

## 十一、发布到 npm / pypi

让别人也能用你的 server：

### Python（pypi）

```toml
# pyproject.toml
[project]
name = "mcp-weather"
version = "1.0.0"
dependencies = ["mcp", "httpx"]

[project.scripts]
mcp-weather = "weather_server:main"
```

```bash
pip install build
python -m build
twine upload dist/*
```

用户：`pip install mcp-weather`，配置 `command: mcp-weather`。

### TypeScript（npm）

```json
{
  "name": "mcp-weather",
  "bin": {
    "mcp-weather": "dist/server.js"
  }
}
```

```bash
npm publish
```

用户：`npx -y mcp-weather`。

## 十二、典型自建 MCP 用例

- 公司内部知识库（接 Confluence / Notion 私有 API）
- 业务数据查询（接你的 admin API）
- DevOps 工具（接你的 CI/CD）
- 自定义代码搜索（接你的代码索引）
- 浏览器自动化（接 Playwright）

## 十三、相关阅读

- [MCP 服务器实战](/blog/mcp-server-cn-guide/)
- [Claude Code Subagent 实战](/blog/claude-code-subagent-practice/)
- [Claude Code Hooks 工作流](/blog/claude-code-hooks-workflow/)
- [Claude 并行 Tool Use 实战](/blog/parallel-tool-use-claude/)
- [AI API 中转的安全与合规边界](/blog/api-relay-security-compliance/)

自建 MCP server 配 [YoTradeApi](https://yotradeapi.com/register) 中转，按上面 demo 跑通后接入 Cursor / Claude Code 即可。
