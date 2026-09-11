---
title: Zed AI 助手配置：Provider、快捷键与中转 API 接入
description: Zed 编辑器内置 AI 助手的配置方法：settings.json 里的 Provider 设置、自定义 OpenAI 兼容端点、Inline Assist 快捷键与常见配置问题排查。
keywords:
  - Zed AI助手配置
  - Zed settings.json
  - Zed自定义API端点
  - Zed Inline Assist
  - Zed编辑器AI配置
pubDate: '2026-09-11'
updatedDate: '2026-09-11'
canonical: https://blog.yotradeapi.com/blog/zed-ai-assistant-config/
tags:
  - Zed
  - 配置教程
  - 工具配置
  - AI编辑器
category: 工具配置
---

Zed 是用 Rust 写的高性能编辑器，主打启动快、协作编辑和原生集成的 AI 助手，跟 Cursor、Cline 的插件式接入不同，Zed 的 AI 能力是编辑器内核自带的一部分。这也导致它的配置思路和其他工具不太一样——不是装扩展、填 API Key 那么简单，而是要理解它的 Provider 抽象和几种交互模式的区别。这篇讲清楚怎么配。

## 一、配置文件位置

Zed 的所有设置都在一个 JSON 文件里，不像 VS Code 那样分全局/工作区两套体系（Zed 也支持工作区级覆盖，但语法是同一套）：

- macOS/Linux：`~/.config/zed/settings.json`
- 编辑器内直接打开：命令面板（`Cmd/Ctrl + Shift + P`）搜索 "Open Settings"

工作区级配置放在项目根目录的 `.zed/settings.json`，字段结构和全局一致，会覆盖全局设置。团队协作时通常把 `.zed/settings.json` 提交进仓库，统一模型和格式化规则，个人的 API Key 之类敏感配置留在全局设置里，不进仓库。

## 二、AI 助手的三种交互模式

配置之前先分清楚 Zed AI 助手的三种使用形态，因为部分配置项是按模式区分的：

1. **Assistant Panel（助手面板）**：类似聊天窗口，侧边栏对话，可以引用文件、执行 slash command。
2. **Inline Assist（行内助手）**：选中一段代码，快捷键唤起，直接在编辑区内生成/修改代码，不用切到侧边栏。
3. **Edit Predictions（编辑预测）**：类似 Copilot 的自动补全，输入时实时给建议，走的是 Zed 自己的补全模型（默认走 Zed 云端），和上面两个走的是独立的模型配置。

这三种模式的模型可以配置成不同的 Provider——比如补全用 Zed 自带的模型，对话和 Inline Assist 用接入的 Claude。

## 三、Provider 配置：接入 Claude / OpenAI / 自定义端点

在 `settings.json` 里，AI 助手相关配置通常放在一个顶层字段下（字段名和层级 Zed 版本迭代较快，以编辑器内 Settings 的自动补全提示或官方文档为准，下面给出的是配置的核心思路和典型结构）：

```json
{
  "assistant": {
    "default_model": {
      "provider": "anthropic",
      "model": "claude-sonnet-4-5"
    },
    "provider": {
      "anthropic": {
        "api_url": "https://your-relay-endpoint.example.com"
      }
    }
  }
}
```

几个关键点：

- **API Key 不写进 settings.json**：Zed 会在首次使用某个 Provider 时弹出输入框，让你粘贴 API Key，存到系统密钥链（macOS Keychain / Linux Secret Service），不会以明文存在配置文件里，这一点比某些工具直接把 key 写进 JSON 更安全。
- **`api_url` 是接入中转服务的关键字段**：如果你的 Anthropic/OpenAI Key 是走中转服务（比如国内直连不稳定，用 [YoTradeApi](https://yotradeapi.com) 这类中转网关），把默认的官方 endpoint 换成中转地址即可，鉴权方式通常保持不变（Bearer Token）。
- **多 Provider 并存**：`provider` 字段下可以同时配置 `anthropic`、`openai`、`google` 等多个条目，`default_model` 只决定默认用哪个，实际对话时可以在助手面板顶部临时切换模型，不用改配置文件。

## 四、Inline Assist 快捷键与常见用法

Inline Assist 是 Zed AI 助手里日常用得最频繁的功能，默认快捷键（不同版本可能有调整，以编辑器内 `Cmd/Ctrl + Shift + P` → "keymap" 查看当前绑定为准）：

- 选中代码后触发 Inline Assist：`Ctrl + Enter`（macOS 上部分版本是 `Cmd + Enter`）
- 唤起后直接输入指令（比如"给这个函数加错误处理"），回车执行
- 生成结果会以 diff 形式展示在原位置，`Cmd/Ctrl + Enter` 接受，`Esc` 取消

快捷键可以在 `~/.config/zed/keymap.json` 里自定义覆盖，格式是标准的 Zed keybinding 语法，如果和其他常用快捷键冲突（比如某些 Vim 模式下的绑定），建议改到不常用的组合键，避免误触。

## 五、Slash Command：助手面板里的效率功能

助手面板对话框里支持 slash command，输入 `/` 会弹出可用命令列表，常用的几个：

- `/file` — 把指定文件内容插入上下文，不用手动复制粘贴
- `/tab` — 引用当前打开的标签页内容
- `/diagnostics` — 把当前文件的报错/警告信息带入上下文，让助手直接看到 LSP 诊断结果
- `/terminal` — 引用终端最近的输出

这几个命令的作用本质是省去手动整理上下文的步骤，配置层面不需要额外设置，装好编辑器就能用，但值得在日常使用里养成习惯，比整段贴代码效率高。

## 六、Edit Predictions 单独配置

如果不想用 Zed 自带的编辑预测模型（比如担心额外的云端调用），可以单独关闭：

```json
{
  "features": {
    "edit_prediction_provider": "none"
  }
}
```

想换成基于其他 Provider 的预测（如果编辑器版本支持），改这个字段的值即可，具体可选项以当前版本 Settings 自动补全为准——这块是 Zed 迭代较快的功能，配置字段变动概率比 Provider 配置本身更高。

## 七、常见配置问题排查

- **API Key 输入框没弹出**：通常是 `default_model.provider` 指定的 Provider 名称拼写有误，或者该 Provider 还没在 `provider` 字段下声明，检查两处名称是否一致。
- **换了 `api_url` 之后请求 404 或鉴权失败**：确认中转服务的接口路径和官方 API 是否完全兼容（多数中转服务会做到路径级兼容，但个别中转的鉴权 header 名称可能不同），先用 `curl` 单独测一次中转端点，确认路径和返回格式没问题，再填进 Zed。
- **团队共享的 `.zed/settings.json` 里 Provider 配置对不同成员生效不一致**：这是预期行为，API Key 是各自本地密钥链存储的，配置文件只统一 Provider 和模型选择，Key 需要每个成员自己在本机输入一次。

## 八、相关阅读

- [Cline 在 VS Code 的配置：从安装到工作区级设置](/blog/cline-vscode-config-guide/)
- [Cursor Rules 最佳实践](/blog/cursor-rules-best-practices/)
- [Cursor vs Claude Code 全面对比](/blog/cursor-vs-claude-code-comparison/)
- [Cursor 团队配置指南](/blog/cursor-team-config-guide/)

如果 Zed 里配置的 API Key 走的是国内中转，[YoTradeApi](https://yotradeapi.com) 支持 Claude、GPT 等主流模型的中转调用，接口路径兼容官方格式，`api_url` 换成中转地址就能直接用，不用改代码逻辑。
