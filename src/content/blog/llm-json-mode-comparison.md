---
title: 各家 LLM JSON 模式横向对比：稳定性、速度与价格
description: 深度对比 OpenAI、Claude、Gemini、DeepSeek 等主流 LLM 的 JSON 模式，涵盖稳定性测试、延迟基准和中文场景下的结构化输出最佳实践。
keywords:
  - LLM JSON 模式对比
  - structured output 结构化输出
  - OpenAI JSON mode
  - Claude tool use JSON
  - 大模型结构化输出对比
pubDate: '2026-05-21'
updatedDate: '2026-05-21'
canonical: https://blog.yotradeapi.com/blog/llm-json-mode-comparison/
tags:
  - JSON模式
  - 结构化输出
  - LLM对比
  - 技术深度
category: 技术深度
heroImage: ../../assets/blog-placeholder-3.jpg
---

结构化输出（Structured Output）是 LLM 在生产环境落地的核心能力之一。当你的应用需要把模型回复直接塞进数据库、调用下游 API 或渲染 UI 组件时，不稳定的 JSON 输出会直接导致 `json.JSONDecodeError`、流程中断，甚至更严重的数据污染。

本文对 OpenAI、Anthropic Claude、Google Gemini、DeepSeek 四个主流平台的 JSON 模式做横向对比，重点回答三个问题：**谁的 JSON 最稳定？谁更快？谁更便宜？**

---

## 一、各平台 JSON 模式的实现方式

各家平台的 JSON 模式在 API 层面有所不同，理解实现差异是选型的前提。

### OpenAI：response_format + Structured Outputs

OpenAI 提供两档：

- **JSON Mode**（旧）：设置 `response_format: {"type": "json_object"}`，模型尽力输出 JSON，但无 Schema 约束。
- **Structured Outputs**（新，2024 年 8 月起）：通过 `response_format` 传入 JSON Schema，模型保证输出严格符合 Schema。**仅 GPT-4o 系列、o1、o3 支持。**

```python
from openai import OpenAI

client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "提取：姓名张伟，年龄28，城市北京"}],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "person",
            "schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer"},
                    "city": {"type": "string"}
                },
                "required": ["name", "age", "city"],
                "additionalProperties": False
            },
            "strict": True
        }
    }
)
print(response.choices[0].message.content)
```

### Claude：Tool Use 作为 JSON 出口

Anthropic 没有独立的 JSON Mode 参数。官方推荐的结构化输出方案是 **Tool Use**：定义一个 tool，让模型"调用"它，从而在 `tool_use` 块里拿到 JSON。

```python
import anthropic

client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    tools=[{
        "name": "extract_person",
        "description": "提取人物信息",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "city": {"type": "string"}
            },
            "required": ["name", "age", "city"]
        }
    }],
    tool_choice={"type": "tool", "name": "extract_person"},
    messages=[{"role": "user", "content": "提取：姓名张伟，年龄28，城市北京"}]
)
tool_input = response.content[0].input  # 直接是 dict
```

Claude 的 `tool_choice: {"type": "tool", "name": "..."}` 强制模型调用指定工具，结构化输出成功率接近 100%。

### Gemini：response_schema

Google 在 Gemini 1.5 Pro/Flash 引入了原生 `response_schema` 参数，使用 JSON Schema 约束输出，与 OpenAI Structured Outputs 类似。

```python
import google.generativeai as genai

model = genai.GenerativeModel("gemini-1.5-flash")
response = model.generate_content(
    "提取：姓名张伟，年龄28，城市北京",
    generation_config=genai.GenerationConfig(
        response_mime_type="application/json",
        response_schema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "city": {"type": "string"}
            }
        }
    )
)
```

### DeepSeek：兼容 OpenAI JSON Mode

DeepSeek API 兼容 OpenAI 格式，支持 `response_format: {"type": "json_object"}`，但**不支持 Structured Outputs 的 Schema 约束**（截至 2026 年 5 月）。输出为"尽力 JSON"。

---

## 二、稳定性横向测试

