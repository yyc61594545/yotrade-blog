---
title: Claude Citations API 引用功能详解：让 AI 回答有据可查
description: 深入讲解 Claude Citations API 的工作原理、使用方法和最佳实践，帮助开发者构建可信赖的知识问答和 RAG 系统。
keywords:
  - Claude Citations API
  - Claude 引用功能
  - RAG 引用溯源
  - Anthropic Citations
  - AI 问答可信度
pubDate: '2026-06-05'
updatedDate: '2026-06-05'
canonical: https://blog.yotradeapi.com/blog/claude-citations-api-guide/
tags:
  - Claude
  - API
  - RAG
  - 技术深度
category: 技术深度
heroImage: ../../assets/blog-placeholder-3.jpg
---

在 RAG（检索增强生成）和企业知识问答系统中，一个经常被忽视却至关重要的问题是：**AI 的回答究竟来自哪里？** 用户需要知道某个结论对应的原始文档段落，审计人员需要核查信息来源，监管场景下更是明确要求每条输出都可溯源。

Claude Citations API 正是为此而生。本文从工作原理到代码实践，全面解析这一功能。

## 一、Citations API 是什么

Citations API 是 Anthropic 在 Claude API 中推出的一项结构化输出能力，允许 Claude 在回答问题时**精确标注每句话对应的文档来源**——包括文档名称、段落位置乃至原文片段。

与普通 RAG 的区别在于，传统 RAG 只是将检索到的文本拼入 prompt，Claude 在生成时知道参考了哪些材料，但**引用信息并不会以结构化方式返回给调用方**。Citations API 则将引用关系提升为一等公民，作为 API 响应的一部分独立返回，调用方可以直接渲染成带脚注的 UI，也可以入库存档、自动校验。

目前（2026 年），Citations API 支持的文档格式包括：

| 格式 | 说明 |
|------|------|
| 纯文本块 | 最通用，字符串形式传入 |
| PDF 文档 | base64 编码传入，Claude 自动解析结构 |
| 自定义文档 | 带元数据的结构化文档对象 |

## 二、核心应用场景

### 2.1 企业知识库问答

法律、合规、医疗等行业的知识库问答系统，每一条 AI 回答都必须对应具体条款或文献。Citations API 让这一需求变成原生 API 支持，而不是靠后处理硬拼字符串。

### 2.2 文档审阅与分析

将合同、报告批量上传，让 Claude 提取关键信息并附上原文出处。业务人员可以一键跳转到原始段落核查，大幅降低核查成本。

### 2.3 研究助手

学术或市场研究场景中，Claude 整理多篇论文或报告的要点，Citations 让每个观点都有对应来源，避免信息张冠李戴。

### 2.4 监管合规报告生成

金融、医疗等受监管行业需要在输出报告中注明数据来源。Citations API 可以直接将来源信息写入报告模板，而不是事后人工补注。

## 三、基本用法：文本文档引用

Citations API 通过在 `messages` 的 `content` 中加入特殊的 `document` 类型来传递文档，并在请求参数中启用引用。以下是最简单的示例：

```python
import anthropic

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-opus-4-8",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "text",
                        "media_type": "text/plain",
                        "data": """第一章 合同主体
甲方：北京科技有限公司（以下简称"甲方"）
乙方：上海软件股份有限公司（以下简称"乙方"）

第二章 服务内容
乙方应于合同签订后 30 个工作日内交付系统原型。
交付物包括：源代码、部署文档、用户手册。

第三章 费用与付款
合同总价为人民币 50 万元整。
甲方应于验收通过后 15 个工作日内完成付款。""",
                    },
                    "title": "服务合同（示例）",
                    "citations": {"enabled": True},
                },
                {
                    "type": "text",
                    "text": "乙方的交付期限是多少？验收后付款期限是多少？",
                },
            ],
        }
    ],
)

# 解析引用
for block in response.content:
    if block.type == "text":
        print("回答:", block.text)
    elif block.type == "citations":
        for citation in block.citations:
            print(f"\n引用来源: {citation.document_title}")
            print(f"原文: {citation.cited_text}")
```

