---
title: LLM 异步任务队列设计：从原型到生产
description: 用 BullMQ/Celery 设计 LLM 异步任务队列：任务分层、重试策略、优先级调度、Worker 弹性扩缩，附 Node.js 与 Python 示例代码。
keywords:
  - LLM 任务队列
  - BullMQ LLM
  - Celery AI 任务
  - LLM 异步处理
  - AI 任务调度设计
pubDate: '2026-06-13'
updatedDate: '2026-06-13'
canonical: https://blog.yotradeapi.com/blog/llm-async-job-queue/
tags:
  - LLM
  - 任务队列
  - 应用工程
  - BullMQ
  - Celery
category: 应用工程
heroImage: ../../assets/blog-placeholder-4.jpg
---

LLM 调用不是普通的 HTTP 请求。它延迟高（几秒到几分钟）、成本按 token 计、可能超时、可能限速。如果你在 API handler 里直接 `await llm.chat(...)`，用户就要盯着旋转动画等 30 秒，服务端也很容易被打挂。

解法是**任务队列**：把 LLM 调用从请求路径里解耦出去，交给 Worker 异步处理，用户拿到任务 ID 轮询结果。这不是什么高深架构，但有很多细节值得系统性整理。本文从设计决策出发，给出 Node.js（BullMQ）和 Python（Celery）两套可落地的实现模式。

---

## 一、为什么 LLM 任务需要专门设计

普通后台任务的队列设计经验用在 LLM 上，往往有几个地方不适配：

**延迟分布异常宽**：一个简单的摘要任务可能 2 秒完成，一个长文档分析任务可能跑 3 分钟。这对 Worker 超时设置、用户轮询频率都有影响。

**费用不均匀**：有的任务 100 tokens，有的任务 100k tokens，不能用"每任务平均费用"来做资源估算。

**限速维度复杂**：LLM API 通常同时限制 RPM（每分钟请求数）和 TPM（每分钟 token 数），任务队列只控制并发度是不够的，还需要 token 感知的调度。

**失败类型需要区分**：网络超时可以重试，上下文窗口超出要截断后重试，内容过滤拒绝则不应该重试。

---

## 二、核心架构：三层分工

一个可维护的 LLM 任务系统通常分三层：

```
请求层（API Server）
    ↓  提交任务 + 返回 task_id
队列层（Redis / RabbitMQ）
    ↓  分发任务
Worker 层（处理 + 重试 + 回调）
```

**请求层**的职责：接收用户输入，校验参数，生成 task_id，把任务推入队列，立刻返回 202 Accepted。

**队列层**的职责：持久化任务，按优先级排序，在 Worker 崩溃时保证任务不丢失。

**Worker 层**的职责：实际调用 LLM API，处理错误，把结果写回数据库，触发 Webhook 或 WebSocket 通知。

---

## 三、Node.js 实现：BullMQ 方案

BullMQ 是 Node.js 生态里最成熟的 Redis 任务队列库，天然支持优先级、延迟任务、失败重试。

### 3.1 安装与基础配置

```bash
npm install bullmq ioredis openai
```

```typescript
// src/queues/llm-queue.ts
import { Queue, Worker, Job } from 'bullmq';
import IORedis from 'ioredis';

const connection = new IORedis(process.env.REDIS_URL!, {
  maxRetriesPerRequest: null, // BullMQ 要求
});

export const llmQueue = new Queue('llm-tasks', {
  connection,
  defaultJobOptions: {
    attempts: 3,
    backoff: { type: 'exponential', delay: 2000 },
    removeOnComplete: { age: 86400 }, // 保留 1 天
    removeOnFail: { age: 604800 },    // 失败任务保留 7 天
  },
});
```

### 3.2 提交任务的 API 端点

