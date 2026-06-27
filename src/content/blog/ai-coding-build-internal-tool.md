---
title: 用 AI 一天搭一个内部工具：实战全流程
description: 用 Claude Code 和 AI 编程工具在一天内构建内部工具的完整实战流程，含选型、提示词模板、避坑点和上线清单。
keywords:
  - AI 搭建内部工具
  - Claude Code 实战
  - AI 编程一天上线
  - 内部工具快速开发
  - AI 辅助全栈开发
  - 低代码 AI 替代
pubDate: '2026-06-27'
updatedDate: '2026-06-27'
canonical: https://blog.yotradeapi.com/blog/ai-coding-build-internal-tool/
tags:
  - AI编程
  - Claude
  - 实战
  - 内部工具
category: 实战经验
heroImage: ../../assets/blog-placeholder-3.jpg
---

"一天搭一个内部工具"在 AI 编程工具出现之前是夸大其词，现在是字面意思可以实现的事情。本文记录一次真实的内部工具开发全流程：从早上确定需求，到下午上线给团队用，中间用到了哪些 AI 工具、遇到哪些坑、怎么绕过去。

## 一、为什么"内部工具"是 AI 编程最佳切入场景

内部工具有几个特点，恰好让它成为 AI 辅助开发的最优场景：

**需求边界清晰**：内部工具的用户就是自己团队，不需要做市场调研，需求文档可以是一段话。AI 最擅长的就是"把一段描述变成代码"。

**质量标准宽松**：内部工具不需要像 C 端产品一样精致，跑通核心流程、数据准确即可。AI 生成的代码如果有小 bug，团队成员反馈后再修即可。

**迭代速度优先**：内部工具往往是"先用起来再说"，这与 AI 辅助开发"快速出原型"的节奏完全匹配。

**技术栈自由**：不需要考虑与现有客户侧技术栈兼容，可以选 AI 生成质量最好的技术栈（Next.js + SQLite / FastAPI + React 都是不错的选择）。

## 二、案例背景：一个 API 调用监控面板

以一个真实场景为例：团队每个月要汇总各业务线的 AI API 调用量和成本，原本是靠 Excel 手工整理，耗时费力还容易出错。目标是做一个简单的 Web 面板，让各业务线自己填报，自动汇总并生成月度报告。

**需求一句话**：各业务线填写本月 AI API 调用量和成本，汇总展示，支持导出 CSV。

**选定技术栈**：

- 前端：Next.js（App Router）+ Tailwind CSS
- 后端：Next.js API Routes
- 数据库：SQLite（部署简单，内部工具不需要 PG 的复杂性）
- 部署：Vercel（免费额度够内部工具用）

## 三、提示词设计：怎么跟 AI 说才能得到可用代码

跟 AI 描述需求有几个关键原则：

**原则一：给出完整的数据模型**，而不是"一个表单"

```
我需要一个内部工具，数据模型如下：

Business（业务线）:
- id (int, PK)
- name (string, 必填)
- owner_email (string)

MonthlyReport（月报）:
- id (int, PK)
- business_id (int, FK)
- year (int)
- month (int)
- api_calls (int, 调用次数)
- cost_usd (float, 美元成本)
- model_breakdown (JSON, 按模型的细分)
- submitted_at (datetime)
- notes (text, 备注)

约束：同一个 business_id + year + month 只能有一条记录
```

**原则二：说清楚用户旅程，而不是页面列表**

```
用户旅程：
1. 业务线负责人打开页面，选择自己所在的业务线（下拉）
2. 填写当月的调用次数和成本，可以填备注
3. 提交后看到汇总页面（所有业务线本月数据，表格形式）
4. 管理员可以点击"导出 CSV"按钮
```

**原则三：明确边界条件**

```
不需要登录/权限系统（内部工具，信任环境）
不需要邮件通知
不需要历史版本
需要：提交后不能重复提交（同月），但可以修改
```

## 四、一天的实际时间分配

以下是实际开发一天的时间线（估算）：

| 时段 | 工作内容 | AI 参与度 |
|------|----------|-----------|
| 09:00–09:30 | 需求梳理，写提示词文档 | 无（纯思考） |
| 09:30–10:30 | 生成项目骨架，配置数据库 | 高（Claude Code 生成） |
| 10:30–11:30 | 开发数据录入表单 | 高 |
| 11:30–12:00 | 联调调试，修 bug | 中（AI 辅助排查） |
| 13:00–14:00 | 汇总展示页面 | 高 |
| 14:00–14:30 | CSV 导出功能 | 高 |
| 14:30–15:30 | 部署到 Vercel，内部测试 | 低（手动操作） |
| 15:30–16:00 | 团队 QA，修小 bug | 中 |
| 16:00 | 上线 | - |

核心编码时间约 4 小时，其中 AI 生成了约 70–80% 的代码，人工审查、修改、调试占 20–30%。

## 五、高价值提示词模板

记录几个在这个过程中效果最好的提示词模板：

