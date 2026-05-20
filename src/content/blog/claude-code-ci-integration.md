---
title: Claude Code 接入 CI/CD：自动 PR 评审与 bug 修复
description: 在 GitHub Actions / GitLab CI 里调用 Claude Code 进行 PR 评审、CI 错误自动修复、代码质量审计的完整方案与示例配置。
keywords:
- claude code ci
- github actions claude
- claude code pr 评审
- ci 自动修复
- claude code 自动化
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/claude-code-ci-integration/
tags:
- Claude Code
- CI/CD
- GitHub Actions
- 自动化
- PR
category: 工程实战
heroImage: ../../assets/blog-placeholder-1.jpg
---

Claude Code 不只是给开发者交互用的——它的 headless 模式在 CI 里可以变身自动评审员、自动修复员。本文给三套实战配置：自动 PR 评审、CI 失败自修、代码质量定期审计。

## 一、基础：CI 里跑 Claude Code

```yaml
name: claude-pr-review
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-node@v4
        with:
          node-version: 22
      - run: npm install -g @anthropic-ai/claude-code
      - env:
          ANTHROPIC_BASE_URL: https://yotradeapi.com
          ANTHROPIC_AUTH_TOKEN: ${{ secrets.YOTRADE_KEY }}
          ANTHROPIC_MODEL: claude-sonnet-4-6
        run: |
          claude --headless --max-turns 10 --task "$(cat <<EOF
          评审本 PR 的改动。给出：
          1. 高风险问题（必改）
          2. 中等问题（建议改）
          3. 学习点（可选）

          输出格式 markdown，简洁、具体引用文件:行号。

          差异：
          $(git diff origin/main..HEAD)
          EOF
          )" > review.md
      - uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const body = fs.readFileSync('review.md', 'utf8');
            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.payload.pull_request.number,
              body: '## 🤖 Claude Review\n\n' + body
            });
```

每个新 PR 都会自动收到 AI 评审。

## 二、CI 失败自动修复

```yaml
name: auto-fix-on-fail
on:
  workflow_run:
    workflows: ["test"]
    types: [completed]

jobs:
  fix:
    if: ${{ github.event.workflow_run.conclusion == 'failure' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.workflow_run.head_branch }}
      - run: npm install -g @anthropic-ai/claude-code
      - run: npm ci
      - env:
          ANTHROPIC_BASE_URL: https://yotradeapi.com
          ANTHROPIC_AUTH_TOKEN: ${{ secrets.YOTRADE_KEY }}
          ANTHROPIC_MODEL: claude-opus-4-7
        run: |
          claude --headless --max-turns 20 --task "$(cat <<EOF
          跑 npm test，根据失败修复。规则：
          - 只改 src/ 下的代码
          - 不改测试本身
          - 不删测试
          - 不引入新依赖
          - 修完跑 npm test 确认通过
          EOF
          )"
      - uses: peter-evans/create-pull-request@v6
        with:
          title: "[auto-fix] CI 失败修复"
          branch: auto-fix/${{ github.run_id }}
          commit-message: "auto-fix from claude code"
```

跑挂的 build 自动开一个修复 PR，等人 review 后合并。

## 三、定期代码质量审计

```yaml
name: weekly-audit
on:
  schedule:
    - cron: "0 0 * * 0"   # 每周日
  workflow_dispatch:

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm install -g @anthropic-ai/claude-code
      - env:
          ANTHROPIC_BASE_URL: https://yotradeapi.com
          ANTHROPIC_AUTH_TOKEN: ${{ secrets.YOTRADE_KEY }}
          ANTHROPIC_MODEL: claude-opus-4-7
        run: |
          claude --headless --max-turns 30 --task "$(cat <<EOF
          做一次代码质量审计：
          1. 找出 src/ 下复杂度 > 15 的函数
          2. 找出无测试覆盖的关键路径
          3. 找出潜在性能问题
          4. 找出 TODO/FIXME 累计超过 7 天的
          输出 audit.md，按优先级排序。
          EOF
          )"
      - run: |
          cat audit.md
      - uses: peter-evans/create-issue-from-file@v5
        with:
          title: "Weekly Audit ${{ github.run_id }}"
          content-filepath: audit.md
          labels: audit, automated
```

