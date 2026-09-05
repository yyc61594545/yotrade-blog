---
title: Cline 在 VS Code 的配置：从安装到工作区级设置
description: Cline 在 VS Code 里的完整配置指南：settings.json 关键项、快捷键、Checkpoints、终端与浏览器工具、多根工作区与扩展冲突处理。
keywords:
  - cline vscode 配置
  - cline settings.json
  - cline 快捷键
  - cline checkpoints
  - cline 多根工作区
pubDate: '2026-09-05'
updatedDate: '2026-09-05'
canonical: https://blog.yotradeapi.com/blog/cline-vscode-config-guide/
tags:
  - Cline
  - VSCode
  - 配置教程
  - 工作区设置
category: 工具配置
---

网上大部分 Cline 教程一上来就讲怎么接 API——本文不重复那部分（详见[《Cline 国内 API 配置详解》](/blog/cline-cn-api-setup/)）。这里讲的是更容易被忽略的**VSCode 层面**的配置：`settings.json` 里能调的项、快捷键、Checkpoints、终端与浏览器工具怎么接管、多根工作区下 Cline 的行为，以及和其他扩展打架时怎么办。这些设置对的话，日常用起来会顺很多。

## 一、安装与版本确认

VSCode 扩展商店搜索 "Cline"，发布者是 `saoudrizwan`，扩展 ID 为 `saoudrizwan.claude-dev`（历史遗留名，插件本体已经叫 Cline）。命令行安装：

```bash
code --install-extension saoudrizwan.claude-dev
```

装好后确认版本号，Cline 更新频率很高，很多配置项（比如 Checkpoints、Focus Chain）是近几个版本才加的，版本太旧会发现设置界面里根本没有对应选项：

```bash
code --list-extensions --show-versions | grep claude-dev
```

如果版本明显落后，扩展面板手动点 "Update"，或者干脆卸载重装一次。

## 二、settings.json 里能配的项

Cline 的大部分设置都能在 UI 里点，但写进 `settings.json` 更适合团队统一配置或者用脚本批量下发。常用项：

```json
{
  "cline.enableCheckpoints": true,
  "cline.mcp.mode": "full",
  "cline.terminalOutputLineLimit": 500,
  "cline.terminalReuseEnabled": true,
  "cline.preferredLanguage": "Chinese (Simplified)",
  "cline.defaultTerminalProfile": "default",
  "cline.autoApprovalMaxRequests": 20
}
```

| 配置项 | 作用 | 建议值 |
| --- | --- | --- |
| `cline.enableCheckpoints` | 是否在每次文件改动前打快照 | `true`（除非磁盘吃紧） |
| `cline.mcp.mode` | MCP 功能开关：`full` / `server-use-only` / `off` | 不用 MCP 就设 `off`，省一截 system prompt |
| `cline.terminalOutputLineLimit` | 终端输出回传给模型的最大行数 | 500，太大会浪费 token |
| `cline.terminalReuseEnabled` | 是否复用已有终端而非每次新开 | `true`，减少终端数量堆积 |
| `cline.preferredLanguage` | Cline 回复用的语言 | 按团队习惯设中文或英文 |
| `cline.autoApprovalMaxRequests` | 自动批准模式下单任务最大请求数 | 20，避免死循环烧 token |

这些键名可能随版本变化，改之前用命令面板 `Preferences: Open Settings (UI)` 搜 "cline" 核对一遍当前版本实际暴露的字段，不要盲抄。

## 三、工作区设置 vs 用户设置

VSCode 的设置分两层：用户级（全局生效）和工作区级（只对当前项目生效，写在 `.vscode/settings.json`）。团队协作场景建议把跟"项目规范"相关的配置放工作区级，跟"个人偏好"相关的放用户级：

```
用户级（~/Library/Application Support/Code/User/settings.json）：
- cline.preferredLanguage
- cline.terminalOutputLineLimit

工作区级（.vscode/settings.json，可提交进仓库）：
- cline.enableCheckpoints
- cline.mcp.mode
- cline.autoApprovalMaxRequests
```

工作区级配置提交进 Git 仓库后，团队所有人打开项目都会自动继承同一套 Cline 行为，不用每个人手动点一遍设置界面。注意 API Key 类的敏感字段**永远不要**放进工作区 `settings.json`（会被提交进仓库），那些应该走 VSCode 的 Secret Storage 或留在用户级。

## 四、快捷键与命令面板

Cline 默认不占用很多快捷键，但常用命令值得手动绑定，尤其是"打开 Cline 侧栏"和"新建任务"这两个：

打开命令面板（`Cmd+Shift+P` / `Ctrl+Shift+P`）搜索 "Cline"，能看到：

- `Cline: Open In New Tab` — 在新标签页打开（而非侧栏），大屏幕上更舒服
- `Cline: New Task` — 开一个新任务，清空当前上下文
- `Cline: Add to Cline` — 把选中代码片段直接发给 Cline（配合右键菜单也能触发）
- `Cline: History` — 查看历史任务列表

在 `keybindings.json` 里给高频命令绑快捷键，比如把"新建任务"绑到 `Cmd+Shift+L`：

