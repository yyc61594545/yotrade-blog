---
title: 走 Anthropic Direct vs Bedrock vs 中转：怎么选
description: 调用 Claude 模型的三种主要路径对比：Anthropic 官方直连、AWS Bedrock、API 中转。从合规、价格、可用性、运维角度选型。
keywords:
- anthropic bedrock
- claude bedrock vs direct
- aws bedrock claude
- claude api 中转
- claude 调用 路径
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/anthropic-bedrock-vs-direct/
tags:
- Anthropic
- Bedrock
- AWS
- 选型
- 合规
category: 模型评测
heroImage: ../../assets/blog-placeholder-1.jpg
---

# 走 Anthropic Direct vs Bedrock vs 中转：怎么选

调用 Claude 模型有三条主路径：Anthropic 官方、AWS Bedrock、第三方中转。每条都有用武之地。本文从 6 个维度对比。

## 一、三条路径概览

| 路径 | 适合 |
| --- | --- |
| Anthropic Direct | 海外团队、需要最新特性 |
| AWS Bedrock | 已有 AWS 基础设施、企业合规 |
| 中转 | 国内、灵活、跨厂商 |

## 二、可用性 / 网络

| 路径 | 国内可用 | 全球可用 |
| --- | --- | --- |
| Anthropic Direct | 网络受限 | ✓ |
| AWS Bedrock | 取决于 region | ✓ |
| 中转 | ✓ | 取决于中转 |

国内开发者**直连 Anthropic 不稳**，AWS Bedrock 部分 region（新加坡、东京）可达但延迟较高。**中转是国内最稳的选择**。

## 三、模型 / 特性可用性

| 特性 | Direct | Bedrock | 中转 |
| --- | --- | --- | --- |
| 最新模型 | 第一时间 | 滞后 1-4 周 | 看中转 |
| Beta features | ✓ | 部分 | 看中转透传 |
| Extended thinking | ✓ | ✓ | 透传 |
| 1M context | ✓ | 部分 | 透传 |
| Computer use | ✓ | 部分 | 透传 |
| Prompt caching | ✓ | ✓ | 透传 |
| Skills | ✓ | 部分 | 看中转 |

**新特性 Direct 最快，Bedrock 慢一拍，中转看实现质量**。

## 四、价格

| 路径 | 价格水平 |
| --- | --- |
| Direct | 标准 |
| Bedrock | Direct × 1.0 ~ 1.1 |
| 中转 | 标准 ± 10% |

价格差不会数量级。**真正影响成本的是 caching 是否生效**——好的中转和官方差异极小。

## 五、合规 / 数据

| 路径 | 数据流 | 适合谁 |
| --- | --- | --- |
| Direct | 直发 Anthropic | 数据出境 OK |
| Bedrock | 留在 AWS | 已有 AWS 合规框架 |
| 中转 | 经过中转方 | 看中转方政策 |

**严格合规要求**（金融 / 医疗 / 政府）：

- 全球团队 + AWS：Bedrock
- 国内 + 严格：考虑自建 LiteLLM Proxy + 直连
- 一般场景：中转完全 OK

详见 [AI API 中转的安全与合规边界](/blog/api-relay-security-compliance/)。

## 六、SDK / 集成

| SDK | Direct | Bedrock | 中转 |
| --- | --- | --- | --- |
| anthropic-sdk | ✓ 原生 | 需 boto3 | 改 base_url |
| openai-sdk 兼容 | ✗ | ✗ | ✓ |
| LiteLLM | ✓ | ✓ | ✓ |
| LangChain | ✓ | ✓ | ✓ |
| Claude Code | ✓ | ✗ 不直接 | ✓ |
| Cursor | 部分 | ✗ | ✓ |

**国内工具生态走中转最顺**，因为 base_url 改一行就行。

## 七、运维复杂度

| 路径 | 运维成本 |
| --- | --- |
| Direct | 极低（注册即用） |
| Bedrock | 中（AWS 账号 + IAM） |
| 中转 | 极低 |
| 自建 LiteLLM + Direct | 中（你运维 proxy） |

**普通用户**：Direct 或中转。**企业**：Bedrock 或自建。

## 八、限速

| 路径 | RPM/TPM |
| --- | --- |
| Direct | 看 tier / 已付钱 |
| Bedrock | 看 region quota |
| 中转 | 看中转配置 |

Bedrock 偶尔有 region 级别全局限速突发。**中转可以按 key 单独配额**。

## 九、决策矩阵

```
你的需求/场景：

A. 国内 + 不严格合规
   → 中转（最简单）

B. 国内 + 严格合规 + 中等规模
   → 自建 LiteLLM Proxy + 中转 / 直连

C. 国内 + 严格合规 + 大企业
   → 看是否能用 Bedrock（新加坡 region）
   → 或自建 + 多 fallback

D. 海外团队 + 已有 AWS
   → Bedrock

E. 海外团队 + 灵活
   → Direct

F. 跨厂商（Claude + GPT + Gemini）
   → 中转（最简单）/ LiteLLM（自建）
```

## 十、混合策略

很多团队最终是混合：

```
日常开发    → 中转（速度 + 灵活）
生产业务    → Bedrock 或 Direct（稳定 + 合规）
batch 任务  → 中转（成本最优）
关键 fallback → Direct（兜底）
```

LiteLLM 可以聚合多路径，给上游应用一个统一接口。详见 [LiteLLM 自部署 LLM 网关](/blog/litellm-cn-gateway-self-host/)。

## 十一、Bedrock 接入要点

```python
import boto3
import json

bedrock = boto3.client("bedrock-runtime", region_name="ap-northeast-1")

response = bedrock.invoke_model(
    modelId="anthropic.claude-sonnet-4-6-v1:0",
    body=json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1000,
        "messages": [{"role": "user", "content": "hi"}],
    }),
)
result = json.loads(response["body"].read())
```

要点：

- IAM 权限（bedrock:InvokeModel）
- 模型 ID 带 "anthropic." 前缀
- 不能用 Anthropic 官方 SDK 默认走法
- 部分 region 需先 enable 模型

## 十二、走 LiteLLM 统一抽象

```yaml
model_list:
  - model_name: claude-sonnet
    litellm_params:
      model: anthropic/claude-sonnet-4-6
      api_key: os.environ/ANTHROPIC_KEY

  - model_name: claude-sonnet
    litellm_params:
      model: bedrock/anthropic.claude-sonnet-4-6-v1:0
      aws_region_name: ap-northeast-1

  - model_name: claude-sonnet
    litellm_params:
      model: openai/claude-sonnet-4-6
      api_base: https://yotradeapi.com/v1
      api_key: os.environ/YOTRADE_KEY
```

三个上游同名，LiteLLM 自动负载均衡 + fallback。

## 十三、相关阅读

- [Claude Code 镜像国内配置完整指南](/blog/claude-code-mirror-cn-setup/)
- [LiteLLM 自部署 LLM 网关](/blog/litellm-cn-gateway-self-host/)
- [AI API 中转的安全与合规边界](/blog/api-relay-security-compliance/)
- [API Key 泄露应急响应](/blog/api-key-leak-emergency-response/)
- [OpenAI 兼容协议 vs Anthropic 原生协议](/blog/openai-compatible-vs-anthropic-protocol/)

国内场景，[YoTradeApi](https://yotradeapi.com/register) 一把 Key + Anthropic 原生协议 = 国内可用的最简路径。
