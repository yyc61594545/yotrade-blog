---
title: OpenAI Batch API 节省 50% 成本实战
description: 详解 OpenAI Batch API 的使用方法、适用场景与最佳实践，帮助开发者将推理成本降低 50%，大幅提升批量任务效率。
keywords:
  - OpenAI Batch API
  - 批量推理
  - AI API 成本优化
  - GPT-4o 批处理
  - OpenAI 节省费用
pubDate: '2026-05-25'
updatedDate: '2026-05-25'
canonical: https://blog.yotradeapi.com/blog/openai-batch-api-cn-guide/
tags:
  - OpenAI
  - 成本优化
  - 批处理
  - API
category: 技术深度
heroImage: ../../assets/blog-placeholder-2.jpg
---

OpenAI 在 2024 年推出的 Batch API 允许开发者以 **50% 的折扣价格**处理大批量异步请求，换取最长 24 小时的处理窗口。对于不需要实时响应的场景——数据标注、大规模文本分类、离线报告生成——这是目前性价比最高的方案之一。本文将从原理到实战，带你掌握 Batch API 的核心用法。

## 一、Batch API 的工作原理与定价

Batch API 与普通同步 API 的核心区别在于**异步队列模型**：

1. 你把所有请求打包成一个 JSONL 文件上传
2. OpenAI 在后台（通常几分钟到几小时内）批量处理
3. 处理完毕后，你通过轮询或 Webhook 获取结果文件

**定价对比（近似值，以公开定价为参考）：**

| 模型 | 同步 API 输入价格 | Batch API 输入价格 | 折扣 |
|------|-----------------|-------------------|------|
| gpt-4o | $2.50/1M tokens | $1.25/1M tokens | 50% |
| gpt-4o-mini | $0.150/1M tokens | $0.075/1M tokens | 50% |
| gpt-4-turbo | $10.00/1M tokens | $5.00/1M tokens | 50% |
| text-embedding-3-large | $0.130/1M tokens | $0.065/1M tokens | 50% |

> **注意**：以上价格仅作参考，实际价格以 OpenAI 官方定价页面为准，可能随时调整。

Batch API 还有一个重要限制：每个 batch 的请求数上限通常为 50,000 条，总 token 数上限约为 100M tokens，且处理窗口为 **24 小时内完成**（通常远快于此）。

## 二、哪些场景适合 Batch API

并非所有任务都适合批处理模式，适合的场景有以下特征：

**强烈推荐：**
- **大规模数据标注**：给数十万条用户评论打情感标签
- **离线 SEO 内容生成**：批量生成产品描述、元标签
- **定期报告**：每晚跑一次摘要任务，第二天早上看结果
- **嵌入（Embedding）计算**：文档库向量化，不需要实时
- **评估/测试集推理**：对 LLM 进行基准测试时的大批量推理

**不适合的场景：**
- 用户直接等待结果的交互式聊天
- 需要立即使用结果的流水线（如 RAG 的实时检索阶段）
- 延迟敏感的 API 服务

判断标准：**如果结果可以延迟 1–24 小时，就值得用 Batch API**。

## 三、快速上手：Python 实战示例

以下以 Python + `openai` SDK 为例，演示完整的 Batch API 工作流。

### 3.1 准备 JSONL 请求文件

每行是一个独立请求对象，包含 `custom_id`（用于匹配结果）、方法和请求体：

```python
import json

requests = []
texts = [
    "这家餐厅的服务太差了，等了半小时没人理",
    "产品质量非常好，下次还会再买",
    "价格还行，但配送速度有点慢",
]

for i, text in enumerate(texts):
    requests.append({
        "custom_id": f"review-{i:04d}",
        "method": "POST",
        "url": "/v1/chat/completions",
        "body": {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": "你是情感分析专家。请将以下评论分类为：正面、负面、中性。只输出分类结果，不要解释。"
                },
                {
                    "role": "user",
                    "content": text
                }
            ],
            "max_tokens": 10
        }
    })

# 写入 JSONL
with open("batch_requests.jsonl", "w", encoding="utf-8") as f:
    for req in requests:
        f.write(json.dumps(req, ensure_ascii=False) + "\n")

print(f"已生成 {len(requests)} 条请求")
```

