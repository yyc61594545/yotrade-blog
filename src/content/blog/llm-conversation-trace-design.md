---
title: LLM 对话轨迹存储与查询设计实践
description: 从数据模型、索引策略到检索场景，讲解如何设计 LLM 对话轨迹（trace）的存储方案，兼顾调试、审计与成本分析的查询需求。
keywords:
  - LLM 对话轨迹存储
  - conversation trace 设计
  - LLM 日志数据库设计
  - Agent 调用链存储
  - 对话审计查询
pubDate: '2026-07-08'
updatedDate: '2026-07-08'
canonical: https://blog.yotradeapi.com/blog/llm-conversation-trace-design/
tags:
  - LLM
  - 可观测性
  - 数据库设计
  - 应用工程
category: 应用工程
heroImage: ../../assets/blog-placeholder-2.jpg
---

可观测性平台（如 Langfuse）能解决"看得见"的问题，但很多团队自建系统时会发现：把对话轨迹接入第三方平台只是第一步，真正的难点是**自己的数据库里要不要存一份、怎么存、怎么查**。原因很现实——审计要求、数据合规、成本归因分析往往需要跑自定义 SQL，而不是依赖第三方平台的固定报表。

本文聚焦对话轨迹（trace）的**数据模型设计**和**查询场景优化**，不重复讲可观测性平台的选型和接入（那部分见[《LLM 可观测性与 Langfuse 实践》](/blog/llm-observability-langfuse/)），也不展开 Agent 层面的追踪架构（见[《AI Agent 可观测性设计》](/blog/ai-agent-observability-design/)）。

## 一、为什么"存一份原始轨迹"是刚需

即便接了第三方可观测性平台，多数团队最终还是要在自己的数据库里保留一份对话轨迹，常见原因：

- **审计与合规**：金融、医疗类场景需要长期留存、可追溯、不依赖第三方服务可用性
- **成本归因**：按用户、按功能模块拆分 token 消耗，第三方平台的报表粒度往往不够细
- **训练数据回流**：把高质量对话轨迹反哺到 few-shot 库或微调数据集
- **故障复盘**：第三方平台数据保留周期有限（通常 30-90 天），长周期问题排查需要自有存储

## 二、核心数据模型：三层结构

对话轨迹的数据模型建议按粒度分三层，而不是一张大表堆所有字段：

```sql
-- 第一层：会话（conversation）
CREATE TABLE conversations (
  id            UUID PRIMARY KEY,
  user_id       UUID NOT NULL,
  started_at    TIMESTAMPTZ NOT NULL,
  ended_at      TIMESTAMPTZ,
  status        TEXT NOT NULL, -- active / completed / abandoned
  metadata      JSONB          -- 渠道、客户端版本等
);

-- 第二层：消息轮次（turn）
CREATE TABLE turns (
  id              UUID PRIMARY KEY,
  conversation_id UUID REFERENCES conversations(id),
  turn_index      INT NOT NULL,
  role            TEXT NOT NULL, -- user / assistant / tool
  content         TEXT,
  created_at      TIMESTAMPTZ NOT NULL
);

-- 第三层：调用明细（span）—— 一个 turn 可能触发多次模型/工具调用
CREATE TABLE spans (
  id            UUID PRIMARY KEY,
  turn_id       UUID REFERENCES turns(id),
  span_type     TEXT NOT NULL, -- llm_call / tool_call / retrieval
  model         TEXT,
  input_tokens  INT,
  output_tokens INT,
  latency_ms    INT,
  cost_usd      NUMERIC(10,6),
  raw_request   JSONB,
  raw_response  JSONB,
  created_at    TIMESTAMPTZ NOT NULL
);
```

三层拆分的核心考量：**会话层用于用户视角查询，轮次层用于对话回放，span 层用于成本与性能分析**。如果全部塞进一张表，会导致常见查询（比如"某用户本月对话次数"）要扫描包含大字段（`raw_request`/`raw_response`）的整表，性能很差。

## 三、大字段的存储取舍

`raw_request`/`raw_response` 往往是最大的存储开销来源，尤其是包含图片、长文档的多模态调用。几种取舍方案：

| 方案 | 优点 | 缺点 | 适用场景 |
|------|------|------|---------|
| 直接存 JSONB 在主表 | 查询简单，事务一致 | 表体积增长快，索引效率下降 | 调用量小、单条记录不大 |
| 拆分冷表 + 外键关联 | 热表保持精简 | 需要 JOIN，多一次查询 | 中等规模，偶尔需要回看原始内容 |
| 对象存储（S3 兼容）+ 数据库存指针 | 成本最低，可无限扩容 | 查询原始内容有额外延迟 | 大规模、长期留存场景 |

