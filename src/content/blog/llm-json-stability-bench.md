---
title: 结构化输出稳定性横评：如何量化 LLM 的 JSON 出错率
description: 用可复现的评测方法量化主流大模型结构化输出的稳定性，涵盖 Schema 违规率、字段级一致性、重试成本模型与自建评测脚本。
keywords:
  - 结构化输出稳定性
  - LLM JSON 出错率
  - Schema 违规率评测
  - 大模型稳定性测试
  - JSON Schema 校验
pubDate: '2026-09-04'
updatedDate: '2026-09-04'
canonical: https://blog.yotradeapi.com/blog/llm-json-stability-bench/
tags:
  - 结构化输出
  - 模型评测
  - JSON Schema
  - 技术深度
category: 模型评测
---

在生产环境里，"这个模型支持结构化输出"和"这个模型的结构化输出稳定"是两件完全不同的事。前者是一个功能开关，后者是一个需要用数字说话的工程问题。团队真正关心的往往不是"能不能返回 JSON"，而是"跑一万次请求，有多少次会让下游解析崩溃、多少次字段类型对不上、多少次需要重试"。

本文不重复对比各家 JSON 模式的功能差异（那部分可以看 [LLM JSON 模式横向对比](/blog/llm-json-mode-comparison/)），而是给出一套可以自己跑起来的稳定性评测方法：怎么定义"稳定"、怎么设计测试集、怎么把结果变成可以放进技术决策文档的数字。

## 一、为什么"支持结构化输出"不等于"稳定"

几乎所有主流模型都宣称支持 JSON 输出，但背后的实现机制差异很大：

- **约束解码（constrained decoding）**：模型在 token 采样层面被强制只能生成符合 Schema 的输出，理论上不会出现格式错误。OpenAI 的 Structured Outputs、部分开源推理框架（如配合 outlines / guidance）属于这一类。
- **提示工程 + 后处理**：模型本质上还是自由生成文本，只是被强 prompt 要求输出 JSON，服务端再做一次解析和修复。很多"JSON mode"标注为 beta 的实现走的是这条路。
- **工具调用复用**：把 JSON Schema 包装成一个 function/tool 定义，让模型走 tool-calling 的生成路径而不是普通文本路径，稳定性通常介于前两者之间。

这三种机制在"格式正确率"上的差异，在小样本测试里几乎看不出来（10 次请求可能全部正确），但在生产环境的百万级调用规模下,失败率哪怕只有 0.5%，也意味着每天几千次需要人工介入或触发重试的请求。稳定性问题不是"会不会出错"，而是"出错的分布长什么样"。

## 二、稳定性的四个可测量维度

与其笼统地问"稳不稳定"，不如把问题拆成四个可以独立测量的维度：

| 维度 | 定义 | 典型故障模式 |
|---|---|---|
| Schema 违规率 | 输出不满足 JSON Schema（类型错误、缺字段、多字段、枚举值超范围） | 数值字段返回字符串、必填字段缺失 |
| 语法有效率 | 输出本身能否被 `JSON.parse` / `json.loads` 成功解析 | 多余的 Markdown 代码块包裹、尾随逗号、截断 |
| 字段级一致性 | 相同输入多次请求，关键字段（如分类标签、布尔判断）是否收敛到同一结果 | 温度参数为 0 时仍出现语义漂移 |
| 长度退化率 | 输出接近 max_tokens 时是否发生截断导致 JSON 不完整 | 长列表字段在末尾被截断 |

这四个维度里，语法有效率是最容易被误判为"已解决"的一项——很多团队看到接入了官方的 Structured Outputs 功能就默认语法层面万无一失，但字段级一致性和长度退化率仍然是模型能力和业务场景强相关的问题，官方功能开关解决不了。

## 三、评测集设计：覆盖真实故障场景，而不是理想输入

自建评测集时最常见的错误是只测"简单场景"——一个三四个字段的扁平对象，模型几乎不可能出错，测出来的数字毫无参考价值。一份有信噪比的评测集至少要覆盖：

1. **深层嵌套结构**：3 层以上的嵌套对象 + 数组，测试模型在复杂 Schema 下的字段丢失率。
2. **强类型边界**：要求返回的数值字段紧贴边界（如枚举值刚好在合法范围边缘、时间戳格式要求精确到毫秒）。
3. **长列表生成**：要求返回 20+ 条数组元素，测试长度退化和截断问题。
4. **对抗性输入**：输入文本本身包含引号、换行符、疑似 JSON 片段，测试模型是否会被输入内容"污染"输出结构。
5. **模糊/矛盾指令**：故意让 Schema 要求和自然语言 prompt 存在轻微冲突（比如 prompt 说"用中文描述"但 Schema 里字段名暗示英文枚举），观察模型的默认解析行为。

