---
title: AI 辅助文档平台迁移实战
description: 记录用 AI 工具将团队文档从旧平台迁移到新平台的完整过程，涵盖格式转换、内容清洗与批量处理脚本实战经验。
keywords:
  - AI 文档迁移
  - 文档平台迁移实战
  - AI 辅助批量处理
  - 文档格式转换
  - LLM 文档清洗
pubDate: '2026-06-18'
updatedDate: '2026-06-18'
canonical: https://blog.yotradeapi.com/blog/ai-doc-platform-migration/
tags:
  - 实战经验
  - 文档工程
  - LLM 应用
  - 自动化
category: 实战经验
heroImage: ../../assets/blog-placeholder-4.jpg
---

每隔几年，团队就会面临一次文档平台迁移：从 Confluence 迁到 Notion、从 GitBook 迁到 Docusaurus、从内部 Wiki 迁到飞书文档……迁移本身不复杂，但当文档数量超过 500 篇时，纯手工处理几乎不可能在合理时间内完成。这篇文章记录了我们用 AI 工具完成一次 800 篇文档迁移的完整过程，包括脚本设计、踩坑经历和最终效果。

---

## 一、迁移背景与挑战

我们的场景是将一套运行了三年的 Confluence Cloud 文档库迁移到自托管的 Docusaurus 站点。主要挑战有三个：

1. **格式不兼容**：Confluence 使用私有的 Storage Format XML，导出的 HTML 夹杂大量平台特有的 `<ac:xxx>` 标签，Docusaurus 只接受 Markdown
2. **内容质量参差不齐**：三年时间内多人协作，有的文章段落逻辑错乱，有的图片链接已失效，有的代码块语言标注缺失
3. **内链全部失效**：Confluence 页面 URL 是 `/pages/viewpage.action?pageId=12345` 格式，迁移后 slug 完全变化

AI 在这三个问题上都能发挥作用，但需要针对不同问题设计不同的处理流程。

---

## 二、整体流程设计

迁移流程分为五个阶段：

```
Confluence 导出 (XML/HTML)
  → 1. 格式转换（HTML → Markdown，去除平台标签）
  → 2. 内容清洗（AI 修复问题段落）
  → 3. 元数据生成（AI 补写 description/tags/slug）
  → 4. 内链重建（URL 映射 + AI 辅助识别）
  → 5. 人工抽查与发布
```

每个阶段都可以独立脚本化，出错时可以只重跑当前阶段而不影响其他阶段。

---

## 三、第一阶段：格式转换

格式转换是最机械的一步，用 Python 的 `markdownify` 库处理基础 HTML 到 Markdown 的转换，再用正则清洗 Confluence 特有标签。

```python
import re
from markdownify import markdownify as md
from pathlib import Path

def clean_confluence_html(html: str) -> str:
    # 移除 Confluence 特有的宏标签
    html = re.sub(r'<ac:[^>]+>.*?</ac:[^>]+>', '', html, flags=re.DOTALL)
    html = re.sub(r'<ac:[^>]+/>', '', html)
    # 移除 ri: 资源标签
    html = re.sub(r'<ri:[^>]+>', '', html)
    # 移除状态宏
    html = re.sub(r'<span class="status-macro[^"]*"[^>]*>.*?</span>', '', html, flags=re.DOTALL)
    return html

def convert_page(html_path: Path, output_dir: Path):
    html = html_path.read_text(encoding="utf-8")
    cleaned = clean_confluence_html(html)
    markdown = md(cleaned, heading_style="ATX", code_language="")
    # 去掉连续空行
    markdown = re.sub(r'\n{3,}', '\n\n', markdown)
    slug = html_path.stem.lower().replace(' ', '-')
    output_path = output_dir / f"{slug}.md"
    output_path.write_text(markdown, encoding="utf-8")
    return slug
```

这一步大约能处理 70% 的文档，格式转换质量符合预期。剩下 30% 因为嵌套表格、代码宏复杂嵌套等原因，转换结果需要进入第二阶段处理。

---

## 四、第二阶段：AI 内容清洗

对于格式转换后仍有问题的文档，我们用 LLM 做批量清洗。核心思路是：**不让 AI 重写内容，只让它修复格式问题**。

```python
from openai import OpenAI
import json

client = OpenAI(
    api_key="your_api_key",
    base_url="https://api.yotradeapi.com/v1",  # API 中转，支持多模型
)

CLEAN_PROMPT = """你是一个 Markdown 格式修复工具。对输入的 Markdown 文本做以下修复：
1. 修复损坏的代码块（补全缺失的 ``` 标记）
2. 修复断裂的表格行（确保每行列数一致）
3. 移除明显的 HTML 残留标签
4. 保持原文内容不变，只修复格式问题
5. 如果代码块缺少语言标注，根据内容推断语言

输出只返回修复后的 Markdown，不要加任何解释。"""

def clean_markdown_with_ai(markdown: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # 成本控制：清洗任务用轻量模型
        messages=[
            {"role": "system", "content": CLEAN_PROMPT},
            {"role": "user", "content": markdown},
        ],
        temperature=0,  # 格式任务不需要创意，temperature=0 稳定性更好
    )
    return response.choices[0].message.content
```

**关键设计决策：使用轻量模型 + temperature=0**

清洗任务不需要创意，只需要一致性。GPT-4o-mini 或 Claude Haiku 的成本比旗舰模型低 10–20 倍，而在格式修复这类任务上，效果差距几乎可以忽略。我们 800 篇文档的清洗成本（仅 AI 部分）控制在了约 15 元人民币以内。

---

## 五、第三阶段：元数据生成

Docusaurus 的 Markdown front matter 需要 `title`、`description`、`sidebar_label` 等字段，Confluence 导出数据里往往只有原始标题，description 和标签需要从正文提取。

```python
META_PROMPT = """根据以下 Markdown 文章，生成 Docusaurus front matter 元数据。
返回 JSON 格式，字段如下：
- title: 文章标题（≤60 字符，保持原标题）
- description: 摘要（100-150 字符，覆盖核心内容）
- sidebar_label: 侧边栏简短标签（≤20 字符）
- tags: 标签数组，3-5 个，从文章内容提取

