---
title: Aider 工作流配置：用 .aider.conf.yml 和约定文件固化团队规范
description: 详解 Aider 的配置文件体系——.aider.conf.yml、.env、CONVENTIONS.md、.aider.ignore，以及 watch 模式与自动 lint/test 钩子，帮团队把 AI 结对编程流程标准化。
keywords:
  - aider 工作流配置
  - aider.conf.yml
  - aider conventions
  - aider watch 模式
  - aider 自动化配置
pubDate: '2026-09-07'
updatedDate: '2026-09-07'
canonical: https://blog.yotradeapi.com/blog/aider-workflow-config/
tags:
  - Aider
  - 工作流
  - 配置教程
  - 命令行工具
category: 工具配置
---

Aider 的默认体验已经够用——装好、配好 API、直接对话写代码。但一旦进入团队协作或者要在多个项目间复用同一套习惯，命令行参数手敲的方式很快就撑不住了：换个仓库要重新背一遍 `--model`、`--edit-format`，代码风格全靠口头约定，AI 生成的代码今天符合规范明天又跑偏。

Aider 其实提供了一整套配置文件机制来解决这个问题，只是文档比较分散，很多人用了很久还是停留在"命令行传参"阶段。这篇文章聚焦配置文件本身——如何用 `.aider.conf.yml`、`CONVENTIONS.md`、`.aider.ignore` 把工作流固化下来，让团队里每个人、每次对话都拿到一致的行为。API 中转与 Architect/Editor 双模型配置这部分内容已经在 [Aider 中文配置与最佳实践](/blog/aider-cn-config-guide/) 里讲过，这里不重复。

## 一、配置文件的加载顺序

Aider 会按下面的优先级依次读取配置，后面的覆盖前面的：

1. 全局配置：`~/.aider.conf.yml`
2. 项目根目录：`./.aider.conf.yml`
3. 环境变量：`.env` 文件或 shell 环境
4. 命令行参数：`aider --xxx`

这个顺序意味着你可以把团队共享的规则放进项目根目录的 `.aider.conf.yml` 并提交到 git，个人偏好（比如模型选择、是否自动提交）放进 `~/.aider.conf.yml`，敏感信息（API Key）放进 `.env` 并加进 `.gitignore`。三层分离,团队规范不会被个人习惯污染,也不会有人不小心把 Key 提交上去。

一个典型的项目级 `.aider.conf.yml`：

```yaml
# .aider.conf.yml — 提交到 git，团队共享
edit-format: diff
auto-commits: true
dirty-commits: false
attribute-author: true
attribute-committer: false
lint-cmd:
  - "python: ruff check --fix"
  - "javascript: eslint --fix"
test-cmd: pytest -x -q
auto-test: true
read:
  - CONVENTIONS.md
  - docs/architecture.md
```

`dirty-commits: false` 是容易被忽略的一项——默认情况下 Aider 允许在有未提交改动的仓库里继续工作，团队协作场景建议关掉,强制每次对话前先把手头改动清干净,避免 AI 的改动和你自己的改动混在一个 diff 里说不清楚。

## 二、用 CONVENTIONS.md 代替反复重复的提示词

如果你发现自己每次对话都要重新告诉 Aider"用中文写注释""错误处理用自定义 AppError""禁止用 any 类型"，说明这些规则该固化成一个约定文件，而不是每次现打。

在项目根目录建一个 `CONVENTIONS.md`：

```markdown
# 项目约定

## 代码风格
- TypeScript 严格模式，禁止 `any`，用 `unknown` + 类型守卫替代
- 异步函数统一用 async/await，不要混用 .then()
- 错误统一抛 `AppError`，禁止裸抛 Error

## 测试
- 新增函数必须配对写单测，放在同目录 __tests__/ 下
- mock 外部依赖，不允许测试里发真实网络请求

## Git
- commit message 用英文，格式 `type: description`
- 不要在一次 commit 里混合功能改动和格式化改动
```

然后在 `.aider.conf.yml` 里通过 `read` 字段把它设为只读上下文——每次对话都会自动带上这份文件,但 Aider 不会去编辑它。这比手动 `/read-only CONVENTIONS.md` 更可靠,因为配置文件被提交进 git,新加入项目的同事第一次跑 Aider 就自动拿到全套规范,不需要人肉传达。

对比效果:没有 CONVENTIONS.md 的团队,AI 生成代码的风格会随着提示词措辞的细微差异漂移；固化之后,同一个仓库不同人跑出来的代码风格基本一致,code review 时能少挑很多"这里不符合规范"的低价值意见。

## 三、.aider.ignore 控制上下文范围

Aider 默认会尊重 `.gitignore`，但很多仓库里 `.gitignore` 忽略的是构建产物，却仍然包含一些你不希望 AI 读取或修改的目录——比如生成的 API 文档、第三方 vendor 代码、大体积的数据文件。

`.aider.ignore` 语法和 `.gitignore` 一致，专门用来收窄 Aider 的上下文范围：

```
# .aider.ignore
vendor/
*.generated.ts
docs/api-reference/
tests/fixtures/*.json
node_modules/
dist/
```

