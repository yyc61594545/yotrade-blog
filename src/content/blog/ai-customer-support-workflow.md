---
title: 用 AI 做客服自动化的工程化方案
description: 构建客户支持 AI 系统的完整工程化方案：意图识别、RAG 知识库、工具调用、人机协作、质量监控、合规边界。
keywords:
- ai 客服
- ai 客户支持
- llm 客服
- chatgpt 客服
- 智能客服 实战
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/ai-customer-support-workflow/
tags:
- 客服
- Agent
- RAG
- 业务应用
- 工程实战
category: 工程实战
heroImage: ../../assets/blog-placeholder-5.jpg
---

# 用 AI 做客服自动化的工程化方案

把 AI 接入客服是商业化最快见效的方向之一。但做得不好就是"机器人客服赶走真人客户"。本文给一份能上线、能扩展的工程化方案。

## 一、整体架构

```
用户消息
  ↓
意图识别（小模型）
  ↓
┌─────────────────────────────────┐
│ Router                          │
├─────────────────────────────────┤
│ FAQ → RAG 答（Sonnet/Haiku）    │
│ 查订单 → tool call + 答（Sonnet）│
│ 投诉 → 升级人工                  │
│ 闲聊 → 简短回 + 引导回正题       │
└─────────────────────────────────┘
  ↓
评估 + 反馈
  ↓
回复用户
```

## 二、意图识别（L1）

用便宜模型先 triage：

```python
intent_prompt = """
判断用户消息的类别，只输出类别名：

类别：
- faq: 关于产品 / 政策 / 服务的一般问题
- order: 查订单 / 退款 / 物流
- complaint: 投诉 / 不满
- chitchat: 闲聊
- other: 其它

消息：{message}

输出（只一个词）：
"""

resp = client.chat.completions.create(
    model="claude-haiku-4-5",
    messages=[{"role": "user", "content": intent_prompt.format(message=user_msg)}],
    max_tokens=10,
    temperature=0.0,
)
intent = resp.choices[0].message.content.strip()
```

便宜 + 快。结合 [结构化输出](/blog/structured-output-llm-guide/) 更稳。

## 三、FAQ：RAG

把知识库做成 RAG：

```python
def faq_answer(question, knowledge_base):
    # 1. 检索
    docs = vector_search(question, knowledge_base, top_k=5)
    
    # 2. rerank
    docs = rerank(question, docs, top_n=3)
    
    # 3. 生成
    resp = client.chat.completions.create(
        model="claude-sonnet-4-6",
        messages=[
            {"role": "system", "content": f"""你是客服。只根据资料回答。
如果资料没答案，明确说"我帮你转给人工"。

资料：
{format_docs(docs)}"""},
            {"role": "user", "content": question},
        ],
        temperature=0.3,
    )
    return resp.choices[0].message.content
```

详见 [中文 RAG 工程实战](/blog/rag-cn-best-practices/)。

## 四、Tool Call：业务查询

```python
@tool
async def lookup_order(order_id: str, user_id: str) -> dict:
    """查订单。仅本人订单可查。"""
    order = await db.fetch_order(order_id)
    if order.user_id != user_id:
        raise PermissionError("not your order")
    return order.to_dict()

@tool
async def refund_request(order_id: str, reason: str) -> dict:
    """提交退款请求。"""
    if not validate(reason):
        return {"ok": False, "error": "reason too vague"}
    return await create_refund(order_id, reason, status="pending_human_approval")
```

**业务工具一定要鉴权 + 审计**：

- 用户 id 必须从 session 拿，不能让 LLM 自己填
- 涉及钱的操作 status=pending，等人工确认
- 所有 tool call 写审计日志

## 五、Router（agent 形态）

```python
agent = Agent(
    name="support",
    instructions="""你是客服。可用工具：lookup_order / refund_request / kb_search。

规则：
- 涉及订单一定要 user_id（从 context 拿）
- 退款 < ¥100 自动处理，≥ ¥100 转人工
- 不知道答案的不要编，转人工
- 中文回复，简洁友好

特殊场景：
- 投诉 → 调用 escalate_human()
- 涉及发票 / 合规 / 法律 → escalate_human()
""",
    tools=[lookup_order, refund_request, kb_search, escalate_human],
)
```

