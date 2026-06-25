---
title: Claude Code 在 Monorepo 里的使用策略
description: 详解 Claude Code 在 monorepo 项目中的最佳实践，包括上下文控制、CLAUDE.md 分层配置、子包定向操作与 CI 集成策略。
keywords:
  - Claude Code monorepo
  - monorepo AI 编码
  - Claude Code 大型项目
  - CLAUDE.md 配置
  - Claude Code 工作区策略
pubDate: '2026-06-25'
updatedDate: '2026-06-25'
canonical: https://blog.yotradeapi.com/blog/claude-code-monorepo-strategy/
tags:
  - Claude Code
  - Monorepo
  - 工程实践
  - AI 编码
category: 实战经验
heroImage: ../../assets/blog-placeholder-3.jpg
---

Monorepo 是大型工程团队的主流代码组织方式——一个仓库包含多个服务、多个 Package，彼此之间共享基础设施但独立演化。Turborepo、Nx、pnpm workspaces 让 monorepo 的构建工具链成熟了，但 AI 编码助手在 monorepo 里的使用策略却缺少系统性的讨论。

Claude Code 在 monorepo 中面临的核心挑战是**上下文爆炸**：一个典型的 monorepo 可能有几百个文件、十几个 Package，如果不加控制地让 Claude Code 读取整个仓库，Token 消耗会急剧上升，而且大量无关代码会稀释上下文质量，反而降低输出准确率。

本文分享在 monorepo 中使用 Claude Code 的具体策略，覆盖目录结构规划、CLAUDE.md 分层配置、上下文边界控制、子包定向操作，以及 CI 集成的最佳实践。

---

## 一、Monorepo 的典型结构与 Claude Code 的挑战

假设一个典型的 monorepo 结构：

```
my-monorepo/
├── apps/
│   ├── web/          # Next.js 前端
│   ├── api/          # Fastify 后端
│   └── mobile/       # React Native
├── packages/
│   ├── ui/           # 共享 UI 组件库
│   ├── config/       # 共享配置（ESLint、TypeScript）
│   ├── auth/         # 身份验证 SDK
│   └── types/        # 共享类型定义
├── tools/
│   ├── scripts/      # 构建脚本
│   └── generators/   # 代码生成器
├── CLAUDE.md         # 根级说明
└── package.json
```

当你在根目录启动 Claude Code 时，它面对的是整个仓库。如果让它"帮我修复 web 应用的登录页面"，它可能会去读 `apps/api/` 里的认证逻辑、`packages/auth/` 的 SDK、`packages/ui/` 的表单组件……在找到正确切入点之前，大量无关 Token 已经消耗完了。

---

## 二、CLAUDE.md 分层配置：核心武器

Claude Code 支持在任意目录放置 `CLAUDE.md`，上层的配置文件会向下继承，子目录的配置可以覆盖或补充。这是 monorepo 场景下最重要的控制手段。

### 2.1 根级 CLAUDE.md：全局导航地图

