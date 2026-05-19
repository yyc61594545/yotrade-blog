---
title: Roo Code 国内配置与 Boomerang 模式实战
description: Roo Code（VSCode 编程代理）的国内中转配置教程，含 Boomerang 子任务、模式切换、API Profile、MCP 与权限管理。
keywords:
- roo code 国内
- roo code 配置
- roo cline
- roo code boomerang
- roo code api
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/roo-code-cn-setup/
tags:
- Roo Code
- VSCode
- Boomerang
- API 中转
- 配置教程
category: 工具配置
heroImage: ../../assets/blog-placeholder-3.jpg
---

# Roo Code 国内配置与 Boomerang 模式实战

Roo Code（前身 Roo Cline）是 Cline 的活跃 fork，加了一些 Cline 没有的特性：Boomerang 子任务、多 API Profile 切换、Mode 系统、内置 MCP 安装器。在国内用 Roo Code 的接入流程跟 Cline 类似，但有几个细节值得单独写。

## 一、安装

VSCode 扩展商店搜 "Roo Code" 安装。注意区分：

- `RooVeterinaryInc.roo-cline`（官方）
- `Roo Code` 由社区 fork 但不官方维护的版本（不推荐）

## 二、添加 API Profile

Roo Code 的「API Profile」比 Cline 更灵活：可以同时存多个 profile，每个 mode 单独绑定。

设置 → API Configuration → 添加：

| 字段 | 填什么 |
| --- | --- |
| Profile Name | `yotrade-sonnet` |
| API Provider | OpenAI Compatible |
| Base URL | `https://yotradeapi.com/v1` |
| API Key | `sk-yo-...` |
| Model | `claude-sonnet-4-6` |

按这个模板再建几个：

- `yotrade-opus` → claude-opus-4-7
- `yotrade-haiku` → claude-haiku-4-5
- `yotrade-gpt5` → gpt-5

## 三、Mode 系统：每个 Mode 用不同模型

Roo Code 内置几个 mode：

| Mode | 用途 | 推荐 Profile |
| --- | --- | --- |
| Code | 写代码 | yotrade-sonnet |
| Architect | 架构规划 | yotrade-opus |
| Ask | 问答 | yotrade-haiku |
| Debug | 调试 | yotrade-opus |
| Orchestrator (Boomerang) | 子任务调度 | yotrade-sonnet |

设置 → Modes → 每个 mode 指定默认 API Profile。

## 四、Boomerang 模式（核心特性）

Boomerang 是 Roo Code 最独特的特性：一个父任务可以 spawn 多个子任务，每个子任务有独立上下文。

工作流：

1. 在 Orchestrator 模式下输入大任务："把项目从 Webpack 4 升级到 Vite 6"
2. Orchestrator 自动拆分：
   - 子任务 1（Architect）：制定迁移计划
   - 子任务 2（Code）：重写 webpack.config
   - 子任务 3（Code）：调整 package.json
   - 子任务 4（Debug）：跑测试修复
3. 每个子任务独立上下文，完成后把结果回传给父任务
4. 父任务汇总，产出最终报告

**这种模式特别省 token**——大任务不会拖一个 200k 上下文跑到底。

## 五、Boomerang 的成本控制

Boomerang 看似省 token，但子任务多了也可能爆账单。建议：

- 子任务 model 默认用 Sonnet 4.6
- Architect 用 Opus 但 system prompt 精简
- 限制最大子任务深度（默认 3 够用）
- 在中转后台为这个 key 设日预算上限

## 六、Auto Approve（自动批准）

Roo Code 的自动批准粒度更细：

```
✓ Read files in workspace
✓ Edit files in workspace
✓ Execute commands (safe)
✗ Execute commands (all)
✓ Use browser
✗ MCP all
✓ Approve some MCPs (按名单)
```

国内长任务的最大风险是中转抖一下导致命令半执行。**不要勾 "Execute commands (all)"**，留个手动审批保兜底。

## 七、MCP 服务器管理

Roo Code 设置 → MCP Servers，可以直接 UI 安装和管理：

```json
{
  "filesystem": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/you/projects"]
  },
  "github": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-github"],
    "env": {
      "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxx"
    }
  }
}
```

**MCP 越多 token 越贵**：每个工具的 schema 都进 system prompt。只装当前任务需要的。

## 八、Memory Bank（项目记忆）

Roo Code 有个 Memory Bank 功能：在项目根放 `.roo/memory/` 目录，文件会在每次对话自动注入上下文。

推荐文件结构：

```
.roo/memory/
├── architecture.md   # 架构说明
├── conventions.md    # 编码规范
├── glossary.md       # 业务术语
└── pitfalls.md       # 常见坑
```

每个文件 < 1k tokens 为好。这部分内容能命中 prompt cache，长期省钱。

## 九、Custom Mode（自定义模式）

可以自己定义 mode：

```yaml
# .roomodes
modes:
  - slug: pr-reviewer
    name: PR Reviewer
    roleDefinition: |
      你是一个严谨的 senior engineer，负责评审 PR。
      重点关注：正确性、性能、安全性、可维护性。
    customInstructions: |
      评审输出格式：
      1. 整体评分（1-10）
      2. 必须修改（blocking）
      3. 建议修改（nice-to-have）
      4. 学习点（可选）
    groups: [read, command]
    apiProfile: yotrade-opus
```

这种 mode 可以 commit 进 repo，团队成员共享。

## 十、与 Cline 的差异

| 维度 | Roo Code | Cline |
| --- | --- | --- |
| Boomerang | ✓ | ✗ |
| 多 API Profile | ✓ | 单一 |
| Mode 系统 | ✓ | Plan/Act |
| Memory Bank | ✓ | ✗ |
| Custom Mode | ✓ | ✗ |
| 社区活跃度 | 高 | 高 |

简单说：**Roo Code 是 Cline 的"增强版"**。需要 Boomerang、需要多模型分工，选 Roo Code；只用单一模型，Cline 也够。

## 十一、相关阅读

- [Cline 国内 API 配置详解](/blog/cline-cn-api-setup/)
- [Cursor API 中转怎么选](/blog/2026-05-15-cursor-api-relay-recommendation-2026/)
- [Claude Sonnet 4.6 与 Opus 4.7 怎么选](/blog/claude-sonnet-4-6-vs-opus-4-7/)
- [AI 编程代理成本控制实战](/blog/ai-coding-agent-cost-control/)

需要支持 Roo Code 多 Profile 的中转？[YoTradeApi](https://yotradeapi.com) 一把 Key 接所有模型，按上面模板配置即可。
