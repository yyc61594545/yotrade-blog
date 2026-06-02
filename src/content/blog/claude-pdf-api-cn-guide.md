---
title: Claude PDF 输入 API 国内使用指南
description: 详解 Claude API 的 PDF 文档输入功能：支持哪些模型、如何构造请求、国内如何通过中转稳定调用，附完整代码示例。
keywords:
  - Claude PDF API
  - Claude 文档理解
  - Claude API 国内使用
  - Anthropic PDF 输入
  - Claude 文件上传
pubDate: '2026-06-02'
updatedDate: '2026-06-02'
canonical: https://blog.yotradeapi.com/blog/claude-pdf-api-cn-guide/
tags:
  - Claude
  - PDF
  - API
  - 技术教程
category: 技术深度
heroImage: ../../assets/blog-placeholder-4.jpg
---

Claude 自 claude-3-5-sonnet 系列起支持直接输入 PDF 文档，无需先把 PDF 转成文字再喂给模型。这对需要处理合同、研报、技术文档的场景来说非常实用。本文从 API 结构讲起，给出国内可用的完整接入方案。

## 一、Claude PDF 输入支持的模型范围

并非所有 Claude 模型都支持 PDF 输入，目前（2026 年 6 月）的支持情况如下：

| 模型 | PDF 输入支持 |
|------|------------|
| claude-opus-4-8 | ✓ |
| claude-sonnet-4-6 | ✓ |
| claude-haiku-4-5 | ✓ |
| claude-3-5-sonnet-20241022 | ✓ |
| claude-3-5-haiku-20241022 | ✓ |
| claude-3-opus / claude-3-haiku | ✗ |

**使用 PDF 输入时，建议用 claude-sonnet-4-6 或更高版本**，这些模型对文档理解做了专项优化，效果明显优于 claude-3 系列。

## 二、PDF 输入的 API 结构

Claude 的 PDF 输入通过 `content` 数组中的 `document` 类型 block 实现，格式如下：

```json
{
  "model": "claude-sonnet-4-6",
  "max_tokens": 2048,
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "document",
          "source": {
            "type": "base64",
            "media_type": "application/pdf",
            "data": "<base64编码的PDF内容>"
          }
        },
        {
          "type": "text",
          "text": "请总结这份文档的主要内容，重点提炼关键结论。"
        }
      ]
    }
  ]
}
```

关键点：
- `type` 必须是 `document`（不是 `image`）
- `source.type` 目前只支持 `base64`（URL 引用方式不支持 PDF）
- `media_type` 固定为 `application/pdf`
- PDF 内容需要用 Base64 编码后放入 `data` 字段

## 三、Python 完整示例

### 3.1 基础用法（读取本地 PDF）

```python
import anthropic
import base64

def read_pdf_base64(file_path: str) -> str:
    with open(file_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")

client = anthropic.Anthropic(
    api_key="YOUR_API_KEY",
    base_url="https://api.yotradeapi.com"  # 国内中转
)

pdf_data = read_pdf_base64("report.pdf")

message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=2048,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": pdf_data,
                    },
                },
                {
                    "type": "text",
                    "text": "请总结这份 PDF 的核心内容，用中文回答。",
                },
            ],
        }
    ],
)

print(message.content[0].text)
```

### 3.2 带 cache_control 的用法（适合多轮问答）

如果要对同一份 PDF 问多个问题，可以用 `cache_control` 缓存文档内容，大幅降低费用：

```python
import anthropic
import base64

client = anthropic.Anthropic(
    api_key="YOUR_API_KEY",
    base_url="https://api.yotradeapi.com"
)

pdf_data = read_pdf_base64("annual_report.pdf")

# 第一次请求：写入缓存
response1 = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": pdf_data,
                    },
                    "cache_control": {"type": "ephemeral"},  # 开启缓存
                },
                {
                    "type": "text",
                    "text": "这份年报的营收增长率是多少？",
                },
            ],
        }
    ],
)

print(response1.content[0].text)
print("缓存使用情况:", response1.usage)
```

`cache_control` 的 `ephemeral` 类型会将文档 token 缓存约 5 分钟。在这 5 分钟内对同一文档发起的请求，文档部分的 token 费用可以降低约 90%，输入 token 的计费按缓存读取价格计算（远低于普通输入）。

## 四、Node.js 示例

