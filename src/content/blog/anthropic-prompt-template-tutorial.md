---
title: Anthropic Prompt Template 模板系统实战
description: 深入讲解 Anthropic API 的提示词模板体系，从 Console 的 Prompt Library 到 SDK 的结构化消息组装，附可复用的工程化模板代码。
keywords:
  - Anthropic Prompt Template
  - Claude 提示词模板
  - Anthropic Console Prompt Library
  - Claude API 消息格式
  - 提示词工程化
pubDate: '2026-06-16'
updatedDate: '2026-06-16'
canonical: https://blog.yotradeapi.com/blog/anthropic-prompt-template-tutorial/
tags:
  - Anthropic
  - Prompt
  - 技术深度
  - 工程化
category: 技术深度
heroImage: ../../assets/blog-placeholder-4.jpg
---

Anthropic 的提示词体系有几个地方和 OpenAI 不一样，值得专门梳理一遍。不管是 Claude 消息格式的设计细节、Console 的 Prompt Library 功能，还是 SDK 里如何优雅地组装复杂提示词——这些都是日常使用中经常遇到但文档分散的知识点。本文把它们串起来，给出可直接复用的工程化模板。

---

## 一、Anthropic 消息格式基础

Anthropic 的消息格式和 OpenAI 大体一致，但有几个关键差异值得关注。

### 基础结构

```python
import anthropic

client = anthropic.Anthropic(api_key="sk-ant-...")

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    system="你是一个专业的代码审查专家，善于发现安全漏洞和性能问题。",
    messages=[
        {"role": "user", "content": "请审查这段代码：\n```python\nimport os\nos.system(input())\n```"},
    ],
)
```

**与 OpenAI 的关键差异**：

| 特性 | OpenAI | Anthropic |
|------|--------|-----------|
| System prompt 位置 | 放在 messages 数组里 | 单独的 `system` 参数 |
| 角色名称 | system/user/assistant | user/assistant（system 独立） |
| 消息开头 | 不支持 assistant turn prefill | 支持 assistant 消息 prefill |
| 多轮 system 变更 | 不支持 | 不支持（system 全局固定） |

### Assistant Prefill（重要特性）

Anthropic 独有的 prefill 功能：你可以预先给 assistant 的回复开个头，让模型按这个方向继续：

```python
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=500,
    messages=[
        {"role": "user", "content": "请用 JSON 格式输出以下信息：名字叫张三，年龄 28"},
        {"role": "assistant", "content": "{"},  # prefill，强制模型从 { 开始回复
    ],
)
# 模型会继续补全 JSON，输出类似：{"name": "张三", "age": 28}
```

Prefill 在以下场景非常有用：
- 强制输出固定格式（JSON、Markdown 表格）
- 引导模型从特定角度回答
- 防止模型加入不必要的开场白

---

## 二、Console 的 Prompt Library

Anthropic Console（console.anthropic.com）提供了一个 Prompt Library，可以保存和管理常用的提示词模板。

### 主要功能

1. **保存提示词**：在 Workbench 里调试好的提示词可以保存为命名模板
2. **版本历史**：每次修改会保留版本，可以回滚
3. **变量支持**：使用 `{{variable_name}}` 语法定义模板变量
4. **API 导出**：保存的模板可以直接生成 SDK 调用代码

### 模板变量语法

Console 使用双花括号标记变量位置：

```
你是一个专门分析 {{industry}} 行业的市场分析师。
请根据以下数据，生成一份面向 {{audience}} 的分析报告：

数据：{{data}}

报告格式：{{format}}
```

在 Console 界面，保存后可以填写变量值进行测试，也可以通过 API 传入变量值。

---

## 三、SDK 层面的模板工程化

Console 的可视化工具适合调试，但生产代码里需要更灵活的模板组装。以下是几种常见的工程化模式。

### 模式一：字符串模板类

```python
from dataclasses import dataclass
from string import Template
from typing import Any


@dataclass
class PromptTemplate:
    system: str
    user_template: str
    model: str = "claude-sonnet-4-6"
    max_tokens: int = 1024
    temperature: float = 0.7

    def render(self, **kwargs: Any) -> dict:
        """渲染模板变量，返回可直接传给 client.messages.create 的参数"""
        return {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "system": self.system,
            "messages": [
                {"role": "user", "content": self.user_template.format(**kwargs)}
            ],
        }


# 定义模板
code_review_template = PromptTemplate(
    system="你是一个专业的 {lang} 代码审查专家，关注安全性、性能和可读性。",
    user_template="请审查以下代码，指出问题并给出修改建议：\n\n```{lang}\n{code}\n```",
    max_tokens=2048,
)

# 使用模板
params = code_review_template.render(
    lang="Python",
    code="import os\neval(input())",
)
response = client.messages.create(**params)
```

### 模式二：多段消息模板（对话历史组装）