这个文件的价值不只是"防止 AI 改错文件"，更直接的收益是 repomap（仓库结构索引）会变小、上下文 token 消耗降低、检索相关代码的准确率提高。仓库越大，这一步的收益越明显——一个几千文件的 monorepo 如果不做 ignore 收窄，repomap 本身就可能吃掉一大截上下文预算。

## 四、Watch 模式:把 Aider 嵌进编辑器工作流

`aider --watch-files` 是个容易被漏掉的功能。开启后 Aider 会监听你在编辑器里保存的文件，扫描其中带 `AI!`、`AI?` 标记的注释，自动触发对应的编辑或提问，不需要切到终端敲命令。

```python
def calculate_discount(price, user_tier):
    # AI! 加一个参数校验，price 不能为负数，user_tier 只能是 bronze/silver/gold
    return price * TIER_RATES[user_tier]
```

保存文件后，Aider 会读到这条注释、执行对应改动、然后把注释自动清掉。这种工作流的好处是你始终保持在编辑器里，不用来回切窗口维护对话上下文，尤其适合那种"改几行就想验证一下"的琐碎任务。

启用方式：

```yaml
# .aider.conf.yml
watch-files: true
```

`AI?` 用来提问而不触发编辑，`AI!` 触发编辑。团队里如果有人习惯 IDE 优先的工作流,这个模式比命令行对话上手快很多。

## 五、Lint 和 Test 自动化:让 AI 对自己的输出负责

前面配置示例里的 `lint-cmd` 和 `auto-test` 不是摆设。开启后，Aider 每次生成代码改动都会自动跑一遍指定的 lint 和测试命令，如果失败，会把报错信息喂回给自己再修一轮，而不是把带错误的代码直接扔给你。

```yaml
auto-lint: true
lint-cmd:
  - "python: ruff check --fix"
test-cmd: pytest -x -q
auto-test: true
```

这里有个实践上的取舍：`auto-test: true` 会显著拉长单次对话的耗时（每次改动都要跑一遍测试套件），如果测试套件本身比较慢，建议只在关键改动或者提交前手动触发 `/test`，日常开发保持关闭,靠人工判断什么时候需要跑测试。团队规模小、CI 资源紧张的情况下,把自动测试放在 CI 而不是本地对话循环里,往往性价比更高——这部分可以参考 [AI 编程 Agent 接入 CI 流水线](/blog/ai-coding-agent-ci-integration/) 里关于自动化触发时机的讨论。

## 六、模型切换与别名:少敲一行是一行

多模型协作是 Aider 的强项，但每次用完整模型名很啰嗦。`.aider.conf.yml` 支持给模型起别名：

```yaml
alias:
  - "fast:deepseek/deepseek-chat"
  - "smart:anthropic/claude-sonnet-4-5"
model: smart
weak-model: fast
```

`weak-model` 用于生成 commit message、总结这类轻量任务，用便宜模型跑可以明显省成本。日常写代码用 `smart`，遇到简单的重命名、格式调整这类任务，对话里临时切 `/model fast` 即可，不需要改配置文件重启。

## 七、多项目场景:全局配置 + 项目覆盖

如果你同时维护多个仓库，个人习惯（比如是否要看 diff 确认、编辑格式偏好）适合放进 `~/.aider.conf.yml`：

```yaml
# ~/.aider.conf.yml — 个人全局偏好
show-diffs: true
edit-format: diff
vim: true
```

项目级配置只放"这个项目特有"的规则（lint 命令、测试命令、约定文件路径），不要在项目配置里重复个人偏好——这样换电脑或者新同事加入时，个人配置和项目配置各自独立，互不干扰。

## 八、常见配置误区

**误区一：把 API Key 写进 `.aider.conf.yml` 并提交**。Key 只应该出现在 `.env` 或环境变量里，`.aider.conf.yml` 是要进 git 的文件，混进去等于把密钥公开。

**误区二：`auto-commits` 和团队 git 流程冲突**。如果团队用 PR + squash merge 的流程，Aider 每次对话自动产出多个小 commit 反而会让历史变乱，可以设 `auto-commits: false`，改为对话结束后手动 `/commit` 一次性提交。

**误区三：CONVENTIONS.md 写得太长**。这个文件是每次对话都会读入上下文的，写成几千字的规范文档反而挤占 token 预算、降低模型对关键规则的注意力。保持在一两百行以内，只写"AI 容易做错的地方"，通用工程常识不需要写进去。

## 九、相关阅读

- [Aider 中文配置与最佳实践](/blog/aider-cn-config-guide/)
- [用 Aider 做 TDD 重构的实战](/blog/aider-test-driven-refactor/)
- [Claude Code vs Aider：命令行 AI 编程工具怎么选](/blog/claude-code-vs-aider-comparison/)
- [Claude Code Hooks 配置实战](/blog/claude-code-hooks-config/)
- [AI 编程 Agent 接入 CI 流水线](/blog/ai-coding-agent-ci-integration/)

把工作流配置固化成文件而不是记在脑子里，是 AI 结对编程从"个人耍花活"走向"团队标准流程"的第一步。如果你的团队用的是多个模型供应商拼起来的技术栈，稳定的 API 中转是这套工作流能跑起来的前提，[YoTradeApi](https://yotradeapi.com) 提供统一的国内可用中转，配置一次即可在 Aider、Claude Code 等工具间共用。
