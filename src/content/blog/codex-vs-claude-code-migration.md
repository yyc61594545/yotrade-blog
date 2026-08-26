---
title: 从 Claude Code 迁移到 Codex 的实践清单
description: 团队决定把部分工作流从 Claude Code 切到 Codex CLI，本文给出一份可执行的迁移检查清单，覆盖配置文件、Hook、Subagent、权限模型的对应关系与取舍。
keywords:
  - Claude Code 迁移 Codex
  - Codex CLI 迁移
  - AGENTS.md 迁移
  - CLAUDE.md 转换
  - AI CLI 切换
pubDate: '2026-08-26'
updatedDate: '2026-08-26'
canonical: https://blog.yotradeapi.com/blog/codex-vs-claude-code-migration/
tags:
  - Claude Code
  - Codex CLI
  - 工具迁移
  - 开发工作流
category: 实战经验
heroImage: ../../assets/blog-placeholder-4.jpg
---

选择用哪个 CLI 编程代理和"把现有工作流从一个迁移到另一个"是两回事。前者的功能对比可以看 [Claude Code vs Codex CLI 全面对比](/blog/claude-code-vs-codex-cli/)，本文假设团队已经做完选型决策，要把一个已经跑了几个月、攒了不少配置和习惯的 Claude Code 项目迁移到 Codex，聚焦"具体要改哪些文件、哪些能力没有直接对应物、迁移过程容易漏掉什么"。

这份清单基于两边工具截至目前的实际能力整理，如果你在阅读时两边工具已经发布新版本，请以官方最新文档为准，但配置文件的对应关系和取舍逻辑通常变化不大。

## 一、迁移前先盘点：哪些东西是"项目资产"

Claude Code 项目里真正需要迁移的不是工具本身，而是几类沉淀下来的项目资产：

1. **项目指令文件**（`CLAUDE.md`）——写给 Agent 看的项目背景、构建命令、代码规范。
2. **Hook 脚本**——`PreToolUse`/`PostToolUse` 等事件触发的自动化逻辑，比如自动格式化、危险操作拦截。
3. **Subagent 定义**（`.claude/agents/*.md`）——专职化的子代理配置。
4. **权限配置**（`settings.json` 里的 allow/deny 列表）——哪些命令免确认、哪些强制拦截。
5. **Skill/Command**（`.claude/skills/`、`.claude/commands/`）——可复用的工作流封装。

逐条盘点清楚"我们到底用了哪些能力"，比直接翻迁移文档更重要——很多团队实际只用了 `CLAUDE.md` 和权限配置两项，迁移工作量会小很多；但如果重度依赖 Hook 和自定义 Skill，工作量会显著上升，需要提前评估清楚再排期。

## 二、项目指令文件：CLAUDE.md → AGENTS.md

这是最直接的一步。Codex 用 `AGENTS.md` 承担和 `CLAUDE.md` 基本相同的角色——项目根目录及子目录均可放置，支持层级覆盖。迁移时注意三个细节：

- **发现顺序不完全一致**。Claude Code 会读取多层级的 `CLAUDE.md`（含用户级 `~/.claude/CLAUDE.md`、项目级、子目录级），Codex 对 `AGENTS.md` 的层级发现规则和覆盖优先级有自己的实现，迁移前务必用一个小测试项目验证子目录级指令是否按预期生效，不要假设两边行为完全对齐。
- **内容基本可以直接复用**。构建命令、代码规范、目录结构说明这类内容和工具本身无关，原样搬过去即可,不需要重写。
- **工具特定的引用要清理**。如果 `CLAUDE.md` 里写了"使用 `/review` 命令做代码审查"这类 Claude Code 命令引用，迁移到 `AGENTS.md` 后需要替换成 Codex 对应的操作方式，否则 Agent 会尝试执行一个不存在的命令。

关于 `AGENTS.md` 本身的编写规范和层级设计，可以参考 [Codex 项目级 AGENTS.md 编写指南](/blog/codex-cli-project-instructions/)，这里不重复展开写法细节。

## 三、Hook 系统：没有直接对应物，需要重新设计

这是迁移中最容易低估工作量的一项。Claude Code 的 Hook 系统（`PreToolUse`、`PostToolUse`、`SessionStart`、`Stop` 等 8 类事件）允许在工具调用前后插入任意 shell 命令，常见用途包括：

- 危险命令拦截（`PreToolUse` 检查即将执行的 bash 命令，匹配黑名单则阻断）
- 自动格式化（`PostToolUse` 在文件写入后自动跑 `prettier`/`black`）
- 会话开始注入上下文（`SessionStart` 读取项目状态并注入）

Codex 目前的自动化钩子能力和 Claude Code 的 Hook 系统在设计理念上不同，没有逐个事件的一一对应。迁移策略上有两条路：

