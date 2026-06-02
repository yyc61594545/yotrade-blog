---
title: Prompt 模板工程实战
description: 从变量设计、模块组合到版本管理和测试，系统讲解如何把一次性 Prompt 升级为可复用、可维护的 Prompt 模板工程体系。
keywords:
  - prompt 模板工程
  - LLM prompt 复用
  - prompt 变量设计
  - prompt 版本管理
  - AI 应用工程化
pubDate: '2026-06-02'
updatedDate: '2026-06-02'
canonical: https://blog.yotradeapi.com/blog/llm-prompt-template-engineering/
tags:
  - Prompt
  - LLM
  - 工程化
  - 应用开发
category: 应用工程
heroImage: ../../assets/blog-placeholder-1.jpg
---

大多数人接触 Prompt 工程的路径是：写一段 Prompt，跑一下看看效果，不满意再改。这种"一次性"的做法在探索阶段没问题，但一旦进入生产，就会遇到一堆麻烦：同一功能有三个版本的 Prompt 散落在代码库里，谁也不知道哪个是最新的；某个 Prompt 改了一个词，结果影响了另一个功能；新同事根本看不懂这些 Prompt 在做什么。

本文讲的是把 Prompt 从一次性脚本升级为工程化资产的完整方法。

## 一、Prompt 模板的核心问题：变量边界在哪里

Prompt 模板最基本的能力是变量替换——把 Prompt 里会变的部分抽出来，固定的部分作为模板。但这里有一个常被忽视的设计决策：**什么应该是变量，什么应该是固定文本**。

一个常见的错误是把变量切得太细：

```python
# 反模式：变量太多，模板失去可读性
template = "{role}是一个{expertise_level}的{domain}专家，请{action}用户提供的{input_type}，要求{requirement_1}、{requirement_2}，输出格式为{output_format}。"
```

这种模板表面上"灵活"，实际上：
- 变量之间的语义关系丢失了（role 和 expertise_level 是什么关系？）
- 调用方需要知道所有变量的含义，认知负担高
- 某个变量填错，整段话语义就乱了

**更好的做法**：把"稳定的逻辑结构"固定，把"业务输入"抽成变量：

```python
# 推荐：只有真正需要变化的部分是变量
template = """你是一位资深{domain}工程师，具备丰富的生产环境实战经验。

任务：对以下内容进行代码审查，重点关注安全性、性能和可维护性。

待审查代码：
{code}

输出要求：
1. 列出发现的问题（按严重程度排序）
2. 针对每个问题给出具体修改建议
3. 若代码整体无问题，明确说明"审查通过"
"""
```

这里只有 `domain` 和 `code` 是变量，其余的审查逻辑、输出格式全部固定在模板里。

## 二、模块化：把复杂 Prompt 拆成积木

对于复杂任务，单一模板很快会变得臃肿。更好的做法是把 Prompt 拆成可组合的模块：

```python
# 基础模块：角色定义
ROLE_MODULE = {
    "code_reviewer": "你是一位资深全栈工程师，专注代码质量和安全性审查。",
    "data_analyst": "你是一位数据分析师，擅长从数据中发现规律和异常。",
    "tech_writer": "你是一位技术文档工程师，善于把复杂概念写成清晰的中文文档。",
}

# 输出格式模块
OUTPUT_MODULE = {
    "structured_list": "请用 Markdown 有序列表输出，每个条目包含【问题】和【建议】两部分。",
    "json": "请严格以 JSON 格式输出，不要包含任何额外文字，格式为：{\"result\": [...]}",
    "prose": "请用连贯的中文段落输出，逻辑清晰，避免使用过多列表。",
}

# 约束模块
CONSTRAINT_MODULE = {
    "concise": "回答精简，不超过 300 字。",
    "exhaustive": "尽可能详尽，确保覆盖所有边界情况。",
    "cited": "每个论断附上代码位置或来源引用。",
}

def build_prompt(role: str, task: str, output: str, constraint: str, **kwargs) -> str:
    parts = [
        ROLE_MODULE[role],
        "",
        task.format(**kwargs),
        "",
        OUTPUT_MODULE[output],
        CONSTRAINT_MODULE[constraint],
    ]
    return "\n".join(parts)
```

