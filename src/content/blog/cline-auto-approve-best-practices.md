---
title: Cline Auto-Approve 设置最佳实践
description: Cline 自动批准（Auto-Approve）的安全配置：哪些动作可以自动批准、风险边界、长任务可用性、与 Plan/Act 模式的搭配。
keywords:
- cline auto approve
- cline 自动批准
- cline 安全
- cline 长任务
- cline 配置
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/cline-auto-approve-best-practices/
tags:
- Cline
- 安全
- 自动化
- 配置
- 最佳实践
category: 工具配置
heroImage: ../../assets/blog-placeholder-1.jpg
---

# Cline Auto-Approve 设置最佳实践

Cline 的 Auto-Approve 是"提效杠杆 + 风险来源"双刃。配错了要么烦死要么出事。本文给一份按场景的安全推荐。

## 一、Auto-Approve 选项一览

设置 → Auto Approve：

| 选项 | 含义 |
| --- | --- |
| Read files | 读文件 |
| Edit files | 改文件 |
| Execute safe commands | 跑"安全"命令（白名单） |
| Execute all commands | 跑任意命令 |
| Use browser | 控制浏览器 |
| Use MCPs | 调 MCP 工具 |
| Approve some MCPs | 选择性批准 MCP |

## 二、按场景推荐

### 场景 A：第一次用 / 学习

```
✓ Read files
✗ Edit files
✗ Execute safe commands
✗ Execute all commands
✗ Use browser
✗ Use MCPs
```

**全部手动**。看清楚每一步在干什么。第一周这样跑，建立信任。

### 场景 B：日常开发（推荐起点）

```
✓ Read files
✓ Edit files
✓ Execute safe commands
✗ Execute all commands
✗ Use browser
✓ Approve some MCPs（白名单）
```

读 / 改 / 跑测试自动，**危险命令手动**。

### 场景 C：长任务自治

```
✓ Read files
✓ Edit files
✓ Execute safe commands
✓ Execute all commands  ← 唯一开 all 的场景
✗ Use browser
✓ Approve some MCPs
```

**前提**：

- 在 git repo 里（出错能回滚）
- 跑的不是 production 环境
- 中转 key 有日预算上限
- 给 .clinerules 写严格禁止条款

### 场景 D：生产 / 敏感数据

```
✓ Read files
✗ 其它全部手动
```

**接触生产数据时，宁慢勿险**。

## 三、Execute safe commands 白名单

Cline 把"safe"命令定义为：

- 不修改文件系统（除了项目目录）
- 不联网（除了已知的 npm / pip 等）
- 不调 sudo
- 不动 dotfiles / system files

但**"safe" 的定义因人而异**。可以自己改：

```json
// settings
{
  "cline.commandWhitelist": [
    "npm test",
    "npm run lint",
    "git status",
    "git diff",
    "pnpm test",
    "pnpm run lint",
    "ls",
    "cat"
  ]
}
```

明确白名单比依赖 Cline 自己判断"safe"更稳。

## 四、危险命令必须手动

无论什么场景，**这些永远手动**：

```
rm -rf
git push --force
git push origin --delete
git reset --hard
sudo *
curl ... | bash
brew install
npm install -g
pip install
docker run ... --privileged
kubectl apply
psql -c "DROP TABLE"
```

可以在 `.clinerules` 写：

```markdown
## 严格禁止自动批准

- 任何 rm 命令
- 任何 force push
- 任何 sudo
- 任何 docker / kubectl
- 任何 curl ... | bash
- 任何包安装（npm/pip/brew）
- 任何 reset --hard
```

Cline 看到这些会暂停问你。

## 五、长任务策略

跑 30 分钟以上的长任务：

1. **先 Plan**：让 Cline 列计划，**你审过再 Act**
2. **Act 时全开**：Edit / Execute all 自动批准
3. **定期看进度**：每 10 分钟瞄一眼
4. **网络抖动准备**：长任务可能因中转抖一下中断，**重启会话 + 让它从上次记录的 progress 继续**

详见 [Cline 国内 API 配置](/blog/cline-cn-api-setup/)。

## 六、Auto-Approve 与 Plan/Act 的关系

| Plan | Act |
| --- | --- |
| 只读 + 思考 | 改 + 跑 |
| 完全不需要 Auto-Approve（自动只读） | 看你设置 |

**好的工作流**：

1. Plan 模式输入大任务（自动只读）
2. 看计划 + 改
3. 切 Act 模式（开 Edit + Execute Safe 自动）
4. 跑

## 七、MCP Auto-Approve

每个 MCP 单独选：

| MCP | 推荐自动 |
| --- | --- |
| filesystem（读） | ✓ |
| filesystem（写） | 看路径 |
| github（read） | ✓ |
| github（write PR/comment） | ✗ |
| postgres（select） | ✓ |
| postgres（write） | ✗ |
| slack（send） | ✗ |
| memory | ✓ |

**写操作普遍手动**，读操作可以自动。

## 八、Max Requests Per Task

设置里 "Max Requests Per Task" 决定单任务最多调用次数：

| 任务类型 | 推荐 |
| --- | --- |
| 简单查询 | 10 |
| 中等编程 | 30 |
| 长任务 | 50 |
| 大重构 | 100 |

防止"无限循环"烧 token。中转 key 设日预算上限二次保险。

## 九、网络 / 流式问题的恢复

Cline 长任务最容易遇到中转抖断流：

1. **Cline 显示 "stream interrupted"**：不要 retry 全部，**只让 Cline 重试最后一步**
2. **本地保留 progress**：在 .clinerules 里要求 "完成每步后写进度到 progress.md"
3. **重连失败 → 重启会话**：从 progress.md 继续

## 十、生产数据安全

涉及生产数据的项目：

- **不连 production DB**：用 read-only replica
- **secrets 用 .env，git ignore**：Cline 看不到
- **测试用伪数据**：production 数据脱敏后给 Cline
- **API key 单独**：给 Cline 用的 key 权限最小化

## 十一、审计

定期看 Cline 的 conversation history：

- 哪些动作被自动批准
- 哪些命令跑过
- 哪些文件被改

发现"自动批准了不该自动批准的"，调白名单。

## 十二、Anti-pattern

- ❌ "全部自动批准" + 在 production 跑（找死）
- ❌ 长任务半夜跑（不在场看不到出问题）
- ❌ 单 key 给所有人共享（出事查不到）
- ❌ 没设预算上限（账单失控）
- ❌ 没 git 保护（无法回滚）

## 十三、相关阅读

- [Cline 国内 API 配置详解](/blog/cline-cn-api-setup/)
- [Cline Rules 与 Memory Bank](/blog/cline-rules-and-memory-bank/)
- [Roo Code 国内配置](/blog/roo-code-cn-setup/)
- [AI 编程的 12 个常见错误与避坑指南](/blog/ai-coding-mistakes-to-avoid/)
- [AI API 中转的安全与合规边界](/blog/api-relay-security-compliance/)

Auto-Approve + [YoTradeApi](https://yotradeapi.com/register) 中转 + 独立 Key + 日预算上限 = 风险可控的长任务自治。
