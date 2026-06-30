---
title: 团队级 System Prompt 库的组织方式
description: 介绍如何在工程团队中构建可维护的 System Prompt 库，涵盖版本管理、目录结构、测试策略和多项目复用机制。
keywords:
  - system prompt 库
  - prompt 版本管理
  - 团队 AI 提示词管理
  - prompt 工程规范
  - LLM 系统提示词
  - prompt 组织最佳实践
pubDate: '2026-06-30'
updatedDate: '2026-06-30'
canonical: https://blog.yotradeapi.com/blog/ai-system-prompt-library/
tags:
  - Prompt工程
  - 团队协作
  - AI工程
  - 最佳实践
category: 应用工程
heroImage: ../../assets/blog-placeholder-1.jpg
---

随着 AI 功能逐渐从"试玩"进入"生产"，团队里维护 System Prompt 的痛点就开始涌现：某个同事把核心 prompt 存在自己的 Notion 里，测试环境和生产环境用的版本不一样，上次改了某个角色描述之后业务效果下降但没有人知道是哪次改动导致的。

本文讲的不是"怎么写好 prompt"，而是**怎么管好 prompt**——像管代码一样管好团队共用的 System Prompt。

## 一、为什么 Prompt 需要像代码一样管理

在大多数小团队的早期实践里，System Prompt 的存储方式大概有这几种：

- 直接硬编码在某个函数里，分散在多个服务里
- 放在数据库的一个配置表里，靠后台界面编辑
- 存在 Notion / Confluence，需要手动复制粘贴到代码
- 塞在环境变量 `SYSTEM_PROMPT=` 里，每个环境配置不同

这些方式的共同问题是**没有版本控制**、**没有变更追踪**、**没有测试门槛**。一个 prompt 被不知名的人悄悄改了一行，可能导致模型输出风格漂移，而你要排查到这是 prompt 的问题，往往需要花几个小时对比生产日志。

更关键的是，随着团队使用 AI 的场景增多，你很快会发现不同产品、不同模块需要的 prompt 之间有大量**可复用片段**——比如公司基调描述、格式约定、输出语言限制。如果每个 prompt 都是孤立的字符串，这些片段就会到处重复，改一处要改十处。

## 二、目录结构设计

一个工程上可维护的 Prompt 库，目录结构可以这样组织：

```
prompts/
├── base/                    # 基础片段，可被引用
│   ├── company-context.md   # 公司背景、产品简介
│   ├── output-format.md     # 通用输出格式约定
│   ├── language-policy.md   # 语言策略（中英文切换）
│   └── safety-guardrails.md # 安全边界约束
├── roles/                   # 不同角色的完整 system prompt
│   ├── customer-support.md
│   ├── code-reviewer.md
│   ├── content-writer.md
│   └── data-analyst.md
├── tasks/                   # 特定任务的 prompt（通常用于单次调用）
│   ├── summarize-meeting.md
│   ├── extract-entities.md
│   └── classify-intent.md
├── templates/               # 含 {{变量}} 占位符的模板
│   ├── onboarding-email.md
│   └── weekly-report.md
└── tests/                   # 每个 prompt 对应的测试用例
    ├── customer-support/
    │   ├── test-cases.json
    │   └── golden-outputs.json
    └── code-reviewer/
        └── test-cases.json
```

这个结构的核心设计原则：

1. **base/ 是积木**：不包含完整 prompt，只是可复用的片段，通过代码拼接使用
2. **roles/ 是完整的角色 prompt**：直接对应一个 AI 功能模块
3. **tasks/ 面向一次性任务**：这类 prompt 不维护对话历史，只关注单次输入输出
4. **tests/ 与 prompt 同级**：改了 prompt 必须跑对应的测试

## 三、版本管理策略

最简单的方式是把整个 `prompts/` 目录放进 Git 仓库（可以是主仓库，也可以是独立仓库）。

**Commit Message 规范建议**：

```
prompt(customer-support): 添加退款拒绝场景的引导话术
prompt(code-reviewer): 优化对 TypeScript 泛型的分析提示
prompt(base/safety): 增加对敏感词的处理约定
```

**分支策略**：

- `main`/`master`：生产环境使用的 prompt
- `staging`：预发布验证
- `dev`：开发测试

部署时，不同环境从对应分支读取 prompt，保证环境隔离。

**语义化版本号**（适合需要显式版本标注的场景）：

```markdown
---
version: 2.3.1
author: alice
last_updated: 2026-06-15
changelog:
  - 2.3.1: 修正退款金额计算规则的描述
  - 2.3.0: 新增多语言切换能力
  - 2.2.0: 增加对竞品品牌的处理规范
---

你是 {company_name} 的客服助手...
```

在 Markdown frontmatter 里加版本元信息，既能被代码解析，又对人类可读。

## 四、模板变量与组合机制

纯字符串 prompt 难以应对"同一个角色、不同配置"的需求。实际工程里至少需要两种组合机制：

**占位符替换**（适合少量变量）：

```python
import re

def load_prompt(path: str, variables: dict) -> str:
    with open(path) as f:
        template = f.read()
    # 替换 {{variable_name}} 格式的占位符
    for key, value in variables.items():
        template = template.replace(f"{{{{{key}}}}}", value)
    return template

# 使用
system_prompt = load_prompt(
    "prompts/roles/customer-support.md",
    variables={
        "company_name": "YoTradeApi",
        "product_name": "API 中转服务",
        "language": "中文"
    }
)
```

