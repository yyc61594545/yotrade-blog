---
title: OpenAI、Anthropic、Gemini 工具 Schema 兼容层设计
description: 三大厂商工具调用 Schema 字段名、类型系统、必填规则均不一致，本文给出一套可落地的中间表示与转换层设计，让 Agent 代码一次编写多模型运行。
keywords:
  - 工具调用兼容层
  - tool schema
  - OpenAI Function Calling
  - Anthropic Tool Use
  - Gemini Function Declaration
  - 多模型 Agent
pubDate: '2026-08-26'
updatedDate: '2026-08-26'
canonical: https://blog.yotradeapi.com/blog/llm-tool-schema-portability/
tags:
  - 工具调用
  - 多模型
  - Agent工程
  - Schema设计
category: 技术深度
heroImage: ../../assets/blog-placeholder-2.jpg
---

多模型 Agent 项目做到一定规模后，几乎都会撞上同一个问题：给 OpenAI 写好的工具定义，直接丢给 Anthropic 或 Gemini 跑不通。三家的工具调用接口看似都是"传一个 JSON Schema 描述函数"，但字段命名、嵌套结构、类型系统的松紧程度全都不一样。如果项目要同时支持三家模型（无论是出于成本路由还是可用性冗余），就绕不开一层工具 Schema 兼容层。

本文不重复三家官方文档已有的入门示例，而是聚焦"怎么设计一个通用中间表示（IR），把它分别编译成三家能接受的格式"这件工程问题。

## 一、三家 Schema 结构对比

先把差异摆在桌面上。以一个"查询天气"的工具为例，三家的顶层结构分别是：

| 维度 | OpenAI | Anthropic | Gemini |
|---|---|---|---|
| 顶层字段 | `type: "function"` + `function: {name, description, parameters}` | 无 `type` 包裹，直接 `{name, description, input_schema}` | `function_declarations: [{name, description, parameters}]` |
| 参数字段名 | `parameters` | `input_schema` | `parameters` |
| Schema 方言 | 标准 JSON Schema（支持 `$ref`、`anyOf`） | JSON Schema 子集，`$ref` 支持有限 | 自定义 OpenAPI 3.0 子集，**不支持** `additionalProperties`、`oneOf` |
| 必填字段声明 | `required: [...]` 数组 | 同左 | 同左，但枚举值需用 `enum` 且类型必须显式声明 |
| 强制调用某工具 | `tool_choice: {type: "function", function: {name}}` | `tool_choice: {type: "tool", name}` | `tool_config: {function_calling_config: {mode: "ANY", allowed_function_names}}` |
| 并行调用开关 | `parallel_tool_calls: false` 可关闭 | 默认允许，无显式开关，靠 prompt 引导 | `mode: "AUTO"` 与 `"ANY"` 行为不同，无独立并行开关 |

这张表说明一件事：**没有任何一家的格式是另外两家的严格超集**。这意味着中间表示不能简单地"以某家为基准，其他两家做减法"，而必须设计成三家能力的交集 + 各自扩展点。

关于三家基础字段差异的详细案例，之前在 [Function Calling vs Tool Use 差异辨析](/blog/function-calling-vs-tool-use/) 里已经拆过，这里不再重复，直接进入兼容层设计。

## 二、为什么"交集设计"是唯一可行路径

工程上容易踩的坑是想做一个"超集 Schema"，把三家所有能力都塞进去，再在转换时按需裁剪。这条路走不通，原因有三：

1. **裁剪逻辑本身会重新引入不一致**——比如 Gemini 不支持 `oneOf`，你在转换时把 `oneOf` 拍平成多个独立参数，这个拍平算法本身就需要针对每个字段单独维护，复杂度并不比直接写三份 Schema 低。
2. **静默降级比报错更危险**。如果 Anthropic 端某个复杂类型被自动降级成字符串，Claude 拿到的实际是"这个字段是字符串"的描述，模型会按字符串去理解语义，产出的参数值可能完全不符合原意，而且不会有任何报错提示你这里发生了降级。
3. **交集设计能提前暴露不可移植的设计**。如果你的工具 Schema 依赖某家独有能力（比如 OpenAI 的 `anyOf` 联合类型），交集校验会在开发阶段就报错，而不是等到线上某个模型返回异常参数才发现。

所以推荐的做法是：**定义一个只包含三家共同支持的类型集合的 IR，工具作者只能用这个子集描述参数**。

## 三、中间表示（IR）的类型子集

三家交集能稳定支持的类型集合大致是：

```typescript
type IRType =
  | { kind: 'string'; enum?: string[]; description?: string }
  | { kind: 'number'; description?: string }
  | { kind: 'integer'; description?: string }
  | { kind: 'boolean'; description?: string }
  | { kind: 'array'; items: IRType; description?: string }
  | { kind: 'object'; properties: Record<string, IRType>; required: string[]; description?: string };

interface IRTool {
  name: string;
  description: string;
  parameters: IRType; // 顶层必须是 object
}
```

刻意排除的能力：

- **`$ref` / 递归引用**：三家对递归 Schema 的支持深度不一致，Gemini 尤其容易在超过两层引用后解析失败。工具参数如果需要递归结构（比如树形筛选条件），改成扁平化的字符串编码（如简单的表达式语法）由函数内部解析，而不是让模型直接生成嵌套 JSON。
- **`oneOf` / `anyOf` 联合类型**：改用"一个字段 + 一个枚举来选变体"的模式，比如不用 `oneOf: [{type: number}, {type: string}]`，而是拆成 `value_type: enum["number","string"]` + `value: string`（数字也用字符串传，函数内部按 `value_type` 解析）。
- **`additionalProperties`、`patternProperties`**：这类动态键的场景一律改成 `array of {key, value}`。