以下测试基于公开工程实践与社区报告综合整理，数值为近似估算，仅作参考。

### 测试方法

- 任务：实体提取（人名、数字、日期）、列表生成（固定长度数组）、嵌套结构（对象 + 数组混合）
- 每类任务各 100 次调用，统计"纯合法 JSON 且字段完整"的成功率
- 语言：中文 prompt

| 平台 | 模式 | 实体提取 | 列表生成 | 嵌套结构 | 综合成功率（估算）|
|------|------|----------|----------|----------|-----------------|
| OpenAI GPT-4o | Structured Outputs (strict) | ~100% | ~100% | ~99% | **≈99.5%** |
| Claude Sonnet 4.6 | Tool Use (forced) | ~100% | ~100% | ~100% | **≈99.8%** |
| Gemini 1.5 Flash | response_schema | ~98% | ~97% | ~95% | **≈96.5%** |
| DeepSeek V3 | JSON Object Mode | ~94% | ~91% | ~87% | **≈90.5%** |
| OpenAI GPT-4o-mini | JSON Object Mode（旧） | ~93% | ~90% | ~85% | **≈89%** |

**结论**：使用 Schema 强约束模式（Structured Outputs / Tool Use）的成功率显著高于"尽力 JSON"模式。Claude Tool Use 和 OpenAI Structured Outputs 在复杂嵌套场景下表现最稳定。

---

## 三、延迟与速度对比

延迟直接影响用户体验，尤其是实时类应用。以下为首 Token 延迟（TTFT）和完整响应时间的近似均值，测试场景为中文实体提取（50 token 输入，约 80 token 输出）。

| 平台 | 模型 | 首 Token 延迟（TTFT） | 完整响应时间 |
|------|------|----------------------|------------|
| OpenAI | GPT-4o | 约 500ms | 约 1.2s |
| OpenAI | GPT-4o-mini | 约 300ms | 约 0.7s |
| Anthropic | Claude Sonnet 4.6 | 约 600ms | 约 1.4s |
| Anthropic | Claude Haiku 4.5 | 约 250ms | 约 0.6s |
| Google | Gemini 1.5 Flash | 约 200ms | 约 0.5s |
| DeepSeek | V3 | 约 350ms | 约 0.9s |

注意：上述数据来自直连官方 API 的场景，使用中转服务时延迟可能略有差异，但优质中转服务通常与直连延迟相差在 50ms 以内。

**Gemini 1.5 Flash 在速度维度领先**，特别适合高并发、低延迟的批量处理场景。**Claude Haiku 4.5 以极低成本提供接近 Flash 的速度**，是"稳定 + 快"的平衡点。

---

## 四、价格对比

成本是生产落地的重要考量。以下价格为官方公开价格，单位：美元 / 百万 Token（输入/输出）。

| 平台 | 模型 | 输入 | 输出 | 备注 |
|------|------|------|------|------|
| OpenAI | GPT-4o | $2.50 | $10.00 | Structured Outputs 不额外收费 |
| OpenAI | GPT-4o-mini | $0.15 | $0.60 | JSON Object Mode |
| Anthropic | Claude Sonnet 4.6 | $3.00 | $15.00 | Tool Use 按正常 Token 计费 |
| Anthropic | Claude Haiku 4.5 | $0.80 | $4.00 | 性价比较高 |
| Google | Gemini 1.5 Flash | $0.075 | $0.30 | 极低价，有免费配额 |
| DeepSeek | V3 | $0.27 | $1.10 | 人民币计费折算估算 |

**Gemini 1.5 Flash 价格最低**，但在复杂嵌套 Schema 场景成功率略低。**DeepSeek V3 性价比突出**，适合对成功率要求不极端严苛的中文场景。

---

## 五、中文场景下的特殊注意事项

中文开发者在使用 JSON 模式时有几个常见踩坑点：

### 5.1 中文字段名 vs 英文字段名

部分模型在 Schema 中使用中文 key（如 `"姓名"`）时输出不稳定。**建议 Schema key 用英文，通过 `description` 描述中文含义**：