调用时只需组合需要的模块：

```python
prompt = build_prompt(
    role="code_reviewer",
    task="请审查以下 Python 函数：\n\n```python\n{code}\n```",
    output="structured_list",
    constraint="cited",
    code=user_code,
)
```

这种积木式组合的优势是：修改某个模块（如调整输出格式要求），所有使用该模块的 Prompt 都会同步更新。

## 三、版本控制：Prompt 也需要 Git 管理

Prompt 是代码的一部分，不应该以字符串形式散落在业务代码里。推荐把 Prompt 模板单独存放：

```
prompts/
├── v1/
│   ├── code_review.txt
│   ├── summarization.txt
│   └── data_extraction.txt
├── v2/
│   ├── code_review.txt     # 升级版
│   └── summarization.txt
└── registry.py             # 统一注册表
```

`registry.py` 维护版本映射：

```python
from pathlib import Path

PROMPT_REGISTRY = {
    "code_review": "v2/code_review.txt",
    "summarization": "v2/summarization.txt",
    "data_extraction": "v1/data_extraction.txt",  # v1 还在用
}

def load_prompt(name: str, version: str = None) -> str:
    if version:
        path = Path(f"prompts/{version}/{name}.txt")
    else:
        path = Path("prompts") / PROMPT_REGISTRY[name]
    return path.read_text(encoding="utf-8")
```

**版本升级的建议流程**：
1. 新版本放在新目录，不覆盖旧版本
2. 用 A/B 测试验证新版本效果
3. 确认优于旧版本后，更新 `registry.py` 中的映射
4. 旧版本保留一段时间（方便回滚），再清理

## 四、Prompt 测试：像测代码一样测 Prompt

Prompt 的输出是自然语言，无法直接用 `assert output == expected_output` 来测试。但可以建立一套实用的测试体系：

### 4.1 格式测试（确定性高）

```python
import json
import re

def test_json_output_format(llm_client, prompt_template, test_input):
    """验证输出是合法 JSON"""
    response = llm_client.call(prompt_template.format(input=test_input))
    try:
        parsed = json.loads(response)
        assert "result" in parsed
        return True
    except json.JSONDecodeError:
        return False

def test_word_count(llm_client, prompt_template, test_input, max_words=300):
    """验证输出不超过字数限制"""
    response = llm_client.call(prompt_template.format(input=test_input))
    word_count = len(response)
    return word_count <= max_words
```

### 4.2 关键词测试（半确定性）

```python
def test_contains_required_sections(response: str, required_sections: list[str]) -> bool:
    """验证输出包含必要章节"""
    return all(section in response for section in required_sections)

# 用法：测试代码审查 Prompt 是否输出了"问题"和"建议"两个部分
test_contains_required_sections(response, ["问题", "建议"])
```

### 4.3 LLM 评估（质量评估）

用另一个 LLM 实例来评估输出质量，也叫"LLM-as-Judge"：

```python
JUDGE_PROMPT = """以下是一段 AI 生成的代码审查报告，请从 1-5 分评估其质量：

评分标准：
- 5分：问题定位准确，建议具体可操作，无幻觉内容
- 3分：有一定参考价值，但部分建议模糊
- 1分：内容与代码无关或严重错误

待评估内容：
{response}

请只输出一个数字（1-5），不要其他内容。"""

def llm_judge_score(response: str, judge_client) -> int:
    score_str = judge_client.call(JUDGE_PROMPT.format(response=response))
    return int(score_str.strip())
```

## 五、常用 Prompt 模板模式

以下是几个高频场景的模板参考，可以直接在项目里使用。

### 5.1 信息提取模板

```
你是一个信息提取助手。请从以下文本中提取指定字段，以 JSON 格式输出。

待提取文本：
{text}

需要提取的字段：
{fields_description}

输出要求：
- 严格 JSON 格式，不包含任何额外文字
- 如果某个字段在文本中不存在，对应值设为 null
- 不要推断或补全文本中没有的信息
```