经验法则：如果日调用量在十万级以下，拆分冷表通常够用；超过百万级调用量，原始 payload 建议直接落对象存储，数据库只存指针和摘要字段（如 token 数、截断后的前 200 字符），避免数据库成为瓶颈。

## 四、索引策略：为常见查询场景设计，而不是"全字段加索引"

对话轨迹系统的典型查询场景决定了索引设计：

- **按用户查历史**：`conversations(user_id, started_at)` 复合索引，覆盖"某用户最近 N 次会话"
- **按时间范围查成本**：`spans(created_at, model)` 部分索引，配合按月分区表效果更好
- **按会话回放全部轮次**：`turns(conversation_id, turn_index)` 保证有序读取
- **异常延迟排查**：`spans(latency_ms)` 上建条件索引（如 `WHERE latency_ms > 5000`），避免对全表建高基数索引浪费空间

**不要**对 `raw_request`/`raw_response` 这类 JSONB 大字段做全文索引，除非有明确的内容检索需求（比如"查找所有提到某个关键词的对话"）。如果确实需要，用专门的搜索引擎（Elasticsearch/Meilisearch）做二级索引，而不是让主数据库承担全文检索职责。

## 五、分区与归档策略

对话轨迹是典型的时序增长数据，按时间分区几乎是必选项：

```sql
-- PostgreSQL 按月分区示例
CREATE TABLE spans (
  ...
) PARTITION BY RANGE (created_at);

CREATE TABLE spans_2026_07 PARTITION OF spans
  FOR VALUES FROM ('2026-07-01') TO ('2026-08-01');
```

配合归档策略：

- **热数据（近 30-90 天）**：保留在主库，支持实时查询
- **温数据（90 天-1 年）**：迁移到低成本存储或降采样后的汇总表
- **冷数据（1 年以上）**：仅保留合规要求的最小字段集，原始 payload 归档到对象存储或直接删除（视数据合规要求而定）

自动化归档任务建议用定时任务（cron job）而不是应用代码里手动触发，避免遗漏。

## 六、查询场景实战：几个高频 SQL 模式

**场景 1：某用户本月 token 消耗汇总**

```sql
SELECT
  DATE_TRUNC('day', s.created_at) AS day,
  SUM(s.input_tokens + s.output_tokens) AS total_tokens,
  SUM(s.cost_usd) AS total_cost
FROM spans s
JOIN turns t ON s.turn_id = t.id
JOIN conversations c ON t.conversation_id = c.id
WHERE c.user_id = $1
  AND s.created_at >= DATE_TRUNC('month', NOW())
GROUP BY 1
ORDER BY 1;
```

**场景 2：定位高延迟调用的模型分布**

```sql
SELECT model, COUNT(*), AVG(latency_ms), PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) AS p95
FROM spans
WHERE created_at >= NOW() - INTERVAL '24 hours'
  AND span_type = 'llm_call'
GROUP BY model
ORDER BY p95 DESC;
```

这两类查询是运维和成本分析中最常跑的，设计索引时应优先保证它们的性能，而不是追求"所有可能的查询都快"。

## 七、多模型场景下的字段兼容设计

如果业务同时调用多个厂商的模型（Claude、GPT、Gemini 等），`raw_request`/`raw_response` 的结构天然不统一。建议在写入前做一层**归一化**，抽取通用字段（`model`、`input_tokens`、`output_tokens`、`stop_reason`、`cost_usd`）落到结构化列，厂商特有字段保留在 JSONB 里作为补充。这样跨模型的成本分析、性能对比查询不需要针对每个厂商写不同的解析逻辑。如果调用层已经通过统一的 API 中转做了归一化，落库时可以直接复用中转层返回的标准化字段，省去自己写适配层的工作量。

## 八、隐私与脱敏处理

对话轨迹经常包含用户的敏感信息（姓名、联系方式、订单号等）。落库前建议加一层脱敏流水线：

- 用正则或轻量 NER 模型识别常见敏感字段（手机号、邮箱、身份证号模式）
- 脱敏后存储用于分析的副本，原始内容单独加密存储并严格限制访问权限
- 明确保留期限，超期自动清理原始内容，只保留脱敏后的统计数据

这一层设计越早做越好——事后给历史数据补脱敏，工作量远大于在写入路径上加一道处理。

## 九、相关阅读

- [AI Agent 可观测性设计](/blog/ai-agent-observability-design/)
- [LLM 可观测性与 Langfuse 实践](/blog/llm-observability-langfuse/)
- [AI 辅助数据库 Schema 设计](/blog/ai-coding-database-schema-design/)
- [LLM 上下文预热（Context Priming）技巧实战](/blog/llm-context-priming-techniques/)

如果需要同时对接多个模型厂商并统一记录调用成本，通过 [YoTradeApi](https://yotradeapi.com) 一个接口调用主流模型，返回结构已做归一化，方便直接落库分析。
