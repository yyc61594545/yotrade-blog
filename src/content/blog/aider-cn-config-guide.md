---
title: Aider 中文配置与最佳实践
description: Aider AI 结对编程工具的国内 API 中转配置，含 Architect/Editor 双模型、git 工作流、repomap 与上下文优化技巧。
keywords:
- aider 国内
- aider api 配置
- aider 中转
- aider architect editor
- aider repomap
pubDate: '2026-05-18'
updatedDate: '2026-05-18'
canonical: https://blog.yotradeapi.com/blog/aider-cn-config-guide/
tags:
- Aider
- 命令行工具
- Git
- API 中转
- 配置教程
category: 工具配置
heroImage: ../../assets/blog-placeholder-1.jpg
---

Aider 走的是命令行结对编程路线：每次对话直接产出 git commit。它不需要 VSCode 插件、不依赖订阅，对国内开发者非常友好——前提是把 base_url 接对。

## 一、安装与基础配置

```bash
# 推荐用 pipx 隔离
python -m pip install --user pipx
pipx install aider-install
aider-install
```

或直接：

```bash
pip install -U aider-chat
```

确认安装：`aider --version` 显示版本号即可。

## 二、最小可用配置

Aider 通过环境变量或 `.aider.conf.yml` 读配置。最小用例：

```bash
export OPENAI_API_BASE="https://yotradeapi.com/v1"
export OPENAI_API_KEY="sk-your-yotrade-key"

cd your-project
aider --model openai/claude-sonnet-4-6
```

要点：

- Aider 用 LiteLLM 做底层，`openai/` 前缀告诉它走 OpenAI 兼容协议。
- 模型名要用网关支持的写法。
- 进入会话后 `/help` 看全部命令。

## 三、推荐配置文件

在项目根放一个 `.aider.conf.yml`：

```yaml
# 默认模型
model: openai/claude-sonnet-4-6
# Architect 模式时的 weak model
weak-model: openai/claude-haiku-4-5
# Architect 模式开关
architect: true
# 自动 git commit
auto-commits: true
# 但不自动推送
gitignore: true
# 显示 token 消耗
show-model-warnings: true
# 流式输出
stream: true
# 编辑器 diff 风格
edit-format: diff
# 中文提示
prompt-prefix: "请用中文回复。"
```

把 API Key 放 `.aider.conf.yml` 同目录的 `.env`：

```
OPENAI_API_BASE=https://yotradeapi.com/v1
OPENAI_API_KEY=sk-your-yotrade-key
```

并加进 `.gitignore`。

## 四、Architect / Editor 双模型策略

Aider 的「Architect 模式」会用两个模型：

- **Architect**：推理强，负责设计与分析（贵）
- **Editor**：写代码快，负责实际改 diff（便宜）

启用方法：

```bash
aider --architect \
  --model openai/claude-opus-4-7 \
  --editor-model openai/claude-sonnet-4-6
```

或在配置里：

```yaml
architect: true
model: openai/claude-opus-4-7
editor-model: openai/claude-sonnet-4-6
```

这种组合在国内中转下特别划算：Opus 处理一次复杂规划，Sonnet 干粗活，单任务能省 30–50% 而效果不输。

## 五、Repomap：让 Aider 看懂整个仓库

Aider 默认只把你 `/add` 的文件加进上下文。但通过 **repomap**，它能用很少的 token 让 LLM 大致理解整个项目结构。

控制 repomap 大小：

```bash
aider --map-tokens 2048   # 默认 1024，大项目可以拉到 4096
```

如果 repomap 卡住或耗时太久：

```bash
aider --no-auto-commits --map-tokens 0   # 完全禁用
```

实战建议：

- 小项目（< 50 文件）：repomap 0，靠 `/add` 显式加文件
- 中等项目：默认 1024 够用
- 大型 monorepo：用 `.aiderignore` 排除 node_modules、dist、生成文件后再开 2048

## 六、命令速查

| 命令 | 作用 |
| --- | --- |
| `/add path` | 把文件加进上下文 |
| `/drop path` | 移出上下文 |
| `/ls` | 看当前上下文里的文件 |
| `/diff` | 看 Aider 最近改了什么 |
| `/undo` | 撤销最后一次 commit |
| `/commit` | 手动 commit |
| `/test cmd` | 跑测试，失败自动让 LLM 修 |
| `/run cmd` | 跑命令，把输出加进上下文 |
| `/tokens` | 看当前上下文的 token 数 |
| `/clear` | 清空对话（保留文件） |
| `/reset` | 完全重置 |
| `/web url` | 抓网页加进上下文 |
| `/model name` | 切模型 |
| `/copy` | 复制最后一次 LLM 回复 |
| `/exit` | 退出 |

## 七、git 工作流

Aider 默认每次成功修改都 `git commit -m "aider: ..."`。这是它最大的卖点：

```
* aider: 添加 retry 装饰器到 fetch_data
* aider: 修复 type hint，统一返回 dict
* (上一手提交)
```

回滚一步用 `/undo` 即可，相当于 `git reset --hard HEAD~1`。

如果你不想自动 commit：

```yaml
auto-commits: false
dirty-commits: false
```

然后手动 `git add` + `git commit`。

## 八、流式 + 长上下文的稳定性

国内中转下 Aider 长任务最容易遇到的问题：

1. **流式中断**：表现为 LLM 回复到一半卡住。Aider 会重试，但会消耗双倍 token。  
   缓解：换模型或在网关侧开 keep-alive；如果连续断三次，重启 aider。
2. **大文件 diff 过长**：超过 8k tokens 的 diff，LLM 经常生成无效格式。  
   缓解：`--edit-format whole`（整文件替换），更稳但更贵。
3. **repomap 失效**：仓库里有大量二进制或自动生成文件。  
   缓解：完善 `.aiderignore`。

## 九、配合 Lint / Test 的"闭环"用法

Aider 真正强大的地方是闭环：

```bash
aider --auto-test --test-cmd "npm test" --auto-lint --lint-cmd "npm run lint"
```

每次它改完文件，会自动跑 test 和 lint，失败的话**把错误信息加进上下文让 LLM 自己修**。我用这个模式重构 100 多文件的 Node 项目，模型大概会出错 2–3 次，但都能在三轮内自我修复。

## 十、Aider 与 Cline / Claude Code 的差异

| 维度 | Aider | Cline | Claude Code |
| --- | --- | --- | --- |
| 界面 | CLI | VSCode | CLI |
| 改文件方式 | git commit | 直接保存 | Edit 工具 |
| 自动 commit | 强 | 无 | 无 |
| Plan/Architect | Architect 模式 | Plan/Act | Plan Mode |
| 上下文管理 | repomap + /add | @-mentions | Auto + /context |
| 适合规模 | 中小型仓库 | 单任务 | 长任务 |

如果你的工作流是 "git-first" 的——所有改动必须可回滚、必须有清晰提交历史——Aider 是最自然的选择。

## 十一、相关阅读

- [Cursor API 中转怎么选：2026 实用清单](/blog/2026-05-15-cursor-api-relay-recommendation-2026/)
- [Claude Code 镜像国内配置完整指南](/blog/claude-code-mirror-cn-setup/)
- [Cline 国内 API 配置详解](/blog/cline-cn-api-setup/)
- [OpenAI SDK base_url 国内配置实战](/blog/openai-sdk-base-url-cn/)

需要支持 Aider Architect 模式（双模型）的中转？[YoTradeApi](https://yotradeapi.com) 提供 Claude Sonnet 4.6 + Opus 4.7 + Haiku 4.5 同 Key 调用，配置 base_url 直接接入。
