---
title: Gemini Live API 会话状态设计
description: 面向实时语音应用开发者，系统拆解 Gemini Live API 的 WebSocket 生命周期、会话恢复令牌、上下文压缩、GoAway 迁移、打断处理与业务状态持久化，并给出防止僵尸连接、重复工具调用和重连风暴的生产级状态机方案，以及上线前必须覆盖的故障注入和监控指标。
keywords:
  - Gemini Live API 会话状态
  - Gemini Live API 重连
  - SessionResumptionUpdate
  - WebSocket 会话恢复
  - 实时语音 Agent 架构
pubDate: '2026-08-22'
updatedDate: '2026-08-22'
canonical: https://blog.yotradeapi.com/blog/gemini-live-api-session-design/
tags:
  - Gemini
  - Live API
  - WebSocket
  - 会话管理
category: 技术深度
heroImage: ../../assets/blog-placeholder-4.jpg
---

实时语音应用最容易低估的部分，不是麦克风采集，也不是把音频写进 WebSocket，而是“连接断了以后，用户还在不在同一场对话里”。Gemini Live API 用持久连接承载双向流，但连接、模型上下文、业务会话和客户端播放状态并不是同一个概念。把它们塞进一个 `sessionId`，短时演示通常能跑，进入移动网络、长对话和工具调用场景后却会迅速失控。

