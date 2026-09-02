---
title: Claude Code Hooks 配置实战：settings.json 层级与三个真实案例
description: 从 settings.json 的用户/项目/本地三层覆盖关系讲起，用三个真实生产场景（自动同步任务、拦截危险操作、多工具协同）拆解 Claude Code hooks 配置的实操细节与调试技巧。
keywords:
  - claude code hooks 配置
  - settings.json 层级
  - claude code 权限模式
  - hooks 调试
  - claude code 自动化配置
pubDate: '2026-09-02'
updatedDate: '2026-09-02'
canonical: https://blog.yotradeapi.com/blog/claude-code-hooks-config/
tags:
  - Claude Code
  - Hooks
  - 工具配置
  - 最佳实践
category: 工具配置
heroImage: ../../assets/blog-placeholder-2.jpg
---

Claude Code 的 hook 事件类型（PreToolUse、PostToolUse、SessionStart 等）已经在 [《Claude Code Hooks 工作流：8 种钩子的实战用法》](/blog/claude-code-hooks-workflow/) 里讲过了。这篇文章不重复那张事件表，而是聚焦一个更容易被忽略、但实际配置时天天会踩的问题：**hooks 该写在哪个 settings.json 里，多层配置怎么叠加，以及三个真实场景下的配置细节**。

## 一、三层 settings.json，覆盖关系怎么算

Claude Code 的配置文件分三层，优先级从低到高：

| 层级 | 路径 | 适用范围 | 是否进 git |
|---|---|---|---|
| 用户全局 | `~/.claude/settings.json` | 所有项目 | 否 |
| 项目共享 | `.claude/settings.json` | 当前项目，团队共享 | 是 |
| 项目本地 | `.claude/settings.local.json` | 当前项目，个人专属 | 否（应加入 .gitignore） |

**hooks 字段是数组合并，不是整体覆盖**——同一个事件（比如 `PostToolUse`）在三层里各写一条，运行时会全部触发，而不是本地层覆盖项目层。这个行为容易让人踩坑：如果你在 `settings.local.json` 里临时加了一个调试用的 hook，又忘了在项目 `settings.json` 里已经配了同名事件的 hook，两个脚本会**都跑一遍**，顺序是用户层 → 项目层 → 本地层。

实操建议：

- **敏感信息**（webhook token、内部脚本路径）只放 `settings.local.json`，绝不进 `settings.json`
- **团队共享的强制规则**（比如禁止 `rm -rf`、禁止 force push）放项目 `settings.json`，这样 clone 仓库的人自动继承
- **个人习惯**（比如自己想要的桌面通知）放用户全局层，不要污染项目配置

## 二、hooks 和权限模式（permission mode）怎么互相作用

很多人第一次配 `PreToolUse` hook 时会疑惑：明明写了 `exit 2` 拦截，为什么工具调用还是被执行了？原因通常是权限模式的判断顺序被搞反了。

实际顺序是：**hook 先跑，hook 的 exit code 会影响后续的权限判断**，而不是权限判断完了才轮到 hook。

- `exit 0`：hook 认为放行，进入正常权限判断流程（可能还要弹用户确认框，取决于 permission mode）
- `exit 2`：hook 主动拦截，stderr 内容会被喂给模型，模型据此调整方案，工具调用不会执行
- 其他非零 exit code：视为 hook 自身出错，Claude Code 会记录但通常仍放行，行为取决于版本——**不要依赖非 0/2 的 exit code 做拦截逻辑**，容易在版本升级后行为跑偏

如果你的项目开着 `--dangerously-skip-permissions` 之类的自动放行模式，`PreToolUse` 的 `exit 2` 拦截依然生效——hook 是权限模式之上的独立防线，这也是为什么危险命令黑名单应该写成 hook 而不是寄希望于交互式确认。

## 三、真实案例一:PostToolUse 联动外部任务系统

一个常见需求是"本地 TodoWrite 状态变化时，自动同步到团队的任务跟踪系统"（Notion、Linear、飞书多维表格都类似）。核心结构：

