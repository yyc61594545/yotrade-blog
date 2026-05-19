---
title: 用 AI 生成与维护技术文档的工程化流程
description: 从代码自动产出 README / API 文档 / 用户指南 / Changelog 的实战方法，含 prompt 模板与质量校验。
keywords:
- ai 写文档
- ai 生成 readme
- ai api 文档
- ai changelog
- 自动文档
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/ai-doc-generation-workflow/
tags:
- 文档
- AI 自动化
- API 文档
- Changelog
- 工程实战
category: 工程实战
heroImage: ../../assets/blog-placeholder-3.jpg
---

# 用 AI 生成与维护技术文档的工程化流程

技术文档是项目里最容易过期的部分。代码改了文档没改，是常态。用 AI 自动把文档贴近代码，本文给完整工程化流程。

## 一、文档分类

| 类型 | 来源 | 更新节奏 |
| --- | --- | --- |
| README | 项目级 | 每次大版本 |
| API 文档 | 代码注解 | 每次 release |
| 用户指南 | 功能维度 | 按需 |
| Changelog | git log | 每次 release |
| 内部 wiki | 决策 + 知识 | 持续 |
| 教程 | 用例 | 按需 |

每类有不同 AI 策略。

## 二、README 自动生成

```python
# scripts/gen-readme.py
import subprocess
from openai import OpenAI

client = OpenAI(api_key="sk-yo-...", base_url="https://yotradeapi.com/v1")

# 收集材料
package = open("package.json").read()
file_tree = subprocess.run(["find", "src", "-type", "f"], capture_output=True, text=True).stdout
key_files = "\n\n".join(
    f"=== {f} ===\n{open(f).read()}"
    for f in ["src/index.ts", "src/config.ts"]
)

resp = client.chat.completions.create(
    model="claude-sonnet-4-6",
    messages=[{
        "role": "user",
        "content": f"""根据以下材料生成 README.md：

# package.json
{package}

# 文件树
{file_tree}

# 关键文件
{key_files}

# 要求
- 第一行：项目一句话描述
- 包含：用途 / 安装 / 基本使用 / 配置 / 贡献
- 中英文（中文优先）
- Markdown 格式
- 直接产出，不解释
""",
    }],
)

open("README.md", "w").write(resp.choices[0].message.content)
```

CI 里定期跑，PR 给你 review。

## 三、API 文档（从 OpenAPI / TS 类型）

如果你的项目有 OpenAPI spec 或 TS 类型，让 AI 生成"人类友好"的 API 文档：

```python
spec = open("openapi.yaml").read()

resp = client.chat.completions.create(
    model="claude-sonnet-4-6",
    messages=[{
        "role": "user",
        "content": f"""把以下 OpenAPI spec 转成开发者友好的 markdown 文档：

{spec}

# 要求
- 按资源分组（/users、/orders 等）
- 每个 endpoint 给 curl 示例 + Python 示例
- 鉴权方式单独一节
- 错误码表
- 输出 markdown
""",
    }],
)
```

跟 OpenAPI 同步更新，文档不会过期。

## 四、Changelog 从 git log 生成

```bash
git log --oneline v1.0.0..HEAD | \
claude --headless --task "把这些 commit 整理成 markdown changelog，按 feat/fix/chore/refactor 分类。每条简洁。"
```

或者用 conventional commits + commitizen 自动化。

更好的是用 AI **从代码改动**生成（commit message 不够准）：

```bash
git diff v1.0.0..HEAD --stat > /tmp/changes.txt
git log v1.0.0..HEAD --format="%s %b" > /tmp/commits.txt

# 让 AI 综合两份信息
```

## 五、用户指南（按功能）

每个功能写一份指南：

```python
template = """
# 标题
[一句话说功能做什么]

# 适合谁
[目标用户]

# 5 分钟上手
[最短可用示例]

# 详细配置
[各选项解释]

# 常见问题
[Q&A 格式]

# 相关阅读
[内链]
"""
```

