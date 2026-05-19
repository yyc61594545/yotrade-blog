---
title: 后端开发者用 AI 编程的实战工作流
description: 后端工程师用 Claude Code / Cursor / Aider 提效的场景：API 设计、数据库 schema、迁移、测试、性能优化、错误处理。
keywords:
- 后端 ai 编程
- claude code 后端
- ai 写 api
- ai 数据库 schema
- ai 写测试
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/ai-coding-for-backend-dev/
tags:
- 后端
- Node.js
- Python
- 数据库
- 实战
category: 实战案例
heroImage: ../../assets/blog-placeholder-3.jpg
---

# 后端开发者用 AI 编程的实战工作流

后端开发的"重复但容易出错"的部分（CRUD、迁移、错误处理、测试）特别适合 AI 协作。本文给后端工程师按真实任务分类的实战工作流。

## 一、API 设计

```
> 我要给文档同步功能设计 REST API。需求：
> 1. 列出当前用户订阅的文档
> 2. 添加一个新订阅
> 3. 取消订阅
> 4. 触发立即同步
> 5. 看同步历史
>
> 输出：
> - OpenAPI YAML（含完整 schema）
> - 错误码定义
> - 鉴权要求
> - 限流策略
```

让 AI 先出 spec，**自己审一遍再让它实现**。spec 错了实现再准也是错的。

## 二、Prisma / TypeORM schema

```
> 给上面的 API 设计数据模型。
> - 用 Prisma
> - PostgreSQL
> - 字段命名 snake_case，模型名 PascalCase
> - 加适当 index
> - 软删除（deletedAt）
> - 时间戳（createdAt / updatedAt）
> 写完跑 `pnpm prisma migrate dev` 验证
```

Claude Code 配合 hook 自动跑 `prisma migrate dev` 验证，**schema 错误立刻可见**。

## 三、CRUD endpoint 生成

```
> 实现 GET / POST /api/v1/subscriptions：
> - 鉴权：JWT in cookie，用 src/lib/auth/validate
> - 输入验证：用 zod
> - 错误处理：抛 AppError（src/lib/errors）
> - 响应：{ ok, data?, error? }
> - 写测试覆盖正常 / 401 / 验证错误三种情况
```

这种"模式化"任务 AI 写得又快又稳。

## 四、数据库迁移

最容易出错的环节。**严格要求**：

```
> 加一个 user.is_admin BOOLEAN NOT NULL DEFAULT false 字段。
> 要求：
> 1. 生成 prisma migration
> 2. 向后兼容（现有数据不受影响）
> 3. 不要 reset 数据
> 4. 写一份 rollback 计划
```

**Production migration 我永远人工审**。AI 给的迁移建议有时省了"backfill"步骤。

## 五、错误处理

```
> 重构 src/api/users.ts 的错误处理：
> - 不要泛用 try/catch
> - 每种异常类型对应一种 HTTP 状态码
> - 用 src/lib/errors.ts 的 AppError 类
> - 不暴露内部错误细节给客户端
> - 日志记录完整信息（含 stack）
```

错误处理一致是后端代码质量的关键。AI 帮你统一。

## 六、性能优化

```
> 慢查询：
> SELECT * FROM orders WHERE user_id = $1 ORDER BY created_at DESC
> EXPLAIN ANALYZE 输出：[贴]
>
> 找出优化方案。给我：
> 1. 根因分析
> 2. 索引建议
> 3. 查询重写建议（如必要）
> 4. 风险评估
```

AI 看 EXPLAIN ANALYZE 给方案，质量不输 senior DBA。

## 七、N+1 排查

```
> 这段代码看上去有 N+1：
> [贴 ORM 查询代码]
> 找出来并修复（用 include / preload / dataloader 等）。
```

ORM 用户最常踩的坑。AI 看到一眼就知道。

## 八、写测试（重要）