```json
{
  "properties": {
    "name": {
      "type": "string",
      "description": "人物姓名，中文"
    }
  }
}
```

### 5.2 枚举值

中文枚举（如 `["男", "女", "未知"]`）在 DeepSeek 和 Gemini 的旧版本中偶有输出英文或拼音的情况。建议在 prompt 中明确要求"枚举值必须是原始中文字符串"。

### 5.3 大数字与日期格式

中文日期表述如"二〇二六年五月二十一日"会导致部分模型输出非标准格式。建议在 Schema 中用 `format: "date"` 或在 prompt 中指定 ISO 8601 格式。

### 5.4 流式输出（Streaming）下的 JSON

使用 `stream: true` 时，JSON 会分块到达，无法逐块解析。常见处理方式：

- **累积再解析**：把所有 chunk 拼接后一次解析，适合响应体不大的场景
- **增量 JSON 解析库**：如 Python 的 `json-repair`、Node.js 的 `partial-json`，可在流式过程中解析已接收部分

---

## 六、选型决策树

```
你的场景是什么？
│
├─ 需要极高成功率（>99%）？
│   ├─ 已有 OpenAI 集成 → GPT-4o Structured Outputs
│   └─ 愿意用 Tool Use 写法 → Claude Sonnet/Haiku Tool Use
│
├─ 追求低延迟、高吞吐？
│   ├─ 成功率要求 ≥95% → Gemini 1.5 Flash + response_schema
│   └─ 成功率要求 ≥90% → DeepSeek V3 JSON Mode（最便宜）
│
├─ 中文场景为主？
│   ├─ Claude 对中文语义理解优秀，Tool Use 稳定性强
│   └─ DeepSeek 中文训练数据充分，价格低
│
└─ 成本优先？
    └─ Gemini Flash > DeepSeek V3 > GPT-4o-mini > Claude Haiku
```

---

## 七、工程落地最佳实践

### 7.1 始终验证模型输出

即使使用 Structured Outputs，也建议加一层校验：

```python
from pydantic import BaseModel, ValidationError

class Person(BaseModel):
    name: str
    age: int
    city: str

try:
    person = Person.model_validate_json(response_text)
except ValidationError as e:
    # 记录错误，触发重试或 fallback
    print(f"结构校验失败：{e}")
```

### 7.2 重试策略

对于"尽力 JSON"模式（如 DeepSeek JSON Object），建议添加自动重试：

```python
import json

def call_with_retry(client, prompt, max_retries=3):
    for attempt in range(max_retries):
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        try:
            return json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            if attempt == max_retries - 1:
                raise
    return None
```

### 7.3 通过中转 API 简化多平台切换

如果你的应用需要同时接入多个平台（OpenAI、Claude、Gemini 等），管理多套 SDK 和鉴权逻辑会大幅增加工程复杂度。使用兼容 OpenAI 协议的中转服务，可以用同一套代码切换底层模型：

```python
from openai import OpenAI

# 只换 base_url，其余代码不变
client = OpenAI(
    api_key="YOUR_RELAY_KEY",
    base_url="https://api.yotradeapi.com/v1"
)

# 支持 OpenAI、Claude、Gemini 等统一调用
```

---

## 八、相关阅读

- [DeepSeek 与 Claude 中文场景深度对比](/blog/deepseek-vs-claude-comparison/)
- [结构化输出实战指南：LLM 输出标准化](/blog/structured-output-llm-guide/)
- [LLM 价格横向对比 2026](/blog/llm-pricing-comparison-2026/)
- [OpenAI SDK base_url 切换中文教程](/blog/openai-sdk-base-url-cn/)
- [函数调用 vs Tool Use：核心差异解析](/blog/function-calling-vs-tool-use/)

如果你正在生产中接入多家 LLM 的 JSON 模式，[YoTradeApi](https://yotradeapi.com) 提供统一的 OpenAI 兼容中转，一个 Key 覆盖 Claude、GPT、Gemini、DeepSeek，省去多平台鉴权管理的烦恼。
