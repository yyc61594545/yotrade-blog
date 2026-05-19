---
title: Claude Agent SDK 国内接入与实战
description: Anthropic Claude Agent SDK 在国内通过中转的接入方法，含 Subagent 定义、Hook 拦截、tool 注册、自定义 agent 的完整代码。
keywords:
- claude agent sdk
- anthropic agent sdk
- claude agent 中转
- claude 自定义 agent
- subagent 编程
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/claude-agent-sdk-cn/
tags:
- Anthropic
- Agent SDK
- Claude
- 工程实战
- Subagent
category: 工程实战
heroImage: ../../assets/blog-placeholder-4.jpg
---

# Claude Agent SDK 国内接入与实战

Anthropic 把 Claude Code 内部的 agent 能力开放成了 Claude Agent SDK——任何应用都能调用 Claude 跑代码、改文件、运行 shell。本文给国内通过中转的接入与实战。

## 一、Claude Agent SDK 是什么

可以理解为"把 Claude Code 当 SDK 用"：

- 你的应用 import 这个 SDK
- 启动一个 agent，给它任务
- agent 在沙箱里跑 LLM + 工具
- 你拿到结果

适合场景：

- 自动化运维脚本（让 agent 处理日常 ticket）
- CI/CD 集成（自动修 lint / 跑测试）
- 内部 IDE / 编辑器扩展
- 客服自动化（带工具能力的客服）

## 二、安装

```bash
# Python
pip install claude-agent-sdk

# Node
npm install @anthropic-ai/claude-agent-sdk
```

## 三、走中转

环境变量：

```bash
export ANTHROPIC_BASE_URL="https://yotradeapi.com"
export ANTHROPIC_AUTH_TOKEN="sk-yo-..."
```

SDK 自动读这些。

## 四、最小 agent（Python）

```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions

async def main():
    options = ClaudeAgentOptions(
        model="claude-sonnet-4-6",
        max_turns=10,
        cwd="/path/to/project",
        permission_mode="bypassPermissions",   # 完全自动；生产用 approveOnce
    )
    async for message in query(
        prompt="读 README.md 然后给出一份项目简介",
        options=options,
    ):
        print(message)

asyncio.run(main())
```

`query()` 返回异步流。每个 message 是 agent 的一步动作或结果。

## 五、自定义 Subagent

`.claude/agents/code-reviewer.md`：

```markdown
---
name: code-reviewer
description: 严谨代码评审
tools: Read, Grep
model: claude-sonnet-4-6
---

你是 senior 工程师。评审代码给：
- Blocking 问题（必改）
- Nice-to-have 建议
- Praise（值得肯定）

简洁、具体，少废话。
```

在主 agent prompt 里调用：

```python
options = ClaudeAgentOptions(
    agents_dir=".claude/agents",
    max_turns=20,
)

async for msg in query(
    prompt="用 code-reviewer subagent 评审 src/api/users.ts",
    options=options,
):
    ...
```

主 agent 看到这个指令会自动 dispatch 给 code-reviewer。

## 六、注册自定义工具

```python
from claude_agent_sdk import tool

@tool(
    "lookup_user",
    "查询用户信息",
    {"user_id": str},
)
async def lookup_user(args):
    user = await db.fetch_user(args["user_id"])
    return {
        "content": [{"type": "text", "text": str(user)}],
    }

options = ClaudeAgentOptions(
    tools=[lookup_user],
    max_turns=10,
)
```

类似 OpenAI Function Call，但和 SDK 的 agent loop 紧密集成。

## 七、Hook 拦截

```python
from claude_agent_sdk import HookMatcher, HookContext

async def pre_bash_hook(input_data, tool_use_id, context: HookContext):
    cmd = input_data["command"]
    if "rm -rf" in cmd or "git push --force" in cmd:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "blocked by safety hook",
            }
        }
    return {}

options = ClaudeAgentOptions(
    hooks={
        "PreToolUse": [
            HookMatcher(matcher="Bash", hooks=[pre_bash_hook])
        ]
    }
)
```

详细 hook 类型见 [Claude Code Hooks 工作流](/blog/claude-code-hooks-workflow/)。

## 八、Permission Mode

```python
permission_mode = "default"            # 每次工具调用都问
permission_mode = "acceptEdits"        # 接受 Edit/Write，其它问
permission_mode = "bypassPermissions"  # 完全自动（仅沙箱）
permission_mode = "plan"               # Plan Mode，只规划
```