每次新增重要功能，AI 按模板初稿。详见 [用 AI 写 SEO 内容的工程化工作流](/blog/ai-content-seo-workflow/)。

## 六、Inline 注解 / docstring

给函数加 docstring：

```
# Cursor / Claude Code 选中函数
Cmd+K：给这个函数加完整 docstring。
- 参数（含类型与说明）
- 返回值
- 异常
- 示例
中文。
```

批量加：

```bash
for file in src/**/*.ts; do
    claude --headless --task "为 $file 中所有公开函数加 JSDoc"
done
```

## 七、保持文档同步：CI 检测

```yaml
# .github/workflows/docs-check.yml
on: [pull_request]
jobs:
  docs-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: |
          # 改了 API 但没改文档？
          if git diff --name-only HEAD~1 | grep "src/api/" && \
             ! git diff --name-only HEAD~1 | grep "docs/api/"; then
            claude --headless --task "检查本次 PR 的 API 改动是否影响 docs/api/，给出需要更新的文档清单"
          fi
```

## 八、文档质量检查

```python
QUALITY_CHECKS = [
    ("dead link", lambda c: re.findall(r"\]\((https?://[^)]+)\)", c)),
    ("TODO", lambda c: "TODO" in c.upper()),
    ("stale screenshot", lambda c: re.findall(r"!\[[^\]]*\]\([^)]+\.png\)", c)),
]

for f in Path("docs").rglob("*.md"):
    content = f.read_text()
    for name, check in QUALITY_CHECKS:
        if check(content):
            print(f"{f}: {name}")
```

CI 里跑，新引入的问题让作者修。

## 九、多语言文档

主语言（中文）写好后，AI 自动翻：

```python
def translate_doc(zh_text):
    glossary = load_glossary()   # 项目术语表
    resp = client.chat.completions.create(
        model="claude-sonnet-4-6",
        messages=[{
            "role": "user",
            "content": f"翻译成英文。保留 markdown 格式 + 代码块。\n术语：\n{glossary}\n\n# 原文\n{zh_text}",
        }],
    )
    return resp.choices[0].message.content
```

详见 [用 AI 做高质量翻译的工程化流程](/blog/ai-translation-workflow/)。

## 十、文档站点

技术文档放 docs/ + 静态站生成器：

| 工具 | 适用 |
| --- | --- |
| Astro Starlight | 文档站首选 |
| Docusaurus | 大型团队 |
| MkDocs | Python 项目 |
| Nextra | Next.js 团队 |

每次 push 到 main 自动部署。

## 十一、文档驱动开发（DDD）

反过来：**先写文档，再 AI 实现**。

```
1. 写功能 spec（人）
2. AI 看 spec 生成代码 + 测试
3. 跑测试通过
4. 更新文档（如有 spec 改动）
```

这种模式 AI 输出质量明显更高——**spec 越清晰，代码越准**。

## 十二、避坑

- ❌ 一次让 AI 写 50 页文档（细节会错乱）
- ❌ AI 生成 = 直接发布（不 review）
- ❌ AI 不知道项目历史决策（要喂上下文）
- ❌ 文档过度形式化（"Step 1: Open the terminal..."）

## 十三、相关阅读

- [用 AI 写 SEO 内容的工程化工作流](/blog/ai-content-seo-workflow/)
- [用 AI 做高质量翻译的工程化流程](/blog/ai-translation-workflow/)
- [AI 代码评审实战](/blog/ai-code-review-workflow/)
- [AI 生成单元测试的工程化方法](/blog/ai-test-generation-workflow/)
- [Claude Code CI/CD 接入](/blog/claude-code-ci-integration/)

文档生成大量调用，配 [YoTradeApi](https://yotradeapi.com/register) 中转 + caching + Haiku 4.5，每月成本可控。
