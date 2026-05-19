---
title: Cline Rules 与 Memory Bank 完整使用指南
description: Cline 的 .clinerules、Custom Instructions、Memory Bank、Workspace Rules 完整配置指南，附实战 yaml 与 markdown 模板。
keywords:
- cline rules
- clinerules
- cline memory bank
- cline 配置
- cline custom instructions
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/cline-rules-and-memory-bank/
tags:
- Cline
- Rules
- Memory Bank
- 配置
- 最佳实践
category: 工具配置
heroImage: ../../assets/blog-placeholder-1.jpg
---

# Cline Rules 与 Memory Bank 完整使用指南

Cline 的核心特性之一是 Rules 与 Memory Bank——把项目知识沉淀下来，让 AI 跨会话保持一致行为。配置好的工程组能让 Cline 用起来质量翻倍。本文给完整配置指南。

## 一、Cline 配置的 4 个层次

| 层级 | 位置 | 作用域 |
| --- | --- | --- |
| Global Custom Instructions | VSCode 设置 | 所有项目 |
| Workspace Rules | `.clinerules` | 当前项目 |
| Memory Bank | `memory-bank/` | 项目长期记忆 |
| Mode-specific Rules | `.clinerules-*` | 特定 mode |

优先级：Mode-specific > Workspace > Global。

## 二、Global Custom Instructions

VSCode 设置（Cmd+,）→ 搜 "Cline" → Custom Instructions：

```markdown
你是经验丰富的工程师，遵循以下原则：

1. 写代码前理解需求，不确定问。
2. 修改最少代码达成目标。
3. 优先复用现有代码，不重复造轮子。
4. 错误处理具体到错误类型，不要泛用 catch-all。
5. 测试驱动：改代码必看测试是否通过。
6. 中文回复。代码注释保持英文（除非项目约定）。
```

这是"全局人设"。所有项目都生效。

## 三、`.clinerules` 项目规则

在项目根创建 `.clinerules`：

```markdown
# 项目规则

## 技术栈
- Next.js 15 + React 19 + TypeScript
- 数据库: PostgreSQL + Prisma
- 部署: Cloudflare Pages
- 包管理: pnpm（不要用 npm）

## 文件组织
- 组件: src/components/{kebab-name}/index.tsx
- API 路由: src/app/api/v1/{resource}/route.ts
- 工具函数: src/lib/{kebab-name}.ts

## 命名约定
- 变量/函数: camelCase
- 类型/组件: PascalCase
- 常量: UPPER_SNAKE_CASE
- 文件: kebab-case

## 编码风格
- 不写空 try/catch
- API 响应统一 { ok, data?, error? }
- 不用 any，用 unknown 或具体类型
- 公开 API 必须 JSDoc

## 不要做
- 不修改 package.json 主版本号
- 不引入新依赖（先和我商量）
- 不动 prisma migrations 历史
- 不删测试，除非真过时

## 测试
- 测试文件 *.test.ts 紧邻被测文件
- 必须覆盖正常 / 边界 / 异常
- 改代码后跑 pnpm test 确认通过
```

每次 Cline 启动会自动读 `.clinerules`。它是项目级 system prompt。

## 四、Memory Bank（核心特性）

Memory Bank 是 Cline 独有的"持久化记忆"。在项目根创建 `memory-bank/` 目录：

```
memory-bank/
├── projectbrief.md
├── productContext.md
├── activeContext.md
├── systemPatterns.md
├── techContext.md
└── progress.md
```

### projectbrief.md

```markdown
# 项目简介

## 是什么
DocSync：Notion / Google Docs 文档同步到 GitHub Markdown 的 SaaS。

## 目标用户
技术博主、Indie hacker。

## 核心价值
让"在 Notion 写文档"和"在 GitHub 托管 Markdown 博客"无缝衔接。

## 商业模式
$9/月订阅，14 天免费试用。
```

### productContext.md

```markdown
# 产品上下文

## 为什么做这个
当前痛点：作者用 Notion 写，发布要手工导出 / 转 Markdown / 推 GitHub。

## 解决方案
连接 Notion API → 转换 → 推 GitHub。自动化。

## 不做什么
- 不做 SEO 服务
- 不做 hosting
- 不做编辑器
```

### activeContext.md

```markdown
# 当前活跃上下文

## 在做什么
正在实现 OAuth 接入 Notion。

## 已完成
- 基础 auth（email magic link）
- 用户表
- 落地页

## 下一步
- Notion OAuth callback
- token 加密存储
- 选择页面同步
```

### systemPatterns.md

```markdown
# 系统设计模式

## API 响应
所有 /api/* 返回 { ok: boolean, data?: T, error?: { code, message } }

## 错误处理
使用 src/lib/errors.ts 的 AppError 类，按 error.code 分类

## 数据库访问
用 src/lib/db.ts 导出的 prisma 实例。不要 import @prisma/client

## 鉴权
JWT in httpOnly cookie，validate by src/lib/auth/validate.ts
```

### techContext.md