1. **能下沉到项目工具链的，下沉**。自动格式化这类需求，本质上不需要依赖 CLI 本身的 Hook 机制，改用 git pre-commit hook 或 CI 阶段跑格式化,效果等价且不依赖具体 Agent 工具，是更彻底的解法。
2. **危险命令拦截这类强依赖 Agent 生命周期的逻辑，需要用 Codex 自身的审批策略（approval policy）和沙箱配置重新实现**，逻辑上不是照搬脚本，而是要重新设计成 Codex 的配置语言能表达的形式。

先把 Hook 按用途分类，能下沉的下沉，不能下沉的再单独评估 Codex 有没有对应能力，比试图找一个"一键转换"的捷径更现实。

## 四、Subagent → 会话/任务边界的重新设计

Claude Code 的 Subagent 是配置文件驱动的专职化子代理（独立上下文、独立工具权限），适合"main agent 负责调度、subagent 负责具体某类任务"的模式。Codex 这边更常见的对应做法是通过 **Worktree 隔离 + 多会话并行**来实现类似的任务分工，机制不同但解决的问题类似。

迁移时不要试图把每个 Subagent 定义文件"翻译"成 Codex 配置——两者的隔离粒度不一样（Subagent 是同一会话内的上下文隔离，Codex 的 Worktree 方案是进程/目录级隔离）。更实际的做法是回到"这个 Subagent 当初是为了解决什么问题"这个问题本身，比如"独立的代码审查视角"这类需求，用单独开一个 Codex 会话跑审查任务、把结果反馈给主任务的方式实现，而不是追求配置层面的一一对应。

多任务并行且需要目录级隔离的场景，[Codex Worktree 隔离开发实战](/blog/codex-worktree-isolation/) 有完整的命令流程，迁移到 Codex 后如果原来的 Subagent 主要用于并行探索多个方案，这篇的模式基本可以直接套用。

## 五、权限配置：allow/deny 列表要重新过一遍，不要直接照搬

Claude Code 的 `settings.json` 权限列表和 Codex 的 approval policy 语法不同，即使功能上都是"哪些命令/操作免确认"，配置格式也无法直接转换，需要手动重写。这一步**不建议图省事直接把旧的允许列表整体导入**，原因是：

- 两边工具对"一次操作"的粒度定义不同（比如 Claude Code 里一条允许规则可能对应 Codex 里需要拆成两条）。
- 这正好是一个复盘的好机会——很多项目跑了几个月后，允许列表里会积累一些当初为了"图快"加进去、现在看不必要的宽松规则。迁移时逐条过一遍，该收紧的收紧，比无脑照搬更安全。

## 六、Skill / Command：评估是否值得重写

Claude Code 的 Skill（`.claude/skills/`）和 Command（`.claude/commands/`）是这次迁移里"值不值得搬"最需要具体判断的一项。判断标准很简单：这个 Skill 是否是**团队高频复用、且逻辑与 Claude Code 特定机制强绑定**？

- 如果 Skill 本质是"一段可复用的操作说明 + 脚本"（比如"如何部署"、"如何跑回归测试"），这类内容和具体 CLI 工具无关，迁移成本低，把 Markdown 说明搬到 Codex 对应的项目文档位置即可。
- 如果 Skill 依赖 Claude Code 特有的 progressive disclosure 机制（按需加载子文件、`references/` 目录结构），需要根据 Codex 对项目指令的加载机制重新设计文档组织方式，不是简单的文件搬运。

不要一次性把所有 Skill 都迁移过去——按实际使用频率排序，先迁移团队每天都要用的那几个，用得少的可以等真正需要时再补,避免把迁移窗口期拉得过长。

## 七、迁移过程中的双跑期建议

不建议"一刀切"式迁移——一天之内切完所有项目、关掉旧工具。更稳妥的做法是选 1~2 个非核心项目先完整走一遍迁移清单，跑 1~2 周双工具并存期，观察：

- Codex 在这些项目里跑长任务的稳定性和 Claude Code 是否有明显差异
- 团队成员在两边工具间切换的学习成本是否可接受
- 权限配置重写后是否有遗漏（比如某个之前免确认的常用命令现在总是要手动批准，影响效率）

确认没有意外情况后，再逐步把其余项目迁移过去。如果团队本身还在评估要不要长期用 Codex 做后台自动化任务（而不只是交互式编程），可以参考 [Codex 后台自动化任务实践](/blog/codex-background-automation/) 提前了解长任务场景下的注意事项，这类经验在迁移决策阶段就该纳入考量，而不是迁移完才发现不适配。

## 八、相关阅读

- [Claude Code vs Codex CLI 全面对比](/blog/claude-code-vs-codex-cli/)
- [Codex 项目级 AGENTS.md 编写指南](/blog/codex-cli-project-instructions/)
- [Codex Worktree 隔离开发实战：多任务并行不冲突](/blog/codex-worktree-isolation/)
- [Codex 后台自动化任务实践](/blog/codex-background-automation/)

无论最终团队用 Claude Code、Codex 还是两者并存，底层模型调用都可以通过 [YoTradeApi](https://yotradeapi.com) 统一中转，迁移工具不必再折腾一遍 API 接入配置。
