---
title: Continue.dev 接自定义端点：私有部署与非标准网关踩坑指南
description: 讲清楚 Continue.dev 如何对接自建网关、私有部署模型等非官方自定义端点，涵盖 provider 选型、鉴权头、流式兼容与多端点路由排错。
keywords:
  - Continue.dev 自定义端点
  - Continue.dev 私有部署
  - OpenAI 兼容网关
  - Continue.dev provider
  - Continue.dev 排错
pubDate: '2026-09-10'
updatedDate: '2026-09-10'
canonical: https://blog.yotradeapi.com/blog/continue-dev-custom-endpoint/
tags:
  - Continue.dev
  - 自定义端点
  - API 中转
  - 工具配置
category: 工具配置
---

Continue.dev 官方文档把"接第三方中转"和"接自建端点"混在一起讲，导致很多人以为只要 `apiBase` 填对了就万事大吉。实际上，公开的中转服务（比如 [Continue.dev 国内 API 配置完整教程](/blog/continue-dev-cn-setup/) 里讲的那种）和你自己搭的网关、私有部署模型，在 Continue.dev 里走的是同一套 `provider: openai` 适配器，但兼容性问题完全不是一个量级。本文只讲后者——当你的端点不是一个成熟商业中转、而是自己搭的网关、内网私有部署、或者非标准实现时，该怎么接、怎么排错。

如果你还没装过 Continue.dev、不熟悉 `config.yaml` 的基本结构，建议先看上面那篇打好基础，本文默认你已经能跑通一个标准中转端点。

## 一、先搞清楚"自定义端点"到底是哪一种

Continue.dev 里能塞进 `apiBase` 的端点，大致分三类，排错思路完全不同：

| 类型 | 例子 | 兼容性 |
|---|---|---|
| 成熟商业中转 | 按 OpenAI 协议完整实现的中转服务 | 高，照抄官方示例基本能跑 |
| 自建网关 | 公司内部用 FastAPI/Nginx 包装的转发层 | 中，取决于自己实现了多少 OpenAI 协议细节 |
| 本地/私有部署 | Ollama、vLLM、LM Studio、TGI | 中低，流式格式、字段命名经常和 OpenAI 有细微差异 |

第一类基本不用看这篇文章。后两类是本文的重点，问题几乎都出在"自己实现的端点没有 100% 复刻 OpenAI 协议"。

## 二、provider 该填 openai 还是自定义值

Continue.dev 的 `provider` 字段决定了它用哪套请求/响应解析逻辑，不是随便填的标签：

```yaml
models:
  - name: 内网网关
    provider: openai        # 只要端点是 OpenAI Chat Completions 协议，一律填 openai
    model: internal-qwen-72b
    apiBase: http://gateway.internal.company.com/v1
    apiKey: internal-token
    roles: [chat, edit]
```

关键认知：`provider: openai` 不代表"调用 OpenAI 官方"，而是代表"按 OpenAI 协议格式解析"。Ollama、vLLM 起的 OpenAI 兼容服务、你自己写的转发层，只要暴露的是 `/v1/chat/completions` 这套接口形状，都应该填 `openai`，而不是去找一个不存在的"custom"值。

Ollama 本地服务是例外——Continue.dev 给它单独做了 `provider: ollama`，走的是 Ollama 原生协议而不是 OpenAI 兼容层，两者不能混填，否则会报字段解析错误。

## 三、自定义鉴权头：不是所有网关都用 Bearer Token

标准 OpenAI 协议用 `Authorization: Bearer <key>`，但很多自建网关会用自定义 header（比如内部单点登录签发的 token、自定义的 `X-API-Key`）。Continue.dev 支持通过 `requestOptions.headers` 覆盖或追加请求头：

```yaml
models:
  - name: 内网网关
    provider: openai
    model: internal-qwen-72b
    apiBase: http://gateway.internal.company.com/v1
    apiKey: placeholder-not-used
    requestOptions:
      headers:
        X-API-Key: your-internal-token
        X-Team-Id: infra-team
    roles: [chat]
```

注意：即使鉴权走自定义 header，`apiKey` 字段也建议填一个非空占位符，部分版本的 Continue.dev 在 `apiKey` 为空时会跳过整个请求头组装逻辑，导致自定义 header 也一起丢失。