```bash
#!/usr/bin/env bash
# .claude/hooks/post-todowrite.sh
# 只在 TodoWrite 完成后触发，见 matcher 配置
payload=$(cat)
tool_name=$(echo "$payload" | jq -r '.tool_name')

if [ "$tool_name" != "TodoWrite" ]; then
  exit 0
fi

# 把提醒文本吐回给模型，而不是自己直接调 API
# 原因见下方"为什么不在 hook 里直接调用外部 API"
echo "检测到 TodoWrite 变化，请按项目规则同步到任务跟踪系统" >&2
exit 0
```

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "TodoWrite",
        "hooks": [{ "type": "command", "command": ".claude/hooks/post-todowrite.sh" }]
      }
    ]
  }
}
```

**为什么不在 hook 脚本里直接调用外部 API,而是把提醒吐给模型自己判断?** 因为外部任务系统的同步经常需要"去重查询、判断优先级、合并相似任务"这类语义判断，shell 脚本做不了，硬做只会写出一堆脆弱的字符串匹配逻辑。让 hook 只负责"提醒 + 传递上下文"，把语义判断留给模型，是更稳的分工方式。

## 四、真实案例二:PreToolUse 拦截 + 分级放行

单纯的黑名单容易漏，更稳的做法是分级：完全禁止、需要额外确认、直接放行。

```bash
#!/usr/bin/env bash
# .claude/hooks/pre-bash-graded.sh
cmd=$(echo "$CLAUDE_TOOL_INPUT" | jq -r '.command')

# 第一级：硬拦截，无论如何都不许跑
case "$cmd" in
  *"rm -rf /"*|*"git push --force"*"main"*|*"DROP TABLE"*)
    echo "blocked (hard): $cmd" >&2
    exit 2
    ;;
esac

# 第二级：涉及生产环境关键词，要求命令里带确认标记
if echo "$cmd" | grep -qE "prod|production" && ! echo "$cmd" | grep -q "CONFIRMED"; then
  echo "blocked (needs confirm): 生产环境相关命令需要先在对话里获得用户明确确认，命令中加 # CONFIRMED 标记后重试" >&2
  exit 2
fi

exit 0
```

这个模式的关键是**第二级拦截给出的 stderr 信息要具体到"怎么才能通过"**，模型才能据此调整策略（比如先在回复里跟用户确认，拿到确认后再重试并带上标记），而不是反复撞墙。

## 五、真实案例三:多 hook 协同时的执行顺序坑

如果同一事件配了多个 hook（比如项目层配了 lint,本地层又加了一个自定义检查),需要注意:

- 同一层内，`hooks` 数组按声明顺序**依次执行**，前一个非 0 且非 2 的失败不会阻断后一个继续跑（除非该 hook 显式 `exit 2`）
- 跨层执行顺序固定为**用户层 → 项目层 → 本地层**，无法通过配置调整
- 任意一层的 `exit 2` 都会导致整个链条在那一步中止，后面还没跑到的 hook 不会执行

这意味着如果你想要"格式化"必须在"检查"之前跑,就得确保它们在**同一层、同一数组里**且顺序正确写——分散在不同层的 hook 无法保证相对顺序符合直觉，写重要的强顺序逻辑时最好合并到一个脚本里，内部用 `&&` 串联，而不是拆成多个 hook 条目依赖跨层顺序。

## 六、调试技巧

- 先用 `echo "..." >> /tmp/claude-hook-debug.log` 加日志，比反复试错快得多
- `CLAUDE_TOOL_INPUT` 环境变量是 JSON 字符串，用 `jq` 解析前先 `echo "$CLAUDE_TOOL_INPUT" | jq .` 确认字段名——不同工具（Bash / Edit / Write）的字段结构不一样，`.command` 只在 Bash 里存在
- hook 脚本本身报错（比如 `jq` 找不到、脚本没有执行权限）会被 Claude Code 静默降级为放行，**不会主动告诉你 hook 挂了**，所以新写的 hook 一定要手动跑一遍验证退出码符合预期
- 用 `chmod +x` 确认脚本有执行权限，这是最容易漏掉的一步

## 七、相关阅读

- [Claude Code Hooks 工作流：8 种钩子的实战用法](/blog/claude-code-hooks-workflow/)
- [Claude Code 镜像国内配置完整指南](/blog/claude-code-mirror-cn-setup/)
- [Claude Code Subagent 实战](/blog/claude-code-subagent-practice/)
- [AI API 支出的发票与报销：国内团队怎么把账做平](/blog/cn-invoice-reimbursement/)

给团队里每个人的 Claude Code 配一个独立 API Key，方便按 hook 场景拆分调用统计和成本归因，[YoTradeApi](https://yotradeapi.com) 后台可以一键生成独立子账号 Key。
