---
title: Codex 项目级 AGENTS.md 编写指南
description: OpenAI 官方把 `AGENTS.md` 作为 Codex 的持久项目指令层。本文讲清项目级文件的发现顺序、根目录与子目录如何分工、何时拆分嵌套规则，以及一份适合真实仓库的写法模板。
keywords:
  - Codex AGENTS.md
  - Codex 项目指令
  - OpenAI Codex 配置
  - AGENTS.md 模板
  - Codex 仓库规则
pubDate: '2026-08-18'
updatedDate: '2026-08-18'
canonical: https://blog.yotradeapi.com/blog/codex-cli-project-instructions/
tags:
  - Codex
  - AGENTS.md
  - 项目规范
  - OpenAI
  - 实战
category: 实战经验
heroImage: ../../assets/blog-placeholder-1.jpg
---

很多团队第一次用 Codex，会把关键约束全塞进临时 prompt：先说代码风格，再说测试命令，再补一句“别动生产配置”，下一次开新会话还得重讲一遍。OpenAI 官方把这类**需要长期跟着代码仓库走**的约束放到了 `AGENTS.md` 里，让它在每次任务开始前就被加载。

问题在于，知道“有这个文件”不等于会写。`AGENTS.md` 写得过短，Codex 不知道你的工程约束；写得过长，它又会变成一份没人维护的项目宣言。真正有用的写法，不是把所有流程复制进去，而是把**每次都必须生效的仓库级规则**放在最小可维护的结构里。

## 一、先理解它怎么被发现：根目录不是唯一入口

OpenAI 官方当前文档给出的规则很清楚：Codex 启动时会构建一条 instruction chain，先读全局层，再从项目根目录一路走到当前工作目录；每一级目录至多纳入一个指令文件，后面的层覆盖前面的层。默认会优先找 `AGENTS.override.md`，其次是 `AGENTS.md`，如果都没有，还可以在配置里通过 `project_doc_fallback_filenames` 指定备用名字。

这意味着项目级 `AGENTS.md` 不是孤立文件，而是分层体系的一部分：

| 层级 | 典型位置 | 适合放什么 |
| --- | --- | --- |
| 全局层 | `~/.codex/AGENTS.md` | 个人通用偏好、默认工作方式 |
| 仓库根层 | `<repo>/AGENTS.md` | 整个项目通用的 build/test/style 规则 |
| 子目录层 | `<repo>/packages/api/AGENTS.md` | 仅对某个模块有效的特殊约束 |

写项目级文件时，最容易犯的错就是把个人偏好、团队约定、子目录细则全堆到仓库根层。结果不是更清晰，而是更难维护。**仓库根文件应该解决“这个 repo 里无论做什么都要知道的事”；子目录文件才负责局部例外。**

## 二、根目录 AGENTS.md 应该写什么，不该写什么

如果你把根目录文件当“项目 README 的重复版”，很快就会失控。更稳的判断标准是：**只有那些缺了就容易让 Codex做错事的规则，才值得放进去。**

比较适合放在根目录的内容通常有这些：

1. 项目结构概览：核心代码在哪，测试在哪，生成物在哪。
2. 必跑命令：例如 `npm test`、`pnpm lint`、`python -m pytest`。
3. 编辑约束：哪些目录不能改，哪些文件需要生成而不是手写。
4. 提交与验证规则：是否要求先跑某个校验、是否一文件一提交。
5. 安全边界：不要碰密钥、不要提交 `.env`、不要连生产库。

反过来，不适合塞进根目录的内容包括：

- 团队文化口号或泛泛的工程价值观
- 很少触发、只对单个子系统有效的细节
- 能从工具自动推断的事实，比如“这是一个 Node 项目”
- 每周都在变、且没有版本管理流程的临时通知

一个好用的项目级 `AGENTS.md` 应该更像**操作合同**，而不是文档中心。站内已有 [Codex CLI 国内配置与使用指南](/blog/codex-cli-cn-setup/) 讲启动与接入，本文关注的是“接入以后怎样让它长期按你的项目方式工作”。

## 三、什么时候要拆成嵌套 AGENTS，什么时候不要

OpenAI 官方之所以支持从根目录一路走到当前目录加载规则，就是为了让不同子树有自己的约束。比如 monorepo 里，前端和后端的测试命令、生成流程、发布边界可能完全不同；这时候把所有细节都塞进根层，只会让每个任务都先吞下一大坨不相关信息。

实务上可以用下面这张表判断：

