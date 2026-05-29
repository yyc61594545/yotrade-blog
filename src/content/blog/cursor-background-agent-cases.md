---
title: Cursor Background Agent 真实案例：5 个落地场景解析
description: 整理 Cursor Background Agent 在真实项目中的 5 个典型用法：批量重构、依赖升级、测试补全、文档生成和 Bug 排查，每个场景附成本和踩坑记录。
keywords:
  - Cursor Background Agent 案例
  - cursor 后台代理实战
  - cursor 长任务
  - cursor 批量重构
  - AI 代码生成实战
pubDate: '2026-05-29'
updatedDate: '2026-05-29'
canonical: https://blog.yotradeapi.com/blog/cursor-background-agent-cases/
tags:
  - Cursor
  - Background Agent
  - 实战案例
  - AI 编程
category: 实战经验
heroImage: ../../assets/blog-placeholder-2.jpg
---

Cursor Background Agent（后台代理）让 AI 把整个代码库跑一遍不再是奢望——它在云端 VM 里持续执行，你去喝咖啡回来看 PR。配置方法可参考 [Cursor Background Agent 国内配置与使用](/blog/cursor-background-agent-config/)，本文专注**真实项目里到底能干什么**，整理了五个场景，每个场景给结论、流程、成本估算和踩坑备注。

## 一、场景：旧项目 JS → TypeScript 迁移

### 任务背景

一个 2019 年的 Express 后端，约 12 万行 JS，手工迁 TS 太耗时，用 Background Agent 试了一次全量迁移。

### 分派方式

在 Cursor Composer 写一条任务描述：

```
将 src/ 下所有 .js 文件迁移为 TypeScript。
要求：
1. 保留所有原有逻辑，不做功能改动
2. 给 function 参数和返回值加类型注解，不确定的先用 unknown
3. 修复 tsc --noEmit 报出的所有 Type Error
4. 每个文件改完后跑 jest 对应测试确认通过
5. 输出迁移报告 MIGRATION.md
```

Background Agent 接单后在云端 VM 逐文件处理，运行约 90 分钟返回 PR。

### 实际结果

- 879 个文件迁移完成，847 个测试通过
- 32 个文件存在 `any` 滥用，需人工复查
- `tsc --noEmit` 零报错
- MIGRATION.md 列出了每处 `unknown` 和 `@ts-ignore`

### 成本估算

| 项目 | 数量 |
| --- | --- |
| 输入 token（含 Context） | 约 280 万 |
| 输出 token | 约 130 万 |
| 使用模型 | claude-sonnet-4-6 |
| 费用（中转价） | 约 ¥18–22 |

### 踩坑

- Background Agent 有时会对 `require()` 的动态导入"过度推断"类型，建议 prompt 明确 `不要改 require 的调用方式，只加类型注解`
- 如果项目有自定义 eslint 规则，建议在 prompt 里带上规则摘要，否则 Agent 生成的代码可能过不了 lint

---

## 二、场景：批量升级依赖并修复 Breaking Change

### 任务背景

某 React 项目卡在 React 17 + Webpack 4，想升到 React 18 + Webpack 5，Breaking Change 太多没动手。

### 分派方式

```
执行以下升级任务：
1. React 17 → 18：修改 ReactDOM.render 为 createRoot，处理 useEffect 严格模式双调用
2. Webpack 4 → 5：更新 webpack.config.js，迁移废弃的 loader 配置
3. 升级完跑 npm test，确保全绿
4. 输出 UPGRADE_NOTES.md 记录每处改动理由
```

### 实际结果

- React 升级部分：95% 自动完成，剩 3 处 class component 的 `UNSAFE_componentWillMount` 需人工决策
- Webpack 升级部分：自动识别了 `file-loader`→`asset/resource` 的替换，但有一个自定义插件兼容性问题 Agent 无法判断，留了注释 `# TODO: verify plugin compat`
- 全程约 45 分钟

### 成本估算

约 ¥8–12（中等规模项目，约 150 万 token）

### 踩坑

- 依赖升级前建议先让 Agent 做一次"dry-run 分析"，列出所有需要修改的文件和理由，人工确认范围再执行，防止它改了你不想动的部分
- 私有 npm registry 的包 Agent 无法访问，需在任务里明确标出哪些包不要动

---

## 三、场景：为遗留代码补全单元测试

### 任务背景

业务高速增长期遗留了大批无测试覆盖的核心模块，覆盖率不到 30%，想在不改功能的前提下把覆盖率提到 80%+。

### 分派方式

```
为 src/services/ 下所有文件生成 Jest 单元测试。
要求：
1. 仅创建 __tests__/ 下的测试文件，不修改源代码
2. 覆盖正常路径 + 至少 2 个异常路径（如空入参、外部服务报错）
3. 使用 jest.mock 隔离数据库和外部 HTTP 调用
4. 跑 jest --coverage，目标覆盖率 ≥ 80%
```

### 实际结果

| 指标 | 数值 |
| --- | --- |
| 测试文件生成数 | 47 |
| 初次跑通率 | 68%（32/47） |
| 人工修复后跑通率 | 94%（44/47） |
| 覆盖率（lines） | 83% |
| 耗时 | 约 60 分钟 |