```typescript
// src/routes/summarize.ts
import { llmQueue } from '../queues/llm-queue';
import { randomUUID } from 'crypto';

app.post('/api/summarize', async (req, res) => {
  const { text, priority = 5 } = req.body;

  const job = await llmQueue.add(
    'summarize',
    { text, userId: req.user.id },
    {
      jobId: randomUUID(),
      priority,       // 1 最高，10 最低
      attempts: text.length > 10000 ? 2 : 3, // 长文本减少重试
    }
  );

  res.status(202).json({ taskId: job.id, status: 'queued' });
});

// 轮询接口
app.get('/api/tasks/:taskId', async (req, res) => {
  const job = await llmQueue.getJob(req.params.taskId);
  if (!job) return res.status(404).json({ error: 'not found' });

  const state = await job.getState(); // waiting | active | completed | failed
  res.json({
    taskId: job.id,
    state,
    result: state === 'completed' ? job.returnvalue : null,
    error:  state === 'failed'    ? job.failedReason : null,
  });
});
```

### 3.3 Worker 处理逻辑

```typescript
// src/workers/llm-worker.ts
import { Worker, Job } from 'bullmq';
import { OpenAI } from 'openai';

const client = new OpenAI({
  apiKey: process.env.YOTRADE_API_KEY!,
  baseURL: 'https://yotradeapi.com/v1',
  timeout: 120_000,
});

const worker = new Worker(
  'llm-tasks',
  async (job: Job) => {
    const { text } = job.data;

    // 更新进度，方便前端显示"处理中"
    await job.updateProgress(10);

    const resp = await client.chat.completions.create({
      model: 'claude-sonnet-4-6',
      messages: [
        { role: 'system', content: '你是一个专业摘要助手，请简洁地总结以下内容。' },
        { role: 'user',   content: text },
      ],
      max_tokens: 1024,
    });

    await job.updateProgress(100);
    return resp.choices[0].message.content;
  },
  {
    connection,
    concurrency: 5,           // 同时处理 5 个任务
    limiter: { max: 10, duration: 60_000 }, // 每分钟最多 10 个任务
  }
);

// 区分可重试和不可重试的错误
worker.on('failed', async (job, err) => {
  if (err.message.includes('context_length_exceeded')) {
    // 上下文超限：移除重试，记录错误
    await job?.discard();
    console.error(`Job ${job?.id} context exceeded, discarded`);
  } else if (err.message.includes('content_filter')) {
    await job?.discard();
    console.warn(`Job ${job?.id} content filtered`);
  }
  // 其他错误（超时、5xx）会按 attempts 配置自动重试
});
```

---

## 四、Python 实现：Celery + Redis 方案

Python 生态里 Celery 是主流选择，结合 Redis 做 broker 非常稳定。

### 4.1 基础配置

```python
# celery_app.py
from celery import Celery
import os

app = Celery(
    'llm_tasks',
    broker=os.environ['REDIS_URL'],
    backend=os.environ['REDIS_URL'],
)

app.conf.update(
    task_serializer='json',
    result_expires=86400,        # 结果保留 1 天
    task_acks_late=True,         # Worker 崩溃时任务重新入队
    worker_prefetch_multiplier=1, # 每次只取 1 个任务，避免长任务堆积
    task_routes={
        'tasks.heavy_analysis': {'queue': 'heavy'},
        'tasks.quick_summary':  {'queue': 'light'},
    },
)
```

### 4.2 定义任务

```python
# tasks.py
from celery_app import app
from openai import OpenAI
import time

client = OpenAI(
    api_key=os.environ['YOTRADE_API_KEY'],
    base_url='https://yotradeapi.com/v1',
    timeout=120,
)

@app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    autoretry_for=(TimeoutError, ConnectionError),
)
def quick_summary(self, text: str, user_id: str) -> dict:
    try:
        resp = client.chat.completions.create(
            model='claude-haiku-4-5',  # 轻量任务用 Haiku 省钱
            messages=[
                {'role': 'system', 'content': '请用 3 句话总结以下内容。'},
                {'role': 'user',   'content': text},
            ],
            max_tokens=300,
        )
        return {
            'summary': resp.choices[0].message.content,
            'tokens_used': resp.usage.total_tokens,
        }
    except Exception as exc:
        # 内容过滤不重试
        if 'content_filter' in str(exc).lower():
            raise exc
        raise self.retry(exc=exc)


@app.task(
    bind=True,
    max_retries=2,
    soft_time_limit=180,   # 3 分钟软超时
    time_limit=200,        # 硬超时
)
def heavy_analysis(self, document: str, user_id: str) -> dict:
    # 长文档分析，走 heavy 队列
    resp = client.chat.completions.create(
        model='claude-opus-4-8',
        messages=[
            {'role': 'system', 'content': '请对以下文档进行深度分析，给出关键洞察。'},
            {'role': 'user',   'content': document},
        ],
        max_tokens=4096,
    )
    return {'analysis': resp.choices[0].message.content}
```

