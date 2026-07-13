---
title: AI Agent Human-in-Loop 模式实战
description: 详解 AI Agent 中 Human-in-the-Loop 设计模式的落地方法，涵盖审批网关、置信度阈值、分级授权与中断恢复的工程实现与代码示例。
keywords:
  - Human-in-the-loop Agent
  - AI Agent 审批机制
  - Agent 人工介入设计
  - Agent 置信度阈值
  - AI Agent 分级授权
pubDate: '2026-07-13'
updatedDate: '2026-07-13'
canonical: https://blog.yotradeapi.com/blog/ai-agent-human-in-loop/
tags:
  - 应用工程
  - AI Agent
  - 系统设计
  - 生产实践
category: 应用工程
heroImage: ../../assets/blog-placeholder-3.jpg
---

全自动 Agent 听起来很美好，但一旦涉及发邮件、改数据库、花钱下单这类操作，纯自动化往往是灾难的开始。Human-in-the-Loop（HITL，人工介入）不是"退回到手动"，而是一种精确控制自动化边界的设计模式：让 Agent 处理确定性高的部分，把不确定或高风险的决策交还给人。

本文聚焦 HITL 在生产级 Agent 系统中的具体实现方式，不谈概念，只谈怎么落地。

## 一、为什么需要 Human-in-the-Loop

Agent 系统失控通常不是因为模型"变笨"了，而是因为它在不该自主决策的地方自主决策了。常见的失控场景：

- Agent 误解用户意图，执行了错误但"看起来合理"的操作（比如把退款金额算错但格式完全正确）
- 工具调用链变长后，早期的小误差被逐步放大，最终执行了完全偏离预期的操作
- 面对模型没见过的边界情况，Agent 用"最像的模式"硬套，而不是承认不确定

HITL 的核心价值在于：把这些风险点变成**显式的检查点**，而不是让它们隐藏在自动化流程里等出问题才发现。这和 [AI Agent 错误恢复设计](/blog/ai-agent-error-recovery/) 讨论的"出错后怎么办"不同，HITL 解决的是"哪些操作从一开始就不该无人值守"。

## 二、三种基础 HITL 模式

### 1. 审批网关（Approval Gate）

最直接的模式：Agent 生成操作计划后暂停，等待人工确认才执行。适合低频、高风险操作（删除数据、大额支付、对外发布内容）。

```python
def execute_action(action, risk_level):
    if risk_level >= RiskLevel.HIGH:
        approval = request_human_approval(
            action=action,
            context=action.reasoning,
            timeout=300,
        )
        if not approval.approved:
            return ActionResult(status="rejected", reason=approval.feedback)
    return action.execute()
```

关键设计点是**把 Agent 的推理过程一并展示给审批人**，而不是只给一个操作按钮。审批人需要知道"为什么 Agent 认为该这么做"，才能做出有效判断，否则审批会退化成无脑点"同意"。

### 2. 置信度阈值路由（Confidence-Based Routing）

不是所有操作都值得打断用户。更精细的做法是让 Agent 对自己的判断给出置信度评分，低于阈值才触发人工介入：

```python
def route_by_confidence(decision, threshold=0.85):
    if decision.confidence >= threshold:
        return auto_execute(decision)
    elif decision.confidence >= threshold - 0.2:
        return execute_with_notification(decision)  # 执行但通知人工
    else:
        return escalate_to_human(decision)  # 暂停等待
```

这里有个容易踩的坑：**模型自报的置信度往往不可靠**，尤其是小模型或者 prompt 没有专门校准过的情况下，容易出现"言之凿凿但其实错了"。更稳妥的做法是用历史数据校准置信度分布，或者结合结构化信号（比如工具返回的错误率、结果是否命中已知模式）来综合判断，而不是完全依赖模型自评。

### 3. 分级授权（Tiered Autonomy）

按操作类型预先分级，不同级别对应不同的自主程度，这是目前生产环境用得最多的模式：

| 授权级别 | 典型操作 | 人工介入方式 |
| --- | --- | --- |
| 只读 | 查询、搜索、生成报告草稿 | 无需介入 |
| 可逆操作 | 创建草稿、发送内部通知、写测试代码 | 事后可撤销，无需前置审批 |
| 有限自主 | 小额退款、非生产环境部署 | 设定金额/范围上限，超限触发审批 |
| 强制审批 | 生产环境变更、对外发布、大额交易 | 每次都需人工确认 |