这个子集看起来"退化"了不少表达力，但实践下来，95% 以上的工具定义本来就不需要这些高级特性——真正复杂的是工具作者习惯性地把参数设计得过于"聪明"。强制走交集子集，反而会倒逼出更简单、模型更容易正确调用的参数设计。

## 四、编译到三家目标格式

有了 IR，编译器就是三个纯函数：`compileToOpenAI(tool: IRTool)`、`compileToAnthropic(tool: IRTool)`、`compileToGemini(tool: IRTool)`。核心逻辑是字段改名 + 少量类型映射，示例（TypeScript 伪代码）：

```typescript
function compileToOpenAI(tool: IRTool) {
  return {
    type: 'function',
    function: {
      name: tool.name,
      description: tool.description,
      parameters: irTypeToJsonSchema(tool.parameters),
    },
  };
}

function compileToAnthropic(tool: IRTool) {
  return {
    name: tool.name,
    description: tool.description,
    input_schema: irTypeToJsonSchema(tool.parameters),
  };
}

function compileToGemini(tool: IRTool) {
  return {
    name: tool.name,
    description: tool.description,
    parameters: irTypeToOpenApiSubset(tool.parameters), // integer 需映射为 number + format: 'int32'
  };
}
```

`irTypeToJsonSchema` 和 `irTypeToOpenApiSubset` 之所以要拆成两个函数而不是共用一个，是因为 Gemini 对 `integer` 类型的期望是 `{type: "number", format: "int32"}` 而非标准 JSON Schema 的 `{type: "integer"}"`——这类"看起来一样实际不一样"的细节，正是手写多套 Schema 时最容易漏改、也最难在 code review 中发现的地方。用编译器统一处理，等于把这类细节从"每次手写都要记住"变成"写一次测试用例锁死"。

## 五、强制调用与并行调用的行为对齐

工具 Schema 转换只是第一层，更隐蔽的不兼容在**调用行为控制**上：

- **强制调用单个工具**：三家参数名和结构都不同（见第一节表格），但语义基本一致，可以在 IR 层定义统一的 `forceCall?: string`（工具名或 `undefined`），编译时映射到各自字段。
- **并行调用控制**：这是最难对齐的一点。OpenAI 可以显式关闭并行；Anthropic 和 Gemini 没有独立开关，只能通过 system prompt 提示"每次只调用一个工具"来软控制，但不保证 100% 生效。如果业务逻辑强依赖"每轮只有一个工具调用"（比如工具有副作用、不支持批量），**不要依赖参数关闭并行，而要在应用层做防御**：拿到多个 `tool_calls` 时，只执行第一个，其余的返回一个"已跳过，请下一轮单独调用"的工具结果，让模型自己重新组织调用顺序。
- **工具结果格式**：三家对 `tool_result` / `function_response` 的角色标记（`role: "tool"` vs `role: "function"` vs 内嵌在 `user` 消息里的 `functionResponse` part）不同，这部分建议和请求端 IR 分开单独做一层 `ToolResultAdapter`，避免和参数 Schema 编译器耦合在一起，职责边界更清晰。

关于并行工具调用的具体测试方法和各家默认行为的实测数据，可以参考 [LLM Function Calling 并行调用机制](/blog/llm-function-calling-parallel/)，这里只强调工程上的应对策略。

## 六、测试策略：契约测试而不是端到端测试

兼容层的测试重点不是"调用真实 API 看返回对不对"，而是**契约测试**：给定一个 IR 工具定义，编译输出的三份 Schema 分别过一遍三家官方（或非官方镜像的）JSON Schema Validator，确认结构合法。这一层测试完全可以离线跑，不消耗任何 token，也不依赖真实 API Key，适合放进 CI 每次提交都跑。

真正需要打真实 API 的，只是"模型是否能正确理解 IR 描述并生成合法参数"这类语义层面的验证，这部分建议做成小规模回归集（10~20 个典型工具场景），定期跑而不是每次提交都跑，控制成本。如果需要多模型比价和路由策略配合测试，可以参考 [多模型成本智能路由方案](/blog/multi-model-cost-routing/) 里的路由设计，把"契约测试通过"作为路由候选池的准入条件之一——不合法的 Schema 直接从候选池剔除，避免线上出现某个模型返回工具调用失败却难以定位是路由问题还是 Schema 问题。

## 七、什么时候不值得做这层兼容层

如果项目只固定用一家模型，或者工具集很小（不超过 5 个）且不常变动，手写三份 Schema 的成本远低于开发一套编译器的成本，不建议提前做这层抽象。IR + 编译器的收益是在"工具数量持续增长 + 需要多模型路由或热切换"这两个条件同时成立时才会显现——通常是工具数量超过 15~20 个、且团队已经在实际做多模型路由决策的阶段。过早引入反而增加了理解成本和维护负担。

## 八、相关阅读

- [Function Calling vs Tool Use 差异辨析](/blog/function-calling-vs-tool-use/)
- [Gemini Function Calling 工程实践](/blog/gemini-function-calling-guide/)
- [LLM Function Calling 并行调用机制](/blog/llm-function-calling-parallel/)
- [多模型成本智能路由方案：让 AI 调用自动选最优性价比](/blog/multi-model-cost-routing/)

如果你的多模型 Agent 项目正被这类 API 差异反复拖慢开发进度，不妨用 [YoTradeApi](https://yotradeapi.com) 统一网关屏蔽底层调用细节，专注在业务逻辑和 Schema 设计本身。
