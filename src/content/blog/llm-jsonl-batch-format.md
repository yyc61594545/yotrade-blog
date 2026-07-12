---
title: LLM Batch JSONL 格式规范与陷阱
description: OpenAI 和 Anthropic Batch API 都要求 JSONL 输入文件，格式规范细节、custom_id 设计、编码陷阱一步错就整批任务失败，本文逐条拆解。
keywords:
  - JSONL格式
  - Batch API文件格式
  - custom_id设计
  - OpenAI Batch JSONL
  - Anthropic Batch JSONL
pubDate: '2026-07-12'
updatedDate: '2026-07-12'
canonical: https://blog.yotradeapi.com/blog/llm-jsonl-batch-format/
tags:
  - Batch API
  - JSONL
  - 技术深度
category: 技术深度
heroImage: ../../assets/blog-placeholder-1.jpg
---

Batch API 能把推理成本砍半，但它的输入不是普通 JSON，而是 JSONL（JSON Lines）——一种一行一个 JSON 对象的格式。这个格式本身不复杂，但恰恰因为"看起来很简单"，很多人会在编码、换行符、字段命名这些细节上栽跟头，导致整批任务提交失败或者部分行被静默跳过。OpenAI 和 Anthropic 的 Batch API 使用方法参考 [OpenAI Batch API 节省 50% 成本实战](/blog/openai-batch-api-cn-guide/) 和 [Anthropic Batch API 国内使用指南](/blog/anthropic-batch-api-cn-guide/)，本文专注格式本身的规范和踩坑记录。

## 一、JSONL 到底是什么

JSONL（JSON Lines，也叫 NDJSON）的规则很简单：**每一行是一个独立、完整的 JSON 对象，行与行之间用换行符 `\n` 分隔，整个文件不是一个 JSON 数组**。

```jsonl
{"custom_id": "req-1", "method": "POST", "url": "/v1/chat/completions", "body": {"model": "gpt-5", "messages": [{"role": "user", "content": "你好"}]}}
{"custom_id": "req-2", "method": "POST", "url": "/v1/chat/completions", "body": {"model": "gpt-5", "messages": [{"role": "user", "content": "介绍一下你自己"}]}}
```

最容易搞混的一点：这**不是**一个包含两个元素的 JSON 数组。如果你写成：

```json
[
  {"custom_id": "req-1", ...},
  {"custom_id": "req-2", ...}
]
```

这是标准 JSON 数组格式，不是 JSONL，Batch API 会解析失败或者直接拒绝整个文件。

## 二、正确生成 JSONL 的方法

**错误做法**：手动拼字符串加 `\n`，容易漏加或多加换行符，尤其是最后一行结尾。

**正确做法**：用 `json.dumps` 逐行写，让库处理转义：

```python
import json

requests = [
    {"custom_id": "req-1", "method": "POST", "url": "/v1/chat/completions",
     "body": {"model": "gpt-5", "messages": [{"role": "user", "content": "你好"}]}},
    {"custom_id": "req-2", "method": "POST", "url": "/v1/chat/completions",
     "body": {"model": "gpt-5", "messages": [{"role": "user", "content": "介绍一下你自己"}]}},
]

with open("batch_input.jsonl", "w", encoding="utf-8") as f:
    for req in requests:
        f.write(json.dumps(req, ensure_ascii=False) + "\n")
```

注意 `ensure_ascii=False`——默认情况下 `json.dumps` 会把中文转成 `\uXXXX` 转义序列。这不会导致解析错误，但会让文件体积膨胀（每个中文字符占用更多字节），也不利于人工检查文件内容。

## 三、custom_id 设计：批量任务的"主键"

`custom_id` 是每条请求的唯一标识，用于把 Batch 返回的结果和原始请求对应起来。设计不好会导致排查问题时无从下手。

**常见错误**：

```python
# 错误：用数组下标当 custom_id，一旦任务重跑或部分失败重试，索引就错位
{"custom_id": "0", ...}
{"custom_id": "1", ...}
```

**更好的做法**：把业务含义编码进 custom_id，方便结果回填和排查：

```python
# 好：包含业务实体 ID + 任务类型，即使乱序返回也能准确对应
{"custom_id": "user_10293_translate_zh_en", ...}
{"custom_id": "order_88421_summary", ...}
```

**关键约束**（以官方文档当前限制为准，不同平台数值可能不同）：
- `custom_id` 通常有长度限制（比如 64 字符以内）
- 同一批次内 `custom_id` 必须唯一，重复会导致提交失败或结果覆盖
- 只能包含特定字符集（字母、数字、下划线、连字符通常安全，避免用空格和特殊符号）

