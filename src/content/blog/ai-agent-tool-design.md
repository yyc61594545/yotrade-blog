---
title: AI Agent 工具集合的设计原则
description: 从实战出发，梳理 AI Agent 工具集合设计的核心原则，帮助开发者构建可靠、高效、易维护的 Agent 工具体系。
keywords:
  - AI Agent 工具设计
  - Agent tool use
  - 工具集合最佳实践
  - LLM function calling
  - Agent 工程化
pubDate: '2026-05-25'
updatedDate: '2026-05-25'
canonical: https://blog.yotradeapi.com/blog/ai-agent-tool-design/
tags:
  - AI Agent
  - 工具设计
  - function calling
  - 工程实践
category: 应用工程
heroImage: ../../assets/blog-placeholder-3.jpg
---

当你把一个任务交给 AI Agent，让它自主决策、调用工具、完成目标时，工具集合的设计质量直接决定了 Agent 的成败。工具太少，Agent 力不从心；工具太多，模型迷路、幻觉频发；工具设计模糊，Agent 调用错误参数然后无限重试。

本文聚焦于**工具集合的工程化设计**，而非 Agent 框架选型——这里讨论的原则在 Claude Tool Use、OpenAI Function Calling、LangChain Tools、Anthropic Agent SDK 等各类实现中都适用。

## 一、工具是 Agent 与世界的接口

在理解设计原则前，需要先确认一个认知：**工具不是"功能点"的堆砌，而是 Agent 与外部世界交互的语义接口**。

模型在调用工具时，依赖两件事：

1. **工具名称和描述**：模型决定"该不该调用这个工具"
2. **参数 schema**：模型决定"该传什么参数"

因此，工具设计实质上是在设计**自然语言与结构化调用之间的映射**。设计不当，模型的推理会在这层转换上出错。

常见的"工具设计烂"的症状：

- Agent 反复调用同一个工具，参数略有差异，在尝试"撞运气"
- Agent 拼凑多个工具完成本该一步做完的事
- 工具返回值格式模型不理解，导致它忽略结果继续瞎猜
- 工具调用成功，但 Agent 认为失败，触发不必要的重试

## 二、单一职责：每个工具只做一件事

**原则：一个工具名对应一个清晰的语义动作。**

反例——把所有数据库操作塞进一个工具：

```python
# 糟糕的设计
def database_operation(action: str, table: str, data: dict = None, filters: dict = None):
    """执行数据库操作，action 可以是 read/write/delete/update"""
    ...
```

这个工具名叫 `database_operation`，但它能做四种完全不同的事。模型调用时必须在描述里猜 `action` 参数该填什么，出错概率大大提升。

好的设计——拆成独立工具：

```python
def read_records(table: str, filters: dict) -> list[dict]:
    """从指定表中读取符合条件的记录"""
    ...

def create_record(table: str, data: dict) -> dict:
    """在指定表中创建一条新记录，返回创建结果"""
    ...

def update_record(table: str, record_id: str, updates: dict) -> dict:
    """更新指定表中的某条记录"""
    ...

def delete_record(table: str, record_id: str) -> bool:
    """删除指定表中的某条记录，返回是否成功"""
    ...
```

拆分后，每个工具名自描述，参数也更少、更清晰。模型的调用准确率会明显提高。

## 三、参数设计：少而精，有默认值

**工具参数越多，模型出错概率越高。**

设计参数时的核实问题：

1. **这个参数是必须的吗？** 能从上下文推断就别强制传入
2. **这个参数能有默认值吗？** 90% 的情况下用同一个值，就设为默认
3. **参数名是否足够自描述？** `limit` 比 `n` 更清楚，`start_date` 比 `d1` 更清楚

参数类型的选择也有讲究：

| 场景 | 推荐类型 | 避免 |
|------|---------|------|
| 固定选项 | `Literal["asc", "desc"]` 枚举 | `str`（模型会乱填） |
| 可选参数 | `Optional[str] = None` | 必填但语义模糊 |
| 列表 | `list[str]` + 描述限制长度 | 无约束的 `list` |
| 时间 | ISO 8601 字符串 + 描述格式 | 时间戳整数 |

一个精简的参数设计示例：

```python
def search_documents(
    query: str,
    max_results: int = 5,
    source: Literal["web", "database", "files"] = "database",
    date_after: Optional[str] = None  # 格式 YYYY-MM-DD，不填则不限制
) -> list[dict]:
    """在文档库中搜索与 query 相关的内容，返回最多 max_results 条结果"""
    ...
```

## 四、工具描述：写给模型看的说明书

工具的 `description` 字段是模型决策的核心依据，要像写给"没有背景知识的聪明人"看一样撰写。

**好的描述应该包含：**
- 工具的核心用途（一句话）
- 什么时候该用 / 什么时候不该用（如果容易混淆）
- 参数的含义和格式要求
- 返回值的格式和含义

**描述模板（Claude Tool Use 风格）：**

