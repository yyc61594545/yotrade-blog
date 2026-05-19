---
title: AI Agent Prompt Engineering 中文实战指南
description: 编程代理（Cursor/Claude Code/Cline）的 system prompt 与任务 prompt 写法，含上下文裁剪、角色定义、验收标准、防漂移技巧。
keywords:
- ai agent prompt
- agent prompt engineering
- claude code system prompt
- cursor rules
- cline 提示词
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/agent-prompt-engineering-cn/
tags:
- Prompt Engineering
- Agent
- 最佳实践
- 系统提示词
category: 最佳实践
heroImage: ../../assets/blog-placeholder-1.jpg
---

# AI Agent Prompt Engineering 中文实战指南

写好 prompt 是 AI 代理产出质量的天花板。同一个模型、同一个任务，prompt 不同结果可以差 3 倍。本文聚焦"编程代理"的 prompt engineering 实战。

## 一、Prompt 的三层结构

| 层级 | 写在哪里 | 内容 |
| --- | --- | --- |
| System Prompt | `.cursorrules` / `CLAUDE.md` / 配置 | 角色、原则、约束 |
| 项目知识 | 项目文档 / hook 注入 | 架构、命名、栈 |
| 任务 Prompt | 对话框输入 | 目标、范围、验收 |

三层独立，但在请求时合并为一个完整 prompt。**职责清晰才能复用**。

## 二、System Prompt 写法

不要写"你是一个有用的助手"——这是废话。System Prompt 应该包含：

```markdown
# 角色
你是有 10 年经验的 TypeScript 工程师。注重正确性与可读性。

# 原则
1. 修改最少代码达成目标
2. 不引入新依赖除非必要
3. 保持现有命名约定
4. 测试不通过就回滚

# 约束
- 不修改 package.json 主版本
- 不动 CI 配置
- 不写空 try/catch

# 风格
- 函数名 camelCase，类名 PascalCase
- 公开 API 必须有 TSDoc
- 错误要包含 context

# 输出
- 改完代码立刻跑 npm test
- 失败时给出 diagnostic，不要静默
- 完成时简述改了什么、为什么
```

**好的 system prompt 像团队 onboarding 文档**，不是 marketing 文案。

## 三、项目知识（CLAUDE.md / .cursorrules）

项目根放一份"AI 看了能干活"的文档：

```markdown
# 项目知识

## 架构
- Next.js 15 + Prisma + PostgreSQL
- 部署：Cloudflare Pages（自动从 main 分支）
- API：/api/v1/* 是公开，/api/internal/* 是内部
- 认证：JWT in httpOnly cookie

## 关键约定
- 所有 API 路由必须返回 { ok, data?, error? } 形式
- 数据库迁移用 `npm run db:migrate`
- 日志用项目里的 logger（不要用 console.log）

## 常见陷阱
- 改 prisma schema 后必须 `prisma generate`
- 别用 fetch，用项目里的 apiClient
- 客户端组件不能直接调 Prisma

## 测试
- 单元：jest，运行 `npm test`
- E2E：playwright，运行 `npm run e2e`
- 改 API 必须更新 OpenAPI spec
```

这部分内容会被 prompt cache 命中——一次写好长期受益。

## 四、任务 Prompt 模板

```markdown
# 任务
[一句话目标]

# 范围
- 改：src/api/users/*
- 不改：tests/*, prisma/migrations/*

# 上下文
- 关联 issue: #123
- 相关文件：[路径]
- 前置依赖：已完成 X

# 验收标准
- [ ] npm test 全绿
- [ ] 新增字段在 OpenAPI 体现
- [ ] migration 向后兼容
- [ ] 改动文件 < 5

# 注意
[潜在坑]
```

**写"不要做什么"和"做什么"一样重要**。代理一旦发散到无关文件，回滚成本高。

## 五、防漂移技巧

长任务最容易出现的问题：开始时还在做对的事，做着做着跑偏。防止：

### 1. 任务开始时 echo 任务

```markdown
# 任务
重构 src/api/users 把回调风格改成 async/await。

任务确认：
- [ ] 我会先改 GET /users 一个 endpoint 验证
- [ ] 跑测试通过
- [ ] 然后批量改其它 endpoint
- [ ] 最后跑全套 e2e
你确认这个计划吗？
```

让代理"自我复述+确认"，能减少 60% 漂移。

### 2. 阶段性 checkpoint

每完成一步要求总结："改了哪些文件，还差什么"。

### 3. 用 Plan/Architect 模式

Cline 的 Plan、Aider 的 Architect、Cursor 的 Plan Mode——让代理先规划再执行。规划阶段你审核一次，执行阶段大概率不漂移。

## 六、上下文裁剪

提示越简洁、信号越强：

| 不好 | 好 |
| --- | --- |
| 把整个项目代码贴进 prompt | `@src/api/users/get.ts` |
| "看下我的代码风格" | 引用具体文件的命名约定 |
| "这个项目用 React" | 直接 link `package.json` |
| 历史对话不清理 | 阶段完成后 /clear |

记住：**每 1k token 都是钱**。

## 七、Few-shot 例子

对结构化输出特别有效：

```markdown
# 任务
为接口生成单元测试。

# 示例输出
对于 `getUser(id: string)`:
- 测试 1：正常 id 返回 user
- 测试 2：不存在 id 返回 null
- 测试 3：空 id 抛 ValidationError
- 测试 4：非法 id 抛 ValidationError

# 现在请为这个接口生成测试：
[接口签名]
```

一个例子能让代理少花 2k token 思考输出格式。

## 八、Tool Use 指引

如果你的工具调用频繁出错，多半是 tool 描述不清：

```python
{
    "name": "search_files",
    "description": "在仓库中搜索文件名匹配 pattern 的文件。返回路径列表。",
    "input_schema": {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "glob 风格，例如 'src/**/*.ts'。不要用正则。"
            },
            "exclude": {
                "type": "array",
                "items": {"type": "string"},
                "description": "排除目录，默认 ['node_modules', 'dist']"
            }
        },
        "required": ["pattern"]
    }
}
```

`description` 要写"用法 + 注意事项"，不是"这是什么"。

## 九、纠错而非泄气

代理给出错误答案时：

**坏纠正**：
> 你错了。重写一遍。

**好纠正**：
> 这里有问题：[具体引用]。这种实现会导致[具体后果]。请考虑用 X 方式替代。

具体反馈让代理学会"对的样子"，泛泛指责只会让它换个错法。

## 十、迭代到稳定

不要指望第一版 prompt 就完美。流程：

1. 写第一版
2. 跑 5 个真实任务，记录"哪里不顺"
3. 把不顺的地方加进 prompt
4. 重复

3 轮迭代后，你的 prompt 就到能用状态。再 3 轮到优秀。

## 十一、Anti-patterns

- ❌ Prompt 写成 marketing 文案（"卓越""完美""最佳实践"）
- ❌ 列 30 条规则（代理记不住）
- ❌ 重复同一意思
- ❌ 用"请"很多次（不影响输出但占 token）
- ❌ 把任务和角色混在一起

## 十二、相关阅读

- [Claude Code Subagent 实战](/blog/claude-code-subagent-practice/)
- [Claude Code Hooks 工作流](/blog/claude-code-hooks-workflow/)
- [Cursor Background Agent 国内配置](/blog/cursor-background-agent-config/)
- [AI 编程代理成本控制实战](/blog/ai-coding-agent-cost-control/)

用 [YoTradeApi](https://yotradeapi.com/register) 创建独立 Key，可以在不同工具间共享同一份 system prompt 与项目知识，按用例切模型。
