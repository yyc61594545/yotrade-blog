---
title: AI Agent 任务分解模式
description: 讲解 AI Agent 拆解复杂任务的常见模式：线性分解、树形分解、动态重规划，附实际工程判断标准和代码示例。
keywords:
  - AI Agent 任务分解
  - Agent 任务规划
  - 多步骤 Agent 设计
  - Agent 子任务拆分
  - LLM 任务编排
pubDate: '2026-07-04'
updatedDate: '2026-07-04'
canonical: https://blog.yotradeapi.com/blog/ai-agent-task-decomposition/
tags:
  - AI Agent
  - 任务分解
  - Agent 架构
  - 应用工程
category: 应用工程
heroImage: ../../assets/blog-placeholder-5.jpg
---

给 Agent 一个复杂目标（比如"重构这个模块并补齐测试"），它需要先把目标拆成可执行的子步骤，再逐步完成。拆得好，Agent 执行稳定、可追踪、易于中途纠错；拆得不好，Agent 要么在一个步骤里塞太多事导致失败率飙升，要么陷入无止境的子任务生成循环。本文梳理三种常见的任务分解模式，以及怎么选。

## 一、为什么任务分解是 Agent 设计的核心问题

单次 LLM 调用能可靠完成的任务复杂度是有上限的——上下文越长、需要维护的状态越多，出错概率越高。任务分解本质上是在做一件事：**把一个模型容易出错的大任务，切成多个模型能可靠完成的小任务**。

拆分粒度不是越细越好。粒度太细会带来：
- 步骤间协调开销变大（每一步都要传递上下文）
- 总执行时间变长（每个子任务都是一次完整的模型调用）
- 中间状态管理复杂度上升

拆分粒度不够又会带来：
- 单步任务过载，模型顾此失彼，容易漏做步骤
- 失败后难以定位是哪个环节出的问题，只能整体重试

判断标准：**一个子任务应该对应一个清晰的、可以独立验证成功与否的产出物**。比如"写一个函数"是好的粒度，"完成整个功能模块"通常不是。

## 二、模式一：线性分解（Sequential Decomposition）

最简单的模式——把任务拆成一串有先后依赖的步骤，按顺序执行：

```python
def linear_plan(goal):
    """让模型生成一个有序步骤列表"""
    steps = llm_call(f"""
    将以下目标拆解为有序的执行步骤，每步应该是独立可验证的：
    目标：{goal}
    以 JSON 数组返回，每项包含 step_id 和 description。
    """)
    return steps

def execute_linear(steps):
    results = []
    for step in steps:
        result = execute_step(step, context=results)  # 每步能看到之前的结果
        if not result.success:
            return replan_from_failure(step, result, steps)  # 失败时局部重规划
        results.append(result)
    return results
```

**适用场景**：步骤之间有明确的先后依赖，比如"先读取文件 → 再分析内容 → 再生成报告"。这类任务的关键风险点在于**中途失败后怎么办**——好的线性分解要支持从失败步骤重新规划，而不是推倒重来。

**不适用场景**：子任务之间相互独立、可以并行执行的情况，线性分解会浪费时间。

## 三、模式二：树形分解（Hierarchical Decomposition）

复杂任务先拆成几个大模块，每个大模块再递归拆成更小的子任务，形成树状结构：

```python
def hierarchical_plan(goal, depth=0, max_depth=3):
    if depth >= max_depth or is_atomic_task(goal):
        return {"task": goal, "children": []}

    sub_goals = llm_call(f"""
    将以下目标拆解为 2-5 个高层子目标（不要拆得太细，每个子目标应该还需要进一步分解）：
    {goal}
    """)

    return {
        "task": goal,
        "children": [hierarchical_plan(sg, depth + 1, max_depth) for sg in sub_goals]
    }
```

执行时按叶子节点（最底层、不可再分的原子任务）从左到右或按依赖顺序执行，父节点的"完成"取决于所有子节点完成。

**适用场景**：任务本身有天然的层级结构，比如"开发一个功能"可以拆成"后端 API"、"前端页面"、"测试用例"三个模块，每个模块再往下拆。树形结构让 Agent 可以在某个分支局部重试，不影响其他分支。

