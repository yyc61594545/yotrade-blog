---
title: Claude Code Subagent 实战：定义、用法与最佳实践
description: Claude Code Subagent 完整使用指南，含定义文件、调用时机、上下文隔离、并行执行、与 Hook/MCP 配合的实战经验。
keywords:
- claude code subagent
- claude code 子代理
- subagent 定义
- claude code 并行
- claude code agent
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/claude-code-subagent-practice/
tags:
- Claude Code
- Subagent
- Agent 工作流
- 最佳实践
category: 工具配置
heroImage: ../../assets/blog-placeholder-4.jpg
---

Claude Code 的 Subagent 是它最强的特性之一：让主对话不直接执行子任务，而是 dispatch 给一个独立上下文的"小代理"。用对了能省 token + 提高准确率，用错了反而拖慢。本文给一份实战指南。

## 一、什么是 Subagent

可以这样理解：

- **主 agent**：你在终端对话的那个 Claude，保持长上下文
- **Subagent**：被主 agent 派出去完成单一职责的"无记忆助手"

每个 Subagent：

- 有独立 system prompt 与工具集
- 上下文不与主 agent 共享（除了 prompt 显式传入）
- 完成后返回一个结构化结果给主 agent

## 二、什么时候用 Subagent

**该用**：

- 任务可以一句话描述完成标准
- 不需要持续对话，一次性产出
- 上下文大且与主任务无关（例如读 100 个文件找 bug）
- 可以并行（多个独立查询）

**不该用**：

- 需要持续对话探索
- 上下文必须共享
- 用户希望看清每一步

## 三、定义 Subagent

在 `.claude/agents/` 目录创建 markdown 文件：

```markdown
---
name: code-reviewer
description: 严谨的代码评审专家，给出 blocking 与 nice-to-have 建议
tools: Read, Grep, Bash
model: claude-sonnet-4-6
---

你是一个 senior 工程师，专注代码评审。

评审重点：
1. 正确性：是否有 bug、边界条件、异常处理
2. 性能：算法复杂度、不必要的循环、I/O 优化
3. 可读性：命名、注释、抽象层次
4. 安全：注入风险、密钥泄露、权限

输出格式：
- **Blocking**：必须修改才能合并
- **Nice-to-have**：建议改但不强求
- **Praise**：值得肯定的地方

简洁、具体，少废话。
```

文件名 = subagent 名（去掉 `.md`）。

## 四、调用 Subagent

主 agent 里：

```
> 用 code-reviewer subagent 评审 src/auth/middleware.ts
```

Claude Code 会自动把这段 prompt + 文件路径 dispatch 给 code-reviewer。结果回流到主对话。

## 五、写 Subagent prompt 的纪律

新接触 subagent 的人最容易犯的错：**把 system prompt 写成行为说明书**。正确做法：

| 坏写法 | 好写法 |
| --- | --- |
| "你需要打开文件，分析每个函数..." | "你评审代码。" |
| 列出 30 条规则 | 写一段简洁原则 |
| "根据用户的需求..." | 直接给输出格式 |

**Subagent 是"无脑执行单一职责"的**。规则越简单，行为越稳定。

## 六、内置 Subagent

Claude Code 内置了几个常用 subagent：

| 名字 | 用途 |
| --- | --- |
| `general-purpose` | 默认通用（用于 Agent 工具，可以委托研究任务） |
| `Explore` | 只读搜索：grep / find / 大致看代码 |
| `Plan` | 设计实现计划 |
| `statusline-setup` | 配置状态栏 |
| `claude-code-guide` | Claude Code 自身使用问题 |

`Explore` 特别有用：把"在仓库里找 X"这类任务全部 delegate 给它，主 agent 上下文不被搜索结果污染。

## 七、并行 Subagent

主 agent 可以一次 dispatch 多个 subagent：

```
> 同时跑：
> 1. Explore subagent 搜 fetchUser 的调用点
> 2. Explore subagent 搜 fetchOrders 的调用点
> 3. code-reviewer subagent 评审 src/api/*.ts
```

Claude Code 会并行执行。**适用**：互不依赖的查询。**不适用**：后一步需要前一步结果。

## 八、Subagent 的上下文边界

Subagent 不会自动看到主 agent 的所有上下文。**只能看到主 agent 在调用时显式传入的内容**。

错误示例：

```
主 agent 里读了 utils.ts，然后说：
> 用 code-reviewer 评审刚才那个文件
```

code-reviewer subagent **看不到** "刚才那个文件"。它得到的只是这句话。

正确示例：

```
> 用 code-reviewer 评审 src/utils.ts（路径要明确）
```

或者主 agent 把文件内容粘贴进 prompt。

## 九、Subagent 模型选择

每个 subagent 可以指定独立模型：

```yaml
---
name: doc-writer
model: claude-haiku-4-5   # 文档场景用快模型
---
```

```yaml
---
name: architect
model: claude-opus-4-7   # 架构思考用强模型
---
```

主 agent 用 Sonnet，subagent 按职责切，**整体成本能砍 30–50%**。

## 十、Hook 与 Subagent 的配合

PreToolUse / PostToolUse hook 在 subagent 调用时也会触发。比如：

```bash
# .claude/hooks/pre-tool-use.sh
case "$CLAUDE_TOOL_NAME" in
  Bash)
    # 不允许 subagent 跑 git push
    if echo "$CLAUDE_TOOL_INPUT" | grep -q "git push"; then
      echo "blocked: subagent cannot push" >&2
      exit 2
    fi
    ;;
esac
```

`exit 2` 阻止工具执行。Subagent 收到错误反馈后会自适应。

## 十一、典型场景

### 场景 1：代码评审

```
> 把当前 PR 拆成三块，并行用 code-reviewer 评审
```

### 场景 2：批量重构验证

```
> 主 agent 改完 10 个文件后，并行用 test-runner 跑这些文件相关的测试
```

### 场景 3：研究新依赖

```
> Explore subagent 看 zustand 在项目里的所有使用模式
> 然后主 agent 决定怎么迁移到 v5
```

### 场景 4：长文档总结

```
> 用 summarizer subagent 把 docs/architecture.md（8000 字）压成 500 字摘要
```

## 十二、常见错误

| 错误 | 表现 |
| --- | --- |
| Subagent system prompt 太长 | Subagent 行为漂移 |
| 没传入必要上下文 | Subagent 返回"我不知道" |
| 多个 subagent 互相调用 | 调用链失控 |
| 在 subagent 里跑 git push | 没 hook 拦截会出事 |

## 十三、相关阅读

- [Claude Code 镜像国内配置完整指南](/blog/claude-code-mirror-cn-setup/)
- [Claude Sonnet 4.6 与 Opus 4.7 怎么选](/blog/claude-sonnet-4-6-vs-opus-4-7/)
- [AI 编程代理成本控制实战](/blog/ai-coding-agent-cost-control/)
- [Cursor Background Agent 国内配置与使用](/blog/cursor-background-agent-config/)

用一把支持 Claude 全系列的 Key 把 Subagent 全跑起来？在 [YoTradeApi 注册](https://yotradeapi.com) 创建 Key，然后 `export ANTHROPIC_BASE_URL=https://yotradeapi.com` 即可。
