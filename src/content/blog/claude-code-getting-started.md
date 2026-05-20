---
title: Claude Code 新手完整教程：从安装到第一个长任务
description: 第一次用 Claude Code CLI？这份教程从安装、5 行环境变量配置、第一个对话、工具使用、settings.json 完整覆盖。
keywords:
- claude code 教程
- claude code 怎么用
- claude code 入门
- claude code 新手
- claude cli 教程
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/claude-code-getting-started/
tags:
- Claude Code
- 入门
- CLI
- 教程
category: 入门
heroImage: ../../assets/blog-placeholder-2.jpg
---

Claude Code 是 Anthropic 官方的命令行 AI 编程代理。它把"在终端里和 AI 协作"做到了极致。本教程从安装到完成第一个长任务，一步步带你上手。

## 一、Claude Code 是什么

简单理解：**Claude Code = "用自然语言代替命令的 shell"**。

你在终端里和它对话，它能：

- 读你的代码
- 改你的代码
- 跑你的命令（包括测试）
- 自己规划长任务
- 调用 Subagent 拆分子任务

它**不是 IDE 插件**——独立 CLI，可以在任何终端跑。

## 二、安装

```bash
# 需要 Node.js 22+
node --version

# 全局安装
npm install -g @anthropic-ai/claude-code

# 验证
claude --version
```

如果 npm 慢，可以用淘宝镜像：

```bash
npm config set registry https://registry.npmmirror.com
npm install -g @anthropic-ai/claude-code
```

## 三、5 行环境变量启动

国内用户必须先把 base_url 指向中转：

```bash
export ANTHROPIC_BASE_URL="https://yotradeapi.com"
export ANTHROPIC_AUTH_TOKEN="sk-your-yotrade-key"
export ANTHROPIC_MODEL="claude-sonnet-4-6"
```

写进 `~/.zshrc` 或 `~/.bashrc` 永久生效。

详见 [Claude Code 镜像国内配置完整指南](/blog/claude-code-mirror-cn-setup/)。

## 四、第一次启动

```bash
cd your-project
claude
```

第一次会问几个问题：

- 选权限模式：**`On Request`** 起步（每次工具调用都批准）
- 选模型：默认就行
- 是否信任当前目录：选 yes（你信你自己的项目）

进入交互界面：

```
> Welcome to Claude Code!

Working directory: /Users/you/your-project

>
```

可以开始打字了。

## 五、第一个对话

```
> 这个项目是干什么的？
```

Claude 会自动读 `README.md`、`package.json`、关键目录，给你一份项目介绍。

```
> 当前代码有哪些值得优化的地方？
```

它会逐文件分析，给出建议。**它默认是 read-only 的，不会乱改文件**。

## 六、让它改文件

```
> 修改 src/utils.ts 里的 fetchData 函数，添加超时和重试。
```

Claude 会：

1. 用 Read 工具读 utils.ts
2. 给你看它要怎么改
3. **弹一个批准提示**（Approve / Reject）
4. 你按 y 接受
5. Edit 工具写入文件
6. 报告"完成"

第一次会觉得"步骤很多"。**但这正是它安全的原因**——每个动作你都看得到。

## 七、让它跑命令

```
> 跑 npm test，把失败的修了。
```

Claude 用 Bash 工具跑 `npm test`，看输出，识别哪些失败，逐个修。**每跑一个命令都会问你**。

如果你信任某些命令不需要每次确认，可以在 `.claude/settings.json` 写白名单：

```json
{
  "permissions": {
    "allow": [
      "Bash(npm test:*)",
      "Bash(npm run lint:*)",
      "Bash(git diff:*)",
      "Bash(git log:*)"
    ],
    "deny": [
      "Bash(rm -rf:*)",
      "Bash(git push --force:*)"
    ]
  }
}
```

## 八、用 Subagent

Claude Code 内置了几个 Subagent。最有用的是 `Explore`：

```
> 用 Explore subagent 找出项目里所有调用 fetchUser 的地方
```

Subagent 在独立上下文里搜索，结果回流给主对话。**主对话上下文不被污染**。