```markdown
# 技术上下文

## 关键依赖
- next@^15 (App Router)
- prisma@^6
- @prisma/adapter-neon (Cloudflare 必须)
- resend@^4
- stripe@^17

## 配置入口
- .env.local（本地）
- Cloudflare Pages secrets（生产）

## 部署
push to main → GitHub Actions → wrangler pages deploy
```

### progress.md

```markdown
# 进度

## 已完成
- [x] 项目骨架
- [x] auth（email magic link）
- [x] 落地页

## 进行中
- [ ] Notion OAuth

## 待办
- [ ] 同步 worker
- [ ] Stripe 集成
- [ ] dashboard
```

## 五、Memory Bank 在 Cline 里怎么用

Cline 启动时如果检测到 `memory-bank/` 会自动读全部 markdown。你**不需要每次手动 @-mention**。

但要它**主动更新**，需要触发：

```
> 完成了 Notion OAuth。把进展写进 memory-bank/progress.md 和 activeContext.md。
```

或者让 Cline 在每个长任务结束时自己写：

```markdown
# .clinerules 加一条

## Memory Bank 更新规则
每完成一个 milestone：
1. 更新 progress.md
2. 更新 activeContext.md
3. 如有架构变更，更新 systemPatterns.md
```

## 六、Mode-specific Rules

`.clinerules-plan-mode` 和 `.clinerules-act-mode` 分别给 Plan / Act 模式独立配置。

### .clinerules-plan-mode

```markdown
# Plan Mode 规则

- 只规划，不动文件
- 输出格式：
  1. 任务目标（1 句话）
  2. 实施步骤（编号列表）
  3. 风险与未知（明确列出）
  4. 验收标准（可测量）
- 复杂任务拆成 3–5 步，每步可独立完成 + 验证
```

### .clinerules-act-mode

```markdown
# Act Mode 规则

- 按 Plan 实施，不要发散
- 每步完成后跑相关测试
- 测试失败要：
  1. 报告失败
  2. 分析根因
  3. 提出修复方案
  4. 修复（如简单）或问我（如复杂）
- 不要静默跳过错误
```

## 七、Cline Rules 与 .cursorrules 的差异

| 维度 | Cline `.clinerules` | Cursor `.cursorrules` |
| --- | --- | --- |
| 注入位置 | system prompt | system prompt |
| Memory Bank | ✓ 独有 | 部分（rules 文件） |
| Mode-specific | ✓ | 部分 |
| 团队共享 | commit 即可 | commit 即可 |

Cline 的 Memory Bank 是它的核心差异化。**Cursor 用户也可以模仿做一份 docs/，但不会自动注入**。

## 八、写好 Rules 的纪律

- **写约束多于描述**：少写"你是好工程师"，多写"不要做 X"
- **具体而非抽象**：不写"代码要简洁"，写"函数 ≤ 30 行"
- **可验证**：不写"风格统一"，写"用 prettier 配置"
- **更新**：每完成一个 milestone 检查 rules 是否要调
- **不要超过 2000 字**：太长 AI 记不住

## 九、防 Memory Bank 漂移

长期使用 Memory Bank 容易"自我矛盾"——前后写的内容冲突。每月做一次 audit：

```
> 审计 memory-bank/ 全部文件，找出：
> 1. 互相矛盾的描述
> 2. 已过时的内容
> 3. 缺失的关键信息
> 列一份清单，但不要改文件。
```

人工 review 后再决定怎么改。

## 十、实战：一个完整的 .clinerules 模板

我们 commit 进项目根：

```markdown
# Cline Rules: DocSync 项目

## 角色
你是 senior fullstack engineer，专注 Next.js + TypeScript。

## 通用原则
- 改最少代码达成目标
- 优先用项目现有模式（看 systemPatterns.md）
- 不引入新依赖，除非必要（要先跟我说）
- 中文回复，代码注释英文

## 技术栈（详见 memory-bank/techContext.md）
- Next.js 15 App Router
- Prisma + @prisma/adapter-neon
- Cloudflare Pages

## 必须遵守
- API 响应 { ok, data?, error? }
- 用 pnpm 不用 npm
- 测试紧邻代码，*.test.ts
- 改完代码跑 pnpm test

## 严格禁止
- rm -rf 任何东西
- git push --force
- 修改 prisma/migrations/* 历史
- 引入 lodash、moment 等大库

## 工作模式
- 默认 Plan Mode 起步
- 复杂任务先列计划
- 每完成一步更新 memory-bank/progress.md
```

## 十一、相关阅读

- [Cline 国内 API 配置详解](/blog/cline-cn-api-setup/)
- [Roo Code 国内配置](/blog/roo-code-cn-setup/)
- [AI Agent Prompt Engineering 中文实战](/blog/agent-prompt-engineering-cn/)
- [Claude Code Subagent 实战](/blog/claude-code-subagent-practice/)

把 Cline + Memory Bank 接入 [YoTradeApi](https://yotradeapi.com/register) 一把 Key，按上面 .clinerules 模板开始即可。