CI / 服务端跑用 `bypassPermissions` + 严格沙箱。

## 九、流式响应处理

```python
async for message in query(prompt="...", options=options):
    match message.type:
        case "assistant_text":
            print(message.text)
        case "tool_use":
            print(f"调用 {message.name}: {message.input}")
        case "tool_result":
            print(f"工具结果: {message.content[:100]}")
        case "result":
            print(f"完成，总 token: {message.total_tokens}")
```

可以在 UI 实时展示 agent 的每步行动。

## 十、实战：自动 Triage GitHub Issue

```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, tool

@tool("get_issue", "读取 issue 内容", {"issue_id": int})
async def get_issue(args):
    issue = await github.get_issue(args["issue_id"])
    return {"content": [{"type": "text", "text": issue.body}]}

@tool("add_label", "给 issue 加标签", {"issue_id": int, "labels": list})
async def add_label(args):
    await github.add_labels(args["issue_id"], args["labels"])
    return {"content": [{"type": "text", "text": "done"}]}

@tool("comment", "回复 issue", {"issue_id": int, "body": str})
async def comment(args):
    await github.create_comment(args["issue_id"], args["body"])
    return {"content": [{"type": "text", "text": "done"}]}

async def triage(issue_id):
    options = ClaudeAgentOptions(
        tools=[get_issue, add_label, comment],
        max_turns=10,
        permission_mode="bypassPermissions",
    )
    async for msg in query(
        prompt=f"""分析 issue #{issue_id}。任务：
1. 读取 issue 内容
2. 判断类型（bug / feature / question / spam）
3. 加合适标签
4. 如果是 question，给出回答
5. 如果是 bug，要求 reporter 给重现步骤""",
        options=options,
    ):
        print(msg)

asyncio.run(triage(123))
```

接入 GitHub webhook，每个新 issue 自动 triage。

## 十一、Node.js SDK

```ts
import { query } from "@anthropic-ai/claude-agent-sdk";

const stream = query({
  prompt: "读 README 然后简述项目",
  options: {
    model: "claude-sonnet-4-6",
    maxTurns: 10,
    cwd: "/path/to/project",
  },
});

for await (const msg of stream) {
  console.log(msg);
}
```

API 风格类似 Python 版。

## 十二、与 Claude Code CLI 的关系

| 维度 | Claude Code CLI | Claude Agent SDK |
| --- | --- | --- |
| 形态 | 终端工具 | 库 |
| 用户 | 开发者交互 | 你的应用 |
| 工具 | 内置完整 | 自己注册 |
| 流式 | 终端展示 | 你处理 |
| 集成 | 独立运行 | 嵌入应用 |

简单说：**Claude Code 是 SDK 的一个具体实例**（带完整工具与终端 UI）。需要自定义 → SDK。

## 十三、与 OpenAI Agents SDK 对比

| 维度 | Claude Agent SDK | OpenAI Agents SDK |
| --- | --- | --- |
| 协议 | Anthropic Messages | OpenAI Responses |
| 工具默认 | Read/Write/Bash 等 | 完全自定义 |
| Hook 系统 | ✓（独有） | ✗ |
| Permission Mode | ✓ | 部分 |
| Subagent | ✓（独有） | Handoff |
| 沙箱 | 内置（OS） | 不强调 |

各有侧重。Claude Agent SDK 更"重"（内置工具丰富），OpenAI Agents SDK 更"轻"（专注 agent 编排）。

## 十四、中转配置

通过中转走 Anthropic Messages 协议。完整性确认：

```bash
curl https://yotradeapi.com/v1/messages \
  -H "x-api-key: $KEY" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model":"claude-sonnet-4-6",
    "max_tokens":64,
    "messages":[{"role":"user","content":"hi"}]
  }'
```

返回 200 即正常。

## 十五、相关阅读

- [Claude Code Subagent 实战](/blog/claude-code-subagent-practice/)
- [Claude Code Hooks 工作流](/blog/claude-code-hooks-workflow/)
- [OpenAI Agents SDK 国内接入](/blog/openai-agents-sdk-cn/)
- [Claude Code CI/CD 接入](/blog/claude-code-ci-integration/)
- [Claude Code 镜像国内配置完整指南](/blog/claude-code-mirror-cn-setup/)

需要 Claude Agent SDK 完整透传的中转？[YoTradeApi](https://yotradeapi.com) 完整支持 Anthropic Messages 协议 + beta headers，按上面 SDK 直接接入。
