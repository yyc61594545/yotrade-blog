---
title: LangChain 中文实战：用中转接入构建 Agent
description: 用 LangChain 在国内通过中转构建 LLM Agent 的实战指南，含 ChatOpenAI 配置、Tools、Memory、LCEL 链式调用、与 LangGraph 的对比。
keywords:
- langchain 中文
- langchain 国内
- langchain agent
- langchain 中转
- langchain 教程
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/langchain-cn-tutorial/
tags:
- LangChain
- Agent
- Python
- 框架
- 教程
category: 工程实战
heroImage: ../../assets/blog-placeholder-4.jpg
---

# LangChain 中文实战：用中转接入构建 Agent

LangChain 是 LLM 应用最流行的开发框架。优势是抽象成熟、生态完整；劣势是 API 改动频繁、文档复杂。本文聚焦"用国内中转通过 LangChain 构建 Agent"的最小可用路径。

## 一、安装

```bash
pip install -U langchain langchain-openai langchain-anthropic langchain-community
```

## 二、最简调用

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="claude-sonnet-4-6",
    api_key="sk-yo-...",
    base_url="https://yotradeapi.com/v1",
    temperature=0.2,
)

resp = llm.invoke([
    {"role": "system", "content": "你是中文程序员助手。"},
    {"role": "user", "content": "解释 LRU 缓存。"},
])
print(resp.content)
```

LangChain 的 ChatOpenAI 兼容 OpenAI 协议，**只需要改 base_url 就能用 Claude 系列**。

## 三、走 Anthropic 原生

如果你要用 Claude 独家特性（extended thinking、cache_control）：

```python
from langchain_anthropic import ChatAnthropic

llm = ChatAnthropic(
    model="claude-sonnet-4-6",
    api_key="sk-yo-...",
    base_url="https://yotradeapi.com",   # 注意不带 /v1
    max_tokens=2000,
)
```

## 四、LCEL：链式调用

LangChain Expression Language 是当前主流写法：

```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

llm = ChatOpenAI(model="claude-sonnet-4-6", base_url="https://yotradeapi.com/v1", api_key="sk-yo-...")

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是 {role}。"),
    ("user", "{question}"),
])

chain = prompt | llm | StrOutputParser()

print(chain.invoke({"role": "数学老师", "question": "解释贝叶斯定理"}))
```

`|` 运算符把组件串起来。`StrOutputParser` 把 message 转 string。

## 五、流式输出

```python
for chunk in chain.stream({"role": "...", "question": "..."}):
    print(chunk, end="", flush=True)
```

LangChain 内部处理 SSE 解析，你只看到 string chunk。

## 六、Tool Use

```python
from langchain_core.tools import tool

@tool
def get_weather(city: str) -> str:
    """获取一个中国城市的天气"""
    return f"{city} 25 度晴"

@tool
def calculator(expr: str) -> float:
    """计算数学表达式"""
    return eval(expr)

llm_with_tools = llm.bind_tools([get_weather, calculator])

resp = llm_with_tools.invoke("北京今天什么天气？算一下 137 * 256")
for call in resp.tool_calls:
    print(call["name"], call["args"])
```

`@tool` 装饰器把函数变成 LLM 可调用的 tool。LangChain 自动生成 schema。

## 七、Agent（用 LangGraph 替代旧 AgentExecutor）

新版本推荐用 LangGraph 而不是老的 AgentExecutor：

```bash
pip install langgraph
```

```python
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="claude-sonnet-4-6", base_url="https://yotradeapi.com/v1", api_key="sk-yo-...")
tools = [get_weather, calculator]
agent = create_react_agent(llm, tools)

for msg in agent.stream(
    {"messages": [{"role": "user", "content": "北京天气怎么样？再算 137*256"}]},
    stream_mode="values",
):
    msg["messages"][-1].pretty_print()
```

ReAct agent 自动：

1. 决定要调哪些工具
2. 调用、看结果
3. 推理下一步
4. 直到给出最终答案

## 八、Memory

```python
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()
agent = create_react_agent(llm, tools, checkpointer=memory)

config = {"configurable": {"thread_id": "alice"}}

agent.invoke({"messages": [{"role": "user", "content": "我叫张三"}]}, config=config)
agent.invoke({"messages": [{"role": "user", "content": "我叫什么？"}]}, config=config)
# → 我记得你叫张三
```

按 `thread_id` 隔离会话。生产用 `PostgresSaver` 持久化。

## 九、Prompt Caching（Anthropic 原生）

```python
from langchain_anthropic import ChatAnthropic

llm = ChatAnthropic(
    model="claude-sonnet-4-6",
    base_url="https://yotradeapi.com",
    api_key="sk-yo-...",
    extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
)

response = llm.invoke([
    {
        "role": "system",
        "content": [{
            "type": "text",
            "text": "长 system prompt...",
            "cache_control": {"type": "ephemeral"},
        }],
    },
    {"role": "user", "content": "..."},
])

print(response.response_metadata["usage"])
# 看 cache_read_input_tokens / cache_creation_input_tokens
```

## 十、Embedding 与 RAG

```python
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

embedding = OpenAIEmbeddings(
    model="text-embedding-3-large",
    base_url="https://yotradeapi.com/v1",
    api_key="sk-yo-...",
)

vectorstore = Chroma.from_texts(
    texts=["文档 1...", "文档 2..."],
    embedding=embedding,
    persist_directory="./chroma_db",
)

retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
docs = retriever.invoke("关键词查询")
```

## 十一、避坑

1. **版本兼容**：LangChain 0.1 → 0.3 接口变了，跟着官方 migration guide
2. **`base_url` vs `openai_api_base`**：新版 `base_url`，老版 `openai_api_base`。统一用 `base_url`
3. **`api_key`**：默认读环境变量 `OPENAI_API_KEY`，要么设它，要么手动传
4. **stream 在 chain 里**：`chain.stream(...)`，不是 `chain.invoke(...)` 加参数
5. **Tool 描述质量决定调用准确度**：写好 docstring

## 十二、LangChain vs LangGraph vs 裸 SDK

| 维度 | 裸 SDK | LangChain | LangGraph |
| --- | --- | --- | --- |
| 学习曲线 | 低 | 中 | 高 |
| 控制粒度 | 极强 | 中 | 强 |
| 状态管理 | 自己 | Memory | Checkpointer |
| 多步 Agent | 自己拼 | AgentExecutor（deprecated） | 原生 |
| 生态 | 大 | 极大 | 在长 |

推荐：

- **简单脚本**：裸 SDK
- **常规 LLM 应用**：LangChain（不上 Agent）
- **复杂 Agent**：LangGraph
- **生产高定制**：自己写 + 适当借鉴

## 十三、何时不用 LangChain

- 简单的 chat / batch 任务（OpenAI SDK 够）
- 严格要求依赖小（LangChain 依赖几十个包）
- 性能敏感（LangChain 抽象层有开销）
- 团队不熟悉 LangChain 生态

## 十四、相关阅读

- [OpenAI SDK base_url 国内配置实战](/blog/openai-sdk-base-url-cn/)
- [Python 异步并发调用 LLM API 实战](/blog/python-async-llm-client/)
- [中文 RAG 工程实战](/blog/rag-cn-best-practices/)
- [Embeddings API 国内对比](/blog/embeddings-api-cn-comparison/)
- [LiteLLM 自部署 LLM 网关](/blog/litellm-cn-gateway-self-host/)

LangChain `base_url` 指向 [YoTradeApi](https://yotradeapi.com/register) 即可在国内稳定调用 Claude / GPT / Gemini 全家。
