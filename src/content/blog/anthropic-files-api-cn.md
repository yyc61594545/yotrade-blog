---
title: Anthropic Files API 国内使用完整指南
description: 详解 Anthropic Files API 上传、管理文件并在 Claude 多轮对话中复用，解决国内访问障碍，含 Python 示例与费用分析。
keywords:
  - Anthropic Files API
  - Claude 文件上传 API
  - Files API 国内使用
  - Claude 文件管理
  - Anthropic API 中转
pubDate: '2026-06-07'
updatedDate: '2026-06-07'
canonical: https://blog.yotradeapi.com/blog/anthropic-files-api-cn/
tags:
  - Anthropic
  - Files API
  - Claude
  - 技术教程
category: 技术深度
heroImage: ../../assets/blog-placeholder-3.jpg
---

Anthropic 在 2025 年底推出了 **Files API**，允许开发者将文档、图片、PDF 等文件先上传到 Anthropic 的服务端，获得一个持久化的 `file_id`，之后在多轮对话或 Batch 请求中反复引用，而无需每次都重新传输原始数据。

对国内开发者而言，这个功能在节省带宽、提升稳定性方面意义明显——但能否在大陆网络环境中顺利使用，又有哪些坑，是本文要重点解答的。

## 一、Files API 解决了什么问题

在 Files API 推出之前，将文件发给 Claude 只有两种方式：

1. **Base64 内联**：把文件编码后塞进 `messages` 的 `content` 字段。每次请求都要重传，如果文件是 20MB 的 PDF，每轮对话就多 20MB 的上行流量。
2. **URL 引用**：把文件托管到公网，传入 URL。这要求文件服务器对 Anthropic 的爬取友好，且文件必须公开可访问。

Files API 的思路是：**先传一次，后续复用**。

| 对比维度        | Base64 内联           | Files API             |
|---------------|--------------------|--------------------|
| 每次请求流量   | 原文件大小           | 仅引用（几十字节）     |
| 文件生命周期   | 单次请求             | 最长 30 天            |
| 多轮对话复用   | 需重复上传           | 一个 `file_id` 复用   |
| Batch API 联动 | 需在 batch JSON 内嵌 | 直接引用 `file_id`    |
| 国内网络依赖   | 单次上传即可         | 上传一次，访问多次     |

对于**合同分析、财务报表审核、代码库批量审查**等场景，Files API 可以大幅降低 API 调用的网络成本和失败率。

## 二、Files API 的基本概念

### 2.1 文件存储期限

上传成功后，文件默认保留 **30 天**，之后自动删除。可以通过 API 手动提前删除。每个 Organization 的存储上限目前约为 100GB，单个文件最大 512MB（PDF 单页超过 100 张时建议分割）。

### 2.2 支持的文件类型

- **文档**：PDF（`application/pdf`）、纯文本（`text/plain`）、Markdown
- **图片**：JPEG、PNG、GIF、WebP（支持 vision 场景）
- **数据**：CSV（当作文本处理，需在 prompt 说明格式）

不支持 Word、Excel 的原始格式（需先转 PDF 或 CSV）。

### 2.3 计费逻辑

上传和存储本身**不额外收费**（截至 2026 年中）。费用发生在**引用文件时**，按实际读取的 token 数计算。如果同一文件在 Batch 中被 100 个请求引用，就计 100 次读取费用——但总费用仍然远低于每次 Base64 重传带来的延迟和重试成本。

## 三、国内网络环境下的访问现状

Anthropic 的 API 端点（`api.anthropic.com`）在中国大陆无法直连，Files API 的上传端点同样如此：

```
https://api.anthropic.com/v1/files
```

常见的解决方案有两种：

**方案 A：自建代理或 VPN**
在境外服务器搭建 Nginx 反向代理，将 `api.anthropic.com` 转发到本地可访问的域名。维护成本高，且 IP 随时可能被封。

**方案 B：使用 API 中转服务**
选择兼容 Anthropic 原生协议的 API 中转平台（如 YoTradeApi），将 `base_url` 替换为中转地址。这是大多数国内开发者的首选——无需自建基础设施，只需改一行配置。

本文后续示例均以**方案 B（API 中转）**为前提，但代码结构与直连完全一致，切换只需改 `base_url`。