3 个仍失败的文件依赖了运行时注入的全局变量，测试写法需要改架构才能完全隔离，这部分 Agent 主动留了 `TODO` 注释说明原因。

### 踩坑

- 如果 services 之间有循环依赖，Agent 生成的 mock 容易出现"mock 了 A 却忘了 B 也引了 A"的问题，建议 prompt 加上 `遇到循环依赖先在测试文件注释里说明，不要强行 mock`
- 测试文件名风格（`xxx.test.ts` vs `xxx.spec.ts`）建议在 prompt 里统一指定

---

## 四、场景：自动生成 API 文档

### 任务背景

Express + Fastify 混用的后端，约 60 个 REST 端点，没有 Swagger 文档，新人上手全靠问。

### 分派方式

```
扫描 src/routes/ 下所有路由文件，生成 OpenAPI 3.0 规范的 docs/openapi.yaml。
要求：
1. 从代码注释和变量名推断参数类型和描述
2. 为每个端点生成请求体 schema 和响应 schema（不确定的用 {}）
3. 添加认证说明（Bearer token）
4. 最终文件能通过 swagger-cli validate 校验
```

### 实际结果

- 60 个端点全部生成
- `swagger-cli validate` 初次通过率 80%，Agent 自行修复后 100% 通过
- 推断精度：参数名和类型约 85% 准确，描述文字约 60% 准确（剩下需人工补充业务含义）

### 踩坑

- `description` 字段 Agent 倾向于写"Gets the list of XXX"这种机械描述，建议二次 pass 时人工加业务语义
- 如果路由里有动态注册（`routes.forEach(...)`），Agent 无法静态分析，建议在 prompt 里列出这些端点的手写说明

---

## 五、场景：线上 Bug 根因排查 + 修复建议

### 任务背景

生产告警：某接口 P99 延迟在高并发下突然到 8s，日志里有大量 `pool timeout`，DBA 说数据库没问题。

### 分派方式

```
分析 src/services/order.service.ts 及其调用链，找出 pool timeout 的根因。
背景：
- 使用 pg-pool，maxConnections = 10
- 高峰期 QPS 约 200
- 日志片段见 logs/2026-05-20-error.log
要求：
1. 列出可能的根因，按可能性排序
2. 给出每个根因对应的最小修复方案
3. 如果能直接修，就改代码并说明改了哪里、为什么
```

### 实际结果

Agent 返回了 3 个根因假设：

1. **连接未释放**（最高可能性）：发现 `order.service.ts:L234` 在某个 try-catch 分支里 `conn.release()` 被跳过了，直接修复
2. **N+1 查询**（中等可能性）：循环内调用 `getUserById`，建议改为批量查询，给出了重构代码
3. **事务超时未设置**（低可能性）：建议加 `statement_timeout`

修复 1 上线后告警消除，命中了根因。

### 踩坑

- 提供实际日志片段非常关键，Agent 有了错误上下文后分析精度明显提升
- 对于"改代码"的请求，建议在 prompt 里明确"改完请先不要 commit，给我 diff 看看"，防止 Agent 改了过多无关代码

---

## 六、综合评估：哪些任务适合 Background Agent

| 任务类型 | 适合度 | 说明 |
| --- | --- | --- |
| 全量迁移（JS→TS、框架升级） | ★★★★☆ | 规模越大价值越高 |
| 批量测试生成 | ★★★★☆ | 节省大量重复工作 |
| API 文档生成 | ★★★☆☆ | 结构准，语义需人工补 |
| Bug 排查 + 修复建议 | ★★★★★ | 有日志上下文时极强 |
| 功能开发（新需求） | ★★☆☆☆ | 需求模糊时结果偏差大 |
| 需要产品决策的改动 | ★☆☆☆☆ | Agent 无法替代业务判断 |

核心规律：**任务越明确、范围越可枚举、验收标准越客观，Background Agent 的完成质量越高**。反之，越模糊越容易"跑偏"。

---

## 七、成本控制建议

Background Agent 长任务的 token 消耗比日常对话高一个量级，控制成本的几个思路：

1. **选对模型**：90% 的迁移/测试类任务用 Sonnet 而非 Opus，质量够用，成本低 4–5 倍
2. **分批派单**：大任务（>5万行）拆成模块分批跑，单次失败损失小
3. **用 API 中转**：通过 [YoTradeApi](https://yotradeapi.com) 等中转接入，相比官方定价节省 40–60%
4. **设 context 边界**：prompt 里明确告知 Agent "只读 src/services/ 下的文件"，避免 Agent 自行扩展 context 消耗 token

关于成本计算的详细方法，可参考 [LLM 成本优化实战 Checklist](/blog/llm-cost-optimization-checklist/)。

---

## 八、相关阅读

- [Cursor Background Agent 国内配置与使用](/blog/cursor-background-agent-config/)
- [Cursor Rules 最佳实践](/blog/cursor-rules-best-practices/)
- [AI 编程代理成本控制](/blog/ai-coding-agent-cost-control/)
- [Claude Code 真实任务实录](/blog/claude-code-real-world-tasks/)
- [LLM 成本优化实战 Checklist](/blog/llm-cost-optimization-checklist/)

如果你在使用 Background Agent 过程中遇到 API 连通性问题，[YoTradeApi](https://yotradeapi.com) 提供全模型覆盖的稳定中转，按量计费无月费门槛。
