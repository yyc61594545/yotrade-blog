---
title: 国产模型接入实战：Qwen、DeepSeek、GLM、Kimi 怎么统一接
description: 国产大模型（Qwen、DeepSeek、智谱 GLM、Kimi、豆包）的 API 接入实战，含协议兼容性、统一网关方案、成本对比与选型建议。
keywords:
  - 国产模型接入
  - qwen api 接入
  - deepseek api 接入
  - 国产大模型 openai 兼容
  - 国内模型网关
pubDate: '2026-09-05'
updatedDate: '2026-09-05'
canonical: https://blog.yotradeapi.com/blog/cn-domestic-model-integration/
tags:
  - 国产模型
  - Qwen
  - DeepSeek
  - API 中转
  - 国内场景
category: 国内场景
---

国产大模型这两年密集发布，Qwen、DeepSeek、智谱 GLM、Kimi、豆包各有强项，但真要在项目里同时接几家，会发现一个很现实的问题：**每家的 SDK、鉴权方式、参数命名都不完全一样**，接一个能用，接五个就是五套维护成本。本文不重复讲某一家模型的能力评测（那些参考文末链接），聚焦"怎么把它们统一接进同一套代码"这件事。

## 一、先分清两条接入路径

国产模型的开放平台基本分两类协议风格：

| 协议风格 | 代表厂商 | 特点 |
| --- | --- | --- |
| OpenAI Chat Completions 兼容 | DeepSeek、智谱 GLM、Moonshot Kimi、部分 Qwen 网关 | 换 `base_url` + `model` 基本能直接跑 |
| 自定义协议 | 阿里云百炼原生 Qwen SDK、百度文心原生 SDK、字节豆包原生 SDK | 字段名、流式格式、函数调用结构都不同 |

**能用 OpenAI 兼容协议的，优先用 OpenAI 兼容协议**——同一份 `openai` SDK 代码，改两行 `base_url` 和 `model` 就能切厂商，不需要为每家单独写适配层。只有当某个功能（比如某家独有的联网搜索插件、多模态专属接口）只在原生 SDK 里暴露时，才值得为它单独接一套。

## 二、五分钟跑通：以 DeepSeek 为例

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://api.deepseek.com/v1",
    api_key="sk-xxx",
)

resp = client.chat.completions.create(
    model="deepseek-chat",
    messages=[{"role": "user", "content": "用一句话解释向量数据库"}],
)
print(resp.choices[0].message.content)
```

换成智谱 GLM 或 Moonshot Kimi，只需要改 `base_url` 和 `model`：

```python
# 智谱 GLM
base_url = "https://open.bigmodel.cn/api/paas/v4"
model = "glm-4-plus"

# Moonshot Kimi
base_url = "https://api.moonshot.cn/v1"
model = "moonshot-v1-8k"
```

代码结构完全不变，这是选择 OpenAI 兼容协议的最大好处：**模型切换是配置问题，不是代码问题**。

## 三、Qwen 的两条路：百炼原生 vs 兼容模式

Qwen 稍微特殊，阿里云百炼平台同时提供两种接入方式：

```python
# 方式一：DashScope 原生 SDK（功能最全，含部分专属参数）
import dashscope
resp = dashscope.Generation.call(model="qwen-max", prompt="...")

# 方式二：OpenAI 兼容模式（推荐，除非需要原生专属功能）
base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
model = "qwen-max"
```

除非你需要 DashScope 原生 SDK 里的一些专属能力（比如某些多模态或 Agent 编排接口），**统一走兼容模式**能让 Qwen 和其他厂商共用同一套调用代码，这也是[《Qwen 与 Claude 的国内开发者对比》](/blog/qwen-vs-claude-cn-developer/)里提到过的接入建议。

## 四、统一网关：一份 Key 管所有模型

同时接五六家模型，账单、Key 管理、限流策略都会分散在五六个后台。更省心的做法是在应用和各家 API 之间加一层**统一网关**，网关负责：

1. 把不同厂商的协议差异抹平，应用侧永远只对接一套 OpenAI 兼容接口
2. 统一计费、统一日志，不用登五个后台对账
3. 某家模型限流或故障时，网关层做熔断/降级切换到备用模型

```python
client = OpenAI(
    base_url="https://yotradeapi.com/v1",
    api_key="sk-yo-xxx",
)

# 同一份代码，model 传哪个厂商的都行
for model in ["deepseek-chat", "qwen-max", "glm-4-plus", "claude-sonnet-4-6"]:
    resp = client.chat.completions.create(model=model, messages=[...])
```

这种架构对做多模型对比测试、或者需要"国产模型兜底、国际模型主力"策略的团队尤其有用——不用为每次切换重新申请 Key、重新改代码。

## 五、成本与场景选型对照

不同国产模型的定价和强项差异很大，实战里按场景选：

| 场景 | 推荐模型方向 | 理由 |
| --- | --- | --- |
| 中文长文本理解、公文/合同类 | GLM、Qwen-Max | 中文语料训练权重高，长文本理解稳 |
| 代码生成 | DeepSeek Coder、Claude Sonnet | 代码基准分数领先，详见[《DeepSeek Coder 深度评测》](/blog/cn-deepseek-coder-deep-review/) |
| 高并发低成本客服/摘要类 | DeepSeek、豆包 | 单 token 价格低，适合走量场景 |
| 复杂推理、多步 Agent | DeepSeek R1、Claude Thinking | 推理链路更完整，参考[对比文章](/blog/deepseek-r1-vs-claude-thinking/) |
| 多模态（图片理解） | Qwen-VL、豆包视觉版 | 国产多模态覆盖场景更贴近中文互联网内容 |

**不要迷信"一个模型打天下"**——实战里更常见的是按任务类型路由到不同模型，这也是统一网关的价值所在：路由逻辑写在应用层，底层模型随时可换。

## 六、鉴权与合规注意事项

国产模型平台的实名认证、企业资质要求比国际平台严格不少，接入前建议提前确认：

- 部分平台（尤其涉及多模态、语音）要求企业实名认证才能开通高并发额度
- 内容安全审核策略比国际平台更严，实测阶段建议先跑一批业务真实语料测试拒答率
- 部分厂商的免费额度有时间窗口限制（比如注册后 30 天内有效），批量测试要在有效期内完成

## 七、一个实用的降级链设计

生产环境不建议单一依赖某一家国产模型，简单的降级链示例：

```python
FALLBACK_CHAIN = [
    "deepseek-chat",      # 主力，成本低
    "glm-4-plus",         # 备用一：DeepSeek 限流时切
    "qwen-max",           # 备用二
]

for model in FALLBACK_CHAIN:
    try:
        resp = client.chat.completions.create(model=model, messages=messages, timeout=15)
        break
    except Exception:
        continue
```

配合统一网关的话，这层降级逻辑甚至可以直接配置在网关侧，应用代码不需要感知失败重试的细节。

## 八、相关阅读

- [Qwen 与 Claude 的国内开发者对比](/blog/qwen-vs-claude-cn-developer/)
- [DeepSeek Coder 深度评测](/blog/cn-deepseek-coder-deep-review/)
- [DeepSeek R1 与 Claude Thinking 对比](/blog/deepseek-r1-vs-claude-thinking/)
- [智谱 GLM 开发者评测](/blog/cn-zhipu-glm-developer-review/)
- [国内网络下的 AI API 中转 vs 自建 VPN](/blog/ai-api-relay-vs-self-vpn/)

如果不想为每家国产模型单独管一套 Key 和账单，[YoTradeApi](https://yotradeapi.com) 支持国产与国际主流模型统一接入，一个 Key 按上面的代码直接切换。
