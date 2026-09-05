---
title: 批处理 API 的排队与结果回收：状态机与轮询设计
description: OpenAI/Anthropic Batch API 提交后的排队生命周期怎么管：状态机设计、轮询退避策略、结果文件回收与 custom_id 对账、部分失败处理。
keywords:
  - batch api 状态机
  - batch job 轮询
  - custom_id 对账
  - batch api 结果回收
  - llm 批处理排队
pubDate: '2026-09-05'
updatedDate: '2026-09-05'
canonical: https://blog.yotradeapi.com/blog/llm-batch-api-queue-design/
tags:
  - Batch API
  - 状态机
  - 技术深度
  - 结果回收
category: 技术深度
---

Batch API 能把推理成本砍半，接入方式和 JSONL 格式规范已经在[《Anthropic Batch API 国内使用指南》](/blog/anthropic-batch-api-cn-guide/)和[《LLM Batch JSONL 格式规范与陷阱》](/blog/llm-jsonl-batch-format/)里讲过。本文专注下一层问题：**提交之后怎么办**——一个 Batch Job 从提交到最终结果落库，中间要经过一套完整的状态机，轮询节奏、部分失败处理、结果对账，任何一环没设计好，都会变成"提交了但不知道什么时候能拿到结果"的糊涂账。

## 一、Batch Job 的标准状态机

不管是 OpenAI 还是 Anthropic，Batch Job 都会经历类似的状态流转：

```
validating → in_progress → finalizing → completed
                  ↓              ↓
               failed         expired
                  ↓
              cancelled（用户主动取消）
```

| 状态 | 含义 | 你该做什么 |
| --- | --- | --- |
| `validating` | 校验输入文件格式 | 等待，一般几秒到几十秒 |
| `in_progress` | 排队处理中 | 轮询，不要频繁 |
| `finalizing` | 结果文件生成中 | 快完成了，可以缩短轮询间隔 |
| `completed` | 全部完成，含成功和失败的行 | 下载结果文件，对账 |
| `failed` | 整批失败（通常是输入文件问题） | 检查错误信息，修复后重新提交 |
| `expired` | 超过时间窗口未完成 | 未完成部分要重新提交 |
| `cancelled` | 主动取消 | 已完成部分可能仍可取回 |

**关键认知**：`completed` 不等于"每一行都成功"。批内每一行是独立处理的，整体状态是 `completed` 时，结果文件里仍然可能夹杂单行的错误（比如某条 prompt 触发了内容过滤）。这是很多人第一次接入时踩的坑——看到 `completed` 就以为万事大吉，直接跳过了逐行检查。

## 二、轮询策略：别把 5 秒轮询写死

Batch Job 处理时间从几分钟到 24 小时不等，取决于批量大小和当前平台负载。固定 5 秒轮询一次会造成两个问题：一是浪费请求配额（轮询接口本身也计入速率限制），二是没有意义——大批量任务不可能 5 秒内出结果。

推荐用**指数退避 + 上限封顶**的轮询节奏：

```python
import time

def poll_batch(client, batch_id, max_wait=86400):
    interval = 10  # 初始 10 秒
    elapsed = 0
    while elapsed < max_wait:
        batch = client.batches.retrieve(batch_id)
        if batch.status in ("completed", "failed", "expired", "cancelled"):
            return batch
        time.sleep(interval)
        elapsed += interval
        interval = min(interval * 1.5, 300)  # 封顶 5 分钟一次
    raise TimeoutError(f"batch {batch_id} 超过 {max_wait}s 仍未完成")
```

如果系统里同时有几十上百个 Batch Job 在跑，**不要每个 Job 单独开一个轮询循环**，而是用一个统一的调度器批量查状态（大部分平台支持按 ID 列表批量查询，或者至少可以在一个循环里顺序查多个 Job，共享同一个退避节奏）。

## 三、更好的方式：Webhook 代替轮询

如果平台支持 Webhook（部分中转网关和自建方案会补齐这个能力），优先用 Webhook 通知代替轮询——Batch Job 完成后平台主动推送一个回调，你的服务只需要暴露一个接收端点：

```python
from flask import Flask, request

app = Flask(__name__)

@app.route("/webhooks/batch-complete", methods=["POST"])
def on_batch_complete():
    payload = request.json
    batch_id = payload["batch_id"]
    status = payload["status"]
    # 触发下载结果文件 + 对账的后续流程
    enqueue_result_reconciliation(batch_id)
    return "", 200
```

