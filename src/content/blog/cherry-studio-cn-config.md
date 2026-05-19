---
title: Cherry Studio 国内 API 中转配置指南
description: Cherry Studio 桌面 LLM 客户端在国内的 API 中转接入完整教程，含模型管理、知识库、MCP、API 密钥隔离实用经验。
keywords:
- cherry studio 国内
- cherry studio api 配置
- cherry studio 中转
- cherry studio openai
- cherry studio claude
pubDate: '2026-05-18'
updatedDate: '2026-05-18'
canonical: https://blog.yotradeapi.com/blog/cherry-studio-cn-config/
tags:
- Cherry Studio
- 桌面客户端
- API 中转
- 知识库
- 配置教程
category: 工具配置
heroImage: ../../assets/blog-placeholder-2.jpg
---

# Cherry Studio 国内 API 中转配置指南

Cherry Studio 是国内开发者最常用的 LLM 桌面客户端之一，特点是「多模型并存、本地知识库、内置 MCP、界面友好」。它最大的优点是不需要写代码就能切换 Claude、GPT、Gemini、Grok 等模型；缺点是默认配置假设你能直连官方，国内用户必须自己接中转。

## 一、安装

去 [cherry-studio 官方仓库](https://github.com/CherryHQ/cherry-studio) 下载对应平台的安装包。macOS 用 `.dmg`，Windows 用 `.exe`，Linux 用 `.AppImage`。

安装后**先不要登录账号**——Cherry Studio 不强制账号，本地用就够。

## 二、添加 Provider（API 中转）

打开 Cherry Studio → 设置 → 模型服务，点 "+ 添加" 创建一个 OpenAI 兼容 Provider：

| 字段 | 填什么 |
| --- | --- |
| 提供商类型 | OpenAI |
| 名称 | YoTradeApi（随便取） |
| API 密钥 | 你的中转 Key |
| API 地址 | `https://yotradeapi.com/v1` |
| 模型 | 手动添加 `claude-sonnet-4-6`、`claude-opus-4-7`、`gpt-5`、`gemini-2.5-pro` 等 |

保存后点 "检查"，绿色对勾代表通了。

**注意点**：

- API 地址结尾**带不带斜杠都行**，但**不要写完整 endpoint**（写 `/chat/completions` 会 404）。
- 模型必须手动添加才能在对话页选到。Cherry Studio 不会自动发现网关支持的模型列表。
- 同一个网关可以重复添加多个 Provider 给不同业务（生产 / 测试 / 个人）。

## 三、按模型分场景

Cherry Studio 的"助手"功能允许给每个对话指定模型、system prompt、参数。推荐这样分：

| 助手名称 | 模型 | system prompt 关键点 |
| --- | --- | --- |
| 编程助手 | `claude-sonnet-4-6` | "你写生产级代码，给出完整可运行示例" |
| 写作助手 | `claude-opus-4-7` | "你是中文写作专家，注意行文节奏" |
| 翻译助手 | `gpt-5-mini` | "把以下内容翻译成中文，保留专业术语" |
| 检索助手 | `gemini-2.5-pro` | 知识库 + 长上下文 |
| 草稿员 | `claude-haiku-4-5` | "快速给出初稿，1 段以内" |

把日常 90% 流量导到便宜模型上，关键任务才用 Opus，账单能优化一个数量级。

## 四、本地知识库（RAG）

设置 → 知识库 → 新建：

1. 选 embedding 模型（推荐 `text-embedding-3-large` 或网关的 BGE 中文模型）
2. 上传文档（PDF、Word、Markdown、网页 URL 都行）
3. 等索引完成
4. 在对话页关联知识库，提问时自动检索

国内用中转走 RAG 有几个细节：

- **embedding 调用量大**：1 万字文档约消耗 2k tokens。网关一定要支持 embeddings 端点。
- **chunk size**：Cherry Studio 默认 500，长技术文档建议拉到 800–1200。
- **检索数量 top_k**：默认 5，复杂查询拉到 8–10。

## 五、MCP 服务器

Cherry Studio 内置 MCP 支持。设置 → MCP 服务器 → 添加：

```json
{
  "name": "filesystem",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/you/projects"]
}
```

常用 MCP：

| 服务器 | 用途 |
| --- | --- |
| filesystem | 读写本地文件 |
| github | 查 PR / issue |
| brave-search | 联网搜索 |
| sqlite | 查本地数据库 |
| memory | 跨会话长期记忆 |

**安全提示**：MCP 让 LLM 能调本地工具，filesystem 务必只暴露专门的工作目录，**不要给整个 home 目录**。

## 六、API 密钥隔离的实操

如果家里多人用同一台机器，或者你要把同一台机器用于工作和个人项目：

- **每个 Provider 用不同 Key**：在网关后台为不同用途生成独立 Key。
- **导出/导入配置**：设置最下方 "导出配置"。导出文件包含 Key 明文，不要传到云盘。
- **关闭遥测**：设置 → 数据 → 关闭"使用情况统计"。

## 七、流式输出 + 长回答的实战配置

国内中转下 Cherry Studio 偶尔会遇到流式中断。三个建议：

1. **对话设置 → 流式响应**：保持开启，体验更顺，但长输出（>4k tokens）容易断。
2. **超时**：高级设置里 Request Timeout 调到 120s。
3. **重试**：设置里"出错时自动重试"开启，但**重试次数 ≤ 2**，否则 429 风险升高。

## 八、常见报错

| 报错 | 原因 | 处理 |
| --- | --- | --- |
| `Provider check failed` | base_url 或 key 错 | 复制粘贴时去掉前后空格 |
| `Model xxx is not supported by this provider` | 模型名拼错 | 看网关后台支持的精确名字 |
| 流式没有任何输出 | SSE 被代理压缩 | 关闭流式重试 |
| 知识库检索结果不相关 | 文档分块太小 | 调大 chunk size，重建索引 |
| MCP 服务器无响应 | command/args 不对 | 终端单独跑命令验证 |

## 九、Cherry Studio vs ChatBox vs LobeChat

| 维度 | Cherry Studio | ChatBox | LobeChat |
| --- | --- | --- | --- |
| 形态 | 桌面 | 桌面 | Web + 桌面 |
| 知识库 | 内置 | 外接 | 内置 |
| MCP | 完整支持 | 部分 | 计划中 |
| 多模型并存 | 强 | 中 | 强 |
| 配置导入导出 | 完整 | 完整 | 部分 |
| 国内中转适配 | 友好 | 友好 | 友好 |

如果你的诉求是「能写文档、能跑代码片段、能查本地资料、还要能切换不同厂商模型」，Cherry Studio 是平衡度最好的选项。

## 十、相关阅读

- [Cursor API 中转怎么选：2026 实用清单](/blog/2026-05-15-cursor-api-relay-recommendation-2026/)
- [Claude Code 镜像国内配置完整指南](/blog/claude-code-mirror-cn-setup/)
- [OpenAI SDK base_url 国内配置实战](/blog/openai-sdk-base-url-cn/)
- [Cline 国内 API 配置详解](/blog/cline-cn-api-setup/)
- [Aider 中文配置与最佳实践](/blog/aider-cn-config-guide/)

需要支持 Claude / GPT / Gemini / Grok 全家桶的中转？在 [YoTradeApi 注册](https://yotradeapi.com/register) 用一把 Key 接所有模型，按上面 base_url 直接接入 Cherry Studio。
