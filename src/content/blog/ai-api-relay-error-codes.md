---
title: AI API 中转常见错误码排查手册
description: 401/403/404/429/500/502/504 全套错误码排查方法，针对 Claude、OpenAI、Gemini 协议在国内中转下的典型故障与处理流程。
keywords:
- api 中转 错误码
- 401 unauthorized api
- 429 too many requests
- 502 bad gateway api
- claude api 报错
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/ai-api-relay-error-codes/
tags:
- 故障排查
- 错误码
- API 中转
- 调试
category: 故障排查
heroImage: ../../assets/blog-placeholder-5.jpg
---

# AI API 中转常见错误码排查手册

任何一家中转都不可能 100% 稳。出问题的时候，能不能 3 分钟内定位是"自己配置错"还是"网关故障"，决定了你今天工作能不能继续。这份手册按 HTTP 状态码组织，每个错误给最小可复现命令与处理流程。

## 一、通用排查工作流

遇到报错先按这个顺序排查：

1. **curl 重现**：脱离 SDK，用最简 curl 看返回。
2. **看 response body**：网关大部分会在 body 里写具体原因。
3. **核对 base_url / key / model**：80% 问题在这三个。
4. **查网关后台**：用量、限频、模型可用性。
5. **换模型 / 换 endpoint**：定位是模型层还是协议层。
6. **联系网关支持**：上面都排除还有问题。

最小 curl 模板（OpenAI Compatible）：

```bash
curl -i https://yotradeapi.com/v1/chat/completions \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model":"claude-sonnet-4-6",
    "messages":[{"role":"user","content":"hi"}],
    "stream":false,
    "max_tokens":16
  }'
```

Anthropic 协议：

```bash
curl -i https://yotradeapi.com/v1/messages \
  -H "x-api-key: $KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "Content-Type: application/json" \
  -d '{
    "model":"claude-sonnet-4-6",
    "max_tokens":16,
    "messages":[{"role":"user","content":"hi"}]
  }'
```

`-i` 返回完整响应头，能看到限流头 `Retry-After`、`X-RateLimit-Remaining` 等关键信息。

## 二、4xx 错误：客户端问题

### 400 Bad Request

含义：请求格式不对。

典型原因：

- 缺 `messages` 或 `max_tokens`
- JSON 序列化错误（引号、逗号）
- `model` 字段类型错（写成数字）
- Anthropic 协议没带 `anthropic-version` 头

排查：

```bash
echo "$REQ_BODY" | jq .   # 先确认 JSON 合法
```

### 401 Unauthorized

含义：身份认证失败。

最常见三种：

| 现象 | 原因 |
| --- | --- |
| `Invalid API key` | Key 写错或被回收 |
| `API key expired` | 后台已停用 |
| `Unauthorized` 无具体描述 | 协议错（OpenAI key 走到了 Anthropic 端点等） |

处理：

1. 复制粘贴 key 时检查前后空格
2. 网关后台确认 key 状态
3. 确认 header 写法：OpenAI 用 `Authorization: Bearer xxx`，Anthropic 用 `x-api-key: xxx`

### 402 Payment Required

含义：余额不足或订阅过期。

直接看网关后台余额。OpenAI 官方多用这个码表示账户欠费。

### 403 Forbidden

含义：身份对但没权限。

| 子原因 | 处理 |
| --- | --- |
| Key 不支持目标模型 | 在网关后台开通该模型 |
| 地域限制 | 换出口 IP |
| 内容被拒绝（moderation） | 调整 prompt |

### 404 Not Found

含义：端点或资源不存在。

最容易踩的坑：

- `base_url` 多写或少写 `/v1`
- 调 `/responses` 但网关只支持 `/chat/completions`
- 模型名错（注意大小写、版本号）

curl 命中后：

```
HTTP/1.1 404 Not Found
{"error":{"message":"Unknown endpoint /v1/embeddings"}}
```

`Unknown endpoint` 说明网关没接这个端点，去看支持列表。

### 408 Request Timeout

客户端没在 server 等待窗口内发完请求。中转下少见，多是网络阻塞导致。

### 422 Unprocessable Entity

JSON 合法但语义不对。常见：

- `temperature` 超出 0–2
- `max_tokens` 超出模型上限
- 工具 schema 不合法
- `tool_choice` 值不在允许集合内

### 429 Too Many Requests

含义：超限流。**最重要的状态码之一**。

看 response header：

```
HTTP/1.1 429 Too Many Requests
Retry-After: 5
X-RateLimit-Limit-Requests: 60
X-RateLimit-Remaining-Requests: 0
X-RateLimit-Reset-Requests: 5s
```

