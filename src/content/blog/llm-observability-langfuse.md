---
title: LLM 可观测性实战：Langfuse 自部署完整指南
description: 用 Langfuse 在国内自部署 LLM 应用可观测性平台：tracing、用量、成本、调试、用户反馈一站搞定，含 Docker 部署与接入示例。
keywords:
- llm 可观测
- langfuse 部署
- llm 监控
- llm tracing
- langfuse 国内
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/llm-observability-langfuse/
tags:
- Langfuse
- 可观测性
- 监控
- 自托管
- 工程实战
category: 工程实战
heroImage: ../../assets/blog-placeholder-4.jpg
---

# LLM 可观测性实战：Langfuse 自部署完整指南

LLM 应用上线后最难的不是写代码，是**回答"这个用户为什么看到了这个回答"**。Langfuse 把这件事工程化了。本文给国内自部署 + 实战接入。

## 一、Langfuse 是什么

简单理解：

```
你的 LLM 应用 → Langfuse SDK → Langfuse 服务（你部署）
                                ↓
                              UI Dashboard
                              （trace / 用量 / 成本 / 反馈）
```

它给你：

- **Trace**：每次请求的完整调用链（prompt + LLM + tool + response）
- **Usage**：按用户 / 项目 / 模型聚合
- **Cost**：自动计算每条请求的成本
- **Eval**：跑离线评估
- **Dataset**：管理测试集

## 二、Docker 部署

```yaml
# docker-compose.yml
services:
  langfuse-server:
    image: langfuse/langfuse:latest
    ports:
      - "3000:3000"
    environment:
      DATABASE_URL: postgresql://postgres:postgres@db:5432/postgres
      NEXTAUTH_SECRET: $(openssl rand -hex 32)
      NEXTAUTH_URL: http://localhost:3000
      SALT: $(openssl rand -hex 32)
      TELEMETRY_ENABLED: "false"
    depends_on: [db]

  db:
    image: postgres:16
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: postgres
    volumes:
      - langfuse-db:/var/lib/postgresql/data

volumes:
  langfuse-db:
```

```bash
docker-compose up -d
```

访问 `http://localhost:3000`，注册第一个账号自动成为 admin。

## 三、创建项目 + 拿 Key

UI → New Project → 创建。Project 设置里拿到：

- `LANGFUSE_PUBLIC_KEY`
- `LANGFUSE_SECRET_KEY`
- `LANGFUSE_HOST = http://localhost:3000`

## 四、Python SDK 接入

```bash
pip install langfuse
```

```python
import os
from langfuse import Langfuse
from openai import OpenAI

os.environ["LANGFUSE_PUBLIC_KEY"] = "pk-..."
os.environ["LANGFUSE_SECRET_KEY"] = "sk-..."
os.environ["LANGFUSE_HOST"] = "http://localhost:3000"

langfuse = Langfuse()
client = OpenAI(api_key="sk-yo-...", base_url="https://yotradeapi.com/v1")

# 用装饰器自动追踪
from langfuse.openai import openai as lf_openai

client = lf_openai.OpenAI(api_key="sk-yo-...", base_url="https://yotradeapi.com/v1")

resp = client.chat.completions.create(
    model="claude-sonnet-4-6",
    messages=[{"role": "user", "content": "..."}],
)
```

仅替换 import，**所有调用自动被记录**。UI 里能看到每条 trace。

## 五、手动 trace（精细控制）

```python
from langfuse import Langfuse

langfuse = Langfuse()

trace = langfuse.trace(
    name="user-question",
    user_id="alice",
    session_id="session-123",
    metadata={"page": "/help"},
)

# 步骤 1：检索
retrieval = trace.span(name="retrieve", input={"query": "..."})
docs = vector_search(...)
retrieval.end(output={"count": len(docs)})

# 步骤 2：LLM
generation = trace.generation(
    name="answer",
    model="claude-sonnet-4-6",
    input=messages,
)
resp = client.chat.completions.create(...)
generation.end(
    output=resp.choices[0].message.content,
    usage={"input": resp.usage.prompt_tokens, "output": resp.usage.completion_tokens},
)

trace.update(output={"final": resp.choices[0].message.content})
```

完整 RAG 链路一目了然。