```typescript
import Anthropic from "@anthropic-ai/sdk";
import fs from "fs";

const client = new Anthropic({
  apiKey: process.env.CLAUDE_API_KEY,
  baseURL: "https://api.yotradeapi.com", // 国内中转
});

async function analyzePdf(filePath: string, question: string) {
  const pdfBuffer = fs.readFileSync(filePath);
  const pdfBase64 = pdfBuffer.toString("base64");

  const response = await client.messages.create({
    model: "claude-sonnet-4-6",
    max_tokens: 2048,
    messages: [
      {
        role: "user",
        content: [
          {
            type: "document",
            source: {
              type: "base64",
              media_type: "application/pdf",
              data: pdfBase64,
            },
          },
          {
            type: "text",
            text: question,
          },
        ],
      },
    ],
  });

  return response.content[0].type === "text" ? response.content[0].text : "";
}

// 使用示例
analyzePdf("contract.pdf", "列出合同中的关键条款和违约条件").then(console.log);
```

## 五、PDF 大小和限制

使用前需了解的限制（近似数字，以官方最新文档为准）：

| 限制项 | 数值 |
|--------|------|
| 单个 PDF 最大大小 | 32 MB |
| 单个请求最多 PDF 数量 | 100 个（估算） |
| 单个 PDF 最大页数 | 无硬性限制（但 token 有上限） |
| 支持的内容类型 | 文字、图表、表格 |
| 不支持的内容 | 加密 PDF、动态表单 |

**关于 token 消耗**：PDF 的每一页大约消耗 1500–3000 个 token（取决于文字密度和图表数量）。一份 20 页的技术文档，文档本身大约消耗 3–6 万 token，用 `cache_control` 可以显著降低多轮对话的成本。

## 六、国内使用的网络方案

直接调用 `api.anthropic.com` 在国内需要代理，且稳定性难以保证。常见方案有两种：

**方案一：配置代理（适合个人开发者）**

```python
import anthropic
import httpx

client = anthropic.Anthropic(
    api_key="YOUR_API_KEY",
    http_client=httpx.Client(proxy="http://127.0.0.1:7890"),
)
```

缺点：代理稳定性影响服务可用性，生产环境不推荐。

**方案二：API 中转（适合生产和团队）**

```python
client = anthropic.Anthropic(
    api_key="YOUR_RELAY_API_KEY",
    base_url="https://api.yotradeapi.com",  # 只需改这一行
)
```

中转服务在国内有节点，延迟低、稳定性高，代码无需其他改动，直接支持 PDF 输入、流式输出、prompt caching 等所有功能。

## 七、常见错误排查

**错误 1：`invalid_request_error - document type not supported`**

原因：使用了不支持 PDF 的旧模型（如 claude-3-haiku）。
解决：换成 claude-sonnet-4-6 或 claude-opus-4-8。

**错误 2：`request_too_large`**

原因：PDF 文件超过大小限制，或者单次 token 超过模型上下文窗口。
解决：拆分 PDF，或者先提取关键页面再发送。

**错误 3：Base64 解码错误**

原因：编码时使用了 URL-safe 的 Base64 变体。
解决：使用标准 Base64（Python 的 `base64.standard_b64encode`，而非 `base64.urlsafe_b64encode`）。

**错误 4：中文内容识别不准**

原因：PDF 是扫描件（图片），文字没有嵌入。
解决：先用 OCR 提取文字，或者用支持图片输入的方式逐页处理。

## 八、实际应用场景参考

以下是 PDF 输入 API 在实际项目中的典型用途：

- **合同审查**：上传合同 PDF，让 Claude 列出关键条款、风险点和缺失项
- **研报分析**：批量处理行业研报，提取数据和结论后写入数据库
- **学术论文总结**：快速提炼 Abstract 之外的核心方法和实验结果
- **财报解读**：分析上市公司年报，提取关键财务指标
- **技术文档问答**：把产品手册上传后，实现自然语言问答

## 相关阅读

- [Anthropic Batch API 国内使用指南](/blog/anthropic-batch-api-cn-guide/)
- [Claude Code 国内网络配置指南](/blog/claude-code-on-cn-network/)
- [AI API 中转 vs 自搭 VPN：国内开发者怎么选](/blog/ai-api-relay-vs-self-vpn/)
- [AI API 中转服务稳定性测试报告](/blog/ai-api-relay-stability-test/)

处理 PDF 文档需要稳定的 API 访问，[YoTradeApi](https://yotradeapi.com) 提供国内直连的 Claude API 中转，支持 PDF 输入、prompt caching 等全部功能，人民币付款开箱即用。
