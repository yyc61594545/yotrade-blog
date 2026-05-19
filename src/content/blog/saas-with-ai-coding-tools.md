---
title: 用 AI 编程工具一周写一个 SaaS 的实战记录
description: 用 Cursor + Claude Code + Aider 组合 7 天写一个全功能 SaaS（注册/订阅/前端/后端/部署）的真实流程与踩坑记录。
keywords:
- ai 编程 saas
- cursor claude code 实战
- ai 写 saas
- 一周 saas
- ai 编程 案例
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/saas-with-ai-coding-tools/
tags:
- 实战
- SaaS
- Cursor
- Claude Code
- 案例
category: 实战案例
heroImage: ../../assets/blog-placeholder-4.jpg
---

# 用 AI 编程工具一周写一个 SaaS 的实战记录

不少人问"AI 编程到底能做到什么程度"。本文记录我用 7 天时间用 AI 编程工具组合写一个完整 SaaS 的真实过程：技术栈、工具切换、踩坑、修复，最终上线。

## 一、项目概况

| 项目 | 内容 |
| --- | --- |
| 类型 | 文档同步 SaaS（类似简版 Notion → Markdown 镜像） |
| 用户 | 技术博主、Indie hacker |
| 栈 | Next.js 15 + Postgres + Prisma + Stripe |
| 部署 | Cloudflare Pages + Neon |
| 总代码量 | ~5800 行 |
| 总 token 消耗 | ~80M（中转账单约 $90） |
| 实际写代码时间 | 7 天 × 6 小时 |

## 二、工具组合

| 阶段 | 工具 | 主力模型 |
| --- | --- | --- |
| 架构 + 设计 | Claude Code | Opus 4.7 |
| 写代码 | Cursor | Sonnet 4.6 |
| 重构 | Aider | Opus + Sonnet |
| 调 bug | Claude Code Subagent | Opus 4.7 |
| 文档 / 营销文案 | Cherry Studio | Opus 4.7 |

**关键**：一把 Key 走中转，所有工具共用。

## 三、Day 1：架构

```bash
$ claude
> 我要做一个文档同步 SaaS。功能：
>   1. 用户连接 Notion / Google Docs
>   2. 选择页面订阅
>   3. 自动同步到用户的 GitHub repo（Markdown）
>   4. 订阅 $9/月（Stripe）
> 
> 给我一个架构方案：技术栈、数据模型、关键流程、风险点。
```

Opus 4.7 在 5 分钟内给出了：

- Next.js 15 + Postgres + Prisma 选型理由
- 6 张表的 schema
- OAuth 流程
- 同步任务的 worker 设计
- Stripe webhook 处理

我审一遍，修了 2 处（schema 多了一张表、worker 用 Cloudflare Queues 替代 BullMQ）。

**产出**：`docs/architecture.md` 3000 字。

## 四、Day 2：脚手架

```bash
$ npx create-next-app@latest my-saas --typescript --tailwind --app
$ cd my-saas
$ cursor .
```

Cursor 里：

```
> 按 docs/architecture.md 创建：
> - prisma schema
> - 6 张表 migration
> - basic auth（email + magic link，用 resend）
> - 首页（简单 landing）
```

Sonnet 4.6 把这部分一次跑出来。几个小修就跑通了。

**踩坑 1**：Prisma 在 Cloudflare Pages 不支持原生 driver。Sonnet 给的方案是用 `@prisma/adapter-neon`。

## 五、Day 3：OAuth

OAuth 流程麻烦：Notion 的 callback、token 加密、refresh 流程。

```bash
$ aider --architect --model openai/claude-opus-4-7 --editor-model openai/claude-sonnet-4-6
> 实现 Notion OAuth 接入。要求：token 加密存数据库（aes-256-gcm），自动 refresh，按用户隔离。
```

Aider 的 architect 模式：

- Opus 设计：用 `crypto` 内置模块加密，用 `nextauth` 走 OAuth flow
- Sonnet 写代码：写了 `lib/encryption.ts`、`app/api/auth/notion/route.ts`、`lib/notion/client.ts`

实测一次跑通。

**踩坑 2**：Aider 默认会 git commit。它一次 commit 太大不容易 review。改 `.aider.conf.yml` 设 `auto-commits: false`，手动每完成一块再 commit。

## 六、Day 4：核心同步

这是项目最难的部分。

```bash
$ claude
> 实现 Notion → Markdown 转换 + 推送到 GitHub repo。要求：
> 1. 增量同步（只处理变化的页面）
> 2. 嵌套数据库支持
> 3. 图片下载到 GitHub
> 4. 错误自动重试
> 5. 写完单元测试
```

启动 `architect` subagent：

```
> 用 architect subagent 先做技术方案
```