### 4.3 Flask API 端点

```python
# api.py
from flask import Flask, request, jsonify
from celery.result import AsyncResult
from tasks import quick_summary, heavy_analysis

flask_app = Flask(__name__)

@flask_app.post('/api/summarize')
def submit_summary():
    data = request.json
    task = quick_summary.apply_async(
        args=[data['text'], data['user_id']],
        priority=data.get('priority', 5),  # 0–9，0 最高
    )
    return jsonify({'task_id': task.id}), 202

@flask_app.get('/api/tasks/<task_id>')
def get_task(task_id):
    result = AsyncResult(task_id)
    return jsonify({
        'task_id': task_id,
        'state': result.state,           # PENDING | STARTED | SUCCESS | FAILURE
        'result': result.result if result.ready() else None,
    })
```

---

## 五、关键设计决策

### 5.1 队列分层

不要把所有任务扔进一个队列。按照延迟预期分层：

| 队列名 | 目标延迟 | 适合任务 | 并发数 |
|--------|---------|---------|-------|
| `critical` | < 5s | 实时摘要、对话 | 10–20 |
| `standard` | < 60s | 文章分析、翻译 | 5–10 |
| `batch` | < 10min | 批量处理、报告生成 | 2–5 |

### 5.2 重试策略

| 错误类型 | 是否重试 | 等待策略 |
|---------|---------|---------|
| 网络超时 | 是 | 指数退避，最多 3 次 |
| 429 限速 | 是 | 固定 60 秒等待 |
| 500/503 | 是 | 指数退避 |
| 400 参数错误 | 否 | 直接失败 |
| 内容过滤 | 否 | 直接失败 |
| 上下文超限 | 否（或截断后重试） | 需要预处理 |

### 5.3 死信队列

失败超过最大次数的任务不应该消失，要进死信队列（Dead Letter Queue）。原因：

- 方便排查为什么任务反复失败
- 可以手动修复参数后重新投入队列
- 统计失败率，监控服务质量

BullMQ 中，失败任务自动保留在 `failed` 状态，可以通过 `queue.getFailed()` 获取。Celery 中需要配置 `task_reject_on_worker_lost = True` 和自定义失败处理器。

---

## 六、监控与可观测性

任务队列是黑盒，不加监控就是在盲飞。最基础的监控应该包括：

**队列深度**：`waiting` 状态的任务数，异常增长说明 Worker 处理不过来。

**任务延迟**：从提交到开始处理的等待时间，这是用户感受到的最直接指标。

**成功率**：`completed / (completed + failed)`，低于 95% 就要排查。

**Token 消耗**：如果你在 job data 里记录了 token 使用量，可以做成本监控。

BullMQ 可以配合 [Bull Board](https://github.com/felixmosh/bull-board) 做可视化面板，30 分钟就能搭起来。Celery 可以用 Flower。

---

## 七、相关阅读

- [Python 异步并发调用 LLM API 实战](/blog/python-async-llm-client/)
- [AI Agent 工具调用设计：如何让 Agent 用好工具](/blog/ai-agent-tool-design/)
- [AI Agent 错误降级设计：构建健壮的 AI 工作流](/blog/ai-agent-fallback-design/)
- [Claude Code 一个月深度使用复盘](/blog/claude-code-1month-real-usage/)
- [API 中转稳定性测试：真实压力下的表现](/blog/ai-api-relay-stability-test/)

需要支持高并发 LLM 任务处理的稳定 API 中转？[YoTradeApi](https://yotradeapi.com) 支持按量计费、自动重试，是构建 LLM 任务队列后端的可靠选择。