## 四、环境准备

```bash
pip install anthropic>=0.40.0
```

设置环境变量：

```bash
# 如使用 API 中转
export ANTHROPIC_BASE_URL="https://api.yotradeapi.com"
export ANTHROPIC_API_KEY="your-relay-key"
```

初始化客户端：

```python
import anthropic
import os

client = anthropic.Anthropic(
    api_key=os.environ["ANTHROPIC_API_KEY"],
    base_url=os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
)
```

## 五、核心操作：上传、引用、删除

### 5.1 上传文件

```python
def upload_file(client: anthropic.Anthropic, file_path: str) -> str:
    """上传文件并返回 file_id"""
    with open(file_path, "rb") as f:
        response = client.beta.files.upload(
            file=(file_path.split("/")[-1], f, "application/pdf"),
        )
    print(f"上传成功: {response.id}")
    return response.id
```

返回的 `response.id` 格式类似 `file-abc123xyz`，保存好，后续引用都靠它。

### 5.2 列出已上传文件

```python
def list_files(client: anthropic.Anthropic):
    files = client.beta.files.list()
    for f in files.data:
        print(f"  {f.id}  {f.filename}  created={f.created_at}")
```

### 5.3 在对话中引用文件（PDF 示例）

```python
def analyze_pdf(client: anthropic.Anthropic, file_id: str, question: str) -> str:
    response = client.beta.messages.create(
        model="claude-opus-4-8",
        max_tokens=2048,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "file",
                            "file_id": file_id,
                        },
                    },
                    {
                        "type": "text",
                        "text": question,
                    },
                ],
            }
        ],
        betas=["files-api-2025-04-14"],
    )
    return response.content[0].text
```

注意两点：
- 必须在请求中加 `betas=["files-api-2025-04-14"]`（beta header）
- `source.type` 为 `"file"`，`file_id` 填上传返回的 ID

### 5.4 在图片分析中引用文件

```python
def analyze_image(client: anthropic.Anthropic, file_id: str, prompt: str) -> str:
    response = client.beta.messages.create(
        model="claude-opus-4-8",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "file",
                            "file_id": file_id,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        betas=["files-api-2025-04-14"],
    )
    return response.content[0].text
```

### 5.5 删除文件

```python
client.beta.files.delete(file_id)
print(f"已删除: {file_id}")
```

删除是立即生效的，之后引用该 `file_id` 会返回 404 错误。

## 六、与 Batch API 联动：批量处理的最优解

Files API 和 [Batch API](/blog/anthropic-batch-api-cn-guide/) 组合是处理大规模文档的利器。典型场景：对 500 份合同逐一做合规审查。

**传统做法**：500 个同步请求，每个都内嵌 PDF，网络稳定性是噩梦。

**Files API + Batch 做法**：

```python
import json

def build_batch_requests(client, pdf_paths: list[str], question: str) -> list[dict]:
    requests = []
    for i, path in enumerate(pdf_paths):
        file_id = upload_file(client, path)
        requests.append({
            "custom_id": f"contract-{i}",
            "params": {
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 1024,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "document",
                                "source": {"type": "file", "file_id": file_id},
                            },
                            {"type": "text", "text": question},
                        ],
                    }
                ],
            },
        })
    return requests

# 提交 batch
requests = build_batch_requests(client, pdf_paths, "请列出合同中的主要违约条款")
batch = client.beta.messages.batches.create(
    requests=requests,
    betas=["files-api-2025-04-14"],
)
print(f"Batch ID: {batch.id}")
```

Batch API 的费用是标准价的 50%，加上 Files API 避免了重复传输，合规批处理的总成本可以下降 60–70%。

## 七、多轮对话场景：同一文件贯穿整个会话

适合「先上传文件，然后用户不断追问」的场景，比如合同问答机器人：

```python
def contract_qa_bot(client, file_id: str):
    history = []
    
    # 第一轮：初始化文件上下文
    history.append({
        "role": "user",
        "content": [
            {
                "type": "document",
                "source": {"type": "file", "file_id": file_id},
            },
            {"type": "text", "text": "请先概括这份合同的主要条款。"},
        ],
    })
    
    while True:
        resp = client.beta.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            messages=history,
            betas=["files-api-2025-04-14"],
        )
        assistant_msg = resp.content[0].text
        history.append({"role": "assistant", "content": assistant_msg})
        
        print(f"Claude: {assistant_msg}\n")
        user_input = input("你: ").strip()
        if user_input.lower() in ("exit", "quit", "退出"):
            break
        
        # 后续轮次只需传文本，文件通过 file_id 已在上下文中
        history.append({"role": "user", "content": user_input})
```

