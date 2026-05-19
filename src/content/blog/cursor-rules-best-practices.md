---
title: .cursorrules 最佳实践：让 Cursor 真正懂你的项目
description: .cursorrules 与 .cursor/rules/*.md 的完整写法、组织结构、模板示例与团队协作策略，把 Cursor 输出质量提升一个量级。
keywords:
- .cursorrules
- cursor rules
- cursor 项目知识
- cursor 配置 最佳实践
- cursor system prompt
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/cursor-rules-best-practices/
tags:
- Cursor
- Rules
- 最佳实践
- 配置
- 项目知识
category: 工具配置
heroImage: ../../assets/blog-placeholder-1.jpg
---

# .cursorrules 最佳实践：让 Cursor 真正懂你的项目

Cursor 输出质量的天花板是 `.cursorrules`。配好它，每次对话不用重复解释项目背景。配不好，Cursor 输出永远像"刚来实习生的代码"。本文给完整最佳实践。

## 一、两种 Rules 形态

| 形态 | 位置 | 作用 |
| --- | --- | --- |
| Legacy | `.cursorrules`（项目根） | 所有任务注入 |
| New | `.cursor/rules/*.md` | 按 glob 选择性注入 |

新版本两者都支持。**推荐用新版**：粒度细，能按文件类型加载不同 rules。

## 二、最小可用 `.cursorrules`

```markdown
# 项目: DocSync

## 是什么
Notion / Google Docs → GitHub Markdown 同步 SaaS。

## 栈
- Next.js 15（App Router）
- React 19 + TypeScript（strict）
- Prisma + PostgreSQL + @prisma/adapter-neon
- Tailwind v4 + shadcn/ui
- 部署：Cloudflare Pages
- 包管理：pnpm（不要用 npm）

## 命名约定
- 文件：kebab-case
- 组件：PascalCase
- 函数/变量：camelCase
- 常量：UPPER_SNAKE_CASE
- 类型：PascalCase

## 必须遵守
- API 路由返回 `{ ok, data?, error? }`
- 不用 console.log，用 src/lib/logger
- 不写空 try/catch
- 用 zod 验证 API 输入
- 改 schema 配套 migration

## 严格禁止
- 引入新依赖（要先和我商量）
- 改 prisma migrations 历史
- 修改 next.config.js 主要配置
- 用 any（用 unknown 或具体类型）
- // @ts-ignore

## 工作流
- 复杂任务先列计划（Plan Mode）
- 改完跑 pnpm test
- 关键路径补单元测试
```

够 80% 项目用了。

## 三、新版 `.cursor/rules/` 结构

```
.cursor/rules/
├── _index.md          # 总览，always 注入
├── react.md           # globs: src/**/*.tsx
├── api.md             # globs: src/app/api/**
├── db.md              # globs: prisma/**, src/lib/db/**
├── tests.md           # globs: **/*.test.ts
└── ci.md              # 描述 CI 流程
```

每个文件 frontmatter 指定 glob：

```markdown
---
description: API 路由规则
globs:
  - src/app/api/**/*.ts
alwaysApply: false
---

# API 规则

- 所有路由用 zod 验证 input
- 用 src/lib/auth/validate 验证 JWT
- 错误抛 AppError，不直接 throw
- 返回 { ok, data?, error? }
- 路由命名 /api/v1/{resource}/{action}
```

这样写 React 组件时不注入 API 规则，省 token + 输出更聚焦。

## 四、关键章节：角色

不要写"你是助手"。写**有特定立场**的角色：

```markdown
## 角色

你是有 10 年经验的高级工程师。原则：
- 修改最少代码达成目标
- 优先复用项目现有抽象，不重复造轮子
- 不确定的事问我，不要瞎猜
- 看到不合理设计，礼貌指出，不一味迎合
```

最后一句**非常重要**——让 AI 能"反对你"而不是只会"是是是"。

## 五、关键章节：栈与版本

```markdown
## 关键依赖（版本敏感）

- Next.js ^15.0（注意 App Router，不要混 Pages Router）
- React 19（Server Component 是默认，Client Component 显式 'use client'）
- Prisma 6（注意 @prisma/adapter-neon 在 Cloudflare 必需）
- Tailwind v4（不再用 tailwind.config.js，改用 @theme 在 CSS 里配）
- zod ^3.23
- @tanstack/react-query ^5
```

写清楚版本，AI 不会给你 React 17 时代的写法。

## 六、关键章节：文件组织

```markdown
## 文件组织

```
src/
├── app/                  # Next.js App Router
│   ├── (auth)/           # auth 相关路由组
│   ├── (dashboard)/      # dashboard 路由组
│   └── api/v1/{资源}/    # API 路由
├── components/
│   ├── ui/               # shadcn 基础组件
│   └── {功能}/           # 业务组件，kebab-case 目录
├── lib/
│   ├── auth/             # 鉴权
│   ├── db/               # 数据库
│   └── utils.ts          # 通用工具
└── styles/
    └── global.css
```