**工程注意点**：递归深度要设上限（示例里的 `max_depth`），否则模型可能无限细分下去；也需要设置"原子任务"的判断标准（`is_atomic_task`），常见做法是用 token 预估或明确的启发式规则（比如"预计一次工具调用能完成"就算原子任务）。

## 四、模式三：动态重规划（Dynamic Replanning）

前两种模式都是"先规划完，再执行"，但很多真实任务在执行过程中会暴露新信息，导致最初的计划不再适用。动态重规划的思路是：**每执行完一步，都重新评估计划是否需要调整**。

```python
def dynamic_plan_and_execute(goal):
    plan = generate_initial_plan(goal)
    completed = []

    while plan:
        next_step = plan[0]
        result = execute_step(next_step, context=completed)
        completed.append(result)

        # 关键区别：每步之后重新评估剩余计划
        should_replan = llm_call(f"""
        原目标：{goal}
        已完成：{completed}
        当前剩余计划：{plan[1:]}
        基于已完成步骤的实际结果，剩余计划是否需要调整？
        如果不需要调整，返回原计划；如果需要，返回调整后的计划。
        """)
        plan = should_replan

    return completed
```

**适用场景**：探索性、结果不可预测的任务，比如"调试一个报错"——你事先不知道根因是什么，第一步的排查结果会决定第二步该往哪个方向查。这类任务如果用固定的线性/树形计划，很容易在计划和现实脱节时卡住。

**代价**：每一步都多一次"是否需要重规划"的模型调用，成本和延迟都比固定计划高。只在任务真的具有强不确定性时才值得用这个模式。

## 五、三种模式的选型对照表

| 模式 | 适用信号 | 主要风险 | 相对成本 |
|---|---|---|---|
| 线性分解 | 步骤顺序固定，依赖关系简单 | 中途失败恢复设计不当会推倒重来 | 低 |
| 树形分解 | 任务有天然模块划分 | 递归深度失控、原子任务判断不准 | 中 |
| 动态重规划 | 结果不可预测，需要探索 | 每步都要重规划，成本和延迟高 | 高 |

实践中很多 Agent 框架是**混合使用**：顶层用树形分解划分模块，模块内部对于探索性强的部分（比如调试）用动态重规划，其余部分用线性分解——不需要在三者中选择"唯一正确"的模式。

## 六、和错误恢复、工具设计的关系

任务分解不是孤立的设计决策，它和另外两个问题紧密相关：

- 子任务失败后怎么办，属于**错误恢复机制**的范畴，参考[AI Agent 错误恢复机制设计](/blog/ai-agent-error-recovery/)
- 子任务粒度也受限于**可用工具的能力边界**——如果工具本身设计得太粗放，任务分解得再细也没用，参考[AI Agent 工具集合的设计原则](/blog/ai-agent-tool-design/)

## 七、常见问题

**Q：任务分解应该由哪个模型来做？拆解和执行用同一个模型吗？**
可以用同一个模型的不同调用，也可以用更强的模型做拆解（因为拆解需要更强的规划能力）、用更便宜的模型执行具体子任务（因为执行阶段任务已经很明确）。后者是常见的成本优化手段。

**Q：怎么判断一次任务分解"拆得好不好"？**
观察执行阶段的失败率和重规划频率。如果单个子任务经常失败，说明粒度太粗；如果重规划频繁触发,说明最初的计划质量不高或任务本身不确定性太强，更适合动态重规划模式。

**Q：需要给 Agent 展示完整的计划树吗？**
生产环境建议展示，即使是简化版——用户能看到 Agent 在做什么、卡在哪一步，出问题时排查会容易很多，这也是可观测性设计的一部分。

## 八、相关阅读

- [AI Agent 工具集合的设计原则](/blog/ai-agent-tool-design/)
- [AI Agent 错误恢复机制设计：让 Agent 在失败中自我修复](/blog/ai-agent-error-recovery/)
- [AI Agent 记忆系统设计：四种模式与工程实践](/blog/ai-agent-memory-design/)
- [Claude Code Subagent 实战：定义、用法与最佳实践](/blog/claude-code-subagent-practice/)

搭建多步骤 Agent 时需要稳定调用多个模型？[YoTradeApi](https://yotradeapi.com) 提供 Claude、GPT 等主流模型的统一中转接口，一个 API Key 按量计费，方便按任务粒度灵活切换模型。