```markdown
# 仓库结构

这是一个使用 pnpm workspaces 的 monorepo。

## 工作区结构
- `apps/web` — Next.js 14 前端（React 18，App Router）
- `apps/api` — Fastify 后端，REST + GraphQL
- `apps/mobile` — React Native（Expo SDK 50）
- `packages/ui` — Tailwind CSS 组件库，供所有 app 使用
- `packages/auth` — JWT + OAuth2 身份验证 SDK
- `packages/types` — 共享 TypeScript 类型，不包含逻辑

## 常用命令
- `pnpm build` — 构建所有包（Turborepo 缓存）
- `pnpm dev` — 并行启动所有开发服务器
- `pnpm test` — 运行所有包的测试
- `pnpm --filter @my/web dev` — 只启动 web

## 跨包依赖规则
- `apps/*` 可依赖 `packages/*`
- `packages/*` 只能依赖其他 `packages/*`，不能依赖 `apps/*`
- 修改 `packages/types` 会影响所有消费者，修改前确认影响范围

## 开始任务时的建议
1. 明确说明你要操作哪个 app 或 package
2. 大多数任务只需要在对应子目录里工作，无需读取整个仓库
```

根级 `CLAUDE.md` 的作用是给 Claude Code 一张地图，让它知道各个目录的职责，从而在开始任务时快速定位正确的工作区，而不是漫无目的地探索。

### 2.2 子包级 CLAUDE.md：具体上下文

每个主要子包都应该有自己的 `CLAUDE.md`：

```markdown
# apps/web/CLAUDE.md

## 这是什么
Next.js 14 前端，使用 App Router。主要负责用户界面和浏览器端逻辑。

## 技术栈
- Next.js 14（App Router）
- React 18
- Tailwind CSS（使用 `packages/ui` 的组件，不直接写内联样式）
- SWR（数据获取）
- Zod（表单验证）

## 目录结构
- `app/` — Next.js App Router 页面
- `components/` — 本 app 私有组件（UI 组件用 packages/ui）
- `hooks/` — 自定义 React Hook
- `lib/` — 工具函数和 API 客户端
- `types/` — 本 app 私有类型（共享类型在 packages/types）

## 常用命令
- `pnpm --filter @my/web dev` — 启动开发服务器（端口 3000）
- `pnpm --filter @my/web build` — 构建
- `pnpm --filter @my/web test` — 运行测试

## 注意事项
- 不要直接引入 `apps/api` 里的代码，通过 HTTP API 通信
- 新增公共 UI 组件请在 `packages/ui` 里添加，不要在 `components/` 里重复
- 认证相关逻辑使用 `packages/auth`，不要自己实现 JWT 解析
```

---

## 三、上下文边界控制策略

### 3.1 在子目录启动 Claude Code

最直接的控制手段：**cd 到目标子目录后启动 Claude Code**。

```bash
# 只处理 web 应用的任务
cd apps/web
claude  # 此时 Claude Code 的默认工作目录是 apps/web

# 只处理 auth 包
cd packages/auth
claude
```

当 Claude Code 从子目录启动时，它仍然可以读取父目录的文件（比如根级 `package.json`），但默认的探索和读取行为会聚焦在当前目录。结合子目录的 `CLAUDE.md`，上下文质量明显提升。

### 3.2 在 Prompt 中显式限定范围

即使在根目录工作，也要在 Prompt 中明确说明范围：

```bash
# 不推荐（模糊，可能触发大范围读取）
claude "帮我实现用户注册功能"

# 推荐（明确范围）
claude "在 apps/api/src/routes/auth/ 下实现用户注册接口，
使用 packages/auth 的 hashPassword 函数，
不要修改其他目录的文件"
```

### 3.3 使用 .claudeignore 排除无关目录

在项目根目录创建 `.claudeignore` 文件（语法与 `.gitignore` 相同），告诉 Claude Code 哪些目录无需读取：

```gitignore
# .claudeignore

# 构建产物
.next/
dist/
build/
.turbo/

# 依赖
node_modules/
.pnpm-store/

# 与当前任务无关的 app（在不同 app 工作时动态调整）
# apps/mobile/  ← 如果只在做 web 任务时可以临时取消注释

# 生成的文件
*.generated.ts
__generated__/

# 大型静态资源
public/videos/
public/fonts/
```

---

## 四、子包定向操作实战

### 4.1 场景：修改共享组件库，验证影响范围

```bash
# 任务：在 packages/ui 添加一个新的 Button 变体

# 步骤 1：在 packages/ui 目录下开始工作
cd packages/ui

# Prompt 要明确范围和验证策略
claude "
在 src/components/Button/ 里添加 'ghost' 变体（透明背景，有边框）。
要求：
1. 修改 Button.tsx 添加 variant='ghost' 的样式
2. 更新 Button.stories.tsx 添加对应 Story
3. 更新 Button.test.tsx 添加测试
4. 不要修改 packages/ui 以外的文件
完成后运行 pnpm test 验证
"
```

### 4.2 场景：跨包的类型变更

当需要修改 `packages/types` 时，必须同时检查所有消费者：

```bash
# 在根目录工作，但明确任务边界
claude "
我要在 packages/types/src/user.ts 里的 User 接口添加 avatarUrl?: string 字段。
请：
1. 修改 packages/types/src/user.ts
2. 搜索 apps/ 和 packages/ 里所有使用 User 类型的文件
3. 评估是否有需要同步更新的代码（如显示头像的组件）
4. 只修改确实需要改动的地方，其他地方不动
"
```

### 4.3 场景：在 CI 中针对变更的包运行 Claude Code

结合 Turborepo 的 affected 能力：

```bash
# CI 脚本：只对本次 PR 变更的包运行 AI 代码审查
#!/bin/bash

CHANGED_PACKAGES=$(pnpm turbo run build --dry=json | jq -r '.tasks[].package' | sort -u)

for pkg in $CHANGED_PACKAGES; do
    echo "=== 审查 $pkg ==="
    pkg_dir=$(pnpm --filter "$pkg" root 2>/dev/null)
    if [ -d "$pkg_dir" ]; then
        cd "$pkg_dir"
        claude --print "
请检查本次变更（git diff HEAD~1）是否有以下问题：
1. 未处理的边界情况
2. 缺失的类型标注
3. 明显的性能问题
只报告确定的问题，不需要建议优化。
" > "/tmp/review-$pkg.md"
        cd -
    fi
done
```

---

## 五、Token 消耗控制实践

### 5.1 善用 --print 模式处理批量任务

Claude Code 的 `--print` 模式（非交互，输出到 stdout）适合脚本化的批量操作：

```bash
# 批量为某个子包的所有函数添加 JSDoc
find packages/auth/src -name "*.ts" | while read file; do
    claude --print "
为 $file 里每个导出函数添加 JSDoc 注释（中英文均可）。
只输出修改后的完整文件内容，不要解释。
" > /tmp/updated.ts && mv /tmp/updated.ts "$file"
done
```

### 5.2 用 Subagent 并行处理多个子包

Claude Code 的子代理（Subagent）功能可以并行处理多个子包，避免串行的上下文累积：

```
# 在 Claude Code 交互中的 Prompt
请并行完成以下任务（每个任务独立，不共享上下文）：
1. 在 packages/auth 里添加 OAuth2 PKCE 支持的类型定义
2. 在 packages/ui 里将所有 className 字符串常量提取为 CSS 变量
3. 在 apps/api 里为所有 route handler 添加 Zod 请求验证

每个任务只在对应目录内操作，不要跨包修改。
```

子代理的详细使用方式可参考 [Claude Code 子代理使用实践](/blog/claude-code-subagent-practice/)。

---

## 六、CI 集成：在 PR 流程中使用 Claude Code

### 6.1 Pre-commit Hook 配置

```bash
# .husky/pre-commit
#!/bin/sh

# 只对本次暂存的文件做 Claude Code 检查
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -E "\.(ts|tsx)$")

if [ -n "$STAGED_FILES" ]; then
    echo "Running Claude Code review on staged files..."
    claude --print "
检查以下文件的代码质量（文件：$STAGED_FILES）：
- TypeScript 类型是否完整
- 是否有明显的 bug 或边界情况遗漏
- 输出格式：每个问题一行，格式为 [文件:行号] 问题描述
如果没有问题，输出 'All clear.'
" || true  # 不因 Claude Code 失败阻断提交
fi
```

### 6.2 GitHub Actions 集成

更完整的 CI 集成策略，可参考 [Claude Code CI 集成实战](/blog/claude-code-ci-integration/)，那篇文章详细讲解了 PR 触发、Secret 管理和并行 Review 配置。

---

## 七、常见陷阱与规避方法

**陷阱一：在根目录做"全局搜索"导致上下文爆炸**

症状：你让 Claude Code 搜索某个接口的用法，它读取了整个 `node_modules` 或 `dist` 目录。

规避：在 `.claudeignore` 里排除构建产物和依赖，或用 `--include` 参数限定搜索范围。

**陷阱二：跨包修改导致构建失败**

症状：Claude Code 修改了 `packages/types` 里的类型，但遗漏了某个 `apps/` 里的消费者，导致 TypeScript 报错。

规避：在 Prompt 里明确要求"修改 packages/types 前先用 `grep -r` 找出所有消费者，确认修改范围"。

**陷阱三：子包 CLAUDE.md 里的命令与实际不一致**

症状：CLAUDE.md 里写的是 `npm run test`，但实际项目用 pnpm，导致 Claude Code 执行错误命令。

规避：将 CLAUDE.md 里的命令视为代码一样维护，每次更新 `package.json` 脚本时同步更新。

**陷阱四：Session 跨 Package 携带了错误的上下文**

症状：在同一个 Claude Code Session 里，先处理了 `apps/api` 的任务，再处理 `apps/web` 的任务，模型混淆了两个应用的技术栈和约定。

规避：跨包的大任务使用新 Session（`/clear` 或重启），每个 Package 的任务保持独立 Session。

---

## 八、相关阅读

- [Claude Code 子代理使用实践](/blog/claude-code-subagent-practice/)
- [Claude Code CI 集成实战](/blog/claude-code-ci-integration/)
- [Claude Code 上手入门指南](/blog/claude-code-getting-started/)
- [Claude Code Hooks 工作流自动化](/blog/claude-code-hooks-workflow/)
- [AI 流水线的错误追踪方案](/blog/ai-pipeline-error-tracing/)

在 monorepo 中使用 Claude Code 时，如果需要切换不同的模型供应商（比如对复杂任务用 Claude Opus 4.8，日常任务用 Claude Sonnet），[YoTradeApi](https://yotradeapi.com) 提供统一 API 中转，支持一个 Key 在不同场景下灵活切换模型，账单人民币结算。