本文聚焦会话状态本身：哪些状态应该放客户端，哪些必须落服务端，恢复令牌怎样轮换，何时应该恢复旧会话，何时应创建新会话。模型名称和限额会变化，涉及具体字段时应以 [Google Live API 会话管理文档](https://ai.google.dev/gemini-api/docs/live-api/session-management) 与 API reference 为准。

## 一、先把四层“会话”拆开

一个可恢复的实时应用至少有四层状态。第一层是 WebSocket 连接，只描述当前传输通道；第二层是 Gemini 模型会话，包含服务端可恢复的上下文；第三层是业务会话，例如工单、访谈或陪练任务；第四层是设备侧媒体状态，包括尚未播放的音频、录音序号和 UI 状态。

| 层级 | 典型标识 | 生命周期 | 断线后的处理 |
| --- | --- | --- | --- |
| 连接层 | `connectionId` | 数分钟或一次网络连接 | 直接重建 |
| 模型层 | resumption handle | 可跨连接延续 | 用最新可恢复令牌恢复 |
| 业务层 | `conversationId` | 由产品流程决定 | 从数据库或缓存读取 |
| 媒体层 | `audioSeq`、播放游标 | 单设备、单次交互 | 丢弃或按序号去重 |

关键结论是：`connectionId` 不能作为业务主键，resumption handle 也不应暴露给前端当永久会话 ID。前者变化太频繁，后者是短期恢复凭据，而且会被后续更新替代。业务层应生成自己的稳定 ID，再把当前模型恢复信息作为可过期的附属状态保存。

## 二、用显式状态机管理生命周期

只用 `connected: boolean` 无法区分“正在恢复”和“已经失败”，也无法阻止两个重连任务同时启动。更稳妥的方式是定义单向状态机，并让每次迁移都记录原因。

```text
IDLE
  -> CONNECTING
  -> ACTIVE
  -> DRAINING       # 收到 GoAway，停止接收新任务
  -> RECONNECTING   # 带 handle 建立新连接
  -> ACTIVE

任意状态 -> FAILED -> NEW_SESSION 或 CLOSED
```

`ACTIVE` 只表示 setup 已完成且可以发送实时输入，不代表浏览器的音频输出已经播完。收到连接错误时，先以原子操作把状态从 `ACTIVE` 改为 `RECONNECTING`；只有成功抢到迁移权的协程才能发起重连。若状态已经是 `RECONNECTING`，其余错误回调只追加诊断信息，不能再开第二条连接。

每次迁移建议记录 `from`、`to`、`reason`、`connectionEpoch` 和时间戳。排查“偶发重复回答”时，单看异常堆栈不够，状态迁移日志通常更有价值。

## 三、恢复令牌要按“最新可用快照”处理

启用 `sessionResumption` 后，服务端会发送会话恢复更新。应用应保留最近一次标记为可恢复的 handle，并在下一条连接的 `SessionResumptionConfig.handle` 中使用它。官方 reference 还说明，会话在某些阶段可能暂时不可恢复，例如模型正在生成内容或执行函数调用时；此时不能假设每条更新都带有可用 handle。

推荐的数据结构如下：

```ts
type ResumeCheckpoint = {
  conversationId: string;
  handleCiphertext: string;
  connectionEpoch: number;
  receivedAt: number;
  resumable: boolean;
};
```

更新时采用 compare-and-set：只有 `connectionEpoch` 不早于已存记录、消息确实可恢复且 handle 非空时才覆盖。这样旧连接迟到的消息不会冲掉新连接的令牌。handle 应像临时凭据一样加密存储、限制日志输出并设置 TTL；它用于恢复模型会话，不应承担鉴权作用。

恢复成功后仍要递增 `connectionEpoch`。客户端发送的每个业务事件都带 epoch 与单调递增序号，服务端拒绝旧 epoch 的音频和工具结果，从源头阻止“僵尸连接”继续写入。

## 四、GoAway 与意外断线要走两条路径

服务端可能在连接结束前发送 `GoAway`，其中的剩余时间给应用留下了平滑迁移窗口。此时应进入 `DRAINING`：暂停开启新的工具任务，保存最新恢复检查点，准备新连接，并在新连接可用后切换输入。它和突然断网不同，不需要立即向用户报错。

意外断线则进入带抖动的指数退避。建议把重试分成三类：网络错误可自动重试；鉴权或配置错误直接失败；恢复 handle 被拒绝时，只允许降级创建一次新模型会话。无限循环使用失效 handle，会把一次可恢复故障放大成重连风暴。

降级新会话也不等于完全失忆。业务服务可以把已经确认的事实、用户目标和未完成任务压缩成一条明确的初始上下文，再创建新连接。但不要把未经确认的实时转写全文直接回灌，否则既浪费上下文，也可能重复执行工具操作。

## 五、上下文压缩与业务记忆不是一回事

Live API 提供 `contextWindowCompression`，可在上下文达到阈值时通过滑动窗口控制长度。它解决的是模型上下文容量与长期连接问题，不等同于产品所需的长期记忆。窗口前部内容被移出后，订单号、用户承诺或任务阶段仍可能是业务必需状态。

因此应维护两条轨道：模型上下文用于保持自然对话，业务摘要用于保存可验证事实。摘要最好采用结构化字段，例如 `goal`、`confirmedFacts`、`pendingActions` 和 `lastToolResultId`，并在工具成功或用户明确确认后更新，而不是每收到一段音频就改写。

如果你正在设计通用的压缩策略，可参考[长对话上下文压缩策略](/blog/context-compression-strategies/)；Live API 这一层只负责配置压缩触发与窗口，产品语义仍由业务层维护。

## 六、打断与工具调用决定了状态一致性

语音应用允许用户在模型说话时插话。收到 `interrupted` 信号后，应立即清空尚未播放的客户端音频缓冲，并把当前输出标记为“未完整呈现”。如果 UI 仍然把整段模型文本显示为已说完，下一轮模型与用户看到的历史就会不一致。

工具调用更需要幂等设计。网络断线可能发生在“外部系统已经成功写入、结果还没传回模型”之间。每个有副作用的调用都应携带由业务会话生成的 `idempotencyKey`，先查询已有结果，再决定是否执行。恢复后优先重放工具结果，而不是重新下单、重新发信或重新扣费。

可以把一个回合记录为 `RECEIVING_INPUT -> GENERATING -> TOOL_PENDING -> DELIVERING -> COMMITTED`。只有用户可感知输出已经播放、或工具结果已经持久化后，才进入 `COMMITTED`。恢复逻辑依据最后的已提交节点继续，避免用“最后收到哪条 WebSocket 消息”猜测业务进度。

## 七、生产环境的最小检查清单

上线前至少验证以下路径：正常对话跨连接恢复；生成中断线；工具调用前后断线；收到 GoAway 后平滑迁移；旧连接迟到消息；恢复 handle 失效后创建新会话；客户端后台切前台；同一账号多设备并发。

监控上不要只看连接成功率。更有用的指标包括恢复成功率、从断线到重新可说话的耗时、每个业务会话的连接数、handle 拒绝率、重复工具调用数、丢弃的旧 epoch 消息数，以及上下文压缩发生频率。日志中记录 handle 的哈希前缀即可关联问题，不要输出完整值。

最后，用故障注入代替人工拔网线：在测试代理中按消息类型主动关闭连接、延迟恢复更新或重复投递工具结果。只有状态机在这些情况下仍保持单一写入者、工具幂等和播放一致，才算真正具备会话恢复能力。

## 八、相关阅读

- [长对话上下文压缩策略](/blog/context-compression-strategies/)
- [OpenAI Realtime API 完全指南](/blog/openai-realtime-api-guide/)
- [LLM 流式输出背压处理](/blog/llm-streaming-backpressure/)
- [AI Chatbot 上下文管理实战](/blog/ai-chatbot-context-management/)

如果你还需要为实时应用统一不同模型的调用入口，[YoTradeApi](https://yotradeapi.com) 可提供兼容常见 SDK 的 API 接入方式，便于把鉴权、用量与故障切换集中在服务端管理。