```
> 给 src/api/subscriptions/create.ts 加单元测试：
> - 正常路径
> - 重复订阅
> - 已删除文档
> - 用户已达订阅上限
> - 认证失败
> 用 jest + supertest
> 覆盖路径全部 ≥ 90%
```

后端**测试覆盖率提升靠 AI 最高效**。一晚上能从 30% 拉到 80%。

## 九、并发与竞态

```
> 这段代码可能有竞态：
> [贴异步代码]
> 找出可能的竞态条件，给出修复方案：
> 1. 行锁 / 表锁 / advisory lock
> 2. 乐观锁（version 字段）
> 3. 队列化
> 评估每种方案的开销
```

AI 在并发上的分析能力近年提升明显，能给出几种 trade-off 的方案。

## 十、缓存策略

```
> 给 GET /api/v1/products/:id 加 redis 缓存：
> - TTL 5 分钟
> - 删 / 改时主动失效
> - 失败时 graceful degrade（fallback DB）
> - 用 src/lib/cache.ts 的 cache wrapper
```

加缓存是模式化的，AI 写完后只要看：

1. 是否正确失效
2. 失败降级是否对
3. 是否引入新的一致性问题

## 十一、消息队列 / 后台任务

```
> 把文档同步从同步改异步：
> - 用 Cloudflare Queues（项目已配）
> - 同步请求只入队，返回 202
> - worker 消费队列实际处理
> - 失败重试 3 次，再失败入死信
> - 进度可查询
```

把"同步 → 异步"的标准重构交给 AI，省一天工时。

## 十二、Rate limit

```
> 给 /api/v1/sync POST 加限流：
> - 每用户 10 次/分钟
> - 用 redis sliding window
> - 限流时返回 429 + Retry-After 头
> - 不影响 GET 端点
```

## 十三、可观测性

```
> 给这个 endpoint 加完整可观测性：
> - structured logging（用 pino，每条 log 带 request_id）
> - metrics: 请求计数、p50/p95 延迟、错误率
> - 错误时上报 Sentry
> 用项目里已有的 logger 与 telemetry 配置
```

可观测性是上线后最大的差异化。AI 帮你补完往往省半天。

## 十四、安全检查

```
> 安全审计 src/api/users/ 下所有路由：
> 1. 鉴权是否完整
> 2. 越权访问可能
> 3. SQL 注入
> 4. XSS（响应中 user input 是否被转义）
> 5. 敏感字段（password、token）是否会漏到响应
> 6. 速率限制是否合理
```

定期跑一次，比手工 review 全面。

## 十五、Python / Node / Go 通用模式

工作流类似，prompt 里讲清楚栈：

```
> 注意：项目用 Go 1.22 + Echo + sqlc + Postgres。
> 不要用 GORM 或 ent。
> 错误处理用 errors.Wrap。
> 配置看 internal/config/config.go。
```

## 十六、避坑

1. **生产数据库别让 AI 直接连**：永远人工审 migration
2. **secrets 永远不进 prompt**：连 dev 都不要
3. **复杂业务规则 AI 容易遗漏**：关键流程拆细 + 严格验收
4. **性能敏感路径要 profile**：让 AI 帮你写 benchmark
5. **不要"一次性大重构"**：拆成小步，每步 commit + 测试通过

## 十七、相关阅读

- [Claude Code 新手完整教程](/blog/claude-code-getting-started/)
- [Aider 中文配置与最佳实践](/blog/aider-cn-config-guide/)
- [Python 异步并发调用 LLM API](/blog/python-async-llm-client/)
- [Claude Code Subagent 实战](/blog/claude-code-subagent-practice/)
- [Claude Code CI/CD 接入](/blog/claude-code-ci-integration/)

后端长任务在 [YoTradeApi](https://yotradeapi.com/register) 用 Claude Opus 4.7 跑 architect，Sonnet 4.6 跑实施，一把 Key 通用。