### 5.2 文本摘要模板

```
请将以下内容概括成 {max_sentences} 句话的摘要，使用中文输出。

摘要要求：
- 保留原文的核心观点和关键数据
- 不添加原文中没有的信息
- 使用主动语态，语言简洁

原始内容：
{content}
```

### 5.3 代码生成模板

```
请根据以下需求描述，生成 {language} 代码：

需求：{requirement}

技术约束：
{constraints}

输出要求：
- 只输出代码块，不要解释
- 代码需要包含必要的错误处理
- 变量和函数名使用英文
```

### 5.4 对话上下文拼装模板

多轮对话时，系统提示和历史消息的组合方式会影响模型行为：

```python
def build_conversation_messages(
    system_prompt: str,
    history: list[dict],
    new_user_message: str,
    max_history_turns: int = 5,
) -> list[dict]:
    # 截断历史，避免 token 超限
    recent_history = history[-(max_history_turns * 2):]

    messages = recent_history + [{"role": "user", "content": new_user_message}]
    return messages
```

系统提示通过 `system` 参数传入（Claude API），而不是拼进 messages 里。关于系统提示和用户提示的边界选择，可以参考：[系统提示与用户提示的边界](/blog/llm-system-prompt-vs-user-prompt/)。

## 六、生产环境的 Prompt 管理建议

在生产中运行 Prompt 模板，还需要考虑几个工程层面的问题：

**监控与日志**：
记录每次调用的 Prompt 版本、输入输出和 token 消耗，便于排查问题和分析效果。

```python
import logging

def call_with_logging(client, prompt: str, prompt_name: str, prompt_version: str, **kwargs):
    logging.info(f"[PROMPT] name={prompt_name} version={prompt_version}")
    response = client.messages.create(
        model="claude-sonnet-4-6",
        messages=[{"role": "user", "content": prompt}],
        **kwargs,
    )
    logging.info(f"[USAGE] input_tokens={response.usage.input_tokens} output_tokens={response.usage.output_tokens}")
    return response
```

**Prompt 缓存**：
对于含有大量固定内容的 Prompt（如长系统提示），使用 Claude 的 prompt caching 功能，可以把输入 token 费用降低约 90%。关于 prompt caching 的详细配置，参考：[Prompt Caching 成本优化指南](/blog/prompt-caching-cost-optimization/)。

**A/B 测试框架**：
生产中不要一次性全量替换 Prompt，采用灰度方式：

```python
import random

def get_prompt_version(user_id: str, experiment_ratio: float = 0.1) -> str:
    """10% 的用户使用新版 Prompt"""
    hash_val = hash(user_id) % 100
    if hash_val < experiment_ratio * 100:
        return "v2"
    return "v1"
```

## 七、工具推荐

目前有一些专门的 Prompt 管理工具可以选用：

| 工具 | 适用场景 |
|------|----------|
| LangSmith | LangChain 生态，Prompt 版本管理 + 评估 |
| PromptLayer | 轻量级，支持多模型，有日志仪表盘 |
| Helicone | 开源，API 代理层，记录所有调用 |
| 自建 Git 仓库 | 简单场景，Prompt 文件纳入代码仓库 |

对于大多数中小型项目，"Git 管理 Prompt 文件 + 简单的日志记录"已经足够。不必一上来就引入重型工具。

## 相关阅读

- [系统提示与用户提示的边界：何时放哪里才正确](/blog/llm-system-prompt-vs-user-prompt/)
- [AI Agent Prompt Engineering 中文实战指南](/blog/agent-prompt-engineering-cn/)
- [Prompt Caching 成本优化指南](/blog/prompt-caching-cost-optimization/)
- [LLM 上下文工程：如何管理长对话](/blog/llm-context-engineering/)

把 Prompt 模板落地到生产还需要稳定的 API 支撑，[YoTradeApi](https://yotradeapi.com) 提供国内直连的 Claude / GPT / Gemini API 中转，支持 prompt caching 和流式输出，帮助你的 Prompt 工程体系稳定运行。