**生成数据库 Schema + CRUD API**：

```
基于以下数据模型，用 Next.js API Routes + better-sqlite3 实现 CRUD：

[粘贴数据模型]

要求：
1. GET /api/reports?year=2026&month=6 → 返回当月所有业务线数据（含业务线名称）
2. POST /api/reports → 插入或更新（根据 business_id+year+month upsert）
3. GET /api/reports/export?year=2026&month=6 → 返回 CSV 格式
4. 错误统一返回 { error: "message" }
5. 不需要认证中间件
```

**生成表单组件**：

```
基于以下 API 接口，用 React + Tailwind CSS 实现一个数据录入表单：

接口：POST /api/reports，body 格式：{ business_id, year, month, api_calls, cost_usd, notes }

要求：
1. 业务线用下拉选择（从 GET /api/businesses 获取）
2. 年月用 select，默认当前月
3. 提交后显示成功提示，3 秒后自动跳转到汇总页
4. 已提交过的月份，加载时自动填充已有数据，标题变为"修改本月数据"
5. 用 Tailwind 做基础样式，不需要额外组件库
```

**排查 bug 的提示词**：

```
以下代码在 SQLite upsert 时报错：[粘贴错误信息]

相关代码：[粘贴代码]

这个错误的原因是什么？给出修复后的代码。
```

## 六、常见踩坑点与解决方式

**坑一：AI 生成的 SQL 不考虑 SQLite 特殊性**

better-sqlite3 的同步 API 与 Prisma 的异步写法不同，AI 有时会混淆。遇到时明确告诉 AI "使用 better-sqlite3 同步 API，不要用 async/await"。

**坑二：日期处理的时区问题**

AI 生成的代码默认用 UTC，而"当前月"按用户本地时区算，会出现月份错位。解决：在前端显式传 year/month 参数，不让后端自动推断。

**坑三：CSV 导出编码**

如果 notes 字段有中文，CSV 直接返回会在 Excel 中乱码。解法是加 BOM 头：

```javascript
const bom = '﻿';
return new Response(bom + csvContent, {
  headers: {
    'Content-Type': 'text/csv; charset=utf-8',
    'Content-Disposition': 'attachment; filename="report.csv"',
  }
});
```

这个问题 AI 通常不会主动提，需要你踩坑后去问它。

**坑四：Vercel 上 SQLite 文件路径**

Vercel 函数的文件系统是只读的（除了 /tmp），SQLite 文件放在项目目录会在生产环境报错。解法：开发阶段用 SQLite，生产换 Vercel Postgres 或 Turso。或者全程用 Turso（SQLite 兼容 API，边缘数据库）。

## 七、哪些环节 AI 还不够好，需要自己来

**部署配置**：Vercel、Cloudflare Pages 的环境变量配置、构建命令调整，AI 能给建议但需要人工操作。

**权限设计决策**：虽然这个案例不需要权限，但如果需要，"谁能看谁的数据"这类业务决策必须人工确认，AI 给的默认设计往往不符合业务实际。

**数据迁移**：如果后期需要修改数据库结构，SQLite 的迁移比较麻烦，AI 能写迁移脚本但需要仔细 review。

**性能问题**：AI 生成的代码通常没有索引优化，内部工具早期数据量小没问题，但如果增长到几万行记录，需要人工加索引。

## 八、复盘与推广建议

用 AI 搭内部工具，改变了什么：

- **单人开发全栈成为常态**：以前后端工程师做前端很慢，现在借助 AI，一个人可以跑通全栈
- **需求到原型的时间从天缩短到小时**：但 AI 处理需求模糊的情况依然力不从心
- **review 代码的重要性上升**：AI 生成的代码功能正确但安全性、健壮性需要人工把关

如果你想在团队推广"用 AI 搭内部工具"，建议从以下场景入手：

1. 替换 Excel 报表（最容易量化价值）
2. 数据展示 dashboard（前端比重高，AI 最擅长）
3. 表单收集 + 审批流（逻辑清晰，边界明确）

涉及到调用 AI API 的内部工具，成本控制参考[AI 编程月度成本实录](/blog/ai-coding-monthly-cost-real/)；AI API 的调用监控设计参考[AI Agent 成本监控](/blog/ai-agent-cost-monitoring/)。

## 相关阅读

- [AI 编程月度成本实录：真实数字](/blog/ai-coding-monthly-cost-real/)
- [AI Agent 成本监控设计](/blog/ai-agent-cost-monitoring/)
- [用 AI 从零到上线 SaaS 全流程](/blog/ai-coding-saas-zero-to-launch/)
- [AI 编程适合后端开发者吗](/blog/ai-coding-for-backend-dev/)
- [Claude Tool Use 最佳实践](/blog/claude-tool-use-best-practices/)

想在内部工具里集成 Claude 或 GPT 能力，[YoTradeApi](https://yotradeapi.com) 提供国内直连的 AI API 中转，省去海外账号和网络配置的麻烦。