## 四、常见格式陷阱清单

| 陷阱 | 现象 | 修复方法 |
|---|---|---|
| 文件末尾多一个空行 | 部分平台会把空行当成空请求报错 | 写文件时确保最后一行不多加换行符，或用平台的官方 SDK 生成文件 |
| 换行符是 `\r\n` 而非 `\n` | Windows 环境下用文本编辑器保存文件容易出现 | 用 Python 写文件时显式指定 `newline=''` 并只用 `\n` |
| 单行 JSON 内部包含未转义的换行符 | 请求体里的多行文本破坏了行边界 | 用 `json.dumps` 生成，不要手动拼接字符串——它会自动把内部换行转成 `\n` 转义 |
| 文件编码不是 UTF-8 | 中文/emoji 内容乱码或解析失败 | 写入时显式指定 `encoding="utf-8"` |
| body 里混用了不同模型 | 有的平台要求一个 batch 文件内模型一致 | 提交前检查所有行的 `body.model` 是否符合平台要求，必要时按模型拆分文件 |
| 单文件超过大小/行数限制 | 提交返回文件过大错误 | 提前拆分成多个文件分批提交，具体限制以官方文档为准 |

## 五、提交前的自校验脚本

与其提交后收到报错才排查，不如在本地先跑一遍校验：

```python
import json

def validate_jsonl(filepath: str) -> list:
    errors = []
    seen_ids = set()

    with open(filepath, "rb") as f:
        raw = f.read()

    if b"\r\n" in raw:
        errors.append("检测到 \\r\\n 换行符，建议统一为 \\n")

    lines = raw.decode("utf-8").splitlines()

    for i, line in enumerate(lines, 1):
        if not line.strip():
            errors.append(f"第 {i} 行为空行")
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            errors.append(f"第 {i} 行 JSON 解析失败: {e}")
            continue

        cid = obj.get("custom_id")
        if not cid:
            errors.append(f"第 {i} 行缺少 custom_id")
        elif cid in seen_ids:
            errors.append(f"第 {i} 行 custom_id 重复: {cid}")
        else:
            seen_ids.add(cid)

        if "body" not in obj:
            errors.append(f"第 {i} 行缺少 body 字段")

    return errors

errors = validate_jsonl("batch_input.jsonl")
if errors:
    for e in errors:
        print(f"❌ {e}")
else:
    print(f"✅ 文件格式校验通过")
```

这个脚本能在本地几秒内跑完，比提交到平台等排队跑完才发现格式错误快得多——批量任务动辄几千上万条，排队处理可能要几十分钟到几小时，格式错误导致的返工成本很高。

## 六、返回结果的解析

Batch 任务完成后，输出文件同样是 JSONL 格式，每一行对应一个 `custom_id` 的结果，顺序不保证和输入文件一致：

```python
results = {}
with open("batch_output.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        obj = json.loads(line)
        cid = obj["custom_id"]
        if obj.get("error"):
            results[cid] = {"status": "failed", "error": obj["error"]}
        else:
            results[cid] = {"status": "success", "response": obj["response"]}

# 用 custom_id 回填到业务数据，而不是依赖行号顺序
for cid, result in results.items():
    if result["status"] == "failed":
        print(f"⚠️ {cid} 失败: {result['error']}")
```

**必须处理部分失败**：一批几千条请求里，个别请求因为内容触发安全策略、超时等原因失败是正常现象，不能假设整批全部成功。解析结果时要遍历检查每一行的 `error` 字段，对失败的 `custom_id` 单独重试或人工介入，而不是假设输出文件行数等于输入文件行数。

## 七、相关阅读

- [OpenAI Batch API 节省 50% 成本实战](/blog/openai-batch-api-cn-guide/)
- [Anthropic Batch API 国内使用指南](/blog/anthropic-batch-api-cn-guide/)
- [OpenAI Batch 与 Streaming 的选择决策](/blog/openai-batch-vs-streaming/)
- [Token 计数国内开发者指南](/blog/token-counting-cn-guide/)
- [LLM 结构化输出完全指南（JSON Schema / Function Call）](/blog/structured-output-llm-guide/)

批量任务调试阶段经常需要小规模反复测试格式是否正确，[YoTradeApi](https://yotradeapi.com) 提供 OpenAI 和 Anthropic 兼容的 API 接入，方便在正式提交大批量任务前用少量请求快速验证 Prompt 和格式。
