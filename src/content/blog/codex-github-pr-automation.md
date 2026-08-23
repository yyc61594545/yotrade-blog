---
title: Codex 自动创建与验证 GitHub PR
description: 一套可审计的 Codex GitHub PR 自动化流程：从任务分支、最小改动、测试证据和 PR 创建，到 required checks、自动代码审查、失败修复与权限隔离。
keywords:
  - Codex 自动创建 PR
  - Codex GitHub 自动化
  - AI Agent PR 验证
  - GitHub Actions Codex
  - 自动代码审查流程
pubDate: '2026-08-23'
updatedDate: '2026-08-23'
canonical: https://blog.yotradeapi.com/blog/codex-github-pr-automation/
tags:
  - Codex
  - GitHub
  - Pull Request
  - CI 自动化
category: 实战经验
heroImage: ../../assets/blog-placeholder-5.jpg
---

让 Codex “改完代码后自动开 PR”并不难，难的是让 PR 可审查、可复现且不绕过保护规则。Codex 在任务分支实现并本地验证，GitHub 管理身份、PR 和 required checks，合并仍由仓库策略控制。目标不是成功调用命令，而是产生一个带证据、等待正常门禁的变更单元。

## 一、确定自动化边界

把生命周期拆成准备分支、实现、本地验证、创建 PR、等待检查五段。默认授权止于创建或更新 PR，不要顺手合并。

| 阶段 | Codex 可负责 | GitHub 应负责 |
| --- | --- | --- |
| 准备 | 同步 base、创建唯一分支 | 保护默认分支 |
| 实现 | 读规则、改文件、补测试 | 保存远端提交 |
| 验证 | 运行项目指定命令、检查 diff | 运行独立 CI |
| PR | 生成标题、正文并调用 CLI/API | 分配 PR 编号和审查状态 |
| 门禁 | 解释失败、提交修复 | required checks 与审批 |

[OpenAI 官方 Codex GitHub Action 文档](https://learn.chatgpt.com/docs/github-action)说明，该 Action 可在 workflow 中运行 `codex exec`，用于 CI 反馈、质量检查和重复任务；GitHub 集成也支持 PR 代码审查。产品入口会变化，因此要把命令、规则和门禁写进版本化文件。

## 二、用 AGENTS.md 定义“什么叫完成”

先在根 `AGENTS.md` 写明构建、测试和安全约束，子目录可增加更具体规则。至少列出允许修改路径、禁止触碰内容、必跑命令、分支命名和 PR 正文要求。

验收命令要能直接执行，例如 `npm test`、`npm run lint`、`npm run build`，不要只写“确保质量良好”。[Codex GitHub 审查文档](https://learn.chatgpt.com/docs/third-party/github)说明，审查会查找适用的 `AGENTS.md`；可用 `## Code Review Rules` 写入仓库特有的数据边界和兼容约束。

测试无法运行或权限不足时，Agent 必须保留证据，不能把未执行写成“已通过”。

## 三、分支与提交要保证幂等

每个任务用稳定 ID 派生分支，例如 `codex/issue-1842`，并先查同名远端分支与现有 PR。重试时更新原 PR，避免不断创建 `fix-2`、`fix-final`。

提交前只暂存任务文件，并检查 `git diff --check`、`git status --short` 和相对 base 的文件列表。不得重置或混入已有用户修改。更新 base 后必须重跑门禁并记录新 head SHA。

修复追加 commit，避免改写历史；是否 squash 交给合并策略。

## 四、本地验证结果要变成 PR 证据

实现后运行指定测试，再摘要改动、验证命令、结果和风险。PR 正文引用结论，完整日志留在 CI artifact。

```bash
git push -u origin "$TASK_BRANCH"
gh pr create \
  --base main \
  --head "$TASK_BRANCH" \
  --title "$PR_TITLE" \
  --body-file "$PR_BODY_FILE"
gh pr checks "$TASK_BRANCH" --required --watch
```

[GitHub CLI 手册](https://cli.github.com/manual/gh_pr_create)说明，`gh pr create` 可显式指定 base、head、标题和正文；`gh pr checks --required --watch` 可等待 required checks。脚本应传入关键参数，避免依赖交互默认值。

## 五、远端 CI 必须独立重跑验证

本地通过只是第一层证据。GitHub runner 应从 PR 提交重新 checkout，在干净环境执行同一组门禁。[GitHub 受保护分支文档](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)说明，required checks 满足规则后才允许合并。

检查名称要稳定且唯一；不同 workflow 使用相同 job 名可能产生歧义。Agent 判断“已验证”时必须绑定当前 head SHA，旧提交的绿色结果不能证明新推送也通过。

## 六、把 Codex Review 作为额外审查层

Codex 可在本地用 `/review` 审查 base diff，也可在 PR 评论中请求 `@codex review` 或启用自动审查。官方说明中，GitHub 审查会遵循仓库指导；本地 `/review` 报告问题但不修改工作树。

自动审查不能替代测试或领域维护者：CI 判断机器规则，Codex Review 查找 diff 风险，人类判断需求取舍。修复后针对新 head SHA 重跑门禁。

把迁移回滚、权限入口、协议兼容等高价值规则写进 `AGENTS.md`，少写通用风格偏好。完整流程可参考 [Codex Code Review 工作流](/blog/codex-code-review-workflow/)。

## 七、权限设计决定这套自动化是否安全

执行身份通常只需读仓库、推任务分支和创建 PR，无需绕过保护或部署。Actions 应声明最小 `permissions`，并分开只读分析与写操作 job；Codex Action 也应选择满足任务的最窄 sandbox。

外部 PR 要特别谨慎。[GitHub Actions 安全指南](https://docs.github.com/en/actions/reference/security/secure-use)提醒，不要在 `pull_request_target` 或 `workflow_run` 的高权限上下文中执行不受信任代码。PR 正文、评论和文件也不能视为可信指令；模型、推送和评论凭证应分开。

## 八、失败恢复与完成判定

等待检查时区分 `pending`、`fail`、`cancel` 和基础设施错误。失败先读日志并复现；外部服务不可用时保留 PR 与 head SHA，稍后重跑，不能用本地结果替代 required checks。

完成意味着：PR 与 head SHA 正确、无无关改动、本地门禁有记录、当前 head 的 required checks 满足策略、审查意见已处理或留待人工。它只表示“可供合并”，不授权 Agent 自动 merge。

流程可封装为可重跑脚本或 workflow。本地启动时让 `git` 管分支提交、`gh` 管 PR 对象，故障边界更清晰。后台模式可阅读 [Codex 后台自动化实战](/blog/codex-background-automation/)。

## 九、相关阅读

- [Codex Code Review 工作流](/blog/codex-code-review-workflow/)
- [Codex 后台自动化实战](/blog/codex-background-automation/)
- [Claude Code CI/CD 集成指南](/blog/claude-code-ci-integration/)
- [AI 编程代理权限模式对比](/blog/ai-coding-agent-permission-models/)

如果你的 Codex 工作流需要统一调用多种模型并集中管理接入配置，[YoTradeApi](https://yotradeapi.com) 可提供兼容 API，便于把模型接入与 GitHub 分支、PR 和 CI 权限分开治理。
