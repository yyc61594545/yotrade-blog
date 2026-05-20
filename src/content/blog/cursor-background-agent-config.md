---
title: Cursor Background Agent 国内配置与使用
description: Cursor Background Agent（云端代理）的国内配置方法，含 base_url、模型选型、长任务可观测性与成本控制实战。
keywords:
- cursor background agent
- cursor 后台代理
- cursor 国内
- cursor composer
- cursor api 配置
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/cursor-background-agent-config/
tags:
- Cursor
- Background Agent
- 长任务
- API 中转
- 成本控制
category: 工具配置
heroImage: ../../assets/blog-placeholder-5.jpg
---

Cursor 2025 推出的 Background Agent 把"AI 写代码"从本地编辑器搬到了云端：你在 IDE 派单，Background Agent 在云端虚拟机里跑长任务，结果回流到 PR 或本地。这套架构国内能用的前提是模型 API 能接通。本文给完整流程。

## 一、Background Agent 是什么

| 特性 | 本地 Composer | Background Agent |
| --- | --- | --- |
| 运行位置 | 你的机器 | 云端 VM |
| 持续时间 | 几分钟 | 几小时 |
| 文件操作 | 直接改本地 | 改云端分支 |
| 网络 | 本地网络 | 云端独立 |
| 适合任务 | 即时编辑 | 长重构、批量改 |

## 二、国内接入难点

国内用 Background Agent 主要堵在两点：

1. **本地编辑器要登录 Cursor 账号**：账号登录走 Cursor 官方，不是用户自己的中转。
2. **Background Agent 调模型 API**：可以走自定义中转，但要正确配置。

第 1 步如果网络层稳定一般不是问题；第 2 步是本文重点。

## 三、配置 Background Agent 用自定义中转

打开 Cursor → Cursor Settings → Models → Custom Model Endpoint，配置一个支持 OpenAI 兼容协议的中转：

```
Endpoint: https://yotradeapi.com/v1
API Key: sk-yo-...
Model: claude-sonnet-4-6
```

然后在 Models 列表里**给 Background Agent 选这个 Custom Model**。

**关键勾选**：

- ✓ Enable Custom Model Endpoint
- ✓ Use this for Background Agent
- ✗ Allow tool fallback to default models（避免 Cursor 偷偷走官方 endpoint）

## 四、模型选型建议

Background Agent 一次任务能跑几小时，对成本敏感。推荐组合：

| 任务复杂度 | 推荐模型 |
| --- | --- |
| 简单重构（同一目录改几个文件） | `claude-sonnet-4-6` |
| 跨目录大型重构 | `claude-opus-4-7` |
| 框架迁移、SDK 升级 | `claude-opus-4-7` |
| 加测试、补类型 | `claude-sonnet-4-6` |
| 文档生成 | `claude-haiku-4-5` |

**不要默认 Opus**：单次长任务 Opus 能烧几十美金。开任务前估算上下文规模，3 个文件以下、单次预期 < 50k tokens 用 Sonnet 就够。

## 五、长任务的可观测性

Background Agent 跑在云端，本地看不到中间状态。监控办法：

1. **中转后台用量**：每分钟看一次请求数和 token 消耗，发现异常立刻停任务。
2. **设置上限**：在中转后台给这个 key 设日预算 / 单任务预算上限。
3. **Cursor 内置进度**：右上角铃铛会推送 agent 状态变更。
4. **PR diff 检查**：任务完成后**一定要看 diff**，长任务可能跑偏。

## 六、Prompt 模板

Background Agent 任务质量很大程度取决于 prompt 写法。推荐结构：

```markdown
# 任务
[一句话目标]

# 范围
- 改：src/api/*, src/utils/*
- 不改：tests/*, docs/*

# 约束
- 保持现有测试通过
- 不引入新依赖
- 函数命名遵循 camelCase

# 验收标准
1. npm test 全绿
2. 编译无 type error
3. 改动文件 < 8 个

# 上下文
[关键文件路径或片段]
```

明确"不改什么"比"改什么"更重要。Agent 一旦发散到无关文件，回滚成本很高。

## 七、cost ceiling：硬上限保护

在 `.cursor/rules` 加一条：

```
# cost-ceiling.md
所有长任务必须在开始时估算 token 消耗。
如果预估单次 > 200k input tokens，先停下确认。
如果累计 > 500k input tokens，必须暂停汇报。
```

配合中转后台的日预算上限，能避免半夜跑爆账单的情况。

## 八、典型踩坑

### 1. Custom Model 被覆盖

Cursor 偶尔会"忘记"你的 Custom Model 配置，回退到官方。每次开任务前确认右下角显示的是你配的模型名。

### 2. 工具调用走默认 endpoint

`web_search`、`run_terminal_cmd` 等内置工具默认走 Cursor 自有服务，不走你的中转。这部分功能在国内可能不可用，可以在 prompt 里要求 agent **不使用** `web_search`。

### 3. Snapshot 上下文太大

Background Agent 首次进入项目会 snapshot 整个仓库，几个 GB 的 monorepo 会非常慢。建议在 `.cursorignore` 排除 `node_modules`、`dist`、`build` 等目录。

### 4. 长任务中途模型限频

Background Agent 默认会自适应重试，但持续 429 会让任务卡住。在中转后台把这个 key 的 RPM/TPM 上限调高。

## 九、长任务实战例子

任务：把项目从 Webpack 4 升级到 Vite 6。

```markdown
# 任务
把项目构建工具从 Webpack 4 迁移到 Vite 6，保持所有功能不变。

# 范围
- webpack.config.js → vite.config.ts
- 所有 entry 文件
- 所有自定义 loader 替换为 Vite 等价物
- package.json scripts 调整
- README 更新构建命令

# 约束
- 保持 dev / build / preview 三个命令
- 保持 alias 配置（@/ → src/）
- 保持环境变量前缀 VITE_*
- 不动业务代码

# 验收
- npm run build 成功
- npm run dev 启动后访问首页能渲染
- 所有现有路由可访问

# 上下文
- 当前 webpack.config.js
- package.json
- 三个最复杂的 loader 配置
```

实测 Sonnet 4.6 在中型 React 项目上一次完成度 75%，Opus 4.7 一次完成度 90%+。差价值得。

## 十、相关阅读

- [Cursor API 中转怎么选](/blog/2026-05-15-cursor-api-relay-recommendation-2026/)
- [Claude Sonnet 4.6 与 Opus 4.7 怎么选](/blog/claude-sonnet-4-6-vs-opus-4-7/)
- [prompt caching 在国内中转下省成本指南](/blog/prompt-caching-cost-optimization/)
- [AI 编程代理成本控制实战](/blog/ai-coding-agent-cost-control/)

需要给 Background Agent 配置一个稳定的 base_url？在 [YoTradeApi 注册](https://yotradeapi.com) 创建独立 API Key，单独设日预算上限，按上面配置接入。
