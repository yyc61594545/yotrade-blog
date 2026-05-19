---
title: Claude Code Hooks 工作流：8 种钩子的实战用法
description: Claude Code 全部 hook 事件解析与实战用法：PreToolUse、PostToolUse、SessionStart、Stop、PreCompact、UserPromptSubmit 等。
keywords:
- claude code hooks
- claude code 钩子
- pretooluse hook
- claude code 自动化
- session start hook
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/claude-code-hooks-workflow/
tags:
- Claude Code
- Hooks
- 自动化
- 工作流
- 最佳实践
category: 工具配置
heroImage: ../../assets/blog-placeholder-4.jpg
---

# Claude Code Hooks 工作流：8 种钩子的实战用法

Claude Code 的 hook 系统让你在 LLM 行为的关键节点插入自己的逻辑：阻止危险命令、自动跑测试、注入项目知识、控制压缩……本文按 hook 类型实战展开。

## 一、Hook 系统总览

Claude Code 当前支持的 hook 事件：

| Hook | 触发时机 | 典型用途 |
| --- | --- | --- |
| `SessionStart` | 会话启动 | 注入项目知识、设置环境 |
| `UserPromptSubmit` | 用户发送 prompt 后、模型调用前 | 注入上下文、prompt 改写、审计 |
| `PreToolUse` | 调用工具前 | 阻止危险命令、需要批准 |
| `PostToolUse` | 工具调用完成 | 跑 lint、记录日志 |
| `PreCompact` | 上下文压缩前 | 保护关键信息 |
| `Notification` | LLM 主动通知 | 桌面提醒 |
| `Stop` | 会话结束 | 清理、汇报 |
| `SubagentStop` | Subagent 结束 | 汇总 subagent 结果 |

Hook 是任意 shell 命令；通信通过环境变量与 stdin/stdout/stderr。

## 二、配置方式

在 `~/.claude/settings.json` 或项目 `.claude/settings.json`：

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command", "command": "/path/to/pre-bash.sh" }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": "/path/to/post-edit.sh" }
        ]
      }
    ]
  }
}
```

`matcher` 是工具名正则，匹配后才触发。

## 三、SessionStart：注入项目知识

```bash
#!/usr/bin/env bash
# .claude/hooks/session-start.sh
# 输出会被加进 system context
echo "## 项目知识"
echo ""
echo "- 数据库：PostgreSQL 15，schema 见 docs/schema.md"
echo "- 部署：Cloudflare Pages，分支自动部署"
echo "- 命名：JS 用 camelCase，Python 用 snake_case"
echo "- 测试：npm test（jest），目标覆盖 70%+"
echo ""
echo "## 当前 git 状态"
git -C "$CLAUDE_PROJECT_DIR" status --short 2>/dev/null | head -20
```

设置：

```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [{ "type": "command", "command": ".claude/hooks/session-start.sh" }] }
    ]
  }
}
```

效果：每次启动 Claude Code，主 agent 都自带项目背景，不用每次重新粘贴 system prompt。

## 四、UserPromptSubmit：审计与改写

```bash
#!/usr/bin/env bash
# .claude/hooks/user-prompt.sh
# 用户的 prompt 在 stdin
prompt=$(cat)

# 审计到日志
echo "$(date -u +%FT%TZ)|$USER|$(echo "$prompt" | head -c 200)" >> ~/.claude/audit.log

# 把 prompt 原样吐回
echo "$prompt"
```

或更高级——自动追加项目最新 commit 信息：

```bash
#!/usr/bin/env bash
prompt=$(cat)
echo "$prompt"
echo ""
echo "[hook] 最新 5 个 commit："
git -C "$CLAUDE_PROJECT_DIR" log --oneline -5 2>/dev/null
```

注意：`UserPromptSubmit` 的 stdout 会被附加到 prompt 末尾。慎用——内容多了占 token。

## 五、PreToolUse：阻止危险命令

```bash
#!/usr/bin/env bash
# .claude/hooks/pre-bash.sh
# $CLAUDE_TOOL_INPUT 是工具参数 JSON