关键参数说明：
- `type: "document"` — 标记这是一个文档内容块
- `citations: {"enabled": True}` — 开启该文档的引用追踪
- `title` — 文档标题，会出现在引用信息中

## 四、PDF 文档引用

对于 PDF 格式的文档，只需将 `source.type` 改为 `"base64"`，`media_type` 改为 `"application/pdf"`：

```python
import anthropic
import base64

client = anthropic.Anthropic()

with open("annual_report.pdf", "rb") as f:
    pdf_data = base64.standard_b64encode(f.read()).decode("utf-8")

response = client.messages.create(
    model="claude-opus-4-8",
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
                    "title": "2025年度财务报告",
                    "citations": {"enabled": True},
                },
                {
                    "type": "text",
                    "text": "请提取本报告中提到的营业收入和净利润数字，并注明来源页面。",
                },
            ],
        }
    ],
)
```

PDF 场景下，`cited_text` 会包含具体的页面段落原文，方便人工核查。

## 五、响应结构解析

启用 Citations 后，API 响应的 `content` 数组会交替出现 `text` 块和 `citations` 块。典型结构如下：

```json
{
  "content": [
    {
      "type": "text",
      "text": "乙方须在合同签订后 30 个工作日内交付系统原型。"
    },
    {
      "type": "citations",
      "citations": [
        {
          "type": "document_citation",
          "cited_text": "乙方应于合同签订后 30 个工作日内交付系统原型。",
          "document_index": 0,
          "document_title": "服务合同（示例）",
          "start_char_index": 82,
          "end_char_index": 120
        }
      ]
    },
    {
      "type": "text",
      "text": "验收通过后，甲方应在 15 个工作日内完成付款。"
    },
    {
      "type": "citations",
      "citations": [
        {
          "type": "document_citation",
          "cited_text": "甲方应于验收通过后 15 个工作日内完成付款。",
          "document_index": 0,
          "document_title": "服务合同（示例）",
          "start_char_index": 178,
          "end_char_index": 210
        }
      ]
    }
  ]
}
```

每个 `citation` 对象包含：
- `cited_text` — 被引用的原文片段
- `document_index` — 引用的是请求中第几个文档（0-indexed）
- `document_title` — 文档标题
- `start_char_index` / `end_char_index` — 在文档中的字符位置，可用于高亮显示

## 六、多文档场景与引用优先级

实际 RAG 系统中，往往需要同时传入多个检索到的文档块。Citations API 支持在同一个请求中传入多个 `document` 块，Claude 会自动区分每个文档的贡献：

```python
response = client.messages.create(
    model="claude-opus-4-8",
    max_tokens=2048,
    messages=[
        {
            "role": "user",
            "content": [
                # 文档一
                {
                    "type": "document",
                    "source": {"type": "text", "media_type": "text/plain", "data": doc1_text},
                    "title": "产品规格说明书 v2.3",
                    "citations": {"enabled": True},
                },
                # 文档二
                {
                    "type": "document",
                    "source": {"type": "text", "media_type": "text/plain", "data": doc2_text},
                    "title": "用户反馈报告 Q1-2026",
                    "citations": {"enabled": True},
                },
                {
                    "type": "text",
                    "text": "产品当前存在哪些已知问题？用户有什么反馈？",
                },
            ],
        }
    ],
)
```

当 Claude 综合两份文档作答时，每句话都会对应到正确的来源文档，`document_index` 字段清晰标注来自文档 0 还是文档 1。

**实践建议**：
- 每个文档块控制在合理长度（1000–3000 字），过长的文档可以按章节拆分为多个 `document` 块，有助于提升引用精度
- 给文档加有意义的 `title`，这是引用中用户可见的部分
- 如果某个文档只是系统背景信息、不需要被引用，可以不加 `citations: {"enabled": True}`，节省 token

## 七、前端渲染：带脚注的 UI 实现

拿到结构化引用数据后，前端可以轻松渲染成带脚注的阅读体验。以下是一个 React 组件思路：

