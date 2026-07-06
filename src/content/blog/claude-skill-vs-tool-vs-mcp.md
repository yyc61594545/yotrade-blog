---
title: Claude Skill、Tool、MCP 三者边界与协作关系详解
description: 拆解 Claude 生态里 Skill、Tool Use、MCP 三个概念的职责边界，讲清楚什么时候该用哪个、三者如何在同一个 Agent 里协作。
keywords:
  - Claude Skill vs Tool
  - Claude MCP vs Tool Use
  - Anthropic Skills 与 MCP 区别
  - Claude Agent 架构
  - Tool Use MCP Skill 选型
pubDate: '2026-07-06'
updatedDate: '2026-07-06'
canonical: https://blog.yotradeapi.com/blog/claude-skill-vs-tool-vs-mcp/
tags:
  - Claude
  - MCP
  - Skills
  - Agent 架构
category: 技术深度
heroImage: ../../assets/blog-placeholder-3.jpg
---

接触 Claude 生态久一点的开发者，大概率都遇到过这个疑惑：Skill、Tool（Tool Use）、MCP 这三个词经常同时出现在同一份文档里，字面意思也有重叠——都是"让模型具备某种能力"的机制。但它们解决的其实是三个不同层次的问题，混在一起理解容易导致架构设计走偏。本文把三者的职责边界拆开讲清楚。

## 一、一句话区分三者

| 概念 | 回答的问题 | 类比 |
| --- | --- | --- |
| Tool Use | 模型怎么"调用"一个具体动作 | 函数签名——定义输入输出接口 |
| MCP | 工具/数据源怎么"接入"到客户端 | USB 协议——标准化的连接方式 |
| Skill | 一套完整能力怎么"打包复用" | 说明书 + 工具箱——包含流程知识和资源 |

简单说：**Tool Use 是调用机制，MCP 是接入协议，Skill 是能力封装**。三者不是互相替代的关系，而是分别解决"怎么调"、"从哪接"、"怎么打包复用"三个独立问题。

## 二、Tool Use：模型和外部动作之间的调用接口

Tool Use（工具调用/Function Calling）是最基础的一层：给模型定义一组带 JSON Schema 的"工具"，模型根据对话上下文决定要不要调用、调用哪个、传什么参数。这一层完全不关心工具的实现细节是本地函数、HTTP 请求还是数据库查询——对模型来说都只是一个可以被调用的接口定义。

Tool Use 本身不解决"这个工具的代码从哪里来、怎么维护、怎么在多个客户端之间复用"的问题，它只解决"模型怎么表达调用意图、怎么拿到结构化的调用参数"。具体的接口设计原则和常见陷阱参考 [Claude Tool Use 最佳实践与陷阱](/blog/claude-tool-use-best-practices/)，多工具场景的并发调用参考 [Claude 并行工具调用实践](/blog/parallel-tool-use-claude/)。

## 三、MCP：让工具接入变成标准化协议而不是各自为战

如果每个客户端（Claude Code、Cursor、自建 Agent）都要为每个数据源（文件系统、GitHub、数据库）单独写一套接入代码，会导致 N 个客户端 × M 个数据源产生 N×M 份重复的接入逻辑。MCP（Model Context Protocol）解决的正是这个问题：定义一套标准协议，让工具/数据源只需要实现一次 MCP Server，就能被任何支持 MCP 的客户端接入，把 N×M 的接入成本降到 N+M。

MCP 本质上是**Tool Use 的"批量供给"机制**——一个 MCP Server 暴露出来的能力，最终还是要通过 Tool Use 的方式被模型调用，只是这些工具的注册、发现、连接管理由 MCP 协议标准化了，不需要在每个客户端里手写。具体的接入配置和自定义 Server 开发参考 [MCP 服务器实战](/blog/mcp-server-cn-guide/) 和 [MCP 自定义服务器开发指南](/blog/mcp-custom-server-development/)。

## 四、Skill：把"怎么做一件事"的完整知识打包复用