## 四、流式响应格式不一致是最常见的报错源

自建网关和本地部署最容易在**流式返回**上和标准 OpenAI 协议出现细微偏差，典型症状：

- Continue.dev 侧栏卡住不动，网络面板能看到数据在传但 UI 不刷新 → 大概率是 SSE 的 `data:` 前缀或 `[DONE]` 结束标记没有严格对齐
- 输出内容被截断或重复 → 网关把多个 chunk 合并/拆分的方式和 OpenAI 官方不一致
- Autocomplete 完全没反应 → 很多自建网关只实现了 Chat Completions，没实现 Completions（legacy）接口，而 Continue.dev 的自动补全默认走 legacy 接口

针对最后一种情况，Continue.dev 提供了强制切换开关：

```yaml
models:
  - name: 自建补全模型
    provider: openai
    model: internal-coder
    apiBase: http://gateway.internal.company.com/v1
    apiKey: placeholder
    useLegacyCompletionsEndpoint: false   # 强制走 chat/completions 而不是 completions
    roles: [autocomplete]
```

排查流式问题最快的办法不是直接调 Continue.dev，而是先用 `curl` 手动测试端点是否符合协议：

```bash
curl http://gateway.internal.company.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-internal-token" \
  -d '{
    "model": "internal-qwen-72b",
    "messages": [{"role": "user", "content": "hello"}],
    "stream": true
  }'
```

如果 `curl` 返回的流式数据本身就不规范（缺 `data:` 前缀、没有 `[DONE]`），问题在网关侧，不在 Continue.dev，先修网关再回来调插件配置能少走很多弯路。

## 五、多个自定义端点同时接入：按角色路由而不是按端点二选一

企业内部常见场景是"公司网关跑对话、本地小模型跑补全、另一个私有部署跑 embedding"，这时不要纠结用哪一个端点，Continue.dev 的 `roles` 机制本来就是为多端点路由设计的：

```yaml
models:
  - name: 公司网关-对话
    provider: openai
    model: internal-qwen-72b
    apiBase: http://gateway.internal.company.com/v1
    apiKey: placeholder
    roles: [chat, edit]

  - name: 本地-补全
    provider: ollama
    model: qwen2.5-coder:7b
    apiBase: http://localhost:11434
    roles: [autocomplete]

  - name: 私有-embedding
    provider: openai
    model: internal-embedding-v2
    apiBase: http://embed.internal.company.com/v1
    apiKey: placeholder
    roles: [embed]
```

三个端点互不干扰，各自只承担自己声明的角色。出问题时也更好定位——先看是哪个角色报错，就去查对应端点，不用把整个配置当成一个黑盒排查。

## 六、私有部署模型名不匹配的坑

vLLM/TGI 起服务时，`model` 字段通常要求填服务端实际加载的模型路径或别名，和你在 `config.yaml` 里习惯性填的"友好名字"经常对不上，报错通常是 `model not found` 或 `404`。排查顺序：

1. 先用 `curl <apiBase>/models` 看服务端实际暴露的模型列表（大多数 OpenAI 兼容服务都实现了这个只读接口）
2. 把返回列表里的 `id` 原样填进 `config.yaml` 的 `model` 字段，不要自己编
3. 如果服务端没实现 `/models` 接口，去问维护网关的人要准确的模型标识，不要靠猜

## 七、相关阅读

- [Continue.dev 国内 API 配置完整教程](/blog/continue-dev-cn-setup/)
- [Cline 国内 API 配置详解](/blog/cline-cn-api-setup/)
- [OpenAI SDK base_url 国内配置实战](/blog/openai-sdk-base-url-cn/)
- [LLM API 限速（Rate Limit）处理完整指南](/blog/llm-rate-limit-handling/)

如果你的自建网关调试太麻烦、只是想先跑通一个标准可靠的 OpenAI 兼容端点做参照，[YoTradeApi](https://yotradeapi.com) 提供开箱即用的中转服务，配置方式和本文的 `provider: openai` 完全一致，可以先拿它验证 Continue.dev 侧的配置没问题，再回头排查自建端点。