```python
from typing import Literal


class ConversationTemplate:
    def __init__(self, system: str):
        self.system = system
        self.messages: list[dict] = []

    def add_turn(
        self,
        role: Literal["user", "assistant"],
        content: str,
    ) -> "ConversationTemplate":
        self.messages.append({"role": role, "content": content})
        return self  # 支持链式调用

    def with_prefill(self, prefix: str) -> "ConversationTemplate":
        """添加 assistant prefill"""
        self.messages.append({"role": "assistant", "content": prefix})
        return self

    def build(self, model: str = "claude-sonnet-4-6", max_tokens: int = 1024) -> dict:
        return {
            "model": model,
            "max_tokens": max_tokens,
            "system": self.system,
            "messages": self.messages,
        }


# 使用示例
params = (
    ConversationTemplate(system="你是一个数据分析助手。")
    .add_turn("user", "分析一下这组销售数据：[100, 150, 120, 200, 180]")
    .add_turn("assistant", "好的，我来分析这组数据。均值是...")
    .add_turn("user", "能生成 Python 代码来可视化吗？")
    .with_prefill("```python\nimport matplotlib")
    .build(max_tokens=500)
)
```

### 模式三：内容块（Content Block）模板

Anthropic API 支持将 content 写成数组格式，适合多模态或结构化消息：

```python
def build_multimodal_message(text: str, image_base64: str) -> dict:
    return {
        "role": "user",
        "content": [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": image_base64,
                },
            },
            {
                "type": "text",
                "text": text,
            },
        ],
    }


def build_document_analysis_prompt(doc_text: str, question: str) -> list[dict]:
    """分析长文档的标准模板"""
    return [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"<document>\n{doc_text}\n</document>\n\n{question}",
                }
            ],
        }
    ]
```

---

## 四、使用 XML 标签结构化提示词

Anthropic 官方推荐使用 XML 标签来分隔不同部分，这对 Claude 的理解效果最好：

```python
def build_analysis_prompt(
    context: str,
    data: str,
    task: str,
    constraints: list[str],
) -> str:
    constraint_list = "\n".join(f"- {c}" for c in constraints)
    return f"""<context>
{context}
</context>

<data>
{data}
</data>

<task>
{task}
</task>

<constraints>
{constraint_list}
</constraints>

请根据以上信息完成任务，并以 JSON 格式输出结果。"""


# 使用
prompt = build_analysis_prompt(
    context="我们是一家 B2B SaaS 公司，主要服务制造业客户",
    data="Q1 营收 200 万，Q2 营收 180 万，Q3 营收 220 万，Q4 营收 250 万",
    task="分析全年营收趋势，指出关键转折点，并预测下一年 Q1",
    constraints=[
        "不要引入未提供的假设数据",
        "预测要给出置信区间",
        "结论要可操作",
    ],
)
```

XML 标签的好处：
1. Claude 能清晰区分不同部分的内容，不会把 `data` 里的数字当指令执行
2. 当某个部分内容很长时，不会影响其他部分的理解
3. 便于程序化生成和解析

---

## 五、提示词版本管理

生产环境里，提示词跟代码一样需要版本管理。一个轻量级的做法：

```python
from typing import NamedTuple


class PromptVersion(NamedTuple):
    version: str
    template: str
    changelog: str


PROMPTS = {
    "code_review": [
        PromptVersion(
            version="v1.0",
            template="请审查以下代码：\n{code}",
            changelog="初始版本",
        ),
        PromptVersion(
            version="v1.1",
            template="请从安全性和性能两个维度审查以下 {lang} 代码：\n\n```{lang}\n{code}\n```\n\n对每个问题，请给出：问题描述、风险等级（高/中/低）、修复建议。",
            changelog="增加维度说明和输出格式要求",
        ),
    ]
}


def get_prompt(name: str, version: str = "latest") -> PromptVersion:
    versions = PROMPTS[name]
    if version == "latest":
        return versions[-1]
    return next(v for v in versions if v.version == version)
```

这样在 A/B 测试时可以方便地切换版本，同时保留回滚能力。

---

## 六、常见模板设计错误

**错误 1：System Prompt 过长**

把大量背景信息塞进 system prompt 会让模型"分心"。建议 system prompt 只放角色定义和全局规则，具体背景放在 user 消息的 XML 标签里。

**错误 2：混淆格式要求和内容要求**

把"请用 JSON 格式"和"分析这份数据"放在同一段里，容易导致模型忽视格式要求。建议把格式要求单独放在末尾，或者用 prefill 强制。

**错误 3：不测试边界情况**

提示词设计好后，要用边界 case 测试：空输入、超长输入、包含特殊字符的输入、与预期完全不同的输入。AI 的行为在边界情况下往往出乎意料。

**错误 4：硬编码模型版本**

```python
# 不推荐：模型版本下线后需要改代码
model = "claude-3-5-sonnet-20241022"

# 推荐：用配置或别名管理
MODEL_ALIASES = {
    "fast": "claude-haiku-4-5",
    "balanced": "claude-sonnet-4-6",
    "powerful": "claude-opus-4-8",
}
model = MODEL_ALIASES["balanced"]
```

---

## 七、相关阅读

- [LLM Prompt 模板工程实战](/blog/llm-prompt-template-engineering/)
- [Claude System Prompt 最佳实践](/blog/claude-system-prompt-engineering/)
- [AI 提示词版本管理实践](/blog/ai-prompt-versioning/)
- [Anthropic Skills API 中文指南](/blog/anthropic-skills-cn-guide/)
- [LLM System Prompt vs User Prompt 深度解析](/blog/llm-system-prompt-vs-user-prompt/)

如果你需要快速测试不同版本的提示词模板而不受网络限制，[YoTradeApi](https://yotradeapi.com) 提供稳定的 Claude API 中转，支持人民币充值，适合在国内环境频繁迭代提示词工程。