如果有 `Retry-After`，按它等。如果没有，固定 5–10s 退避。

常见触发：

- **RPM 超限**：单位时间请求数太多。降并发。
- **TPM 超限**：单位时间 token 数太多。压缩上下文。
- **日配额耗尽**：换 key 或等次日。

OpenAI 协议下的 429 还可能是模型层面限流（rate_limit_exceeded vs tokens_limit_exceeded），细看 message。

## 三、5xx 错误：服务端 / 上游问题

### 500 Internal Server Error

含义：上游异常。可能原因：

- 模型供应商当时挂了
- 请求 prompt 触发了某个边界 bug
- 网关内部异常

最小处理：等 30s 重试一次。**不要立刻连续重试**，会被风控。

### 502 Bad Gateway

含义：网关连不上上游。

国内中转下出现 502 几乎都是网关到模型供应商之间的网络问题。处理：

- 切其它模型（Claude 502 时试 GPT，反之亦然）
- 等 1–2 分钟再试
- 检查网关 status page

### 503 Service Unavailable

含义：服务维护或过载。

通常会附 `Retry-After` 头，按它等。

### 504 Gateway Timeout

含义：网关等上游响应超时。

国内长 prompt 容易出 504：上游处理太慢，网关默认超时（一般 60–120s）就断了。处理：

- 缩短 prompt（特别是单次 50k+ 输入）
- 拆任务：用多次短请求代替一次长请求
- 换模型：Sonnet/Haiku 比 Opus 快

## 四、连接层错误（无 HTTP 状态码）

### connection reset / TLS handshake failed

底层 TCP 或 TLS 握手失败。**纯网络问题**。

排查：

```bash
nslookup yotradeapi.com
traceroute yotradeapi.com   # macOS/Linux
tracert yotradeapi.com      # Windows
```

如果 DNS 解析失败，换 DNS（8.8.8.8 / 1.1.1.1）。
如果 traceroute 在某一跳卡住，网络绕路，需要换出口。

### read timeout

客户端 socket 读超时。把 timeout 调大：

```python
client = OpenAI(timeout=120.0)
```

### chunked encoding error / stream interrupted

流式响应中途断。原因：

- 中间代理压缩 SSE
- 网关 keep-alive 不够长
- 中转节点切换

短期缓解：换非流式 `stream=false`，确认是否真的是模型问题。长期：联系网关支持。

## 五、按工具排错

### Cursor 报错

Cursor 错误一般在右下角弹一个小通知。看 **Help → Logs** 里 `Cursor.log` 的最后一段。

典型：

- `Request failed with status 401`：API Key 错
- `Failed to fetch`：网络层

### Claude Code 报错

Claude Code 错误会写在终端。带 `--verbose` 重跑能看完整请求：

```bash
claude --verbose
```

### Cline 报错

Cline 错误显示在 VSCode 侧栏底部。完整 trace 在 **Output → Cline** 面板。

## 六、给自己写一个错误码 dashboard

如果你有多家中转，建议在自己机器上跑一个简单的探针：

```python
import time, requests

PROBES = [
    ("yotrade", "https://yotradeapi.com/v1/chat/completions", "sk-yo-..."),
    ("backup",  "https://other-relay.example.com/v1/chat/completions", "sk-bk-..."),
]

PAYLOAD = {
    "model": "claude-sonnet-4-6",
    "messages": [{"role": "user", "content": "ping"}],
    "max_tokens": 4,
}

for name, url, key in PROBES:
    t0 = time.time()
    try:
        r = requests.post(url, headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }, json=PAYLOAD, timeout=30)
        print(f"{name}: {r.status_code} {round(time.time()-t0,2)}s")
    except Exception as e:
        print(f"{name}: ERR {e}")
```

每 5 分钟跑一次，把结果写 sqlite 或 csv。一周后你就有了一份"哪家中转什么时段稳"的真实数据。

## 七、相关阅读

- [Cursor API 中转怎么选：2026 实用清单](/blog/2026-05-15-cursor-api-relay-recommendation-2026/)
- [Claude Code 镜像国内配置完整指南](/blog/claude-code-mirror-cn-setup/)
- [OpenAI SDK base_url 国内配置实战](/blog/openai-sdk-base-url-cn/)
- [AI API 中转稳定性测试方法](/blog/ai-api-relay-stability-test/)

需要带完整用量日志、错误码可查的中转？[YoTradeApi](https://yotradeapi.com) 在后台展示每条请求的状态码、耗时与原因，方便排查。
