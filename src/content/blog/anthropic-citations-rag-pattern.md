---
title: Anthropic Citations 与 RAG 组合实战
description: 讲解如何把 RAG 检索结果转换为 Anthropic 可引用文档，启用 Citations、解析引用位置、渲染来源，并用召回与引用指标验证生产质量。
keywords:
  - Anthropic Citations RAG
  - Claude API 引用
  - RAG 引用溯源
  - Claude 文档问答
  - Citations API 实战
pubDate: '2026-08-21'
updatedDate: '2026-08-21'
canonical: https://blog.yotradeapi.com/blog/anthropic-citations-rag-pattern/
tags:
  - Anthropic
  - Citations
  - RAG
  - Claude
category: 技术深度
heroImage: ../../assets/blog-placeholder-5.jpg
---

普通 RAG 能把检索片段塞进 prompt，却很难稳定回答“这句话具体来自哪一段”。让模型在正文后手写 `[1]`，常见问题是编号与来源错位、引用范围不明确，甚至引用了上下文中不存在的句子。Anthropic Citations 的价值，是把引用作为 Messages API 的结构化结果返回，而不是依赖模型自由生成脚注格式。

它并不会替你完成检索，也不会保证答案里的每个判断都正确。生产链路仍然是“召回 → 重排 → 文档封装 → 模型回答 → 引用解析 → 质量验证”。本文重点讲 Citations 应放在哪一层，以及如何避免把“引用存在”误当成“回答可信”。

## 一、Citations 与 RAG 各自负责什么

RAG 的职责是从知识库中找出可能相关的证据，Citations 的职责是让回答中的具体文本块关联到输入文档里的位置。两者解决不同问题：召回错了，引用功能不会自动找到知识库里没传入的文档；召回正确但模型表述没有证据，结构化引用能帮助应用发现和展示这种缺口。

| 环节 | 输入 | 主要质量问题 |
| --- | --- | --- |
| 检索 | 用户问题、索引 | 漏召回、召回噪声 |
| 重排 | 候选 chunks | 相关性排序错误 |
| 文档封装 | 精选 chunks | 元数据丢失、粒度不当 |
| 生成与引用 | 文档、问题 | 结论不完整、引用错配 |
| 展示与验证 | text blocks、citations | 来源映射错误、用户不可读 |

因此调试时要分别记录 `retrieved_chunk_ids` 与最终 `cited_chunk_ids`。前者衡量检索器找到了什么，后者衡量模型实际使用了什么。把两者混成一个指标，会让召回问题被误诊为生成问题。

## 二、先选择适合的文档类型

Anthropic 官方当前支持三类可引用文档：纯文本、PDF 和 custom content。纯文本会自动按句子切分，引用返回字符位置；PDF 引用返回页码位置；custom content 不再自动切分，引用返回输入内容块的索引范围。

对于已经切好 chunk 的 RAG，有两种常见封装方式：

1. 每个 chunk 作为一个独立纯文本文档，继续由 API 做句子级引用；
2. 把多个 chunks 放进 custom content 文档，保留自己定义的块边界。

如果用户希望看到精确句子，第一种更直观；如果 chunk 本身就是法规条款、FAQ 项或带时间戳的转录段落，第二种更容易保持业务边界。不要把许多来源拼成一个巨大字符串再靠自定义 `[source_id]` 分隔，这会削弱结构化位置与原始元数据的对应关系。

官方文档还区分可引用与不可引用字段：文档 `source` 中的文本可以被引用，`title` 与 `context` 会提供给模型但不作为被引用正文。`context` 适合放 chunk ID、URL、版本和权限标签等元数据，但展示引用时仍应以服务端保存的来源映射为准。

## 三、把检索结果封装成 document blocks

下面是纯文本 chunk 的简化 Python 示例。模型名应由应用配置提供，避免写死在业务代码中：

```python
documents = []
for chunk in reranked_chunks[:6]:
    documents.append({
        "type": "document",
        "source": {
            "type": "text",
            "media_type": "text/plain",
            "data": chunk.text,
        },
        "title": chunk.title,
        "context": json.dumps({
            "chunk_id": chunk.id,
            "url": chunk.url,
            "version": chunk.version,
        }, ensure_ascii=False),
        "citations": {"enabled": True},
    })

response = client.messages.create(
    model=MODEL_NAME,
    max_tokens=1600,
    messages=[{
        "role": "user",
        "content": documents + [{
            "type": "text",
            "text": "仅依据所给资料回答；资料不足时明确说明。",
        }],
    }],
)
```

