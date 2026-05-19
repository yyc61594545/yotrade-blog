---
title: 用 AI 做数据分析的实战工作流
description: 用 Claude / GPT 做数据分析的端到端流程：探索性分析、SQL 生成、可视化、报告自动化、与 Pandas 的配合。
keywords:
- ai 数据分析
- ai sql 生成
- claude 数据
- ai 可视化
- llm 数据分析
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/ai-data-analysis-workflow/
tags:
- 数据分析
- AI 应用
- Python
- SQL
- 工程实战
category: 工程实战
heroImage: ../../assets/blog-placeholder-2.jpg
---

# 用 AI 做数据分析的实战工作流

数据分析师 / 工程师用 AI 提效有明显空间：SQL 写得快、图表配得准、文字解读不愁。本文给端到端工作流。

## 一、AI 在数据分析的核心场景

| 场景 | AI 价值 |
| --- | --- |
| 写 SQL | 极高 |
| 解释 SQL | 极高 |
| 数据探索（EDA） | 高 |
| 可视化代码 | 高 |
| 写报告 / 总结 | 极高 |
| 异常检测 / 模式发现 | 中 |
| 解读复杂指标 | 高 |
| Pipeline 调试 | 高 |

## 二、写 SQL 的标准 prompt

```
你是 SQL 专家。根据需求写 PostgreSQL 查询。

# 表结构
```sql
CREATE TABLE orders (
  id BIGINT,
  user_id BIGINT,
  amount NUMERIC,
  status TEXT,
  created_at TIMESTAMPTZ
);
CREATE TABLE users (
  id BIGINT,
  registered_at TIMESTAMPTZ,
  country TEXT
);
```

# 需求
找出最近 30 天每个国家的人均订单金额，按金额降序。
只看 status='paid' 的订单。
排除测试账号（user_id < 1000）。

# 要求
- 用 CTE 提高可读
- 加注释
- 性能考虑（用 index 友好的写法）
- 数字保留 2 位

# 输出
仅 SQL，不解释。
```

把表结构 + 业务规则给清楚，AI 出的 SQL 通常一次就对。

## 三、SQL 自审

让 AI 自己 review：

```
> 这段 SQL 有什么潜在问题？性能、正确性、可读性。
> [贴 SQL]
```

经常发现：缺索引会爆、JOIN 顺序导致 N+1、统计语义错误。

## 四、Pandas / Polars 实战

```python
# 让 AI 写 pandas
prompt = """
我有 DataFrame `df`，列：
- order_id, user_id, amount, country, created_at

任务：
1. 算每个国家最近 30 天的总订单数和总金额
2. 找出环比增长 > 50% 的国家
3. 输出按增长率降序的 DataFrame
"""
```

让 AI 一次写完整代码，**自己跑一遍验证**。

## 五、可视化代码

```
> 用 plotly 画一张图：x 轴是国家，y 轴是订单数。
> 颜色按国家分组。
> 标题 "Q3 各国订单分布"
> 中文支持（注意字体）
> 数据：[贴 sample]
```

Plotly / Altair / matplotlib 都可以。**让 AI 给完整代码 + 输出 HTML**。

## 六、Jupyter Notebook 集成

Jupyter AI 扩展 / Cursor Notebook 模式：

```python
# %% [magic]
# AI: 加载 ./data/orders.csv，做 EDA，找出 outlier
```

Cursor 支持 .ipynb 文件，可以在 cell 用 AI 一键填代码。

## 七、报告自动化

```python
def auto_report(df):
    stats = df.describe().to_dict()
    top_countries = df.groupby("country")["amount"].sum().nlargest(5).to_dict()
    
    resp = client.chat.completions.create(
        model="claude-sonnet-4-6",
        messages=[{
            "role": "user",
            "content": f"""根据以下数据写一份周报，markdown 格式：

# 统计
{stats}

# Top 国家
{top_countries}

# 要求
- 1 句话 executive summary
- 3-5 个 key insights
- 1-2 条建议
- 不超过 400 字
""",
        }],
    )
    return resp.choices[0].message.content
```

每周自动生成。**但要人审一次再发**。

## 八、Code Interpreter 模式

把数据上传给 GPT-5 用其 Code Interpreter：

```python
# OpenAI Responses API
client.responses.create(
    model="gpt-5",
    input="分析这份 CSV 数据，找出销量异常的国家",
    tools=[{"type": "code_interpreter"}],
    attachments=[{"file_id": file.id}],
)
```

**走中转不一定支持**——code_interpreter 是 OpenAI 端服务。如不支持，自己起 sandbox：

```python
# 自建：让 AI 写代码 → exec
code = ai_generate_pandas_code(question, df_schema)
local_vars = {"df": df}
exec(code, {"pd": pd, "np": np}, local_vars)
result = local_vars["result"]
```

**严格 sandbox**：只允许 pandas / numpy，不允许 fs / network。

## 九、与 Pandas Profiling / Sweetviz 配合

```python
import ydata_profiling

profile = ydata_profiling.ProfileReport(df)
profile.to_file("profile.html")

# 让 AI 看 profile.html 解读
ai_summary = client.chat.completions.create(
    model="claude-sonnet-4-6",
    messages=[{
        "role": "user",
        "content": f"看完这份 profile 报告（HTML），用 300 字总结主要发现：\n{html}",
    }],
)
```

工具收集 + AI 解读 = 高效 EDA。

## 十、SQL 解释

```
> 解释这段 SQL 做了什么：
> [贴一段复杂的 SQL]
```

新接手项目 / 老旧 ETL 看不懂时特别有用。

## 十一、数据 schema 探索

```python
# 自动收集 schema
inspector = inspect(engine)
schema = {}
for table in inspector.get_table_names():
    schema[table] = [c["name"] + ": " + str(c["type"]) for c in inspector.get_columns(table)]

# 让 AI 总结
resp = client.chat.completions.create(
    model="claude-sonnet-4-6",
    messages=[{
        "role": "user",
        "content": f"基于以下 schema 总结这个数据库的业务模型：\n{schema}",
    }],
)
```

新员工 onboarding 一份"数据库总览"。

## 十二、避坑

- ❌ 直接把生产数据给 AI（用脱敏样本）
- ❌ AI 写的 SQL 直接在生产跑（先在 staging 验证）
- ❌ AI 解读数据 = 业务结论（人复核）
- ❌ exec(ai_code) 没沙箱（巨大风险）
- ❌ 报告生成 = 全自动发布（要人审）

## 十三、相关阅读

- [中文 RAG 工程实战](/blog/rag-cn-best-practices/)
- [LLM 结构化输出完全指南](/blog/structured-output-llm-guide/)
- [Python 异步并发调用 LLM API](/blog/python-async-llm-client/)
- [OpenAI Responses API 完整指南](/blog/openai-responses-api-guide/)
- [Claude vs GPT vs Gemini 国内开发者怎么选](/blog/claude-vs-gpt-vs-gemini-cn-developer/)

数据分析高频调用，用 [YoTradeApi](https://yotradeapi.com) 中转 + Sonnet 4.6 性价比最高，分析输出 + 报告生成同 Key 通用。
