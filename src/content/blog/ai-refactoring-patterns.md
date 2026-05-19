---
title: AI 重构的 10 种实战模式
description: 用 AI 做代码重构的高频场景与对应 prompt 模板：函数提取、类型加固、回调改 async、依赖注入、模块拆分等。
keywords:
- ai 重构
- ai 代码 refactor
- claude 重构
- ai 代码改造
- 重构 模式
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/ai-refactoring-patterns/
tags:
- 重构
- 模式
- AI 编程
- 工程实战
category: 工程实战
heroImage: ../../assets/blog-placeholder-2.jpg
---

# AI 重构的 10 种实战模式

重构是 AI 编程收益最高的场景之一——模式化强、容易验证、风险可控。本文给 10 种高频模式 + 对应 prompt 模板。

## 模式 1：抽取函数

```
> 这段代码 [贴 100 行函数] 太长。
> 抽取出 3-5 个有意义的子函数。
> 主函数变短但行为不变。
> 跑测试确认通过。
```

AI 通常能找到清晰的"语义块"切分。**不强求一次抽完美**，先 80%，再迭代。

## 模式 2：类型加固

```
> 给 src/utils/ 下所有公开函数加完整 TypeScript 类型。
> 不写 any，不写 unknown，给具体类型。
> 用 mypy/tsc 验证通过。
```

新代码 + 老代码混合时特别需要。详见 [用 Aider 重构 5 年遗留 Python 项目](/blog/legacy-python-refactor-with-aider/)。

## 模式 3：callback → async/await

```
> 把这个文件改成 async/await：
> [贴代码]
> 
> 要求：
> 1. 保留所有错误处理
> 2. 并行能改的改并行（Promise.all）
> 3. 测试必须通过
> 4. 不引入新依赖
```

最容易得分的重构之一。

## 模式 4：注入依赖

```
> 这个函数硬编码了 db / config / logger，难测试。
> 改成 dependency injection 模式：
> - 参数接受 deps: { db, config, logger }
> - 默认从 src/lib 导出的 createDeps() 拿
> - 现有调用方都改
> - 新增的测试可以 mock deps
```

可测性 + 0。

## 模式 5：拆模块

```
> src/services/order.ts 已经 800 行了，混了：
> - CRUD 操作
> - 业务规则
> - 通知逻辑
> - 报表
> 
> 拆成 4 个文件，每个一个职责。
> 保持 API 不变（重导出）。
> 跑测试。
```

模块化是渐进式重构最常见动作。

## 模式 6：移除全局状态

```
> 项目里到处用 global.cache / global.config。
> 替换成 IoC 模式：
> - 在 src/lib/context.ts 定义 Context 类
> - 入口创建 context，向下传
> - 移除 global.* 引用
> 一步步来，每改一个文件跑测试。
```

注意：这是大重构，**严格走 Plan → Act**。

## 模式 7：API 版本演进

```
> 我要加 /api/v2/users，与 /api/v1/users 共存。
> v2 改动：
> 1. 响应字段从 snake_case → camelCase
> 2. 加 cursor pagination
> 3. 字段 created_at 改返回 createdAt ISO 字符串
> 
> 复用 v1 实现核心逻辑，v2 只做格式适配。
> v1 完全不动。
> 加 v2 测试覆盖 3 种场景。
```

API 兼容性场景。

## 模式 8：错误处理统一

```
> 整理 src/api/ 下错误处理：
> 1. 不要 try/catch return null
> 2. 用 src/lib/errors.ts 的 AppError 类
> 3. 按错误类型映射 HTTP 状态码
> 4. 不暴露内部 stack 给客户端
> 5. 日志记录完整 context
> 
> 逐文件改，每改一个跑相关测试。
```

错误处理一致性 = 后端可靠性基础。

## 模式 9：消除 N+1

```
> 这段代码看上去是 N+1：
> [贴 ORM 查询]
> 
> 用 include / eager load 优化。
> 加一个性能测试验证：100 条数据，query 数应 ≤ 3。
```

ORM 用户必备的高频重构。

## 模式 10：测试驱动重构

```
> src/utils/parser.ts 想重写实现（性能不够）。
> 步骤：
> 1. 先给现有 parser 加 100 个测试 case
> 2. 跑通后，我们改实现
> 3. 测试全绿才算完成
> 4. 改完跑 benchmark 对比性能
```

**先有安全网再重构**。这是高质量 AI 重构的关键。

---

## 重构 Anti-pattern

- ❌ "把整个项目重构一下"（任务太大，必失败）
- ❌ 同时改多种东西（拆开来，一种一次）
- ❌ 没测试就动（盲飞）
- ❌ 改完不跑测试（自欺欺人）
- ❌ commit 一团乱（中间状态不可回滚）

## 重构的纪律

每次重构必须：

1. **明确范围**：改什么、不改什么
2. **建保护网**：测试覆盖到位
3. **小步前进**：一个改动一个 commit
4. **持续验证**：每步跑测试
5. **可回滚**：随时能 git reset

## 工具选择

| 重构规模 | 工具 |
| --- | --- |
| 单文件改名 / 抽函数 | Cursor / Cline 行内编辑 |
| 单目录改造 | Cursor Composer / Cline |
| 跨文件大改 | Claude Code + Subagent / Aider Architect |
| 整库迁移 | Claude Code 长任务 |

详见 [2026 AI 编程工具全景图](/blog/ai-coding-tools-2026-overview/)。

## 模型选择

| 重构难度 | 推荐 |
| --- | --- |
| 简单（明确套路） | Sonnet 4.6 |
| 中（跨文件） | Sonnet 4.6 |
| 难（架构决策） | Opus 4.7 |
| Architect + Editor | Opus + Sonnet |

详见 [Claude Sonnet vs Opus](/blog/claude-sonnet-4-6-vs-opus-4-7/)。

## 实战例子

```
# .clinerules 加一段
## 重构纪律

接受重构任务时：
1. 先说明范围（改什么、不改什么）
2. 列保护网状态（测试是否够）
3. 不够就先补测试
4. 每完成一步给 diff 让我看
5. 跑 pnpm test 验证
6. 测试失败立刻停，不要"修测试让它过"
```

把规则沉淀进 rules，**所有重构任务自动走纪律**。

## 相关阅读

- [AI Agent Prompt Engineering 中文实战](/blog/agent-prompt-engineering-cn/)
- [AI 编程代理成本控制实战](/blog/ai-coding-agent-cost-control/)
- [AI 编程的 12 个常见错误与避坑指南](/blog/ai-coding-mistakes-to-avoid/)
- [用 Aider 重构 5 年遗留 Python 项目](/blog/legacy-python-refactor-with-aider/)
- [Claude Sonnet 4.6 与 Opus 4.7 怎么选](/blog/claude-sonnet-4-6-vs-opus-4-7/)
- [AI 生成单元测试的工程化方法](/blog/ai-test-generation-workflow/)

大重构推荐 Architect + Editor 双模型，[YoTradeApi](https://yotradeapi.com/register) 一把 Key 同时支持 Opus 4.7 + Sonnet 4.6。