**片段组合**（适合动态拼装 prompt）：

```python
def build_system_prompt(*fragment_paths: str, variables: dict = None) -> str:
    parts = []
    for path in fragment_paths:
        with open(path) as f:
            parts.append(f.read())
    combined = "\n\n---\n\n".join(parts)
    if variables:
        for key, value in variables.items():
            combined = combined.replace(f"{{{{{key}}}}}", value)
    return combined

# 组合示例
system_prompt = build_system_prompt(
    "prompts/base/company-context.md",
    "prompts/base/output-format.md",
    "prompts/roles/content-writer.md",
    variables={"tone": "专业但不失亲切"}
)
```

这种方式的好处是 `company-context.md` 改了一次，所有用到它的角色都自动更新。

## 五、Prompt 测试策略

改了 prompt 没有测试就上线，是很多团队的痛点来源。测试不需要很复杂，最简单的形式是**Golden Set 测试**。

**测试用例结构**（`tests/customer-support/test-cases.json`）：

```json
[
  {
    "id": "refund-request-001",
    "description": "正常退款请求",
    "user_input": "我买的套餐想退款，能退吗？",
    "expected_behaviors": [
      "询问订单号或账户信息",
      "不直接承诺退款金额",
      "语气友好，不使用反问句"
    ],
    "forbidden_patterns": [
      "不能退",
      "不支持退款"
    ]
  }
]
```

**自动化测试脚本**：

```python
import json
import openai

def run_prompt_tests(prompt_path: str, test_cases_path: str) -> dict:
    with open(prompt_path) as f:
        system_prompt = f.read()
    with open(test_cases_path) as f:
        test_cases = json.load(f)
    
    results = {"passed": 0, "failed": 0, "failures": []}
    
    for case in test_cases:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": case["user_input"]}
            ],
            temperature=0
        )
        output = response.choices[0].message.content
        
        # 检查禁止模式
        failed = False
        for pattern in case.get("forbidden_patterns", []):
            if pattern in output:
                results["failures"].append({
                    "id": case["id"],
                    "reason": f"包含禁止词: {pattern}",
                    "output": output[:200]
                })
                failed = True
                break
        
        if not failed:
            results["passed"] += 1
        else:
            results["failed"] += 1
    
    return results
```

这个脚本可以挂在 CI/CD 流水线里，每次 PR 改了 `prompts/` 目录就自动跑，通过才允许合并。

关于更系统的 LLM 评估方法，可以参考 [LLM Eval Golden Set 建设指南](/blog/llm-eval-golden-set/)。

## 六、多项目复用方案

如果你的团队有多个项目（多个微服务、多个产品线）都需要用到同一套核心 prompt，可以考虑以下方案：

**方案 A：Git Submodule**

把 `prompts/` 作为独立 Git 仓库，各项目通过 submodule 引用：

```bash
git submodule add git@github.com:your-org/ai-prompts.git prompts
git submodule update --init
```

更新时：
```bash
cd prompts && git pull origin main && cd ..
git add prompts && git commit -m "chore: update prompt library to v2.4"
```

**方案 B：私有 npm/pip 包**

把 prompt 库打包成内部私有包，版本号语义化，各项目 `import` 后使用。适合 prompt 需要配合解析逻辑一起发布的场景。

**方案 C：内部 Prompt API 服务**

搭一个简单的 HTTP 服务，各项目按 `GET /prompts/{role}?version=2.3` 拉取 prompt。适合 prompt 需要动态下发（热更新）且不想每次改 prompt 都重新部署应用的场景。

**选型建议**：

- 团队 < 5 人、项目 < 3 个：Git Submodule 足够
- 中等规模团队：npm/pip 私有包，配合语义化版本
- 大型团队 / 需要热更新：独立 Prompt API 服务

## 七、常见反模式与避坑点

**反模式 1：把 prompt 放在数据库配置表里**

这让 prompt 脱离了代码审查流程。一个业务同学在后台界面改了两行，没有人知道，也没有测试——这是生产事故的温床。

**反模式 2：一个 prompt 文件几千行**

超长 prompt 很难维护和测试。超过 500 行的 prompt 应该考虑拆分成多个片段，通过代码组合。

**反模式 3：prompt 变量用字符串拼接**

```python
# ❌ 危险：用户输入可能含有 "请忽略以上所有指令"
system_prompt = f"你是助手，回答关于 {user_topic} 的问题。"

# ✅ 正确：用户输入走 user message，不混入 system prompt
system_prompt = "你是助手，回答用户提出的问题。"
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_input}
]
```

用户输入永远不应该进入 system prompt，这是 prompt injection 的经典入口。

**反模式 4：不记录 prompt 版本号到日志**

每次调用 LLM 时，把当前使用的 prompt 版本号记录到日志/可观测性系统里。排查问题时你会感谢自己做了这件事。

## 八、相关阅读

- [LLM Prompt 模板工程实战](/blog/llm-prompt-template-engineering/)
- [AI Prompt 版本管理策略](/blog/ai-prompt-versioning/)
- [LLM System Prompt 与 User Prompt 的本质区别](/blog/llm-system-prompt-vs-user-prompt/)
- [OpenAI Completions 与 Chat API 选型与差异](/blog/openai-completion-vs-chat-api/)

想在项目里快速接入高质量 LLM 能力，[YoTradeApi](https://yotradeapi.com) 提供 OpenAI、Claude、Gemini 全系模型的稳定中转，无需境外信用卡。
