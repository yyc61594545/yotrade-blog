---
title: AI 代码评审实战：让 AI 当 PR Reviewer
description: 把 AI 接入 GitHub PR 评审流程的完整方案：触发、prompt 设计、评审维度、避免噪音、与人工 review 的边界。
keywords:
- ai 代码评审
- ai pr review
- claude code review
- github ai review
- 自动 pr 评审
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/ai-code-review-workflow/
tags:
- 代码评审
- CI/CD
- GitHub
- AI 自动化
- 工程实战
category: 工程实战
heroImage: ../../assets/blog-placeholder-4.jpg
---

让 AI 在每个 PR 上自动评审，是 AI 编程工具最容易出收益的应用之一。但写不好评审 prompt，AI 会变成"PR 噪音机器"。本文给完整落地方案。

## 一、为什么 AI 评审有用

| 痛点 | AI 缓解 |
| --- | --- |
| Reviewer 时间不够 | AI 先扫一遍 |
| 同样错误反复出现 | AI 比人更耐烦 |
| 风格不一致 | AI 严格按 rules |
| 周末 / 跨时区 PR 卡住 | AI 立即响应 |
| 大 PR 复杂度 | AI 拆分各 file 分别看 |

但**不是替代人 review**。AI 看的是"模式 + 已知陷阱"，人看的是"业务正确性 + 设计意图"。

## 二、整体架构

```
PR 提交 → GitHub Action → 拉 diff → AI 评审 → 评论回 PR
```

每个 PR 增量评审，不需要装 GitHub App，纯 Action 就行。

## 三、最小 workflow

```yaml
# .github/workflows/ai-review.yml
name: AI Review
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  review:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Get diff
        id: diff
        run: |
          git diff origin/${{ github.base_ref }}...HEAD > /tmp/pr.diff
          echo "size=$(wc -c < /tmp/pr.diff)" >> $GITHUB_OUTPUT
      - name: AI review
        if: steps.diff.outputs.size < 100000   # 跳过过大 PR
        env:
          ANTHROPIC_BASE_URL: https://yotradeapi.com
          ANTHROPIC_AUTH_TOKEN: ${{ secrets.YOTRADE_KEY }}
        run: |
          curl https://yotradeapi.com/v1/messages \
            -H "x-api-key: $ANTHROPIC_AUTH_TOKEN" \
            -H "anthropic-version: 2023-06-01" \
            -H "content-type: application/json" \
            -d "$(jq -n --arg diff "$(cat /tmp/pr.diff)" '{
              model: "claude-sonnet-4-6",
              max_tokens: 4000,
              messages: [{
                role: "user",
                content: "[评审 prompt]\n\n# Diff\n\($diff)"
              }]
            }')" | jq -r '.content[0].text' > /tmp/review.md
      - name: Post review
        if: steps.diff.outputs.size < 100000
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const body = fs.readFileSync('/tmp/review.md', 'utf8');
            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.payload.pull_request.number,
              body: '## 🤖 AI Review\n\n' + body,
            });
```

## 四、评审 prompt 设计

```markdown
你是严谨的 senior 工程师评审 PR。

# 评审维度（按优先级）
1. 正确性：是否引入 bug、是否处理边界条件
2. 安全性：注入风险、密钥泄露、权限越界
3. 性能：明显低效操作（N+1、大量内存、错误异步）
4. 可读性：命名、注释、抽象层次
5. 一致性：与项目现有模式是否对齐

# 输出格式（严格）

## 🔴 Blocking
- 必须修改才能合并
- 引用具体 file:line
- 给出修复建议

## 🟡 Suggestion
- 建议改但不强求
- 同样引用 file:line

## 🟢 Praise
- 1-2 处值得肯定的地方（鼓励作者）

## 总结
1 句话总体评价。

# 规则
- 不要列空类别（没有 blocking 就不写这段）
- 不要重复"这段代码做了..."（diff 已经说明）
- 不要套话（"代码质量很好"）
- 只评审 diff 内的改动
- 关注变更，不要展开未改的文件
```

**关键**：**严格的输出格式 + 不写废话**。否则 AI 会变成"PR 噪音机器"。

## 五、避免噪音

AI review 第一个礼拜很有用，第二个礼拜变成噪音的常见原因：