每类场景至少准备 30-50 条测试样本，同一 prompt 用相同参数跑 5-10 次取稳定性均值，避免单次采样的偶然性掩盖真实故障率。

## 四、一个可以直接跑的评测脚本骨架

下面是一个精简的 Python 评测框架示例，核心逻辑是"请求 → 校验 → 记录 → 聚合"：

```python
import json
from jsonschema import validate, ValidationError
from dataclasses import dataclass, field

@dataclass
class BenchResult:
    total: int = 0
    parse_fail: int = 0
    schema_violation: int = 0
    truncated: int = 0
    consistency_mismatch: int = 0

def run_case(client, prompt, schema, repeats=5):
    outputs = []
    result = BenchResult()
    for _ in range(repeats):
        result.total += 1
        raw = client.generate(prompt, response_schema=schema)
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            result.parse_fail += 1
            continue
        try:
            validate(instance=parsed, schema=schema)
        except ValidationError:
            result.schema_violation += 1
            continue
        if raw.rstrip().endswith(("...", "}\n", "")) is False and len(raw) >= 3900:
            result.truncated += 1
        outputs.append(parsed)

    # 一致性检查：同一 prompt 多次输出的关键字段是否收敛
    if len(outputs) > 1:
        key_field = list(schema.get("properties", {}).keys())[0]
        values = {json.dumps(o.get(key_field)) for o in outputs}
        if len(values) > 1:
            result.consistency_mismatch += 1

    return result
```

真正落地时需要补上速率限制、超时重试、结果落盘（建议直接写 JSONL，方便后续用 pandas 聚合），以及针对不同模型 SDK 的适配层。这套骨架的价值在于把"稳定性"从主观印象变成可以每次模型升级前后跑一遍、对比数字的回归测试。

## 五、把稳定性数字换算成重试成本

拿到 Schema 违规率之后，下一步是把它换算成实际的工程成本，这样才能进入技术选型的决策依据。一个简化的成本模型：

```
预期重试次数 = 1 / (1 - 违规率)
额外 Token 成本 = (预期重试次数 - 1) × 单次请求平均 Token 成本
```

举例：如果某模型在你的评测集上违规率是 2%，重试策略是"失败就用相同参数重跑一次"，那么预期重试次数约为 1.02 次，额外成本增加 2%。但如果违规率是 8%（在复杂嵌套 Schema 下并不少见），额外成本会跳到 8.7% 左右，同时还要考虑重试带来的延迟尾部拉长——这对于同步等待响应的用户交互场景往往比 Token 成本更致命。

如果观察到某个模型在特定 Schema 结构下违规率显著偏高，比起无脑加重试逻辑，更值得做的是拆分 Schema：把容易出错的深层嵌套字段拆成单独一次请求，用多次简单调用替代一次复杂调用，虽然增加了请求数，但整体的端到端成功率通常反而更高。

## 六、CI 里跑稳定性回归测试

结构化输出的稳定性不是一次性测完就结束的——模型服务商会静默更新底层模型版本，同样的 model 字符串在不同月份的行为可能不同。建议把稳定性评测脚本接入 CI，在以下时机触发：

- 依赖的模型版本号发生变更（如从 `gpt-x` 切到显式的 dated snapshot）
- Schema 定义发生变更（尤其是新增嵌套层级或数组字段）
- 每周定时跑一次基线对比，及时发现服务商静默降级

把违规率、一致性不匹配率作为门禁指标（例如超过 5% 阈值则告警但不阻断部署，因为模型层面的问题通常无法靠改代码修复），能在问题扩散到生产环境之前提前发现。

## 七、相关阅读

- [LLM JSON 模式横向对比：稳定性、速度与价格](/blog/llm-json-mode-comparison/)
- [LLM 结构化输出完全指南（JSON Schema / Function Call）](/blog/structured-output-llm-guide/)
- [OpenAI Structured Outputs vs tool_choice 选型指南](/blog/openai-structured-outputs-vs-tool/)
- [LLM Function Calling 并行调用实战](/blog/llm-function-calling-parallel/)

如果你的评测已经跑出了模型选型结论，需要频繁切换 API 供应商或做多模型对比测试，用 [YoTradeApi](https://yotradeapi.com) 一个中转账号访问所有主流模型，省去多头开票和分别管理密钥的麻烦。