```tsx
interface CitationBlock {
  type: "text" | "citations";
  text?: string;
  citations?: Array<{
    cited_text: string;
    document_title: string;
    document_index: number;
  }>;
}

function CitedAnswer({ blocks }: { blocks: CitationBlock[] }) {
  let footnoteCount = 0;
  const footnotes: Array<{ title: string; text: string }> = [];

  return (
    <div>
      <p>
        {blocks.map((block, i) => {
          if (block.type === "text") {
            return <span key={i}>{block.text}</span>;
          }
          if (block.type === "citations" && block.citations) {
            const refs = block.citations.map((c) => {
              footnoteCount++;
              footnotes.push({ title: c.document_title, text: c.cited_text });
              return (
                <sup key={footnoteCount}>
                  <a href={`#fn${footnoteCount}`}>[{footnoteCount}]</a>
                </sup>
              );
            });
            return <span key={i}>{refs}</span>;
          }
          return null;
        })}
      </p>
      <hr />
      <ol>
        {footnotes.map((fn, i) => (
          <li key={i} id={`fn${i + 1}`}>
            <strong>{fn.title}</strong>：{fn.text}
          </li>
        ))}
      </ol>
    </div>
  );
}
```

这个模式可以直接套用在企业知识库、合同审阅、合规报告等场景的前端界面上。

## 八、费用与性能注意事项

Citations API 并不额外收费，但要注意以下几点：

**Token 消耗**：文档内容会计入输入 token，文档越长消耗越多。建议在 RAG 阶段先做好检索过滤，只传入与问题相关的片段，而不是整篇文档。

**响应长度**：引用块本身也会占用输出 token（`cited_text` 是原文摘录）。在高频调用场景下，可以评估是否需要对每个请求都开启 Citations，还是只在需要展示给用户时开启。

**延迟影响**：启用引用会让 Claude 在生成时进行额外的溯源对齐，可能略微增加首 token 延迟。实测通常在 200–500ms 范围内，大多数场景可以接受。

**Prompt Caching 配合**：如果同一批文档要被多次查询，可以结合 [Prompt Caching](https://blog.yotradeapi.com/blog/prompt-caching-cost-optimization/) 功能缓存文档内容的 token，大幅降低重复调用成本。具体见相关文章。

## 九、常见问题与调试技巧

**Q：Citations 没有出现在响应中？**
检查是否在 `document` 块中设置了 `"citations": {"enabled": True}`。如果忘记设置，Claude 仍然会参考文档回答，但不会返回结构化引用。

**Q：引用的 `cited_text` 和原文有轻微出入？**
Claude 会对引用文本做轻微规范化（如去除多余空格），字符位置 `start_char_index` / `end_char_index` 是精确的，建议以位置定位原文，而不是完全依赖 `cited_text` 字符串比对。

**Q：文档很长，引用精度下降？**
将长文档按段落或章节拆分为多个 `document` 块，每块加上对应的 `title`（如"第三章 付款条款"），有助于 Claude 更精确地定位来源。

**Q：想在 system prompt 中预设文档？**
目前 Citations API 要求文档在 `messages` 的 `content` 中传入，不支持直接放在 system prompt。如果需要固定文档集，可以在每次请求中将文档块放在 user message 的最前面。

## 十、相关阅读

- [Prompt Caching 成本优化：让 Claude 长文档调用降本 80%](/blog/prompt-caching-cost-optimization/)
- [Claude Tool Use 最佳实践：Function Calling 完整指南](/blog/claude-tool-use-best-practices/)
- [RAG 中文最佳实践：从检索到生成的完整链路](/blog/rag-cn-best-practices/)
- [Claude PDF API 中文开发指南：文档理解与信息提取](/blog/claude-pdf-api-cn-guide/)
- [结构化输出：让 LLM 稳定返回 JSON 的实用指南](/blog/structured-output-llm-guide/)

如果你在国内访问 Anthropic API 存在网络或付款障碍，[YoTradeApi](https://yotradeapi.com) 提供稳定的 Claude API 中转服务，支持国内支付，Citations API 完全兼容。
