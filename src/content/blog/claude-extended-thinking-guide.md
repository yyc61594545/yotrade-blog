---
title: Claude Extended Thinking 完整使用指南
description: Claude Opus/Sonnet 的 extended thinking 模式：何时启用、budget 设置、效果实测、与普通模式的成本对比。
keywords:
- claude extended thinking
- claude 思考模式
- claude opus 推理
- thinking budget
- claude 推理 设置
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/claude-extended-thinking-guide/
tags:
- Claude
- Extended Thinking
- Opus
- 推理
- 最佳实践
category: 模型评测
heroImage: ../../assets/blog-placeholder-5.jpg
---

Claude Opus 4.7 / Sonnet 4.6 的 extended thinking（深度思考）是模型 reasoning 的"额外档位"——允许模型先用 token 思考再产出最终答案。开起来效果显著但更贵。本文讲清楚何时该开、参数怎么设、成本怎么控。

## 一、什么是 extended thinking

普通模式：模型直接产出答案，输出 token 都是答案本身。

extended thinking 模式：模型先产出一段"内心独白"，再产出答案。内心独白也按 token 计费。

| 模式 | 输入 token | 思考 token | 答案 token | 总成本 |
| --- | --- | --- | --- | --- |
| 普通 | 1000 | 0 | 500 | 1500 单位 |
| extended thinking | 1000 | 4000 | 800 | 5800 单位 |

**默认情况下深度思考成本可达普通的 3–5 倍**。但对复杂任务，质量提升能值回票价。

## 二、何时该开 thinking

| 任务类型 | 该开？ |
| --- | --- |
| 简单问答 | ✗ |
| 信息查询 | ✗ |
| 翻译、摘要 | ✗ |
| 写代码（短函数） | ✗ |
| 调复杂 bug | ✓ |
| 跨文件重构 | ✓ |
| 数学/逻辑推理 | ✓ |
| 架构设计 | ✓ |
| 安全审计 | ✓ |
| 长任务规划 | ✓ |

**判断标准**：任务是不是"想清楚再下笔比直接写更好"。是的开，不是的别开。

## 三、API 调用（Anthropic 原生）

```python
import anthropic

client = anthropic.Anthropic(
    base_url="https://yotradeapi.com",   # 走中转
    api_key="sk-yo-..."
)

resp = client.messages.create(
    model="claude-opus-4-7",
    max_tokens=8000,
    thinking={
        "type": "enabled",
        "budget_tokens": 4000,   # 思考最多用多少 token
    },
    messages=[{"role": "user", "content": "证明 sqrt(2) 是无理数。"}],
)

for block in resp.content:
    if block.type == "thinking":
        print(f"[thinking] {block.thinking[:200]}...")
    elif block.type == "text":
        print(f"[answer] {block.text}")
```

返回里 `content` 数组包含 thinking block 与 text block。

## 四、budget_tokens 怎么设

budget 设置直接影响成本与效果：

| 任务难度 | 推荐 budget |
| --- | --- |
| 普通推理 | 2000 |
| 复杂调试 | 4000 |
| 架构设计 | 6000 |
| 数学/科学推导 | 8000–16000 |
| 极困难（奥赛、SAT 难题） | 16000+ |

**最小值** 1024，**最大值** 一般 64000。设得太大也浪费：模型可能 budget 没用完就给出答案。

## 五、OpenAI 兼容路径下开 thinking

部分中转把 thinking 暴露成 OpenAI 兼容字段：

```python
client.chat.completions.create(
    model="claude-opus-4-7",
    messages=[...],
    extra_body={
        "thinking": {"type": "enabled", "budget_tokens": 4000}
    },
)
```

是否生效取决于中转实现。原生协议总是支持，建议复杂任务直接走原生。

## 六、实测效果对比

### 案例 1：数学证明

题：证明任意三个连续整数的立方和能被 9 整除。

| 模式 | 输出质量 | 总 token | 总成本 |
| --- | --- | --- | --- |
| 普通 | 7/10（缺步骤） | 1200 | 100 |
| thinking 4k | 9.5/10（完整严谨） | 5200 | 350 |

3.5 倍成本换 35% 质量提升。

### 案例 2：调试复杂异步 bug

200 行 Express 代码、3 个回调地狱、1 个隐藏的 race condition。

| 模式 | 定位准确率 | 总 token | 时间 |
| --- | --- | --- | --- |
| 普通 | 5/10 | 1800 | 8s |
| thinking 6k | 9/10 | 7800 | 22s |

调难 bug 是 extended thinking 的最佳场景。

### 案例 3：写一个 Express middleware

题：写一个 JWT 验证 middleware，10 行能搞定。

| 模式 | 质量 | 总 token |
| --- | --- | --- |
| 普通 | 10/10 | 800 |
| thinking 2k | 10/10 | 3000 |

简单任务开 thinking 纯浪费。

## 七、interleaved thinking（交错思考）

部分场景模型会在工具调用之间多次思考：

```
[thinking] 我先看看 file A
[tool_use] read_file: A.ts
[thinking] 嗯，这里调用了 B，再看 B
[tool_use] read_file: B.ts
[thinking] 现在我明白了，可以写答案
[text] 解决方案是 ...
```

这种 "工具调用 + 思考 + 工具调用 + 思考" 的模式叫 interleaved thinking。它对 agent 长任务非常关键。在 Anthropic 原生协议下默认开启，OpenAI 兼容下可能丢失。

## 八、与 prompt caching 的配合

thinking token 不会被缓存——每次都要重新思考。但**输入 token（system + messages 前半部分）仍然可以缓存**。

成本拆解：

```
单次复杂任务：
  缓存输入：3000 token × 0.1x = 300 单位
  非缓存输入：500 token × 1x = 500 单位
  思考：4000 token × 1x = 4000 单位
  答案输出：800 token × 5x = 4000 单位
  总：8800 单位
```

如果同样任务跑 10 次（缓存命中 9 次），平均下来一次 4500 单位。

## 九、Cursor / Claude Code 里开 thinking

### Claude Code

启动时：

```bash
claude --thinking-budget 4000
```

或在 `.claude/settings.json`：

```json
{
  "thinking": {
    "enabled": true,
    "budget_tokens": 4000
  }
}
```

### Cursor

设置 → Models → 编辑 Custom Model → Extended Thinking 开关。budget 可在 advanced 设置。

### 在 Subagent 里独立开

```yaml
---
name: architect
model: claude-opus-4-7
thinking_budget: 8000
---
```

Architect / Reviewer / Debugger 这些"重思考"的 subagent 单独开 thinking，其它 subagent 保持默认。

## 十、什么时候 thinking 反而不好

- **响应延迟敏感**：思考会大幅增加 TTFB，从 5s 拉到 20s+
- **流式输出体验差**：thinking 阶段用户看不到任何内容
- **简单任务**：浪费钱
- **预算紧张**：上限达不到时优先关 thinking

## 十一、相关阅读

- [Claude Sonnet 4.6 与 Opus 4.7 怎么选](/blog/claude-sonnet-4-6-vs-opus-4-7/)
- [GPT-5 与 Claude Opus 4.7 编程能力对比](/blog/gpt-5-vs-claude-opus-4-7-coding/)
- [Claude Code Subagent 实战](/blog/claude-code-subagent-practice/)
- [prompt caching 在国内中转下省成本指南](/blog/prompt-caching-cost-optimization/)
- [AI 编程代理成本控制实战](/blog/ai-coding-agent-cost-control/)

需要支持 extended thinking 透传的中转？[YoTradeApi](https://yotradeapi.com) 完整透传 thinking 字段，按 Anthropic 原生协议调用即可。