Skill 解决的是另一个层面的问题：很多任务不是"调一个工具就能完成"，而是需要一套**流程性知识**——什么时候该做什么、参考哪些模板、用什么顺序组织步骤。这类知识如果每次都在对话里重新解释一遍,既低效又容易出偏差。Skill 把这套知识（通常是 Markdown 说明 + 配套脚本/模板文件）打包成一个可复用的包，模型在需要时加载对应 Skill 的说明，按照里面的流程执行。

Skill 和 Tool Use/MCP 不是同一层级的东西：一个 Skill 内部完全可以调用若干个 Tool（本地函数）或 MCP 提供的能力，Skill 提供的是"这些工具该按什么顺序、什么逻辑组合使用"的流程编排知识，而不是新增了调用能力本身。完整的 Skill 定义方式和实战案例参考 [Anthropic Skills 实战：把能力封装成可复用包](/blog/anthropic-skills-cn-guide/)。

## 五、三者协作的典型架构

在一个成熟的 Agent 系统里，三者通常是这样组合工作的：

```
用户请求
   │
   ▼
Skill 层：识别任务类型，加载对应的流程说明
   │  （比如"写周报"这个 Skill，说明里规定了取数顺序、格式模板）
   ▼
Tool Use 层：按照 Skill 里规定的步骤，逐个调用具体工具
   │  （调用"查询数据库"工具、调用"生成图表"工具）
   ▼
MCP 层：工具背后的实际连接由 MCP 协议标准化接入
   （数据库连接、文件系统访问，都通过统一的 MCP Server 提供）
```

也就是说：**Skill 决定"做什么、按什么顺序做"，Tool Use 决定"具体这一步怎么调用"，MCP 决定"这个可调用的工具从哪里、怎么接进来"**。三者分别在编排层、调用层、接入层各司其职，不存在互相替代的关系。

## 六、常见的误用和边界模糊场景

**误用一：把 MCP Server 当成 Skill 使用**。有团队直接把一整套业务流程逻辑写进 MCP Server 的工具实现里，导致 MCP Server 变得臃肿且难以复用——MCP Server 应该保持工具粒度的原子性（比如"查询一条记录""执行一次搜索"），复杂的编排逻辑应该放在 Skill 层。

**误用二：给每个细粒度操作都定义单独的 Tool，而不用 MCP 统一管理**。如果项目里需要接入多个数据源，且未来可能被多个客户端复用，直接手写 Tool 定义会导致后续维护成本累积；这种场景更适合把数据源封装成 MCP Server，一次实现多处复用。

**边界模糊场景：一个 Skill 只调用一个 Tool，看起来像是重复定义**。这种情况下，如果这个能力未来大概率只被这一个场景使用，直接用 Tool Use 已经足够，不需要额外包一层 Skill；只有当这套流程知识需要在多个上下文里被复用、且包含的不只是"调用哪个工具"而是"按什么逻辑判断调用哪个、怎么处理异常"时，封装成 Skill 才有意义。

## 七、选型速查

| 场景 | 该用什么 |
| --- | --- |
| 只需要模型调用一个具体动作（查天气、发邮件） | Tool Use 就够了 |
| 需要接入的数据源/工具会被多个客户端复用 | 用 MCP 封装成 Server |
| 一套任务有固定流程、需要跨会话复用 | 封装成 Skill |
| 流程简单、一次性、不涉及外部工具调用 | 直接写 system prompt 说明即可，不需要上升到 Skill |

## 八、相关阅读

- [Claude Tool Use 最佳实践与陷阱](/blog/claude-tool-use-best-practices/)
- [MCP 服务器实战：Claude Code/Cursor/Cherry Studio 接入](/blog/mcp-server-cn-guide/)
- [Anthropic Skills 实战：把能力封装成可复用包](/blog/anthropic-skills-cn-guide/)
- [MCP 自定义服务器开发指南](/blog/mcp-custom-server-development/)
- [Claude 并行工具调用实践](/blog/parallel-tool-use-claude/)

搭建多层 Agent 架构时需要同时对比不同模型的 Tool Use 调用准确率？[YoTradeApi](https://yotradeapi.com) 一个 Key 接入全系模型，方便验证同一套 Skill/MCP 架构在不同模型上的表现差异。