详见 [OpenAI Agents SDK 国内接入](/blog/openai-agents-sdk-cn/) 与 [Claude Agent SDK 国内接入](/blog/claude-agent-sdk-cn/)。

## 六、人机协作

明确边界：

| 场景 | AI | 转人工 |
| --- | --- | --- |
| 政策 / FAQ | ✓ | |
| 查订单状态 | ✓ | |
| 小额退款 | ✓ | |
| 大额退款 / 升级 | | ✓ |
| 投诉 / 法律 | | ✓ |
| 用户明确要求"找人" | | ✓ |
| AI 不确定 / 失败 3 次 | | ✓ |

`escalate_human()` tool 把对话转给人工，人工看到完整 AI 历史 + 用户上下文。

## 七、监控指标

| 指标 | 目标 |
| --- | --- |
| 自动解决率 | > 60% |
| 用户满意度 | > 4.0 / 5 |
| 转人工率 | < 35% |
| 首响应延迟 | < 3s |
| 错误率 | < 2% |
| 单 conversation 成本 | < ¥0.5 |

详见 [LLM 评估实战](/blog/llm-evaluation-cn-guide/) 与 [LLM 可观测性 Langfuse](/blog/llm-observability-langfuse/)。

## 八、用户反馈

每条 AI 回复带反馈按钮：

```tsx
<div>
  <p>{answer}</p>
  <button onClick={() => feedback(1)}>👍</button>
  <button onClick={() => feedback(-1)}>👎</button>
</div>
```

后台聚合：

- 👎 集中的问题 → 看是不是 KB 缺
- 👎 集中的模型 → 评估升级 / 切换
- 👎 集中的功能 → 看是不是产品本身问题

## 九、对话保持与多轮

```python
# Redis 存对话历史
async def chat(user_id, message):
    history = await redis.get(f"chat:{user_id}") or "[]"
    history = json.loads(history)
    
    history.append({"role": "user", "content": message})
    
    # 控制上下文长度
    history = trim_messages(history, max_tokens=180_000)
    
    resp = await agent.run(history, context={"user_id": user_id})
    
    history.append({"role": "assistant", "content": resp})
    await redis.setex(f"chat:{user_id}", 3600, json.dumps(history))
    
    return resp
```

会话超时 1 小时清理。**长会话定期 compact 节省 token**。

## 十、合规与边界

- ✗ 不替用户做有法律风险的决策（退保险 / 法律咨询）
- ✗ 不输出敏感个人信息（即使用户问的是自己）
- ✗ 不答与产品无关的问题（引导回正题）
- ✓ 明确标记"AI 回答，准确度不保证"（部分场景）
- ✓ 涉及钱要二次确认 + 人工 review

详见 [AI API 中转的安全与合规边界](/blog/api-relay-security-compliance/)。

## 十一、成本估算

| 量 | 估算 |
| --- | --- |
| 1k 对话 / 日 | $5–15 / 月 |
| 10k 对话 / 日 | $50–150 / 月 |
| 100k 对话 / 日 | $500–1500 / 月 |

加 prompt caching：

- 长 system prompt 缓存命中 → 输入费用 ↓ 80%
- 业务 SOP 在 system 里写好别动

## 十二、避坑

- ❌ 一开始全 AI（不要，先 50% AI + 50% 人工跑一阵）
- ❌ 不留转人工出口
- ❌ 让 AI 自己决定退款额度上限
- ❌ AI 答完不收反馈（看不到问题）
- ❌ 一个 system prompt 包打天下

## 十三、相关阅读

- [中文 RAG 工程实战](/blog/rag-cn-best-practices/)
- [OpenAI Agents SDK 国内接入](/blog/openai-agents-sdk-cn/)
- [Claude Agent SDK 国内接入](/blog/claude-agent-sdk-cn/)
- [LLM 可观测性 Langfuse](/blog/llm-observability-langfuse/)
- [LLM 评估实战](/blog/llm-evaluation-cn-guide/)
- [LLM 流式 UI 实战模式](/blog/llm-streaming-ui-patterns/)

客服系统大量调用，配 [YoTradeApi](https://yotradeapi.com/register) 中转 + 独立业务 Key + 日预算上限，控成本 + 监控。