### 3.2 上传文件并创建 Batch

```python
from openai import OpenAI

client = OpenAI(api_key="your-api-key")

# 上传 JSONL 文件
with open("batch_requests.jsonl", "rb") as f:
    batch_file = client.files.create(
        file=f,
        purpose="batch"
    )

print(f"文件 ID: {batch_file.id}")

# 创建 Batch 任务
batch = client.batches.create(
    input_file_id=batch_file.id,
    endpoint="/v1/chat/completions",
    completion_window="24h",  # 目前只支持 "24h"
    metadata={
        "description": "用户评论情感分析 - 2026-05-25"
    }
)

print(f"Batch ID: {batch.id}")
print(f"状态: {batch.status}")
```

### 3.3 轮询状态并获取结果

```python
import time

def wait_for_batch(client, batch_id, poll_interval=30):
    """轮询 batch 状态，直到完成或失败"""
    while True:
        batch = client.batches.retrieve(batch_id)
        status = batch.status
        
        print(f"[{time.strftime('%H:%M:%S')}] 状态: {status} | "
              f"完成: {batch.request_counts.completed}/{batch.request_counts.total}")
        
        if status == "completed":
            return batch
        elif status in ("failed", "expired", "cancelled"):
            raise RuntimeError(f"Batch 失败，状态: {status}")
        
        time.sleep(poll_interval)

# 等待完成（生产环境建议用队列或定时任务，不要同步等待）
completed_batch = wait_for_batch(client, batch.id)

# 下载结果
result_content = client.files.content(completed_batch.output_file_id)
results = [json.loads(line) for line in result_content.text.strip().split("\n")]

# 解析结果
for item in results:
    custom_id = item["custom_id"]
    if item["error"] is None:
        content = item["response"]["body"]["choices"][0]["message"]["content"]
        print(f"{custom_id}: {content}")
    else:
        print(f"{custom_id}: 错误 - {item['error']}")
```

运行后输出类似：
```
review-0000: 负面
review-0001: 正面
review-0002: 中性
```

## 四、生产级最佳实践

### 4.1 大文件分片策略

当你有 100 万条记录时，不要一次性打包全部，建议按每批 **10,000–20,000 条**分片，原因：
- 单个文件上传有大小上限（约 100MB）
- 分片后可以并行提交多个 batch，缩短整体完成时间
- 单片失败不影响其他分片

```python
def split_into_batches(all_requests, batch_size=10000):
    for i in range(0, len(all_requests), batch_size):
        yield all_requests[i:i + batch_size]

batch_ids = []
for chunk_idx, chunk in enumerate(split_into_batches(all_requests)):
    # 写临时文件、上传、创建 batch
    batch_id = create_batch(client, chunk, f"chunk-{chunk_idx}")
    batch_ids.append(batch_id)
    print(f"提交分片 {chunk_idx}，共 {len(chunk)} 条")
```

### 4.2 结果持久化与断点续传

由于 batch 可能需要几小时，进程崩溃是常有的事。推荐做法：

1. 创建 batch 后立即将 `batch_id` 存入数据库或文件
2. 重启时先检查未完成的 batch，继续轮询
3. 结果文件下载后立即写入持久化存储（S3/数据库），再删除临时文件

```python
import sqlite3

def save_batch_record(conn, batch_id, description, total):
    conn.execute(
        "INSERT INTO batches (batch_id, description, total, status) VALUES (?, ?, ?, 'submitted')",
        (batch_id, description, total)
    )
    conn.commit()
```

### 4.3 错误处理与重试

Batch API 的部分请求可能失败（token 超限、内容违规等），结果文件中的 `error` 字段会有详情：