5 分钟后产出方案。我看了一遍，要求：

```
> 实施。每个文件改完跑 npm test 验证。
```

Claude Code 跑了大约 45 分钟，期间：

- 调用 Read 100+ 次
- 调用 Edit/Write 60+ 次
- 跑 npm test 12 次
- 自动修了 3 个 bug

**总消耗约 800k tokens（中转账单 $8）**。

## 七、Day 5：Stripe

```bash
$ cursor .
> 用 stripe@^17 接入订阅。$9/月，14 天免费试用。处理 webhook：subscription.created / updated / deleted。
> 把订阅状态同步到 user.subscriptionStatus。
```

Sonnet 4.6 给方案 + 代码。一次跑通。

**踩坑 3**：本地测 webhook 要用 `stripe listen`，本地 URL 转发到 stripe CLI 用的端口。Cursor 默认没装。我让它给一份 README 添加这部分。

## 八、Day 6：UI + 文案

```bash
$ cursor .
> 优化 dashboard 设计：左边订阅列表，右边页面预览。用 shadcn/ui。
```

UI 改动 Cursor 的 Composer 一次性搞定。

文案用 Cherry Studio 跑 Claude Opus：

```
> 写一个 SaaS 落地页文案：
> 产品：Notion / Google Docs 同步到 GitHub
> 目标用户：技术博主
> 风格：简洁、技术导向、不过度营销
> 输出：H1、副标题、3 个卖点 + 描述、CTA
```

Opus 给出非常好的文案。微调即用。

## 九、Day 7：上线 + 修 bug

部署 Cloudflare Pages。第一次部署遇到 6 个 build error。

```bash
$ claude
> npm run build 失败，错误如下：
> [粘贴错误]
> 一个一个修，跑测试确认。
```

Claude Code 跑 30 分钟全部修完。

部署成功后跑 e2e：

```bash
$ claude
> 写一个简单 playwright e2e：跑通注册 → 连接 Notion → 选页面 → 同步成功
```

测试发现一个 bug（OAuth callback URL 在 prod 写死了 localhost）。修复后上线。

**Day 7 总 token 消耗约 1.5M（中转账单约 $18）**。

## 十、整体复盘

### 时间分配

| 类别 | 时间占比 |
| --- | --- |
| 让 AI 写代码 | 35% |
| Review AI 输出 | 25% |
| 自己写代码 | 15% |
| 调 bug（人 + AI） | 15% |
| 写文档 / 文案 | 10% |

### 成本

| 项 | 金额 |
| --- | --- |
| AI API（通过中转） | ~$90 |
| Cloudflare Pages | $0 |
| Neon Postgres | $0（免费层） |
| Resend | $0（免费层 100/天） |
| Stripe | $0（按抽成） |
| 总 | **~$90** |

如果不开缓存，账单大概 $250+。

### 模型选择经验

| 任务 | 用了什么 | 体感 |
| --- | --- | --- |
| 架构 + 文案 | Opus 4.7 | 值 |
| 90% 写代码 | Sonnet 4.6 | 最佳性价比 |
| 长任务 + Subagent | Opus 4.7 | 值 |
| 摘要 / 翻译 | Haiku 4.5 | 完全够 |

## 十一、能给别人的建议

1. **先用 Claude Code 出架构方案**：长文档级输出能压缩后期返工
2. **写代码主力用 Cursor**：补全 + Composer 体验最佳
3. **重构 / 升级用 Aider**：自动 commit 让回滚成本极低
4. **长任务用 Subagent**：上下文不污染主对话
5. **文案别用便宜模型**：人能看出 Haiku 的味道
6. **每天看一次中转账单**：失控前 24 小时一定有信号

## 十二、不该过度乐观的地方

- ❌ AI 不会替你做产品决策。需求不清楚再多代码也没用
- ❌ AI 会犯低级错误。一定要 review，不要盲信
- ❌ AI 不能保证安全。涉及钱、用户数据的关键路径要自己看
- ❌ 复杂业务逻辑 AI 容易丢细节。关键流程拆小

## 十三、相关阅读

- [Cursor API 中转怎么选](/blog/2026-05-15-cursor-api-relay-recommendation-2026/)
- [Claude Code 镜像国内配置完整指南](/blog/claude-code-mirror-cn-setup/)
- [Aider 中文配置与最佳实践](/blog/aider-cn-config-guide/)
- [AI 编程代理成本控制实战](/blog/ai-coding-agent-cost-control/)
- [AI Agent Prompt Engineering 中文实战](/blog/agent-prompt-engineering-cn/)

想用一把 Key 接所有工具？[YoTradeApi](https://yotradeapi.com) 创建 API Key 后按各工具教程配置 base_url 即可。
