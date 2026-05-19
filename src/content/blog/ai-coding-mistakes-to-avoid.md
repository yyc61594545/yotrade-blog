---
title: AI 编程的 12 个常见错误与避坑指南
description: 真实生产中 AI 编程容易踩的 12 个坑：盲信输出、prompt 模糊、上下文污染、依赖增长、测试缺失、安全疏漏等，附具体修正方法。
keywords:
- ai 编程 错误
- ai 编程 避坑
- cursor 错误
- claude code 踩坑
- ai 编程 最佳实践
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/ai-coding-mistakes-to-avoid/
tags:
- 最佳实践
- 避坑
- AI 编程
- 经验
category: 最佳实践
heroImage: ../../assets/blog-placeholder-5.jpg
---

# AI 编程的 12 个常见错误与避坑指南

用 AI 编程一年下来，看过最多的"事故"都不是模型不行，是工作流不行。本文整理 12 个真实场景下最常见的错，每个给具体修正方法。

## 一、盲信 AI 输出

**症状**：模型给的代码看着合理，直接合并，几周后线上出 bug。

**修正**：

- 编程任务：跑测试验证
- 业务逻辑：自己 review，不要依赖模型的"看起来对"
- 性能优化：profile 验证，别相信"这样更快"
- 数据库操作：先在测试库跑

## 二、Prompt 太模糊

**症状**："写一个用户管理"——模型不知道用什么栈，什么约定，写出和你项目风格完全不同的代码。

**修正**：

- 写好 `.cursorrules` / `CLAUDE.md`（项目知识）
- 每个任务 prompt 包含范围 + 约束 + 验收
- 不确定时让 AI 先问澄清问题

参考 [AI Agent Prompt Engineering 中文实战](/blog/agent-prompt-engineering-cn/)。

## 三、上下文污染

**症状**：一次对话里讨论了 5 个不相关的任务，AI 开始"乱串"——给 A 任务的回答混进 B 任务的思路。

**修正**：

- 每个独立任务起新对话
- 长任务定期 `/clear` 或 compact
- 用 Subagent 隔离子任务

## 四、依赖增长失控

**症状**：让 AI 解决问题，它装了 5 个新依赖。一个月后 `package.json` 多了 30 个新包。

**修正**：

- `.cursorrules` 写明"不引入新依赖除非必要"
- review 时盯紧 `package.json` 改动
- 每月跑一次 depcheck / npm-check 清未用包

## 五、测试缺失

**症状**：AI 改了代码不写测试，下次再改不知道有没有破坏旧功能。

**修正**：

- 项目知识里强制要求"改代码必加测试"
- 用 Aider 的 `auto-test` / Claude Code hook 自动跑测试
- 改完跑覆盖率，新代码必须 ≥ 80%

## 六、安全疏漏

**症状**：

- AI 写的 API 没鉴权
- SQL 拼字符串
- 密码写明文
- secrets 写进代码

**修正**：

- `.cursorrules` 列硬约束（参考 [安全合规](/blog/api-relay-security-compliance/)）
- 提交前 git-secrets 扫描
- 定期跑 SAST / 让 AI 自审

## 七、过度优化

**症状**：AI 给一段简单代码加了 useMemo、useCallback、缓存、批量处理 —— 实际上原代码本来就够快。

**修正**：

- prompt 里加："不要过度优化，只对真实瓶颈下手"
- 优化必须 profile 验证
- 简单代码保持简单

## 八、忽略错误信号

**症状**：AI 给的代码报错，AI 自己 "fix" 一下就让错误消失（用 `// @ts-ignore`、空 try/catch、把测试改对）。

**修正**：

- 看 commit diff，特别注意：`@ts-ignore`、`eslint-disable`、空 catch、测试预期改动
- 错误处理一定要"具体到类型"，不要泛用 catch-all
- Hook 拦截 `@ts-ignore` 等模式

## 九、长任务漂移

**症状**：让 AI 跑长任务，开始时还在重构 X，半小时后已经在改 Y。

**修正**：

- 用 Plan/Act 双模式，Plan 阶段你审一遍
- 长任务拆成 5 个 30 分钟以内的小任务
- 中转后台设单任务预算上限

## 十、不看账单

**症状**：开 Background Agent 跑通宵，第二天账单 $200。

**修正**：

- 每天看一次中转账单
- 设独立 Key + 日预算上限
- 长任务 schedule 前估算 token

参考 [AI 编程代理成本控制实战](/blog/ai-coding-agent-cost-control/)。

## 十一、不更新项目知识

**症状**：`.cursorrules` 半年没动，项目栈早变了，AI 还在按旧规则写。

**修正**：

- 每个 milestone 后 review 一次项目知识文件
- 把"踩过的坑"沉淀进去（pitfalls 段）
- Memory Bank 模式：让 AI 主动更新（Cline 的 Memory Bank）

## 十二、不评估，只感觉

**症状**：换了新模型，"感觉"比之前好。但实际任务通过率反而下降。

**修正**：

- 维护一份固定测试集
- 换模型 / 改 prompt 都跑一遍回归
- A/B 测试线上

参考 [LLM 评估实战](/blog/llm-evaluation-cn-guide/)。

## 一份"项目级"避坑清单

把下面这段写进 `.cursorrules` 或 `CLAUDE.md`：

```markdown
# AI 协作原则

## 必须
- 改代码 → 跑测试
- 加功能 → 加测试
- 改 schema → 写 migration + rollback 计划
- 大改动 → 先列计划

## 严格禁止
- @ts-ignore（除非和我商量）
- 空 try/catch
- 任意 eslint-disable
- 引入新依赖（除非和我商量）
- 跑 rm -rf
- git push --force
- 改 prisma migrations 历史
- 调用 production 数据库

## 风险信号要主动提醒
- 改了 auth / payment / billing
- 改了 .env / secrets
- 改了 build / deploy 配置
- 改了数据库 schema
- 性能优化（提醒需要 profile）
```

## 十四、相关阅读

- [AI Agent Prompt Engineering 中文实战](/blog/agent-prompt-engineering-cn/)
- [AI 编程代理成本控制实战](/blog/ai-coding-agent-cost-control/)
- [Claude Code Hooks 工作流](/blog/claude-code-hooks-workflow/)
- [LLM 评估实战](/blog/llm-evaluation-cn-guide/)
- [AI API 中转的安全与合规边界](/blog/api-relay-security-compliance/)

完整避坑工作流需要稳定中转 + 可设上限的 Key。[YoTradeApi](https://yotradeapi.com/register) 后台直接配独立 Key + 日预算上限。