新文件创建必须遵守这个组织。
```

AI 不知道你的目录结构 → 它会随便放。**用 ASCII 树喂给它**。

## 七、关键章节：约定与禁止

```markdown
## 通用约定

- 用 named export，避免 default export（除 Next.js page 必须 default）
- async function 优先于 Promise.then
- 用 `??` 而不是 `||` 处理 nullish
- 数据获取用 server component 或 react-query，不要 useEffect + fetch
- 表单用 react-hook-form + zod，不要手动 state

## 严格禁止

- 引入 lodash（用原生或写小工具）
- 引入 moment.js（用 date-fns 或 dayjs）
- 用 React.FC（直接写函数签名）
- 用 enum（用 const object as const）
- 在 client component 里 import server-only 代码
```

## 八、关键章节：常见陷阱

```markdown
## 项目特定陷阱

### 1. Cloudflare Pages 限制
- 不能用 Node 内置的 `fs`、`crypto`（用 web crypto）
- 不能用 Prisma 默认 driver（必须用 adapter-neon）
- Edge runtime 没有 setTimeout 阻塞，注意异步顺序

### 2. Prisma 迁移
- 改 schema 后必须跑 `pnpm prisma generate`
- 不要直接改 migrations/*.sql，用 prisma migrate dev

### 3. shadcn 组件升级
- 升级前看 changelog，CLI 可能改 className
- 升级一个组件，相关组件可能需要同步改

### 4. React 19 注意点
- ref 不再需要 forwardRef
- use client 边界要清楚
- server action 用 'use server'
```

这些是项目的"经验沉淀"。一年攒下来能让 AI 输出质量翻倍。

## 九、关键章节：测试要求

```markdown
## 测试

- 单元：紧邻代码，*.test.ts
- 用 vitest（不是 jest）
- 改业务逻辑必须新增 / 更新测试
- 覆盖：正常 / 边界 / 异常 三种 case
- 改完跑 pnpm test --run，必须全绿
```

## 十、按文件类型的 rules

```markdown
---
description: React 组件规则
globs:
  - src/components/**/*.tsx
  - src/app/**/*.tsx
---

# 组件

- 默认 server component，client component 顶部 'use client'
- props 用 interface，导出（供其它处复用）
- 不写 className 拼接，用 src/lib/utils.ts 的 cn()
- 长 className 提取到 const
- 用 shadcn/ui 组件优先，不重写
- 表单永远用 react-hook-form，不要 useState 手控
```

```markdown
---
description: 数据库与 Prisma
globs:
  - prisma/**
  - src/lib/db/**
---

# 数据库

- schema 修改必须配套 migration
- migration 必须向后兼容
- index 显式声明（@@index）
- 软删除字段统一 deletedAt
- 时间戳统一 createdAt / updatedAt
- 不在 prisma schema 里写注释（README 解释）
```

## 十一、文档化"为什么"

最容易被忽略的部分：

```markdown
## 设计决策

### 为什么用 Prisma 而不是 Drizzle
- 团队熟悉
- ecosystem 更成熟
- migration 工具更完善

### 为什么用 Cloudflare Pages
- 免费层够
- Edge 加速
- 与 Workers / D1 / R2 集成

### 为什么不用 Server Action
- 复杂业务流程难调试
- 表单库（react-hook-form）配合不顺
- 用 API route + react-query 模式更清晰
```

AI 知道"为什么"才不会**反向重构**（推翻已有决策）。

## 十二、Anti-patterns

- ❌ 写成营销文案（"我们追求卓越"）
- ❌ 列 50 条无重点
- ❌ 没具体例子
- ❌ 永远不更新
- ❌ 在 rules 里写 secrets

## 十三、长度建议

| 项目规模 | rules 总长度 |
| --- | --- |
| 个人小项目 | 200–500 字 |
| 个人中型 | 500–1500 字 |
| 团队项目 | 1500–3500 字 |
| 大型 monorepo | 用 `.cursor/rules/` 分段 |

超过 3500 字单文件 → 拆。

## 十四、团队协作

`.cursorrules` 和 `.cursor/rules/` 都应该 commit。每个 PR 如果发现 AI 出错的模式，**反思是不是 rules 缺**，补一条。

```markdown
## 学到的教训（持续追加）

- 2025-10: AI 老在 server component 里 use state，rules 补"server component 不能有状态"
- 2025-11: 几次写出 Promise.then，补"async 优先"
- 2025-12: AI 引入 lodash 被发现，明确禁止
```

## 十五、相关阅读

- [Cursor 新手完整教程](/blog/cursor-getting-started-cn/)
- [Cline Rules 与 Memory Bank](/blog/cline-rules-and-memory-bank/)
- [AI Agent Prompt Engineering 中文实战](/blog/agent-prompt-engineering-cn/)
- [AI 编程的 12 个常见错误与避坑指南](/blog/ai-coding-mistakes-to-avoid/)
- [Cursor API 中转怎么选](/blog/2026-05-15-cursor-api-relay-recommendation-2026/)

把 .cursorrules 配好 + 接 [YoTradeApi](https://yotradeapi.com/register) 中转，Cursor 体验会立刻和"一开始"完全不同。