```json
[
  {
    "key": "cmd+shift+l",
    "command": "cline.plusButtonClicked"
  }
]
```

命令的具体 ID 可能因版本而异，绑定前用 `Preferences: Open Keyboard Shortcuts (JSON)`，在图形化界面里先找到目标命令再复制它的真实 ID，不要凭记忆手写。

## 五、Checkpoints：改坏了怎么退回去

Checkpoints 是 Cline 在每次 Act 模式执行文件改动前自动打的快照，出问题时能一键回退，不用手动 `git reset`。UI 上在每条消息右侧会有一个"恢复到这里"的按钮。

需要注意的几点：

1. Checkpoints 依赖项目是 Git 仓库（或 Cline 会在后台自建一个隐藏的 shadow git）。如果项目本身不用 Git，Cline 会在 `.git` 之外维护一份独立快照仓库，占用额外磁盘空间。
2. 大型项目（数万文件）打 Checkpoint 会比较慢，可以在设置里关掉 `cline.enableCheckpoints`，改成手动 `git commit` 兜底。
3. Checkpoints 和真正的 Git 历史是分开的两套东西，回退 Checkpoint **不会**产生 Git commit，团队协作场景最终仍然要靠正常的 commit 流程留痕。

## 六、终端集成：让 Cline 跑对 Shell

Cline 执行命令时用的是 VSCode 内置终端，行为跟你手动开的终端逻辑一致，但有几个坑：

- **Shell 类型**跟着 VSCode 的 `terminal.integrated.defaultProfile.osx`（或对应平台）走，如果你在用 `zsh` 但配置文件写的是 `bash` 语法，Cline 跑出来的命令可能报错，先确认两者一致。
- **`terminalReuseEnabled`** 开着时 Cline 会复用同一个终端跑多条命令，好处是环境变量、`cd` 状态能延续；坏处是如果某条命令卡住（比如误跑了一个交互式程序），后续命令会一起卡住。长任务建议留意终端面板，发现卡住及时手动中断。
- **输出截断**：`terminalOutputLineLimit` 限制了回传给模型的行数，跑测试套件这类输出很长的命令时，模型可能看不到完整报错。调大这个值前先权衡 token 成本。

## 七、浏览器工具怎么接管

Cline 的浏览器工具（Browser Use）能让模型截图、点击、填表单，调试前端页面很有用，但默认没开：

设置 → Browser Settings：

```
✓ Enable browser tool
Viewport size: 900x600
Remote browser connection: (留空，用内置 Chromium)
```

如果本机已经装了 Chrome 且想用它而不是 Cline 自带的 Chromium（比如需要复用已登录的 Cookie），可以填 `Remote browser connection` 指向一个开了远程调试端口的 Chrome 实例：

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-cline-debug
```

注意用独立的 `--user-data-dir`，避免 Cline 操作把你日常浏览的标签页搞乱。

## 八、多根工作区（Multi-root Workspace）下的行为

如果你的 `.code-workspace` 挂了多个文件夹，Cline 的上下文默认以**第一个根目录**为基准。跨文件夹引用文件时用完整相对路径更保险：

```
@/frontend/src/App.tsx
@/backend/src/routes/api.ts
```

`.clinerules` 只在放置它的那个根目录里生效，不会自动应用到工作区里的其他文件夹。多仓库场景下，每个子项目根目录都需要单独放一份 `.clinerules`——这部分模板可以参考[《Cline Rules 与 Memory Bank 完整使用指南》](/blog/cline-rules-and-memory-bank/)。

## 九、和其他扩展的冲突

最常见的冲突对象是 **GitHub Copilot**：两者都会在编辑器里插入内联建议，同时开着容易出现建议互相覆盖、或者 Tab 键被抢占的情况。处理方式：

| 场景 | 建议 |
| --- | --- |
| 主力用 Cline 做代理式开发 | 保留 Copilot 但关掉它的 inline suggestions，只留 Chat |
| 偶尔切换用哪个 | 用 VSCode Profile 功能，分别建 "Cline Profile" 和 "Copilot Profile"，切换时互不干扰 |
| 只想要一个 | 直接禁用不用的那个扩展，避免常驻内存 |

VSCode Profile（左下角图标 → Profiles）是处理"多个 AI 插件共存"最干净的方式，比手动来回启用/禁用扩展省心。

## 十、相关阅读

- [Cline 国内 API 配置详解（VSCode 编程代理）](/blog/cline-cn-api-setup/)
- [Cline Rules 与 Memory Bank 完整使用指南](/blog/cline-rules-and-memory-bank/)
- [Cline Auto-Approve 设置最佳实践](/blog/cline-auto-approve-best-practices/)
- [Cline 在大型代码库的实战经验与调优技巧](/blog/cline-on-large-codebase/)

配置好 VSCode 侧之后，剩下就是接一个稳定的模型入口——[YoTradeApi](https://yotradeapi.com) 一个 Key 接入 Claude、GPT 等主流模型，直接填进上面的 Provider 设置里就能用。
