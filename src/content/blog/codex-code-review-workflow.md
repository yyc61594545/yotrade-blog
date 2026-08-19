---
title: 用 Codex 建立可重复的代码审查流程
description: 讲解如何用 Codex CLI 的非交互执行模式，把代码审查从一次性 prompt 变成可复用、可版本化的仓库级流程。
keywords:
  - Codex 代码审查
  - Codex CLI exec 模式
  - 可重复代码审查流程
  - Codex 审查清单
  - AI 代码审查自动化
pubDate: '2026-08-19'
updatedDate: '2026-08-19'
canonical: https://blog.yotradeapi.com/blog/codex-code-review-workflow/
tags:
  - Codex
  - 代码审查
  - CLI 工具
  - 实战经验
category: 实战经验
heroImage: ../../assets/blog-placeholder-5.jpg
---

很多团队用 AI 做代码审查的第一版做法,是在 PR 里临时打一段 prompt:"帮我看看这个改动有没有问题"。这种用法有个通病——**审查质量取决于当天怎么问**,同一个人今天问得细,评审就细;明天偷懒少写两句,评审就松。这篇文章讲的不是"要不要用 AI 评审"([之前的文章](/blog/ai-code-review-workflow/)已经讨论过这个决策),而是**怎么用 Codex CLI 把评审流程固化成可重复、可版本化的仓库资产**,让评审质量不再依赖当天的运气。

## 一、为什么"临时 prompt"型评审不可重复

判断一个评审流程是否可重复,有三个简单标准:

- **同一份 diff,不同时间跑,给出的评审维度应该基本一致**——不能今天查安全问题,明天只查命名规范
- **评审标准能被团队新成员直接复用**,而不是只存在于某个人的聊天记录里
- **评审结果能被结构化处理**(比如自动分类严重程度、自动生成 checklist),而不是一段自然语言散文

临时 prompt 三条都不满足:标准全凭记忆,新人不知道该问什么,输出格式每次还可能不一样。要解决这个问题,核心思路是把"评审该做什么"从对话里搬到仓库文件里,再用 Codex 的非交互模式跑固定流程。

## 二、用 codex exec 把评审变成脚本

Codex CLI 提供非交互的 `exec` 模式,可以把一次评审当作脚本调用,而不是聊天。基本结构:

```bash
#!/bin/bash
# scripts/review-diff.sh
set -e

DIFF=$(git diff origin/main...HEAD)

if [ -z "$DIFF" ]; then
  echo "无变更，跳过审查"
  exit 0
fi

codex exec --full-auto "$(cat <<'EOF'
你是本仓库的代码审查员，请按以下固定维度审查当前 diff：

1. 正确性：是否存在明显逻辑错误、边界条件遗漏
2. 安全性：是否引入注入、权限绕过、密钥硬编码等风险
3. 一致性：是否符合仓库既有的命名与结构约定（参考 AGENTS.md）
4. 测试覆盖：改动涉及的逻辑是否有对应测试，缺失的要点名

对每一条发现，按「严重程度: 高/中/低」「文件:行号」「问题描述」「建议」的格式输出。
不要评论与本次 diff 无关的历史代码。
EOF
)" --diff "$DIFF"
```

这个脚本的关键不在于命令本身,而在于**评审维度写死在脚本里,而不是每次现场想**。谁跑这个脚本、什么时候跑,输出的评审角度都是一致的。

## 三、把评审标准做成仓库文件,而不是脚本里的字符串

上一节的 prompt 直接写死在脚本里,维护起来不方便——改一条标准要改脚本本身,不便于 review 和版本追踪。更好的做法是拆成独立文件:

```
.codex/
  review-checklist.md   # 评审维度与标准，纯 Markdown，便于团队讨论修改
  review-prompt.txt      # 引用 checklist 的固定 prompt 模板
```

`review-checklist.md` 示例:

```markdown
# 代码审查清单

## 正确性
- [ ] 边界条件（空值、空数组、超时）是否处理
- [ ] 并发场景下是否有竞态风险

## 安全性
- [ ] 用户输入是否直接拼接进 SQL / shell 命令
- [ ] 密钥、token 是否硬编码在代码里

## 一致性
- [ ] 是否复用了已有工具函数，而不是重复实现
- [ ] 命名是否符合 AGENTS.md 里约定的风格

## 测试
- [ ] 新增逻辑分支是否有对应用例
- [ ] 修复的 bug 是否补了回归测试
```

脚本里改成读取这份文件:

```bash
CHECKLIST=$(cat .codex/review-checklist.md)
codex exec --full-auto "请严格按以下清单逐项审查 diff，未覆盖的项标注「不适用」并说明原因：\n\n${CHECKLIST}\n\n--- diff ---\n${DIFF}"
```

这样清单本身可以像代码一样被 PR、被 review、被逐条讨论要不要加新维度——评审标准的演进有了版本历史,而不是散落在某次对话里。这份清单如果和仓库根目录的 `AGENTS.md`([项目级配置的写法参考这篇](/blog/codex-cli-project-instructions/))保持一致的风格约定,Codex 在评审时引用的标准也会和它日常写代码时遵循的标准对齐,减少"评审说要这样,但 Codex 自己写代码时又不这样"的自相矛盾。

## 四、接入 CI:让评审在每次 PR 自动跑

固化成脚本之后,接入 CI 就是水到渠成的事:

```yaml
# .github/workflows/codex-review.yml
name: Codex Review
on: pull_request

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Run Codex review
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: bash scripts/review-diff.sh > review-output.md
      - name: Post review as PR comment
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const body = fs.readFileSync('review-output.md', 'utf8');
            await github.rest.issues.createComment({
              ...context.repo,
              issue_number: context.issue.number,
              body: `## Codex 自动审查\n\n${body}`
            });
```

需要注意几点工程细节:

- **`--full-auto` 模式不代表评审可以无限信任**,它只是免去交互确认,输出仍需要按严重程度过滤——建议只把"高"和"中"严重级别的发现自动评论到 PR,"低"级别写入 workflow summary 供需要时查看,避免刷屏式的低价值评论
- **超时和费用要有上限**,大 diff 应该分文件分批审查而不是一次性把整个 diff 塞进单次调用,否则容易命中上下文或时间限制
- **要有明确的"人工才是最终决策者"边界**,Codex 的评审结论是建议不是阻断门禁,这一点和 AI 评审能力边界的讨论是一致的,自动化的价值在于减少重复劳动,不是替代最终判断

## 五、可重复流程带来的额外收益

把评审流程仓库化之后,还能顺带得到两个副产品:

- **新成员上手评审标准的时间大幅缩短**:`.codex/review-checklist.md` 本身就是一份可读的团队规范文档,不需要靠老员工口口相传
- **评审标准的变更可追溯**:哪次 PR 加了"并发竞态"这一条检查,git blame 一下就知道是因为哪次事故补上的,比翻聊天记录靠谱得多

## 六、相关阅读

- [AI 代码评审实战：让 AI 当 PR Reviewer](/blog/ai-code-review-workflow/)
- [AI 替代 PR 评审的实战边界：哪些能替代，哪些不能](/blog/ai-coding-pr-review-replacement/)
- [Codex 项目级 AGENTS.md 编写指南](/blog/codex-cli-project-instructions/)
- [Codex CLI 中国区配置指南](/blog/codex-cli-cn-setup/)

把评审流程做成可版本化的仓库资产,是让 AI 代码审查真正落地而不是"用一阵子就荒废"的关键一步,稳定的 API 调用是这套自动化流程能持续跑在 CI 里的前提,[YoTradeApi](https://yotradeapi.com) 提供高可用的模型中转服务,适合接入这类频繁调用的 CI 场景。