```python
failed_requests = []
for item in results:
    if item["error"] is not None:
        failed_requests.append({
            "custom_id": item["custom_id"],
            "error_code": item["error"]["code"],
            "error_message": item["error"]["message"]
        })

print(f"失败 {len(failed_requests)} 条，可提取后单独重试")
```

对于失败条目，可以调整 prompt 后单独用同步 API 补跑，成本影响通常很小。

## 五、配合中转 API 使用

如果你在中国大陆访问 OpenAI API 有网络问题，可以通过兼容 OpenAI 协议的中转服务来使用 Batch API。只需修改 `base_url`：

```python
client = OpenAI(
    api_key="your-relay-api-key",
    base_url="https://api.yotradeapi.com/v1"  # 中转地址
)

# 以下代码完全不变，batch 创建、文件上传逻辑一致
batch_file = client.files.create(...)
batch = client.batches.create(...)
```

使用中转时需确认中转服务支持 `/v1/files` 和 `/v1/batches` 端点，不是所有中转都有完整 Batch API 支持。

## 六、成本计算实例

假设你需要对 **100 万条**中文评论做情感分类：

| 项目 | 估算 |
|------|------|
| 平均每条 prompt tokens | 约 80 tokens |
| 平均每条 completion tokens | 约 5 tokens |
| 总 tokens | 85M tokens |
| gpt-4o-mini 同步 API 费用 | 约 $13.6 |
| gpt-4o-mini Batch API 费用 | 约 $6.8 |
| **节省** | **约 $6.8（50%）** |

> 以上为估算值，实际 token 数和价格以实际为准。

对于更大规模（千万级）或使用 gpt-4o 的任务，节省会更显著。

## 七、与 Anthropic Batch API 的对比

OpenAI 和 Anthropic 都提供了批量 API，两者定位类似但细节有差异：

| 特性 | OpenAI Batch API | Anthropic Batch API |
|------|-----------------|---------------------|
| 折扣幅度 | 50% | 50% |
| 处理窗口 | 24 小时 | 24 小时 |
| 请求格式 | JSONL 文件上传 | JSON 数组（直接 API 调用） |
| 状态查询 | 轮询 `/v1/batches/{id}` | 轮询 `/v1/messages/batches/{id}` |
| 取消支持 | 支持 | 支持 |
| Embedding 批处理 | 支持 | 不适用 |

如果项目同时使用两个平台的模型，可以封装一个统一的 batch 调度层，按模型类型路由到对应的 Batch API。

## 八、常见问题与排查

**Q：Batch 卡在 `validating` 状态很久？**
通常是 JSONL 格式有问题。检查：每行是否是合法 JSON、`url` 字段是否正确（如 `/v1/chat/completions`）、`method` 是否全大写 `POST`。

**Q：`completed` 但 `output_file_id` 为空？**
说明所有请求都失败了，此时会有 `error_file_id`。下载错误文件查看原因。

**Q：处理时间超过预期？**
高峰期可能稍慢，但通常几小时内完成。如果超过 12 小时仍未完成，可以考虑取消后重提。

**Q：可以混合不同模型的请求吗？**
不可以。一个 batch 只能指定一个 `endpoint`，且所有请求需使用相同的模型端点。不同模型需创建不同的 batch。

## 九、相关阅读

- [Anthropic Batch API 完全指南](/blog/anthropic-batch-api-cn-guide/)
- [LLM API 定价横向对比 2026](/blog/llm-pricing-comparison-2026/)
- [Prompt Caching 降低 API 成本实战](/blog/prompt-caching-cost-optimization/)
- [AI Coding Agent 成本控制策略](/blog/ai-coding-agent-cost-control/)
- [LLM 限流与重试最佳实践](/blog/llm-rate-limit-handling/)

需要在中国大陆稳定访问 OpenAI Batch API？[YoTradeApi](https://yotradeapi.com) 提供全协议兼容的中转服务，支持 Files 和 Batches 端点，无需修改代码即可接入。
