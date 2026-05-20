---
title: Anthropic Skills 实战：把能力封装成可复用包
description: Anthropic Skills（技能包）的概念、定义方式、与 Subagent/MCP 的差异、Claude Code 中的接入实战。
keywords:
- anthropic skills
- claude skills
- claude 技能包
- agent skills
- claude code skill
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/anthropic-skills-cn-guide/
tags:
- Anthropic
- Skills
- Claude Code
- Agent
- 工程实战
category: 工程实战
heroImage: ../../assets/blog-placeholder-4.jpg
---

Anthropic Skills 是 Agent SDK 引入的新概念：把"做某件事的能力"打包成可复用的 markdown + 文件目录。本文给完整定义、使用、与 Subagent/MCP 的差异。

## 一、Skills 是什么

简单理解：

```
Skill = 一份 SKILL.md（说明什么时候用 + 怎么用）
      + 可选的辅助文件（脚本、模板、示例）
```

加载 Skill 之后，agent 在对应场景**会主动 invoke 这个 Skill**。

## 二、与 Subagent / MCP / Tool 的差异

| 维度 | Skill | Subagent | MCP | Tool |
| --- | --- | --- | --- | --- |
| 形态 | markdown + files | markdown | server | 函数 |
| 触发 | agent 主动判断 | 显式调用 | 模型决定 | 模型决定 |
| 上下文 | 加载到主 agent | 独立 | 远程调用 | 调用 |
| 适合 | "知道何时用" | "完整任务委托" | "外部数据 / 动作" | "原子操作" |

简单决策：

- **可流程化的能力** → Skill
- **完整子任务** → Subagent
- **外部 API / 数据** → MCP
- **原子动作** → Tool

## 三、Skill 文件结构

```
.claude/skills/excel-export/
├── SKILL.md          # 主说明
├── template.xlsx     # 辅助文件
└── helpers/
    ├── convert.py    # 脚本
    └── README.md
```

## 四、SKILL.md 模板

```markdown
---
name: excel-export
description: |
  把数据导出为 Excel 文件。
  适用场景：用户要求 "导出 Excel"、"生成报表"、"下载 xlsx"。
---

# Excel 导出技能

## 你能做什么

- 把 JSON / CSV 数据转 xlsx
- 应用预定义模板（template.xlsx）
- 多 sheet
- 公式 + 格式

## 怎么使用

1. 用户提供数据（任意结构）
2. 调用 helpers/convert.py：

```bash
python .claude/skills/excel-export/helpers/convert.py \
    --input data.json \
    --output result.xlsx \
    --template .claude/skills/excel-export/template.xlsx
```

3. 输出文件路径告诉用户

## 注意事项

- 单文件 < 1M 行
- 列名映射在 helpers/README.md
- 失败时检查 input JSON schema
```

**关键**：`description` 字段决定 agent 何时调用这个 skill。**写得越精准，触发越准**。

## 五、Claude Code 接入

把 skills 放在 `.claude/skills/`，主 agent 启动时自动发现。

在主对话里：

```
> 把这份用户数据导出 Excel
[agent 自动识别到 excel-export skill，按 SKILL.md 流程执行]
```

不需要显式调用，agent 看 description 自己决定。

## 六、共享给团队

skills commit 到项目 repo，团队成员 clone 项目就有。

公司级共享：

```
$HOME/.claude/skills/   # 全局，所有项目可用
   └── company-data-export/
       └── SKILL.md
```

## 七、Skill 之间的协作

一个 skill 可以引用另一个：

```markdown
---
name: weekly-report
description: 生成每周报表
---

# 流程

1. 用 data-fetcher skill 从数据库取数据
2. 用 excel-export skill 导出
3. 邮件发送（用 email skill）
```

agent 看到这个 SKILL.md 会按步骤调用各 skill。

## 八、Skill vs `.cursorrules` / `CLAUDE.md`

| 维度 | Skill | CLAUDE.md |
| --- | --- | --- |
| 触发 | 按 description 选择性 | 永远注入 |
| 粒度 | 一个能力一个 | 项目级 |
| 大小 | 可大（含文件） | 不宜过大 |
| 共享 | 文件夹打包 | 单文件 |

简单说：**通用约定写 CLAUDE.md，特定能力写 Skill**。

## 九、典型 Skill 例子

### 1. data-quality-check

```
description: 数据集质量检查
files:
  - check.py（按 schema 验证）
  - sample-schema.json
```

### 2. github-pr-helper

```
description: 创建 PR 时按规范生成 title / description
files:
  - templates/
    - feat.md
    - fix.md
    - refactor.md
```

### 3. deploy-runner

```
description: 部署到 staging / prod
files:
  - staging.sh
  - prod.sh
```

### 4. db-migration

```
description: Prisma 迁移流程（含 rollback）
files:
  - patterns/
  - safety-checks.md
```

### 5. test-coverage-up

```
description: 把测试覆盖率提到 80%+ 的标准流程
files:
  - templates/
  - mock-helpers/
```

## 十、Skill 设计原则

- **description 精准**：每行都影响 agent 是否触发
- **流程化**：步骤明确，不要"看情况"
- **可调试**：失败时能定位
- **幂等**：重跑不破坏状态
- **依赖最小**：尽量 shell + python 标准库

## 十一、与 MCP 的搭配

很多场景 Skill 调用 MCP：

```
# SKILL.md 里
1. 用 filesystem MCP 读 input.csv
2. 转换
3. 用 github MCP 提 PR
```

Skill 是"流程",MCP 是"动作"。两者互补。

## 十二、走中转的注意

Skill 本身是 markdown + 文件，**不直接走中转**。但 Skill 流程里调用 LLM 时走中转：

```bash
# Skill 脚本里
curl https://yotradeapi.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_AUTH_TOKEN" \
  ...
```

继承主 agent 的环境变量即可。

## 十三、生产部署建议

1. **每个 Skill 独立目录**：方便升级 / 回滚
2. **版本化**：SKILL.md 末尾加 `version: 1.0`
3. **测试**：写测试脚本验证 Skill 行为
4. **review 后 commit**：不要随手加 Skill
5. **审计**：每月 review 哪些 Skill 真被用了，删掉死的

## 十四、相关阅读

- [Claude Agent SDK 国内接入](/blog/claude-agent-sdk-cn/)
- [Claude Code Subagent 实战](/blog/claude-code-subagent-practice/)
- [MCP 服务器实战](/blog/mcp-server-cn-guide/)
- [自定义 MCP Server 开发实战](/blog/mcp-custom-server-development/)
- [Claude Code Hooks 工作流](/blog/claude-code-hooks-workflow/)

Skills + Subagent + MCP 三件套配 [YoTradeApi](https://yotradeapi.com) 中转，能搭出强大的私有 Agent 系统。