```json
{
  "name": "get_weather",
  "description": "获取指定城市的当前天气信息。仅用于查询实时天气，不支持历史天气和天气预报。返回温度（摄氏度）、天气状况和湿度。",
  "input_schema": {
    "type": "object",
    "properties": {
      "city": {
        "type": "string",
        "description": "城市名称，支持中文和英文，如 '北京' 或 'Beijing'"
      },
      "unit": {
        "type": "string",
        "enum": ["celsius", "fahrenheit"],
        "description": "温度单位，默认 celsius（摄氏度）"
      }
    },
    "required": ["city"]
  }
}
```

注意 `description` 里主动说明了"不支持历史天气"——这能防止模型在历史查询场景下误用这个工具。

## 五、返回值设计：结构化但不冗余

工具返回值有两个读者：**模型**和**开发者**。为了模型，返回值要语义清晰；为了开发者，要便于调试。

**核心原则：**

1. **始终返回结构化 JSON**，不要返回纯文本字符串（"操作成功" 这类）
2. **包含操作状态**：`success: true/false` 让模型知道是否成功
3. **失败时给出原因**：`error: "record_not_found"` 比静默返回 `null` 好得多
4. **不要返回超长数据**：搜索结果截断到必要字段，避免撑爆上下文

```python
# 推荐的返回格式
def create_task(title: str, assignee: str) -> dict:
    try:
        task = db.create(title=title, assignee=assignee)
        return {
            "success": True,
            "task_id": task.id,
            "title": task.title,
            "created_at": task.created_at.isoformat()
        }
    except ValueError as e:
        return {
            "success": False,
            "error": "invalid_input",
            "message": str(e)
        }
    except Exception as e:
        return {
            "success": False,
            "error": "internal_error",
            "message": "任务创建失败，请稍后重试"
        }
```

模型看到 `success: false` 和 `error: "invalid_input"` 后，会尝试修正参数重试，而不是直接报告"任务创建失败"然后停下来。

## 六、工具数量控制：少即是多

经验数字：**一次对话提供 5–10 个工具是比较合适的范围**，超过 20 个时模型的工具选择准确率明显下降（不同模型容忍度不同，GPT-4o 和 Claude 3.5 以上表现较好）。

控制工具数量的策略：

**动态工具加载**：根据任务类型动态注入相关工具子集，而不是把所有工具全部塞给模型。

```python
def get_tools_for_task(task_type: str) -> list:
    tool_registry = {
        "data_analysis": [query_db, run_sql, export_csv],
        "email_management": [read_email, send_email, create_draft],
        "code_review": [read_file, search_code, add_comment],
    }
    return tool_registry.get(task_type, [])
```

**工具分组/命名空间**：相关工具用统一前缀，帮助模型理解工具体系。例如 `file_read`、`file_write`、`file_delete` 而不是 `read`、`write`、`delete`（容易与其他工具混淆）。

## 七、幂等性与副作用声明

**有副作用的工具（写操作、发邮件、删除数据）必须在描述中明确声明。**

原因：模型可能因为不确定工具是否成功而重复调用。如果是查询工具，重复调用没有问题；如果是"发送邮件"或"从账户扣款"，重复调用是灾难。

两个应对策略：

1. **在描述里明确**：`⚠️ 此工具会真实发送邮件，请确认后再调用`
2. **写操作添加幂等键**：传入 `idempotency_key`，服务端防重复

```python
def send_email(
    to: str,
    subject: str,
    body: str,
    idempotency_key: str  # 相同 key 重复调用不会重复发送
) -> dict:
    """
    发送电子邮件。⚠️ 此操作会真实发送邮件，不可撤回。
    使用 idempotency_key 防止因网络原因导致的重复发送。
    """
    ...
```

## 八、测试工具的思路

工具设计完成后，**最有效的测试方法是模拟模型视角**：让 Agent 实际运行任务，观察工具调用日志。

关注这些指标：

| 指标 | 健康状态 | 需优化信号 |
|------|---------|-----------|
| 工具选择准确率 | > 95% | 频繁误选或不选 |
| 参数填写正确率 | > 90% | 参数格式错误频繁 |
| 不必要的重复调用 | < 5% | 同工具同参数调用多次 |
| 任务完成率 | 看任务复杂度 | 在工具调用环节卡死 |

如果发现某个工具误用频率很高，优先检查**工具描述**是否有歧义，而不是第一时间调整模型提示词。工具描述清楚了，往往问题自然消失。

## 九、相关阅读

- [AI Agent Prompt 工程实战](/blog/agent-prompt-engineering-cn/)
- [Claude Tool Use 最佳实践](/blog/claude-tool-use-best-practices/)
- [并行工具调用：Claude 多工具协同实战](/blog/parallel-tool-use-claude/)
- [MCP 自定义 Server 开发指南](/blog/mcp-custom-server-development/)
- [OpenAI Batch API 节省 50% 成本实战](/blog/openai-batch-api-cn-guide/)

构建 Agent 应用需要稳定的 API 调用环境，[YoTradeApi](https://yotradeapi.com) 提供高可用的 Claude 和 GPT 中转服务，支持 Tool Use 和 Function Calling 全部特性。