cmd=$(echo "$CLAUDE_TOOL_INPUT" | jq -r '.command')

# 黑名单
case "$cmd" in
  *"rm -rf"*) echo "blocked: rm -rf" >&2; exit 2 ;;
  *"git push --force"*) echo "blocked: force push" >&2; exit 2 ;;
  *"DROP TABLE"*) echo "blocked: drop table" >&2; exit 2 ;;
  *":(){:|:&};:"*) echo "blocked: fork bomb" >&2; exit 2 ;;
esac

# 通过
exit 0
```

`exit 2` 表示拦截，Claude Code 会把 stderr 反馈给模型。模型会自适应（要么换方式，要么报错）。

## 六、PostToolUse：自动跑 lint

```bash
#!/usr/bin/env bash
# .claude/hooks/post-edit.sh
# Edit/Write 完成后跑

file=$(echo "$CLAUDE_TOOL_INPUT" | jq -r '.file_path')

case "$file" in
  *.ts|*.tsx)
    cd "$CLAUDE_PROJECT_DIR" && npx prettier --write "$file" >/dev/null 2>&1
    cd "$CLAUDE_PROJECT_DIR" && npx eslint "$file" --fix >/dev/null 2>&1
    ;;
  *.py)
    cd "$CLAUDE_PROJECT_DIR" && ruff check --fix "$file" >/dev/null 2>&1
    cd "$CLAUDE_PROJECT_DIR" && ruff format "$file" >/dev/null 2>&1
    ;;
esac
```

效果：模型改完代码立刻格式化，agent 不用学会"先格式化再 commit"。

## 七、PreCompact：保护关键信息

长会话自动压缩时，hook 可以注入「不要压缩什么」：

```bash
#!/usr/bin/env bash
# .claude/hooks/pre-compact.sh
echo "压缩时务必保留："
echo "- 用户已确认的 API 设计决策"
echo "- 当前任务的验收标准"
echo "- 测试失败时的 root cause"
```

## 八、Stop：会话结束汇报

```bash
#!/usr/bin/env bash
# .claude/hooks/stop.sh
echo "session ended at $(date)"
git -C "$CLAUDE_PROJECT_DIR" log --oneline HEAD@{1}..HEAD 2>/dev/null | head -10
```

效果：每次退出看到本次会话的 commit 列表。

## 九、Notification：钉钉/Slack 提醒

```bash
#!/usr/bin/env bash
# .claude/hooks/notification.sh
msg=$(cat)
curl -s -X POST "$DINGTALK_WEBHOOK" \
  -H 'Content-Type: application/json' \
  -d "{\"msgtype\":\"text\",\"text\":{\"content\":\"Claude Code: $msg\"}}" >/dev/null
```

效果：长任务跑完模型 ping 一下，你手机就收到通知，不用守在终端。

## 十、Hook 写法纪律

- **快**：hook 阻塞 LLM。慢 hook = 慢响应。控制在 < 1s。
- **幂等**：可能被重复调用，要兼容。
- **错误处理**：失败时 stderr 写清楚，不要静默。
- **副作用最小**：不要写一堆全局状态。
- **可调试**：先用 `echo "..."  >> /tmp/claude-hook.log` 做基础调试。

## 十一、共享 hook 到团队

把 hook 脚本 commit 进项目 `.claude/hooks/`，配置写在 `.claude/settings.json`，团队成员 clone 项目就有同样的工作流。**敏感信息**（如钉钉 webhook）放 `.env` 不要 commit。

## 十二、相关阅读

- [Claude Code 镜像国内配置完整指南](/blog/claude-code-mirror-cn-setup/)
- [Claude Code Subagent 实战](/blog/claude-code-subagent-practice/)
- [Cursor API 中转怎么选](/blog/2026-05-15-cursor-api-relay-recommendation-2026/)
- [AI 编程代理成本控制实战](/blog/ai-coding-agent-cost-control/)

需要给 Claude Code Hooks 配一个稳定的 base_url？[YoTradeApi](https://yotradeapi.com) 后台支持独立 Key，方便给每个 hook 用例分配独立 token。