| 噪音来源 | 修复 |
| --- | --- |
| 重复指出相同 issue | rules 里写 "我已经接受这个模式" |
| 评论已修复的旧 issue | 只评审本次 diff（不是全文件） |
| 鸡毛蒜皮（拼写、tab/space） | prompt 排除"格式问题"（lint 工具做） |
| 长论文式回答 | 强制 "blocking ≤ 5 条" |
| 无关重构建议 | "只评审本次 diff，不建议大改" |

## 六、按文件 / 路径分流

不同路径用不同 prompt：

```yaml
- name: Detect changes
  id: detect
  run: |
    if git diff --name-only origin/main | grep -q "^src/api/"; then
      echo "type=api" >> $GITHUB_OUTPUT
    elif git diff --name-only origin/main | grep -q "^src/components/"; then
      echo "type=frontend" >> $GITHUB_OUTPUT
    fi
- name: Review (api)
  if: steps.detect.outputs.type == 'api'
  run: ... API 专用 prompt
- name: Review (frontend)
  if: steps.detect.outputs.type == 'frontend'
  run: ... 前端专用 prompt
```

每种代码用专用 prompt，**评审质量明显提升**。

## 七、自动 reply / resolve 流程

```
1. AI 在 PR 评论：Blocking #3 SQL 注入
2. 你修复，push
3. AI 自动 re-review，发现已修复
4. AI 评论："Blocking #3 已 resolve"
5. 人审 + 合并
```

实现：

```yaml
on:
  pull_request:
    types: [synchronize]   # 每次 push 重跑
```

## 八、控制成本

PR 大就贵：

| PR 大小 | 评审成本（Sonnet） |
| --- | --- |
| 100 行 | $0.02 |
| 1000 行 | $0.10 |
| 5000 行 | $0.50 |
| 10000+ 行 | $1+ |

控制：

- 跳过超过 N 行的 PR（让人 review）
- 用 cache（每天第一次评审写入，后续重审命中）
- 用 Sonnet 不用 Opus

## 九、敏感文件不让 AI 看

```yaml
- name: Filter sensitive files
  run: |
    git diff --name-only origin/main | grep -v -E "(secrets|\.env|credentials)" > /tmp/files.txt
```

`.env` / secrets / credentials 永远不发给 AI。

## 十、用 Claude Code Headless（替代裸 curl）

```yaml
- run: npm install -g @anthropic-ai/claude-code
- env:
    ANTHROPIC_BASE_URL: https://yotradeapi.com
    ANTHROPIC_AUTH_TOKEN: ${{ secrets.YOTRADE_KEY }}
  run: |
    claude --headless --max-turns 5 --task "评审 git diff origin/main..HEAD" > review.md
```

更智能——Claude Code 可以**主动读相关文件、跑测试、查依赖**，给出更深入的评审。详见 [Claude Code CI/CD 接入](/blog/claude-code-ci-integration/)。

## 十一、与现有工具的对接

| 工具 | 用途 |
| --- | --- |
| CodeRabbit | SaaS AI review |
| Sourcery | Python review |
| Cursor PR | Cursor 内置 |
| Greptile | 大仓库分析 |
| 自建 + 中转 | 完全自主 |

国内 + 数据敏感 + 完全可控：**自建**。其它场景看预算。

## 十二、人 vs AI 评审的分工

| 评审项 | AI | 人 |
| --- | --- | --- |
| 拼写 / 风格 | ✓ | ✗ |
| 类型 / lint | ✓（更适合 linter） | ✗ |
| 明显 bug | ✓ | ✓ |
| 性能（明显） | ✓ | ✓ |
| 安全（已知模式） | ✓ | ✓ |
| 业务正确性 | ✗ | ✓ |
| 设计意图 | ✗ | ✓ |
| API 演进 | ✗ | ✓ |
| 团队规范的"新例外" | ✗ | ✓ |

**AI 看 70% 的常规问题，留 30% 给人**。

## 十三、相关阅读

- [Claude Code CI/CD 接入](/blog/claude-code-ci-integration/)
- [Claude Code Subagent 实战](/blog/claude-code-subagent-practice/)
- [AI 编程的 12 个常见错误与避坑指南](/blog/ai-coding-mistakes-to-avoid/)
- [.cursorrules 最佳实践](/blog/cursor-rules-best-practices/)
- [AI Agent Prompt Engineering 中文实战](/blog/agent-prompt-engineering-cn/)

AI review 配 [YoTradeApi](https://yotradeapi.com) 中转 + 独立 CI key + 日预算上限，最大可控。