只返回 JSON，不要 markdown 代码块。"""

def generate_metadata(markdown_body: str, original_title: str) -> dict:
    prompt = f"标题：{original_title}\n\n正文：\n{markdown_body[:3000]}"  # 只送前 3000 字符
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": META_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return json.loads(response.choices[0].message.content)
```

`response_format={"type": "json_object"}` 能强制模型输出合法 JSON，避免解析失败。这是元数据批量生成任务里最重要的一个设置。

---

## 六、第四阶段：内链重建

内链失效是迁移中最难自动化处理的问题。我们的方案分两步：

**Step 1：建立 pageId → slug 映射表**

Confluence 导出文件里每个页面都有 pageId，在导出的 XML 根目录里可以提取出完整映射：

```python
import xml.etree.ElementTree as ET

def build_id_slug_map(export_xml: str) -> dict:
    tree = ET.parse(export_xml)
    root = tree.getroot()
    mapping = {}
    for page in root.findall('.//object[@class="Page"]'):
        page_id = page.find('id').text
        title = page.find('property[@name="title"]').text
        slug = title.lower().replace(' ', '-').replace('/', '-')
        mapping[page_id] = slug
    return mapping
```

**Step 2：用 AI 处理模糊内链**

有些链接是通过标题文字而非 pageId 引用的（比如 `[参见部署文档](https://xxx.atlassian.net/wiki/spaces/...)`），对这类链接，我们让 AI 根据链接上下文文字，在 slug 列表里找最相似的目标：

```python
def find_best_slug_match(link_text: str, all_slugs: list[str]) -> str:
    slugs_str = "\n".join(all_slugs[:200])  # 限制 token 数
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "从 slug 列表里找与链接文字语义最相近的 slug，只返回 slug 字符串。"},
            {"role": "user", "content": f"链接文字：{link_text}\n\nSlug 列表：\n{slugs_str}"},
        ],
        temperature=0,
    )
    return response.choices[0].message.content.strip()
```

这个方案的匹配准确率约 85%，剩余 15% 的误匹配在人工抽查阶段修正。

---

## 七、批量运行与质量控制

整个流程用一个主脚本串联：

```python
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

def process_single_doc(html_file: Path, output_dir: Path, slug_map: dict) -> dict:
    try:
        slug = convert_page(html_file, output_dir)
        md_path = output_dir / f"{slug}.md"
        content = md_path.read_text()
        if needs_cleaning(content):
            cleaned = clean_markdown_with_ai(content)
            md_path.write_text(cleaned)
        meta = generate_metadata(content, html_file.stem)
        return {"slug": slug, "status": "ok", "meta": meta}
    except Exception as e:
        return {"slug": html_file.stem, "status": "error", "error": str(e)}

html_files = list(Path("confluence_export").glob("**/*.html"))

with ThreadPoolExecutor(max_workers=5) as executor:  # 并发 5，避免触发限速
    futures = {executor.submit(process_single_doc, f, Path("output"), slug_map): f for f in html_files}
    for future in as_completed(futures):
        result = future.result()
        if result["status"] == "error":
            print(f"❌ {result['slug']}: {result['error']}")
        else:
            print(f"✅ {result['slug']}")
        time.sleep(0.1)  # 轻微限速
```

**并发数不要设太高**：AI API 有 RPM（每分钟请求数）限制，并发 5 是个安全的起点。如果触发 429，把 max_workers 降到 2-3。

---

## 八、踩坑总结

迁移过程中遇到的几个典型问题：

**1. AI 擅自改内容**

早期 prompt 里写了"修复格式"，但 AI 会顺手改掉一些"语气不通顺"的句子。解决方案：在 prompt 里加上 `严禁修改原文内容，只处理格式`，并在清洗后做 diff 检查，超过 15% 变化率的文章自动标记人工复查。

**2. 长文档超出 context window**

部分文档超过 8000 字，直接塞入会超出轻量模型的 context。解决方案：对超长文档按段落切片，每片独立处理后拼回。

**3. 图片链接大量失效**

Confluence 的图片是相对路径，导出后无法解析。AI 处理不了这个问题——只能从 Confluence API 批量下载附件，重新上传到新平台的 CDN。这部分估计占了整个迁移工时的 30%。

**4. 表格重复列头**

markdownify 处理复杂表格时，有时会把表头行重复输出两次。加了一个后处理函数专门检测并去重。

---

## 九、相关阅读

- [AI 文档生成工作流实战](/blog/ai-doc-generation-workflow/)
- [AI 辅助数据库迁移](/blog/ai-helping-with-database-migration/)
- [百川大模型 API 开发者评测](/blog/cn-baichuan-developer-review/)
- [AI 编码工具成本管理](/blog/ai-coding-monthly-cost-real/)
- [LLM 在 SEO 内容工作流中的应用](/blog/ai-content-seo-workflow/)

批量调用 AI API 做文档处理时，[YoTradeApi](https://yotradeapi.com) 支持多模型统一接入，按需切换 GPT-4o-mini 与 Claude Haiku，人民币账单，适合国内团队的批量自动化任务。