这个分级思路和 Claude Code 自身的权限模式（比如哪些 Bash 命令自动允许、哪些需要用户确认）是同一套逻辑——按操作的可逆性和影响范围分级，而不是按"是否是 Agent 发起的"一刀切。

## 三、工程实现：中断与恢复

HITL 最难的部分不是"要不要问人"，而是**问完之后怎么无缝恢复执行上下文**。如果 Agent 在等待审批期间丢失了状态，恢复后重新推理一遍，既浪费 token 也可能产生和暂停前不一致的结果。

实践中常见的做法是把 Agent 执行状态显式序列化，暂停时落盘或存入队列：

```python
class AgentCheckpoint:
    def __init__(self, session_id, pending_action, context_snapshot):
        self.session_id = session_id
        self.pending_action = pending_action
        self.context_snapshot = context_snapshot
        self.created_at = timestamp()

def pause_for_approval(agent_state):
    checkpoint = AgentCheckpoint(
        session_id=agent_state.session_id,
        pending_action=agent_state.next_action,
        context_snapshot=agent_state.serialize(),
    )
    save_checkpoint(checkpoint)
    notify_approver(checkpoint)
    return checkpoint.session_id

def resume_from_approval(session_id, approval_result):
    checkpoint = load_checkpoint(session_id)
    if approval_result.approved:
        return checkpoint.pending_action.execute(
            context=checkpoint.context_snapshot
        )
    return handle_rejection(checkpoint, approval_result.feedback)
```

如果审批人给出了修改意见而不是简单的通过/拒绝，还需要设计"带反馈恢复"的路径——把人工反馈作为新的上下文注入，让 Agent 重新生成方案而不是重新理解整个任务，这样能明显减少多轮打断带来的体验损耗。

## 四、UI/UX 层面的关键细节

工程实现之外，HITL 的实际效果很大程度取决于审批界面的设计质量：

- **展示差异而非全量**：如果 Agent 是在修改已有内容（代码、文档、配置），展示 diff 而不是完整新版本，审批人能更快抓住重点。
- **给出可操作的拒绝方式**：单纯的"拒绝"按钮价值有限，最好允许审批人直接编辑或留言，把修改意见结构化传回 Agent。
- **超时策略要明确**：审批请求不能无限期挂起，需要设定超时后的默认行为（比如自动降级为只读模式，或标记任务失败并通知负责人），否则整条流水线可能被卡死。
- **批量审批**：高频低风险操作如果逐条审批会造成审批疲劳，可以设计"批量确认"界面，让人工一次性审核一批同类操作。

## 五、什么时候不该用 HITL

HITL 不是免费的——每一次人工介入都是延迟和认知负担。滥用 HITL 的典型表现是"什么都要问一遍"，结果人工审批变成了新的性能瓶颈，团队干脆开始无脑点同意，HITL 名存实亡。

判断是否需要 HITL 的简单原则：

1. **操作是否可逆**：可逆且成本低的操作，宁可执行后允许撤销，也不要事前审批。
2. **错误的影响范围**：只影响单个用户 vs 影响多个下游系统，前者可以更自主。
3. **历史准确率**：某类操作 Agent 长期保持高准确率后，可以逐步把它从"强制审批"降级为"置信度路由"，用数据驱动授权级别的调整，而不是一次性配置后就不再变化。

## 六、相关阅读

- [AI Agent 错误恢复设计](/blog/ai-agent-error-recovery/)
- [AI Agent 权限设计实践](/blog/ai-agent-permission-design/)
- [AI Agent 回滚策略](/blog/ai-agent-rollback-strategy/)
- [AI Agent 可观测性设计](/blog/ai-agent-observability-design/)

搭建 HITL 系统离不开稳定的模型调用能力，无论是审批网关里的置信度评分，还是暂停恢复时的重新推理，都需要低延迟、高可用的 API 支持，可以了解 [YoTradeApi](https://yotradeapi.com)，为开发者提供稳定的 AI API 中转服务。