关键设计：**文件只在第一轮传入一次**，后续轮次的 `messages` 里不需要重复引用 `file_id`，Claude 会在整个会话中记住文件内容。

## 八、错误处理与重试策略

国内网络环境下，API 调用可能因网络抖动中断。以下是推荐的重试结构：

```python
import time
from anthropic import APIStatusError, APIConnectionError

def robust_upload(client, file_path: str, max_retries=3) -> str:
    for attempt in range(max_retries):
        try:
            return upload_file(client, file_path)
        except APIConnectionError as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt  # 2s, 4s
                print(f"连接失败，{wait}s 后重试 ({attempt+1}/{max_retries})")
                time.sleep(wait)
            else:
                raise
        except APIStatusError as e:
            if e.status_code == 413:
                raise ValueError(f"文件过大（最大 512MB）: {file_path}")
            elif e.status_code == 415:
                raise ValueError(f"不支持的文件类型: {file_path}")
            raise
```

常见错误码：

| 错误码 | 含义                        | 处理建议                    |
|------|---------------------------|---------------------------|
| 400  | 请求格式错误（缺 beta header）| 检查 `betas` 参数           |
| 404  | file_id 不存在或已过期       | 重新上传                    |
| 413  | 文件超过 512MB              | 分割文件                    |
| 415  | 不支持的 MIME 类型           | 转换为 PDF/PNG/TXT         |
| 429  | 速率限制                    | 指数退避重试                 |

完整的速率限制处理可参考 [LLM 速率限制处理实战](/blog/llm-rate-limit-handling/)。

## 九、文件管理最佳实践

**本地维护 file_id 映射表**：上传后立即写入本地数据库或 JSON 文件，避免重复上传同一文件。

```python
import json
from pathlib import Path

MAPPING_FILE = Path("file_id_cache.json")

def load_cache() -> dict:
    return json.loads(MAPPING_FILE.read_text()) if MAPPING_FILE.exists() else {}

def save_cache(cache: dict):
    MAPPING_FILE.write_text(json.dumps(cache, indent=2, ensure_ascii=False))

def get_or_upload(client, file_path: str) -> str:
    cache = load_cache()
    if file_path in cache:
        print(f"缓存命中: {cache[file_path]}")
        return cache[file_path]
    
    file_id = upload_file(client, file_path)
    cache[file_path] = file_id
    save_cache(cache)
    return file_id
```

**主动清理过期文件**：30 天期限到期前，如果文件不再使用，主动删除可以保持存储空间整洁（虽然目前不收存储费，但良好习惯有助于未来配额管理）。

## 十、与 PDF API 的区别

如果你用过 [Claude PDF API](/blog/claude-pdf-api-cn-guide/)，会有一个疑问：两者有什么区别？

- **Claude PDF API** 是更早期的实现，通过 Base64 在每次请求中内联 PDF，仅支持 PDF 格式。
- **Files API** 是更通用的文件管理层，支持多种格式，且文件持久化存储，适合复用场景。

对于新项目，**优先选择 Files API**；对于已有 PDF API 集成，可以在性能瓶颈出现时迁移。

## 十一、相关阅读

- [Anthropic Batch API 国内使用完整指南](/blog/anthropic-batch-api-cn-guide/)
- [Claude PDF API 国内使用指南](/blog/claude-pdf-api-cn-guide/)
- [LLM 速率限制处理实战](/blog/llm-rate-limit-handling/)
- [OpenAI File Search vs RAG：如何选型](/blog/openai-file-search-vs-rag/)
- [Anthropic Console Key 与 API 中转对比](/blog/anthropic-console-key-vs-relay/)

如果你在国内使用 Files API 遇到连接问题，[YoTradeApi](https://yotradeapi.com) 提供稳定的 Anthropic 原生协议中转，支持 Files API 全部端点，无需修改业务代码。