| 场景 | 做法 |
| --- | --- |
| 整个仓库统一用一种测试/格式化流程 | 只放根目录 AGENTS |
| 某个子包有完全不同的 build 命令 | 在子目录再放一份 AGENTS |
| 某个目录禁止手改、必须走代码生成 | 在对应目录局部声明 |
| 只是想重复根目录内容 | 不要再拆，避免重复覆盖 |

**嵌套规则的价值在于“补充差异”，不在于“复制总则”。** 如果一个 `packages/mobile/AGENTS.md` 里又把根目录那套提交规则、测试规则、风格规则抄一遍，你等于平白制造了一份未来会漂移的副本。

## 四、最实用的写法：短、硬、可执行

官方文档和实战案例都在强调一件事：`AGENTS.md` 要偏紧凑，最好直接告诉 Codex“做什么”和“别做什么”，而不是讲一大段背景故事。因为它的任务不是培训新人，而是**让 agent 在执行时少犯低级错**。

一份项目级文件，通常用这种骨架就够了：

```md
# AGENTS.md

## Project overview
- Web app lives in `apps/web/`
- API server lives in `services/api/`
- Shared libraries live in `packages/*`

## Commands
- Install: `pnpm install`
- Test: `pnpm test`
- Lint: `pnpm lint`
- Build: `pnpm build`

## Editing rules
- Do not edit generated files under `src/generated/`
- Run `pnpm codegen` after schema changes
- Keep commits focused and avoid unrelated refactors

## Safety
- Never modify deployment secrets or `.env` files
- Do not run destructive database commands
```

这里最关键的不是格式有多漂亮，而是每一条都能转成可执行判断。比如“保持代码优雅”没有操作价值；“改 schema 后必须跑 `pnpm codegen`”就有明确约束。

## 五、用 `/init` 起步，但不要停在脚手架

如果仓库里还没有 `AGENTS.md`，OpenAI 官方开发者命令页明确建议直接运行 `/init` 生成初稿。这个命令的价值不在于“它会自动写出完美规则”，而在于它能给你一个足够像样的骨架，省掉从空白文件起手的成本。

但更重要的是第二步：**一定要把脚手架改成你仓库自己的语言**。常见需要手改的地方包括：

- 把泛化表述替换成真实命令
- 删掉对你项目无意义的段落
- 加上最容易出事故的局部约束
- 明确哪些验证是提交前强制门禁

很多团队的问题不是“没有 AGENTS”，而是“有一份从没维护过的 AGENTS”。这种文件和没有差别不大，因为 Codex 会照着读，但读到的是过期规则。

## 六、一个判断标准：它能不能替你省下重复口头提示

要判断项目级 `AGENTS.md` 写得好不好，可以不用看它有多长，而看一个更实际的问题：**如果拿掉这份文件，团队每次开新任务时是否又得重复讲同一批提醒？**

如果答案是肯定的，那这些提醒就应该沉淀进去。典型例子包括：

- “改完必须跑这三个命令”
- “这里的 SQL 迁移不能手写，要跑生成器”
- “前端包管理器只能用 pnpm，别混用 npm”
- “这个目录是镜像同步来的，不要直接编辑”

这类规则一旦进入 `AGENTS.md`，Codex 才会把它们当作启动时上下文，而不是本轮对话里的偶发补充。对长期维护的仓库来说，这一点比在 prompt 里临时强调更稳定，也比把所有细节埋进 README 更直接。

## 七、结论：先写最小合同，再按目录分层细化

项目级 `AGENTS.md` 最容易走向两个极端：要么什么都不写，导致每次任务都重头解释；要么把仓库知识全堆进去，最后没人敢改。更稳的路线其实很简单：先在根目录写一份**最小而刚性的执行合同**，只覆盖项目通用规则；等到某个子目录确实有明显不同，再拆出局部 `AGENTS.md`。

你可以把它当成“仓库给 Codex 的长期 onboarding”。写得好的文件，应该能减少重复沟通、降低误改概率，并把真正重要的命令和边界放到最前面。至于 README、架构文档、设计记录，仍然继续承担“解释背景”的角色；`AGENTS.md` 负责的是“告诉 agent 现在该怎么做”。

## 八、相关阅读

- [Codex CLI 国内配置与使用指南](/blog/codex-cli-cn-setup/)
- [Claude Code vs Codex CLI 全面对比](/blog/claude-code-vs-codex-cli/)
- [自定义 MCP Server 开发实战（Python + TypeScript）](/blog/mcp-custom-server-development/)
- [Prompt 版本管理实战：从混乱到可追溯的工程化之路](/blog/ai-prompt-versioning/)

如果你希望把 Codex、Claude Code、Cursor 等多种开发工具接到同一套模型入口里统一管理，[YoTradeApi](https://yotradeapi.com) 可以帮你减少不同协议和供应商切换时的接入成本。