同一请求中的文档应统一启用或关闭 citations，不能只给其中一部分开启。发送前还要做权限过滤：向量检索命中并不代表当前用户有权查看该 chunk。权限检查必须发生在文档进入模型上下文之前，不能指望模型根据 `context` 中的标签自行保密。

## 四、引用粒度由 chunk 设计决定

RAG chunk 越大，检索上下文越完整，但引用展示可能包含大量无关文字；chunk 越小，引用更精确，却容易丢失前后定义。最合适的粒度应以知识结构为准，而不是机械地按固定字符数切分。

对于产品文档，可以按标题与段落切分；法规按条款切分；会议转录按说话人和时间窗切分；表格则先转换成保留表头语义的文本块。Custom content 的最小可引用单位是你提供的内容块，引用位置使用从 0 开始、结束索引不包含在内的区间，因此块本身必须足够独立。

还要避免重复 chunks。若同一段内容以不同版本或重叠窗口多次进入请求，模型可能引用任意副本，前端就难以展示“权威来源”。索引层应记录内容哈希、版本与生效时间，重排后优先保留最新且权限正确的唯一证据。

## 五、解析响应时按 text block 读取 citations

启用 Citations 后，响应可能包含多个 text blocks，每个文本块带有支持该段陈述的 citations 列表。不要把整个响应先拼成字符串，再用正则寻找脚注；应保留块级关联。

```python
rendered = []
for block in response.content:
    if block.type != "text":
        continue

    sources = []
    for citation in block.citations:
        sources.append({
            "document_index": citation.document_index,
            "title": citation.document_title,
            "quote": citation.cited_text,
            "location_type": citation.type,
        })

    rendered.append({"text": block.text, "sources": sources})
```

位置字段随文档类型变化：纯文本使用 `start_char_index` 与 `end_char_index`，PDF 使用起止页码，custom content 使用起止块索引。字符和块索引从 0 开始且结束位置为 exclusive；PDF 页码从 1 开始，结束页码同样是 exclusive。应用应对不同类型做显式分支，不要假设所有引用都有字符偏移。

`cited_text` 适合直接预览，但来源链接、权限和版本仍应通过 `document_index` 映射回本次请求对应的服务端记录。不要让客户端根据模型返回的标题拼接 URL。

## 六、前端展示要帮助用户核验

引用 UI 的目标不是让答案看起来“更学术”，而是降低核验成本。正文可以在每个有依据的陈述后显示编号，点击后展开来源标题、原文摘录、更新时间和跳转链接。多个相邻文本块引用同一来源时可合并视觉标记，但底层仍保留各自引用关系。

对于 PDF，跳转到对应页；对于网页知识库，跳到稳定锚点；对于内部文档，先检查用户当前权限再打开。若某段回答没有 citation，不要自动给它继承上一段来源。可以把无引用段落标为“模型说明”或在严格模式下要求重新回答。

引用原文也可能包含敏感信息。服务端返回前应再次执行脱敏和授权检查，日志中不要无限期保存完整 `cited_text`。特别是多租户知识库，文档索引只是本次请求内的位置，不是可跨请求信任的全局 ID。

## 七、用四组指标验证，而不只看有无引用

评估集应包含可回答、跨文档综合、冲突资料和资料不足四类问题。至少追踪下面四组指标：

- 召回命中率：标准答案所需 chunk 是否进入候选；
- 引用正确率：引用原文是否真的支持相邻陈述；
- 引用完整率：需要证据的陈述中有多少带有效引用；
- 拒答正确率：资料不足或冲突时是否明确说明限制。

还要测试版本冲突：旧政策和新政策同时召回时，模型是否依据 `context` 选择有效版本；测试权限隔离：无权文档是否在调用前就被移除；测试索引变更：同一知识条目重建后，前端来源映射是否仍正确。

结构化引用能保证指针落在所提供文档中，却不能证明陈述对引文的解释一定正确。官方功能细节可能更新，接入时应核对 [Anthropic Citations 官方文档](https://platform.claude.com/docs/en/build-with-claude/citations) 与当前 Messages API 类型定义。

## 八、相关阅读

- [Claude Citations API 中文指南](/blog/claude-citations-api-guide/)
- [Claude vs Gemini 文档 RAG 能力对比](/blog/claude-vs-gemini-document-rag/)
- [LLM 评估实战：构建可靠的 Eval 体系](/blog/llm-evaluation-cn-guide/)
- [LLM Eval 黄金数据集构建指南](/blog/llm-eval-golden-set/)

如果你需要在 RAG 应用中统一接入多种模型，[YoTradeApi](https://yotradeapi.com) 可以减少不同 API 协议的适配工作；检索权限、来源映射和引用质量评估仍应由应用侧完整实现。
