---
title: JetBrains 系 AI 插件配置
description: 面向 IntelliJ IDEA、PyCharm、WebStorm 等 JetBrains IDE，讲解 AI Assistant 安装、官方服务与自定义模型配置、上下文控制、团队治理和常见故障排查。
keywords:
  - JetBrains AI 插件配置
  - IntelliJ AI Assistant
  - PyCharm AI 插件
  - JetBrains 自定义模型
  - JetBrains OpenAI Compatible
tags:
  - JetBrains
  - AI Assistant
  - IDE 配置
  - 工具配置
pubDate: '2026-09-13'
updatedDate: '2026-09-13'
canonical: https://blog.yotradeapi.com/blog/jetbrains-ai-plugin-config/
category: 工具配置
---

JetBrains 系 IDE 的 AI 配置容易被理解成“装一个插件、填一个 Key”。实际要先分清三个层次：AI Assistant 是 IDE 功能入口；JetBrains AI、第三方 API 或本地模型负责提供模型；Chat、代码补全与 Agent 又可能使用不同的连接和模型分配。只验证聊天窗口能回答，并不代表行内补全和工具调用都已正确配置。

本文以 IntelliJ IDEA、PyCharm、WebStorm、GoLand 等共用设置为主。JetBrains 会持续调整界面与支持范围，菜单名称应以当前 IDE 和 [AI Assistant 官方文档](https://www.jetbrains.com/help/ai-assistant/installation-guide-ai-assistant.html)为准，不要照搬旧教程中的截图。

## 一、安装前先决定接入路径

常见接入路径有三种：使用 JetBrains AI 托管服务；使用第三方服务商的 API Key；连接 Ollama、LM Studio 或 OpenAI-compatible endpoint。它们不是简单的“同一个聊天框换模型”，在功能覆盖、网络路径、账号治理和数据处理责任上都有差异。

| 路径 | 适合场景 | 配置重点 | 先确认什么 |
| --- | --- | --- | --- |
| JetBrains AI | 希望开箱即用 | JetBrains Account 与组织授权 | 订阅及组织是否允许 |
| 第三方 API | 已有模型账号或统一网关 | Provider、Key、URL、模型 | 功能是否被该模型支持 |
| 本地模型 | 数据边界严格、可自备算力 | 本地服务地址与上下文窗口 | 硬件和模型能力是否够用 |

不要一开始同时启用多个来源。先让一条路径完成“连接测试—聊天—补全—项目上下文”四项验证，再增加备用模型，否则故障时很难判断请求究竟发往哪里。

## 二、安装并确认插件真正启用

官方文档说明 AI Assistant 默认并非随 IDE 捆绑启用。可从 AI Chat 工具窗口、窗口顶部的 JetBrains AI widget，或 `Settings | Plugins | Marketplace` 搜索 AI Assistant 安装。安装后若 IDE 要求重启，应先重启再排查设置缺失。

打开插件设置前，先检查三件事：IDE 版本是否满足当前插件要求；公司提供的商业许可证是否由管理员关闭 JetBrains AI；当前项目是否单独禁用了 AI Assistant。团队环境中，个人能安装插件并不等于组织已允许云端模型。

安装完成后，建议新建一个无敏感数据的小型测试项目。先让 Chat 解释一段示例代码，再触发行内补全。这样可以把插件问题与大型项目索引、代理或权限问题分开。

## 三、配置 JetBrains AI 托管服务

选择托管服务时，登录 JetBrains Account，并在 JetBrains AI widget 中确认当前许可状态。随后进入 `Settings | Tools | AI Assistant` 检查功能开关和 Provider。组织账号若无法激活，应先找管理员确认组织策略，不要反复退出登录或重装插件。

模型列表与额度属于会变化的信息，本文不固化具体型号和价格。实际选型时从三个维度验证：该模型能否用于目标功能、项目语言上的表现、一次典型任务的响应速度。对大型重构用的 Chat 模型与高频行内补全模型，不一定应该相同。

如果 IDE 中没有教程所说的模型，应以账号、地区、组织策略和当前插件显示为准。不要手工写入一个界面未识别的托管模型名，然后假设请求已经切换成功。

## 四、配置第三方或 OpenAI-compatible 接口

当前官方设置把第三方模型放在 `Settings | Tools | AI Assistant | Providers & API keys`。根据服务选择 Provider，填写 API Key；使用兼容接口时还要填写 URL，并点击 `Test Connection`。模型是否能聊天、补全或调用工具，需要分别确认，不能由“连接成功”推导出来。

配置兼容接口时建议记录如下清单，不要把真实密钥写入项目文档：

```text
Provider: OpenAI Compatible
Base URL: 由服务商文档确认的 API 根地址
API Key: 仅存入 IDE 的凭据设置
Model: 先调用服务商模型列表或查官方文档
Tool calling: 只有接口和模型都支持时启用
Connection test: 通过后再验证 Chat 与 Completion
```

URL 最常见的问题是多写或漏写版本路径，模型名错误则常表现为连接能通、正式请求却返回 not found。若经过中转，还应确认其兼容的是 Chat Completions 还是 Responses 等具体协议，而不是只看“OpenAI compatible”这一宣传词。

## 五、单独配置 AI Completion 与模型分工

JetBrains 官方设置把 AI Completion 单列出来，可为行内补全选择 JetBrains 或 OpenAI-compatible provider，并配置 Base URL、模型、context window、最大输出和 prompt schema。聊天可用而补全无响应时，优先检查这里，而不是继续改 Chat 的 Provider。

行内补全强调低延迟、短输出与代码续写；Chat 和 Agent 更依赖长上下文、工具调用与多步判断。若界面支持 Model Assignment，可将 Core features 与 Instant helpers 分配给不同模型。先使用默认 schema，只有 IDE 无法识别自定义模型时才手动选择模板。

上下文窗口也不是越大越好。填写值应与服务端真实限制一致；虚报更大窗口可能让请求到达服务端后被拒绝。对于大型仓库，应先改进上下文选择和项目规则，而不是把所有文件都塞入一次请求。团队采用 AI 结对流程时，可结合 [AI 结对编程实战指南：让 AI 真正成为你的副驾驶](/blog/ai-coding-pair-programming/) 制定任务边界。

## 六、控制项目上下文与敏感数据

AI 功能工作时，Prompt、代码片段和辅助上下文可能被发送给所选 LLM provider。使用第三方或本地服务后，数据处理还受对应服务条款和部署方式约束。团队应先列出禁止外发的仓库、目录和数据类型，再决定哪些项目允许启用。

JetBrains 文档提供 AI Assistant 请求日志，可通过 Search Everywhere 查找 `Open AI Assistant Requests Log in Editor`，检查本次会话发出的 Prompt 与上下文。它适合在测试项目中验证数据边界，但日志本身也可能包含代码，分享或上传工单前必须脱敏。

API Key 不应写入 `.idea` 中会被提交的文件、README、Run Configuration 环境模板或聊天 Prompt。若怀疑泄漏，立即撤销并重新签发；详细处置步骤见 [API Key 泄漏应急响应：从撤销到复盘](/blog/api-key-leak-emergency-response/)。

## 七、按症状排查常见故障

插件入口不存在时，检查插件是否启用、IDE 是否重启以及版本是否兼容。能打开 Chat 但提示未授权时，检查 JetBrains Account、组织策略和 Provider 状态。连接测试失败时，再检查代理、DNS、证书、Base URL 与 Key 权限。

Chat 正常但行内补全失败，转到 AI Completion 的独立 Provider 与模型设置；普通问答正常但 Agent 工具不可用，则核对所选模型和兼容端点是否支持 tool calling。响应很慢时，分别测一个空项目和真实项目，以判断瓶颈来自网络、模型还是上下文收集。

每次只改一个变量，并保存失败时间、IDE 版本、插件版本、Provider、模型名与脱敏后的错误码。不要把 Key 或完整请求日志贴到公开 issue。若团队要规模化采用，还应把允许的 Provider、升级节奏与审查规则写入统一规范，可参考 [AI 编程 Agent 团队治理指南](/blog/ai-coding-agent-team-governance/)。

## 八、相关阅读

- [AI 结对编程实战指南：让 AI 真正成为你的副驾驶](/blog/ai-coding-pair-programming/)
- [国内 AI 编程工具厂商盘点：现状与选型参考](/blog/cn-ai-coding-tools-overview/)
- [AI 编程 Agent 权限模型设计](/blog/ai-coding-agent-permission-models/)
- [API Key 泄漏应急响应：从撤销到复盘](/blog/api-key-leak-emergency-response/)