## 四、安全考虑

CI 里跑 Claude Code 有几个安全点：

### 1. Key 用最小权限

CI 专用 key 在中转后台只授给"读 + 改文件 + 跑命令"权限，不要给"管理员"权限。

### 2. 限制改动范围

`--task` 里明确"不改 X、不删 Y"。

### 3. 不允许直接 push 到主分支

CI 应该开 PR，不能 push --force 到 main。

### 4. 预算上限

中转后台给 CI Key 设日预算上限（比如 $5）。万一 workflow 出 bug 跑爆账单也有底。

### 5. 不要给 GITHUB_TOKEN 过大权限

`permissions:` 块明确写：

```yaml
permissions:
  contents: write
  pull-requests: write
  issues: write
```

## 五、headless 模式参数

```
claude --headless           # 非交互
       --max-turns 20       # 最多对话轮数
       --task "..."         # 任务描述
       --model claude-opus-4-7
       --approval never     # 完全自动（沙箱内）
       --output result.md   # 输出到文件
```

`--max-turns` 是防止失控的关键。20 轮够 90% 任务，超过通常是任务不清晰。

## 六、与 GitLab CI 的对接

```yaml
# .gitlab-ci.yml
review-pr:
  image: node:22
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  variables:
    ANTHROPIC_BASE_URL: https://yotradeapi.com
    ANTHROPIC_AUTH_TOKEN: $YOTRADE_KEY
    ANTHROPIC_MODEL: claude-sonnet-4-6
  before_script:
    - npm install -g @anthropic-ai/claude-code
  script:
    - git fetch origin $CI_MERGE_REQUEST_TARGET_BRANCH_NAME
    - DIFF=$(git diff origin/$CI_MERGE_REQUEST_TARGET_BRANCH_NAME..HEAD)
    - claude --headless --max-turns 10 --task "评审：\n$DIFF" > review.md
    - cat review.md
```

可以再加一步用 GitLab API post 评审到 MR。

## 七、监控 CI 中 Claude 的健康

每次跑完看：

- 退出码（非 0 = 任务失败）
- token 用量（异常高 = 任务可能没收敛）
- 总耗时（异常长 = 网络或限频问题）

记录到 Prometheus / Datadog，建立基线。

## 八、典型用例

### 用例 1：每日自动 lint 修复

每天凌晨跑一次 `npm run lint --fix` 之后，让 Claude Code 修剩下的：

```bash
claude --headless --task "把 npm run lint 剩余报错修掉，不动业务逻辑"
```

开一个 PR。早上来 review 一下合并。

### 用例 2：自动文档同步

每次合 PR 之后跑：

```bash
claude --headless --task "根据本次改动更新 docs/ 下相关文档"
```

技术文档不再永远过期。

### 用例 3：安全扫描

```bash
claude --headless --task "扫描 src/ 下潜在的 SQL 注入、XSS、Path Traversal 风险，给出修复建议"
```

补充 SAST 工具看不出的语义级风险。

## 九、不该用 CI 自动跑 Claude Code 的情况

- ❌ 涉及生产数据 migration（人审）
- ❌ 涉及钱（支付逻辑、订阅）
- ❌ 改 secrets / 权限配置
- ❌ 大规模重构（一次 100+ 文件）
- ❌ 没有完善测试的项目（保护网不够）

## 十、相关阅读

- [Claude Code 镜像国内配置完整指南](/blog/claude-code-mirror-cn-setup/)
- [Claude Code Subagent 实战](/blog/claude-code-subagent-practice/)
- [Claude Code Hooks 工作流](/blog/claude-code-hooks-workflow/)
- [AI Agent Prompt Engineering 中文实战](/blog/agent-prompt-engineering-cn/)

需要 CI 友好的中转（独立 Key + 预算上限 + 日志可追溯）？[YoTradeApi](https://yotradeapi.com) 后台直接配置。