Webhook 方式省掉了轮询本身的开销，也让"结果什么时候到"从"不确定要等多久"变成"事件驱动"。没有 Webhook 支持时，退避轮询是唯一选择，但要在架构里把它当成临时方案对待，别把轮询间隔硬编码在业务逻辑深处，方便以后切换。

## 四、结果回收：按 custom_id 对账

Batch 输出文件里的每一行都带一个 `custom_id`，对应提交时你自己指定的标识。回收结果的核心工作就是把输出行按 `custom_id` 映射回原始请求，而不是假设输出顺序和输入顺序一致——**批处理不保证顺序**。

```python
def reconcile_batch_results(output_lines, original_requests_by_id):
    results = {}
    errors = {}
    for line in output_lines:
        record = json.loads(line)
        cid = record["custom_id"]
        if record.get("error"):
            errors[cid] = record["error"]
        else:
            results[cid] = record["response"]["body"]

    # 找出提交了但输出文件里完全没出现的行（比平台报错更隐蔽的失败模式）
    missing = set(original_requests_by_id) - set(results) - set(errors)
    return results, errors, missing
```

`missing` 这一步经常被漏掉，但在实战里出现过：某些边缘情况下平台会静默丢弃格式有微小问题的行，既不放进成功结果也不放进错误列表。对账逻辑必须显式对比"提交了多少行"和"输出文件里出现了多少行"，缺口本身就是一个需要告警的信号。

## 五、部分失败的处理策略

批内单行失败常见原因：内容安全过滤、单条 prompt 超过 token 限制、模型对某些字符编码处理异常。处理策略按失败原因分流：

| 失败类型 | 处理方式 |
| --- | --- |
| 内容过滤拒答 | 记录，人工review，一般不做自动重试 |
| 单条超限（如 prompt 太长） | 修正后单独走实时 API 补跑，不值得为一条重新提一批 |
| 平台侧临时错误（5xx） | 收集成一个新的小批次重新提交 |
| 格式错误（自己的输入问题） | 修复 JSONL 后整批重新提交 |

失败率如果超过某个阈值（比如 5%），应该触发告警而不是静默重试——大批量失败往往意味着输入数据本身有系统性问题，重试解决不了。

## 六、时间窗口与过期处理

Batch API 通常有处理时间窗口（比如 24 小时），超过窗口任务会变成 `expired`。设计上要注意：

- **不要把业务逻辑写死等待 Job 完成才返回响应**——批处理场景本质是"提交-离开-回来取"，中间应该有其他任务在跑，不要阻塞主流程。
- **过期任务要能区分"部分完成"和"完全没跑"**：`expired` 状态下，已经处理完的行结果文件里通常仍然可以取到，只有未处理的部分需要重新提交，不要整批重跑造成浪费。
- 给每个提交的 Job 记录一个业务侧的"提交时间戳"，超过窗口没等到终态时主动查询而非被动等 Webhook——Webhook 也可能因为网络问题丢失。

## 七、一个可落地的最小架构

把上面几点串起来，一个够用的 Batch Job 管理表结构：

```sql
CREATE TABLE batch_jobs (
    id TEXT PRIMARY KEY,
    platform_batch_id TEXT NOT NULL,
    status TEXT NOT NULL,          -- validating/in_progress/completed/failed/expired
    submitted_at TIMESTAMP,
    finalized_at TIMESTAMP,
    total_requests INT,
    succeeded INT DEFAULT 0,
    failed INT DEFAULT 0,
    missing INT DEFAULT 0,
    next_poll_at TIMESTAMP         -- 配合退避轮询使用
);
```

调度器定期扫描 `status NOT IN (completed, failed, expired, cancelled) AND next_poll_at <= now()` 的行，逐个查询并更新退避后的 `next_poll_at`，完成后触发对账流程写回 `succeeded/failed/missing`。这套设计不复杂，但比"写个 while 循环轮询然后祈祷"要稳得多，尤其是当 Batch Job 数量从个位数涨到几十上百个的时候。

## 八、相关阅读

- [Anthropic Batch API 国内使用指南](/blog/anthropic-batch-api-cn-guide/)
- [OpenAI Batch API 节省 50% 成本实战](/blog/openai-batch-api-cn-guide/)
- [LLM Batch JSONL 格式规范与陷阱](/blog/llm-jsonl-batch-format/)
- [AI 任务重试队列设计](/blog/ai-task-retry-queue/)
- [LLM 异步任务队列设计：从原型到生产](/blog/llm-async-job-queue/)

批处理任务的中转稳定性同样重要——[YoTradeApi](https://yotradeapi.com) 支持 Anthropic 与 OpenAI Batch API 的国内直连，提交与轮询都不用额外绕网络。