定义自己的 Subagent（在 `.claude/agents/code-reviewer.md`）：

```markdown
---
name: code-reviewer
description: 代码评审
model: claude-sonnet-4-6
tools: Read, Grep
---

你是 senior 工程师。评审代码给出 Blocking / Nice-to-have / Praise 三类。
简洁、具体。
```

然后：

```
> 用 code-reviewer 评审 src/auth/middleware.ts
```

详见 [Claude Code Subagent 实战](/blog/claude-code-subagent-practice/)。

## 九、CLAUDE.md：项目知识

在项目根创建 `CLAUDE.md`：

```markdown
# 项目知识

## 技术栈
- Next.js 15 + Prisma + PostgreSQL
- 部署：Cloudflare Pages

## 约定
- 函数 camelCase
- 测试用 jest
- 公开 API 必须返回 `{ ok, data?, error? }`

## 不要做
- 不动 prisma migrations
- 不引入新依赖
```

每次启动 Claude Code 都会自动读这份文件。**写好 = AI 立刻懂项目**。

## 十、第一个长任务

```
> 把 src/legacy/utils.ts 重构：
> 1. 加完整 TypeScript 类型
> 2. 把 callback 改成 async/await
> 3. 加单元测试覆盖所有公开函数
> 4. 跑 npm test 验证
> 5. 改完总结改了什么
```

Claude 会跑 20–40 分钟，期间：

- 反复 Read / Edit
- 跑 npm test
- 失败自动修
- 全部通过后总结

**第一次看会觉得震撼**。这是 Claude Code 的核心价值。

## 十一、五个最有用的命令

| 命令 | 作用 |
| --- | --- |
| `/help` | 看所有命令 |
| `/model` | 切换模型 |
| `/clear` | 清空当前对话 |
| `/compact` | 压缩历史以节省 token |
| `/mcp` | 看 MCP server 状态 |
| `/agents` | 列出 Subagent |

## 十二、什么时候不该用 Claude Code

- 简单一两行改动（直接编辑器改更快）
- 涉及生产数据库操作（自己来更安全）
- 涉及密钥 / secrets 配置
- 不熟悉的、风险大的命令（先在测试环境跑）

## 十三、避坑

1. **第一次别给 dangerously-skip-permissions**——每个动作要确认
2. **CLAUDE.md 写好再开工**——AI 没上下文等于盲跑
3. **长任务用 Plan Mode**：先让 AI 给出方案，你审核，再让它执行
4. **定期 /clear**：长会话上下文膨胀，token 烧得快
5. **关注中转账单**：第一次长任务跑完就看看花了多少

## 十四、下一步学什么

| 下一步 | 看这个 |
| --- | --- |
| 配置中转 | <a href="/blog/claude-code-mirror-cn-setup/">Claude Code 国内配置</a> |
| 用 Subagent | <a href="/blog/claude-code-subagent-practice/">Subagent 实战</a> |
| 用 Hook | <a href="/blog/claude-code-hooks-workflow/">Hooks 工作流</a> |
| 接 CI | <a href="/blog/claude-code-ci-integration/">CI/CD 接入</a> |
| 控成本 | <a href="/blog/ai-coding-agent-cost-control/">成本控制</a> |
| 选模型 | <a href="/blog/claude-sonnet-4-6-vs-opus-4-7/">Sonnet vs Opus</a> |

## 十五、相关阅读

- [Claude Code 镜像国内配置完整指南](/blog/claude-code-mirror-cn-setup/)
- [Cursor vs Claude Code](/blog/cursor-vs-claude-code-comparison/)
- [Claude Code Subagent 实战](/blog/claude-code-subagent-practice/)
- [AI Agent Prompt Engineering 中文实战](/blog/agent-prompt-engineering-cn/)
- [2026 AI 编程工具全景图](/blog/ai-coding-tools-2026-overview/)

注册 [YoTradeApi](https://yotradeapi.com) 创建独立 API Key，按本教程第 3 节 5 行环境变量配置直接接入 Claude Code。