## 六、Node.js SDK

```bash
npm install langfuse
```

```ts
import { Langfuse } from "langfuse";
import OpenAI from "openai";
import { observeOpenAI } from "langfuse";

const langfuse = new Langfuse();
const openai = observeOpenAI(
  new OpenAI({ apiKey: "sk-yo-...", baseURL: "https://yotradeapi.com/v1" }),
);

const resp = await openai.chat.completions.create({ ... });
```

## 七、用户反馈

```python
trace.score(name="user_feedback", value=1, comment="great answer")
trace.score(name="user_feedback", value=-1, comment="wrong, hallucinated")
```

UI 里能按反馈筛选，看"差评回答"集中在什么 prompt / 模型上。

## 八、成本追踪

Langfuse 内置 LLM 价格表（OpenAI / Anthropic / Gemini 等）。trace 自动算成本。

UI Dashboard：

- 总花费（日 / 周 / 月）
- 按模型分布
- 按用户分布
- 按 endpoint 分布

异常突升立刻能看到。

## 九、Dataset + Eval

```python
# 创建测试集
dataset = langfuse.create_dataset(name="qa-benchmark")
langfuse.create_dataset_item(
    dataset_name="qa-benchmark",
    input={"question": "什么是 LRU 缓存？"},
    expected_output={"contains": ["缓存", "least recently used"]},
)

# 跑评估
for item in langfuse.get_dataset("qa-benchmark").items:
    trace = langfuse.trace(name="eval-run", input=item.input)
    out = client.chat.completions.create(
        model="claude-sonnet-4-6",
        messages=[{"role": "user", "content": item.input["question"]}],
    ).choices[0].message.content
    
    # 自动评分
    score = 1.0 if all(k in out for k in item.expected_output["contains"]) else 0.0
    trace.score(name="auto-eval", value=score)
```

跑完 UI 里直接看到测试集的整体通过率。详见 [LLM 评估实战](/blog/llm-evaluation-cn-guide/)。

## 十、Prompt 管理

Langfuse 可以管理 prompt 版本：

```python
prompt = langfuse.create_prompt(
    name="qa-system-prompt",
    prompt="你是中文助手。简洁回答。",
    labels=["production"],
)

# 应用时拉最新版
p = langfuse.get_prompt("qa-system-prompt")
print(p.prompt)
```

**不用改代码就能更新 prompt**——上线、回滚、A/B 都在 UI。

## 十一、与中转的配合

Langfuse 自己只是观察平台，不影响 LLM 调用。中转处理实际 API，Langfuse 记录每次调用细节。

唯一注意：**敏感 prompt 不要上 Langfuse**（除非自部署完全内网）。

## 十二、生产部署建议

1. **托管 DB**：用 RDS / Neon 不用 docker postgres
2. **TLS**：内部也 HTTPS
3. **Auth SSO**：接公司 OAuth
4. **Retention**：按合规设定数据保留期
5. **备份**：定期 dump
6. **高可用**：3 副本前面挂 LB

## 十三、Langfuse vs Helicone vs LangSmith

| 维度 | Langfuse | Helicone | LangSmith |
| --- | --- | --- | --- |
| 部署 | ✓ 自托管 | ✓ 自托管 | SaaS 为主 |
| Trace | ✓ | ✓ | ✓ |
| 评估 | ✓ | 中 | ✓ |
| Dataset | ✓ | 中 | ✓ |
| Prompt 管理 | ✓ | 弱 | ✓ |
| 开源 | ✓ | ✓ | ✗ |

**国内 + 数据合规 + 自托管**：Langfuse 是最佳选择。

## 十四、相关阅读

- [LLM 评估实战](/blog/llm-evaluation-cn-guide/)
- [AI 编程代理成本控制实战](/blog/ai-coding-agent-cost-control/)
- [LiteLLM 自部署 LLM 网关](/blog/litellm-cn-gateway-self-host/)
- [LangChain 中文实战](/blog/langchain-cn-tutorial/)
- [AI API 中转的安全与合规边界](/blog/api-relay-security-compliance/)

Langfuse + [YoTradeApi](https://yotradeapi.com/register) 组合：中转管 API 路由，Langfuse 管观察。两侧用量数据可交叉校对。
