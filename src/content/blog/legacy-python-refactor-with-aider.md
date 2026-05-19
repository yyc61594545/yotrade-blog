---
title: 用 Aider 重构 5 年遗留 Python 项目的完整记录
description: 真实案例：用 Aider Architect + Editor 模式重构一个 5 年遗留 Python 项目，从 Python 2 兼容到现代化栈的全过程与踩坑。
keywords:
- aider 重构 python
- python 遗留 重构
- aider 实战
- python 2 升级
- aider architect
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/legacy-python-refactor-with-aider/
tags:
- Aider
- Python
- 重构
- 实战案例
- 遗留代码
category: 实战案例
heroImage: ../../assets/blog-placeholder-2.jpg
---

# 用 Aider 重构 5 年遗留 Python 项目的完整记录

接手一个 5 年没大改的 Python 项目：18000 行、Python 3.6 时代的语法、几乎没有 type hint、测试覆盖 20%。本文记录用 Aider 把它升级到现代化的全过程。

## 一、项目初始状态

```
total: 18,237 lines
language: Python
python target: >=3.6 (代码假设兼容 3.6+)
type hints: ~5%
test coverage: 20%
formatter: 无（多种风格混用）
linter: pylint with 200+ warnings
dependencies: 12 包，5 个 outdated
最近 commit: 14 个月前
```

目标：

1. 升级到 Python 3.12
2. 添加 type hint 覆盖 80%+
3. 测试覆盖到 60%+
4. 用 ruff + black 统一风格
5. 依赖全部 update 到 latest stable

## 二、准备工作

```bash
$ pip install aider-chat
$ cd legacy-project
$ git checkout -b ai-refactor
```

`.aider.conf.yml`：

```yaml
model: openai/claude-sonnet-4-6
editor-model: openai/claude-sonnet-4-6
architect: true
weak-model: openai/claude-haiku-4-5

map-tokens: 4096          # 大项目放大 repomap

auto-commits: false       # 手动 commit，每步可 review
auto-test: true
test-cmd: pytest -x --tb=short

cache-prompts: true

show-model-warnings: true
```

`.aiderignore`：

```
.venv/
*.pyc
*.log
data/                     # 大数据文件
deprecated/               # 已废弃模块
docs/_build/
```

中转配置：

```bash
export OPENAI_API_BASE="https://yotradeapi.com/v1"
export OPENAI_API_KEY="sk-yo-..."
```

## 三、Step 1：先建保护网

不要直接动代码。**先把测试加厚**。

```
$ aider
> /add tests/
> 用 architect 模式分析当前测试覆盖。找出关键路径上没覆盖的函数，按优先级列出。
```

Architect（Opus）输出了一份 25 个函数的清单。我选了最关键 10 个：

```
> 为以下 10 个函数补充单元测试。每个函数 3–5 个 case（正常、边界、异常）。
> [10 个函数列表]
```

跑 1 小时，测试覆盖从 20% 提到 38%。

**Token 消耗**：约 600k（成本 $4）。

## 四、Step 2：依赖升级

```
> /run pip list --outdated
[输出 5 个 outdated 包]
> 一个一个升级：先 requests 6.x → 8.x。看 changelog 找 breaking changes，把代码同步改。
```

Aider 跑了 1 小时，处理了 requests、urllib3、tenacity 三个。剩下两个需要手工介入（一个有 enterprise 边缘 case，一个被弃用要换库）。

**关键纪律**：依赖升级**一次只动一个**。一次性升级多个，出错时不知道是谁的锅。

## 五、Step 3：Type Hints 增量加

直接说"全加 type hint"会让 Aider 跑爆。**按模块切**：

```
$ aider
> /add src/core/
> 为 src/core/ 下所有公开函数加 type hint。私有函数（_ 开头）暂时不加。
> 加完跑 mypy --strict src/core/ 确认通过。
```

Sonnet 4.6 处理这种结构化任务非常稳。一次跑通。

按这个流程把 12 个模块挨个处理完。**总耗时约 8 小时，分 3 天**。

**Token 消耗**：约 4M（成本 $25）。

## 六、Step 4：Python 版本升级

这一步预期最容易出问题。

```
> 升级到 Python 3.12 兼容。具体动作：
> 1. setup.py / pyproject.toml 把 python_requires 改成 ">=3.12"
> 2. 找出 typing 模块过时用法（如 Optional → |None）
> 3. 找出 collections.abc 没用的地方
> 4. f-string、walrus、match-case 优化机会
> 5. 跑 pytest 验证
```

Aider 跑了约 2 小时。最后跑 pytest 失败 3 个，自己看了一眼：

- 一个是 dict.keys() 在某处被当 list 用，加 `list(...)` 即可
- 一个是 mock 的版本变化导致测试假阳性
- 一个是 deprecation warning 被 strict 误判

我提示：

```
> 上面这 3 个错误，逐个分析根因，给修复方案
```

它一次给对方案，我审一遍合并。

## 七、Step 5：格式化与 lint

```
> 配置 ruff（替代 flake8 + pylint）和 black（formatter）。
> 在 pyproject.toml 加 [tool.ruff] 段。
> 跑 ruff check --fix . && black .
> 然后开始处理 ruff 剩余的报错。
```

ruff --fix 自动修了 60%。剩下 40% 让 Aider 处理：

```
> 跑 ruff check . 把剩余 warning 修掉。
> 不要 # noqa 隐藏，除非真的不可避免。
```

最终 ruff 0 warnings。

## 八、Step 6：测试覆盖再提升

```
> 当前覆盖 38%。目标 60%。
> 找出 src/ 下覆盖 < 50% 的模块，按代码量排序。
> 选前 5 个，每个补 5 个测试 case。
```

跑了 3 小时，覆盖到 62%。

**Token 消耗**：约 3M（成本 $18）。

## 九、Step 7：文档与 changelog

```
> 把这次重构的内容写一份 CHANGELOG.md。覆盖：
> - Python 版本升级到 3.12
> - 依赖升级清单
> - 添加完整 type hints（80%+ 覆盖）
> - 测试覆盖从 20% 提到 62%
> - 引入 ruff + black 统一风格
> - 移除已废弃的 X、Y、Z 模块
```

Sonnet 一次给出。微调即用。

## 十、整体总结

### 时间

| 阶段 | 时间 |
| --- | --- |
| 准备 + 测试加固 | 1 天 |
| 依赖升级 | 半天 |
| Type hints | 3 天（分批） |
| Python 3.12 升级 | 1 天 |
| 格式化 + lint | 半天 |
| 测试覆盖到 60% | 1 天 |
| 文档 + 收尾 | 半天 |
| **总计** | **7 个工作日** |

如果纯手工，**预计 4–6 周**。AI 辅助压缩到约 30%。

### 成本

| 阶段 | Token 估算 | 成本 |
| --- | --- | --- |
| 测试加固 | 600k | $4 |
| 依赖升级 | 300k | $2 |
| Type hints | 4M | $25 |
| Python 升级 | 800k | $6 |
| Lint | 500k | $3 |
| 覆盖率提升 | 3M | $18 |
| 收尾 | 200k | $1 |
| **总计** | **9.4M** | **~$60** |

## 十一、经验

### 1. Architect + Editor 双模型省一半

Opus 规划 + Sonnet 实施，质量不输纯 Opus，成本只有 40%。

### 2. 按模块切，每模块独立 commit

不要"一次性重构全项目"。Aider 在小范围任务上稳定，大范围容易漂移。

### 3. 测试是保护网

没有测试就重构 = 走钢丝不带安全绳。**第一步永远是补测试**。

### 4. auto-commits 关掉

Aider 默认每次成功就 commit。在长重构中关掉它，自己按"语义化提交"打包，commit 历史更清晰。

### 5. 复杂决策不能交给 AI

依赖选型、API 设计、性能 trade-off，**自己决定，让 AI 实施**。

### 6. 每步先跑测试

`auto-test: true` + `pytest -x` 让 AI 自己发现错误。比手工核对快 10 倍。

## 十二、不该用 AI 处理的

- ❌ 涉及业务逻辑的大改（理解错代价高）
- ❌ 涉及数据迁移（不可逆）
- ❌ 涉及安全（鉴权、加密）
- ❌ 性能关键路径（要 profile 不是猜）

## 十三、相关阅读

- [Aider 中文配置与最佳实践](/blog/aider-cn-config-guide/)
- [Claude Sonnet 4.6 与 Opus 4.7 怎么选](/blog/claude-sonnet-4-6-vs-opus-4-7/)
- [AI 编程代理成本控制实战](/blog/ai-coding-agent-cost-control/)
- [AI Agent Prompt Engineering 中文实战](/blog/agent-prompt-engineering-cn/)
- [用 AI 编程工具一周写一个 SaaS](/blog/saas-with-ai-coding-tools/)

需要 Architect + Editor 双模型同 Key 调用？[YoTradeApi](https://yotradeapi.com/register) 支持 Opus 4.7 + Sonnet 4.6 同一把 key，按上面 yaml 配置直接接入。
